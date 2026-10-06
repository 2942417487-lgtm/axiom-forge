"""Operator-only Canon review/approval and atomic creation of a Git branch.

Not a research tool. Local OS access is the trust boundary, not human identity
authentication. Approval MAC detects tampering by actors without the host key.
"""

import copy
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import tempfile
from pathlib import Path

from .snapshots import build_snapshot, utc_now
from .tools.storage import Workspace, check_links, read_bounded, safe_relative, strict_json
from .validation import (DataError, KNOWLEDGE_DIRECTORIES, SchemaStore, canonical_bytes,
                         collect_world, digest, record_schema, validate_dataset, validate_task)


def document(path):
    data = strict_json(read_bounded(path))
    if not isinstance(data, dict): raise DataError("Expected a JSON object")
    return data


def render_review(task, bundle, bundle_hash):
    markdown = "# Canon 变更审查包\n\n" + f"内容 SHA-256：`{bundle_hash}`\n\n"
    markdown += "批准整份变更包，包括新 Evidence 和审批记录。批准不证明现实 FACT；无自动推送或合并。\n\n"
    sections = [("最终提案、来源、假设、不确定性与反例", task["proposed_changes"]),
                ("Red Team 与综合（包括未解决问题）", {"redteam_results": task["redteam_results"], "synthesis": task["synthesis"]}),
                ("文件前后内容（null 表示新增或删除）", bundle["files"])]
    for title, content in sections:
        raw = json.dumps(content, ensure_ascii=False, indent=2)
        fence = "`" * max(3, 1 + max((len(x) for x in re.findall(r"`+", raw)), default=0))
        markdown += f"## {title}\n\n{fence}json\n{raw}\n{fence}\n\n"
    return markdown.encode("utf-8")


class CanonHost:
    def __init__(self, repo):
        self.repo = Path(repo).absolute()
        check_links(self.repo)
        self.schemas = SchemaStore(self.repo / "schemas")
        self.key_path = self.repo / ".env.approval"

    def git(self, *args, raw=None, index=None):
        # No shell, external diff, prompts, inherited GIT_* redirects, API secrets,
        # global config, fsmonitor, signing programs or user hooks.
        env = {key: value for key, value in os.environ.items() if key.upper() in
               {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "USERPROFILE"}}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
        if index is not None: env["GIT_INDEX_FILE"] = str(index)
        hooks = self.repo / ".cache/empty-hooks"
        check_links(hooks)
        hooks.mkdir(parents=True, exist_ok=True)
        # Use a new empty directory for every call so no pre-existing hook executes.
        with tempfile.TemporaryDirectory(dir=hooks) as empty_hooks:
            try:
                result = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.autocrlf=false",
                    "-c", "commit.gpgsign=false", "-c", "core.hooksPath=" + empty_hooks, *args],
                    cwd=self.repo, env=env, input=raw, capture_output=True, timeout=30, shell=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise DataError("Git host command unavailable or timed out") from exc
        if result.returncode: raise DataError("Git host command failed: " + args[0])
        if len(result.stdout) > 2 * 1024 * 1024: raise DataError("Git response exceeds size limit")
        return result.stdout

    def head(self):
        sha = self.git("rev-parse", "--verify", "HEAD").decode("ascii").strip()
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha): raise DataError("Invalid Git object ID")
        return sha

    def base_ref(self):
        ref = self.git("symbolic-ref", "-q", "HEAD").decode("ascii").strip()
        if not re.fullmatch(r"refs/heads/[A-Za-z0-9_./-]+", ref):
            raise DataError("Canon review requires a named local branch")
        return ref

    def git_world(self, sha):
        files = {}
        for item in self.git("ls-tree", "-r", "-z", sha, "--", "world").split(b"\0"):
            if not item: continue
            info, raw_path = item.split(b"\t", 1)
            path = raw_path.decode("utf-8")
            if path != "world/world.json" and not any(path.startswith(d + "/") and path.endswith(".json")
                                                        for d in KNOWLEDGE_DIRECTORIES): continue
            record_schema(path)
            mode, kind, oid = info.decode("ascii").split()
            if mode != "100644" or kind != "blob": raise DataError("Knowledge must be regular Git blobs")
            files[path] = strict_json(self.git("cat-file", "blob", oid))
        validate_dataset(files, self.schemas)
        return files

    def check_base(self, sha, snapshot):
        if self.head() != sha: raise DataError("Git HEAD changed; restart/review against the current base")
        for record in snapshot["files"]: read_bounded(self.repo / safe_relative(record["path"]))
        committed = build_snapshot(self.git_world(sha), self.schemas)
        live = build_snapshot(self.live_world(), self.schemas)
        if any(s["canon_version"] != snapshot["canon_version"] for s in (committed, live)):
            raise DataError("Canon differs from the reviewed snapshot or committed Git base")

    def live_world(self):
        for folder in KNOWLEDGE_DIRECTORIES:
            directory = self.repo / folder
            check_links(directory)
            for path in directory.rglob("*.json"): read_bounded(path)
        read_bounded(self.repo / "world/world.json")
        return collect_world(self.repo, self.schemas)

    def init_key(self):
        # Key stays in a separately ignored .env file, never in a review package.
        if self.git("ls-files", "-z", "--", ".env.approval"):
            raise DataError("Approval credentials cannot be a tracked file")
        self.git("check-ignore", "--no-index", ".env.approval")
        Workspace(self.repo).write(".env.approval", b"AXIOM_APPROVAL_KEY=" + secrets.token_hex(32).encode("ascii") + b"\n")
        if os.name != "nt": self.key_path.chmod(0o600)
        return {"status": "initialized", "key_file": str(self.key_path), "key_printed": False}

    def key(self):
        raw = read_bounded(self.key_path, limit=128)
        if not re.fullmatch(rb"AXIOM_APPROVAL_KEY=[0-9a-f]{64}\r?\n?", raw):
            raise DataError("Initialize the dedicated host approval key with canon init-approval")
        return bytes.fromhex(raw.decode("ascii").strip().split("=", 1)[1])

    def task(self, path):
        path = Path(path).absolute()
        task = document(path)
        expected = self.repo / ".cache/tasks" / task["task_id"] / "waiting.json"
        if path != expected: raise DataError("Approval accepts only the host's waiting TaskState")
        validate_task(task, self.schemas)
        if (task["lifecycle"] != "WAITING_APPROVAL" or task["approval_status"] != "pending"
                or not task["proposed_changes"] or task["synthesis"] is None
                or task["metadata"].get("task_manager") != "1.0"
                or len(task["runs"]) != 1 or task["runs"][0]["status"] != "completed"):
            raise DataError("Only a completed research task with pending final proposals can be reviewed")
        if task["proposed_changes"] != task["synthesis"]["proposed_changes"]:
            raise DataError("Only the exact final synthesis proposals can be applied")
        if any(c["approval"]["status"] != "pending" for c in task["proposed_changes"]):
            raise DataError("Model output cannot authorize Canon approval")
        for artifact in task["artifacts"]:
            value = document(self.repo / safe_relative(artifact["path"]))
            if digest(value) != artifact["sha256"]: raise DataError("Task artifact content changed")
        return task

    def projected(self, task):
        before = {r["path"]: copy.deepcopy(r["data"]) for r in task["canon_snapshot"]["files"]}
        after = copy.deepcopy(before)
        for result in task["research_results"]:
            for evidence in result["evidence"]:
                after[f"world/evidence/{evidence['evidence_id']}.json"] = copy.deepcopy(evidence)
        for change in task["proposed_changes"]:
            target = change["target_entity_id"]
            if change["before"] is not None:
                original = next(p for p, data in after.items() if data.get("entity_id") == target)
                del after[original]
            if change["after"] is not None:
                entry = change["after"]
                directory = next(d for d, (_, domain) in KNOWLEDGE_DIRECTORIES.items() if domain == entry["domain"])
                after[f"{directory}/{target}.json"] = copy.deepcopy(entry)
        validate_dataset(after, self.schemas)
        return before, after

    def prepare(self, task_path):
        task = self.task(task_path)
        base = task["metadata"]["base_git_sha"]
        self.check_base(base, task["canon_snapshot"])
        before, after = self.projected(task)
        # This decision template is itself part of the reviewed content. It is only
        # published after approval; reviewer/time/MAC are stored in Git message.
        decision_id = "DEC-" + task["runs"][0]["run_id"].removeprefix("RUN-")
        decision = {"entity_id": decision_id, "domain": "decisions", "title": "Canon 人工审批记录：" + task["task_id"],
            "statement": "本提交的 Canon 变更已由本地操作者批准。批准详情与审查包哈希见 Git 提交消息；批准不证明现实科学事实。",
            "status": "Soft Canon", "source": {"kind": "user", "description": "宿主 CLI 人工批准后记录；研究模型无审批权限。"},
            "dependencies": [], "implications": ["proposal_sha256=" + digest(task["proposed_changes"])],
            "conflicts": [], "evidence_ids": [], "claims": [], "last_updated": task["runs"][0]["finished_at"]}
        decision_path = f"world/decisions/{decision_id}.json"
        if decision_path in after: raise DataError("Decision identity already exists")
        after[decision_path] = decision
        validate_dataset(after, self.schemas)
        bundle = {"schema_version": "1.0", **{k: task[k] for k in ("world_id", "task_id", "canon_version")},
            "run_id": task["runs"][0]["run_id"], "task_path": Path(task_path).absolute().relative_to(self.repo).as_posix(),
            "task_sha256": digest(task), "base_git_sha": base, "base_ref": self.base_ref(),
            "branch": "canon/" + task["runs"][0]["run_id"], "decision_id": decision_id,
            "proposal_hashes": {c["proposal_id"]: digest(c) for c in task["proposed_changes"]},
            "files": [{"path": p, "before": before.get(p), "after": after.get(p)}
                      for p in sorted(set(before) | set(after)) if before.get(p) != after.get(p)],
            "created_at": task["runs"][0]["finished_at"]}
        self.schemas.validate("canon_review", bundle)
        bundle_hash = digest(bundle)
        workspace = Workspace(self.repo / ".cache/canon-reviews" / bundle_hash)
        if workspace.path("bundle.json").exists():
            if document(workspace.path("bundle.json")) != bundle: raise DataError("Existing review differs")
        else:
            workspace.write_json("bundle.json", bundle)
        markdown = render_review(task, bundle, bundle_hash)
        if workspace.path("review.md").exists():
            if workspace.read("review.md") != markdown: raise DataError("Human-readable review was modified")
        else: workspace.write("review.md", markdown)
        return {"bundle": str(workspace.path("bundle.json")), "review": str(workspace.path("review.md")), "sha256": bundle_hash}

    def reviewed(self, bundle_path):
        bundle = document(bundle_path)
        self.schemas.validate("canon_review", bundle)
        task = self.task(self.repo / safe_relative(bundle["task_path"]))
        if digest(task) != bundle["task_sha256"]: raise DataError("Reviewed task content changed")
        expected = self.prepare(self.repo / safe_relative(bundle["task_path"]))
        if expected["sha256"] != digest(bundle): raise DataError("Review differs from the task's projected Canon")
        if Path(bundle_path).absolute() != Path(expected["bundle"]): raise DataError("Review must use the host content-addressed package")
        return bundle, task, Workspace(Path(bundle_path).absolute().parent)

    def decide(self, bundle_path, reviewer, confirmed_hash, *, status="approved"):
        bundle, task, workspace = self.reviewed(bundle_path)
        if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 120 or any(ord(c) < 32 for c in reviewer):
            raise DataError("A short operator name is required")
        if confirmed_hash != digest(bundle): raise DataError("Operator must confirm the exact review SHA-256")
        if status not in ("approved", "rejected"): raise DataError("Unknown human decision")
        receipt = {"schema_version": "1.0", "status": status, "reviewer": reviewer,
            "reviewed_at": utc_now(), "decision_id": bundle["decision_id"], "bundle_sha256": digest(bundle),
            "task_sha256": digest(task), "proposal_hashes": bundle["proposal_hashes"]}
        receipt["mac_sha256"] = hmac.new(self.key(), canonical_bytes(receipt), hashlib.sha256).hexdigest()
        self.schemas.validate("canon_approval", receipt)
        workspace.write_json("approval.json", receipt)
        if status == "rejected":
            rejected = copy.deepcopy(task)
            rejected.update(lifecycle="SYNTHESIS", approval_status="rejected", final_result=task["synthesis"]["summary"])
            validate_task(rejected, self.schemas)
            Workspace(self.repo / ".cache/tasks" / task["task_id"]).write_json("rejected.json", rejected)
        return {"status": status, "approval": str(workspace.path("approval.json")), "bundle_sha256": digest(bundle)}

    def apply(self, bundle_path):
        bundle, task, workspace = self.reviewed(bundle_path)
        approval = document(workspace.path("approval.json"))
        self.schemas.validate("canon_approval", approval)
        signed = {k: v for k, v in approval.items() if k != "mac_sha256"}
        if (approval["status"] != "approved" or approval["bundle_sha256"] != digest(bundle)
                or approval["task_sha256"] != digest(task) or approval["proposal_hashes"] != bundle["proposal_hashes"]
                or approval["decision_id"] != bundle["decision_id"]
                or not hmac.compare_digest(approval["mac_sha256"], hmac.new(self.key(), canonical_bytes(signed), hashlib.sha256).hexdigest())):
            raise DataError("Missing, rejected, tampered or mismatched host approval")
        if workspace.path("commit-prepared.json").exists():
            raise DataError("Apply already attempted; inspect the prepared receipt/branch, no automatic retry")
        before, after = self.projected(task)
        for change in bundle["files"]:
            path = safe_relative(change["path"]).as_posix()
            record_schema(path)
            if before.get(path) != change["before"]: raise DataError("Reviewed before content changed")
            if change["after"] is None: after.pop(path, None)
            else: after[path] = copy.deepcopy(change["after"])
        new_snapshot = build_snapshot(after, self.schemas)
        with tempfile.TemporaryDirectory(dir=workspace.root) as temporary:
            index = Path(temporary) / "index"
            self.git("read-tree", bundle["base_git_sha"], index=index)
            for change in bundle["files"]:
                path = change["path"]
                if change["after"] is None:
                    self.git("update-index", "--force-remove", "--", path, index=index)
                else:
                    oid = self.git("hash-object", "-w", "--stdin", raw=canonical_bytes(change["after"]) + b"\n").decode("ascii").strip()
                    self.git("update-index", "--add", "--cacheinfo", "100644," + oid + "," + path, index=index)
            tree = self.git("write-tree", index=index).decode("ascii").strip()
            message = "Apply human-approved Canon " + task["task_id"] + "\n\n" + canonical_bytes(approval).decode("utf-8") + "\n"
            commit = self.git("commit-tree", tree, "-p", bundle["base_git_sha"], raw=message.encode("utf-8")).decode("ascii").strip()
        if build_snapshot(self.git_world(commit), self.schemas)["canon_version"] != new_snapshot["canon_version"]:
            raise DataError("Prepared Git tree differs from validated Canon")
        control = {"schema_version": "1.0", "task_sha256": digest(task), "approval": approval,
            "branch": bundle["branch"], "base_git_sha": bundle["base_git_sha"], "commit_sha": commit,
            "new_canon_version": new_snapshot["canon_version"]}
        self.schemas.validate("canon_commit", control)
        committed = copy.deepcopy(task)
        committed.update(lifecycle="COMMITTED", approval_status="approved", final_result=commit, canon_commit=control)
        validate_task(committed, self.schemas)
        workspace.write_json("commit-prepared.json", committed)
        # Validate again immediately before publishing. CAS verifies the named base
        # branch and atomically creates a previously nonexistent Canon branch.
        self.check_base(bundle["base_git_sha"], task["canon_snapshot"])
        if self.base_ref() != bundle["base_ref"]: raise DataError("Current base branch changed")
        transaction = f"start\nverify {bundle['base_ref']} {bundle['base_git_sha']}\ncreate refs/heads/{bundle['branch']} {commit}\nprepare\ncommit\n"
        self.git("update-ref", "--stdin", raw=transaction.encode("ascii"))
        path = Workspace(self.repo / ".cache/tasks" / task["task_id"]).write_json("committed.json", committed)
        return {"status": "committed", "branch": bundle["branch"], "commit_sha": commit,
                "state_path": str(path), "new_canon_version": new_snapshot["canon_version"]}
