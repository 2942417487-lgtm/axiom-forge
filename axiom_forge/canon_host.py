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
from contextlib import contextmanager
from pathlib import Path

from .git_host import git
from .workspaces import require_world
from .snapshots import build_snapshot, utc_now
from .journal import TaskJournal, publish
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
        self.world = require_world(repo)
        self.repo = self.world.root
        check_links(self.repo)
        self.schemas = self.world.schemas
        self.key_path = self.world.key_path
        self._journals = {}

    def git(self, *args, raw=None, index=None):
        self.world.validate_current()
        return git(self.repo, *args, raw=raw, index=index)

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
        # Explicit operator action, using host-local storage outside world Git.
        require_world(self.world)
        Workspace(self.key_path.parent).write(".env.approval",
            b"AXIOM_APPROVAL_KEY=" + secrets.token_hex(32).encode("ascii") + b"\n")
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
        require_world(self.world)
        self.world.validate_world(task["world_id"])
        self.world.validate_binding(task["metadata"].get("workspace_binding"))
        expected = self.repo / ".axiom/local/tasks" / task["task_id"] / "waiting.json"
        if path != expected: raise DataError("Approval accepts only the host's waiting TaskState")
        validate_task(task, self.schemas)
        if (task["lifecycle"] != "WAITING_APPROVAL" or task["approval_status"] != "pending"
                or not task["proposed_changes"] or task["synthesis"] is None
                or task["metadata"].get("task_manager") != "2.0"
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

    def prepare(self, task_path, *, verify_base=True, base_ref=None):
        task = self.task(task_path)
        base = task["metadata"]["base_git_sha"]
        if verify_base: self.check_base(base, task["canon_snapshot"])
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
        bundle = {"schema_version": "1.1", "workspace_binding": self.world.binding, **{k: task[k] for k in ("world_id", "task_id", "canon_version")},
            "run_id": task["runs"][0]["run_id"], "task_path": Path(task_path).absolute().relative_to(self.repo).as_posix(),
            "task_sha256": digest(task), "base_git_sha": base, "base_ref": base_ref or self.base_ref(),
            "branch": "canon/" + task["runs"][0]["run_id"], "decision_id": decision_id,
            "proposal_hashes": {c["proposal_id"]: digest(c) for c in task["proposed_changes"]},
            "files": [{"path": p, "before": before.get(p), "after": after.get(p)}
                      for p in sorted(set(before) | set(after)) if before.get(p) != after.get(p)],
            "created_at": task["runs"][0]["finished_at"]}
        self.schemas.validate("canon_review", bundle)
        bundle_hash = digest(bundle)
        workspace = Workspace(self.repo / ".axiom/local/canon-reviews" / bundle_hash)
        if workspace.path("bundle.json").exists():
            if document(workspace.path("bundle.json")) != bundle: raise DataError("Existing review differs")
        else:
            workspace.write_json("bundle.json", bundle)
        markdown = render_review(task, bundle, bundle_hash)
        if workspace.path("review.md").exists():
            if workspace.read("review.md") != markdown: raise DataError("Human-readable review was modified")
        else: workspace.write("review.md", markdown)
        return {"bundle": str(workspace.path("bundle.json")), "review": str(workspace.path("review.md")), "sha256": bundle_hash}

    def reviewed(self, bundle_path, *, verify_base=True):
        bundle = document(bundle_path)
        self.schemas.validate("canon_review", bundle)
        self.world.validate_binding(bundle.get("workspace_binding"))
        task = self.task(self.repo / safe_relative(bundle["task_path"]))
        if digest(task) != bundle["task_sha256"]: raise DataError("Reviewed task content changed")
        expected = self.prepare(self.repo / safe_relative(bundle["task_path"]),
                                verify_base=verify_base, base_ref=bundle['base_ref'])
        if expected["sha256"] != digest(bundle): raise DataError("Review differs from the task's projected Canon")
        if Path(bundle_path).absolute() != Path(expected["bundle"]): raise DataError("Review must use the host content-addressed package")
        return bundle, task, Workspace(Path(bundle_path).absolute().parent)

    def decide(self, bundle_path, reviewer, confirmed_hash, *, status="approved"):
        with self.operator(bundle_path) as journal:
            return self._decide(bundle_path, reviewer, confirmed_hash, status=status, journal=journal)

    def _decide(self, bundle_path, reviewer, confirmed_hash, *, status, journal):
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
        self.record_decision(journal, task, workspace, receipt)
        return {"status": status, "approval": str(workspace.path("approval.json")), "bundle_sha256": digest(bundle)}

    @contextmanager
    def operator(self, bundle_path):
        bundle = document(bundle_path)
        self.schemas.validate('canon_review', bundle)
        journal = self._journals.setdefault(bundle['task_id'], TaskJournal(self.world, bundle['task_id']))
        with journal.lock():
            # Legacy Phase 10 packages stay usable, without fabricated past events.
            records = journal.read()
            if not records:
                task = self.task(self.repo / safe_relative(bundle['task_path']))
                if task['metadata'].get('task_manager') in ('1.1', '2.0'): raise DataError('Phase 11 task journal is missing')
            yield journal if records else None

    def record_decision(self, journal, task, workspace, receipt):
        status = receipt['status']
        if status == "rejected":
            rejected = copy.deepcopy(task)
            rejected.update(lifecycle="SYNTHESIS", approval_status="rejected", final_result=task["synthesis"]["summary"])
            validate_task(rejected, self.schemas)
            publish(Workspace(self.repo / '.axiom/local/tasks' / task['task_id']), 'rejected.json', rejected)
        if journal:
            kind = 'HumanApproved' if status == 'approved' else 'HumanRejected'
            data = {'approval_path': workspace.path('approval.json').relative_to(self.repo).as_posix(),
                    'approval_sha256': digest(receipt), 'bundle_sha256': receipt['bundle_sha256']}
            existing = [e for e in journal.events() if e['event_type'] == kind]
            if existing:
                if len(existing) != 1 or existing[0]['data'] != data: raise DataError('Approval audit differs')
                return
            latest = journal.latest()
            if latest['status'] != 'waiting_approval' or digest(latest['task_state']) != digest(task):
                raise DataError('Approval must bind the waiting checkpoint')
            journal.append(rejected if status == 'rejected' else task, latest['control'],
                           'rejected' if status == 'rejected' else 'approved', [(kind, data)])

    def verified_approval(self, bundle, task, workspace):
        approval = document(workspace.path('approval.json'))
        self.schemas.validate('canon_approval', approval)
        signed = {k: v for k, v in approval.items() if k != 'mac_sha256'}
        if (approval['bundle_sha256'] != digest(bundle) or approval['task_sha256'] != digest(task)
                or approval['proposal_hashes'] != bundle['proposal_hashes'] or approval['decision_id'] != bundle['decision_id']
                or not hmac.compare_digest(approval['mac_sha256'], hmac.new(self.key(), canonical_bytes(signed), hashlib.sha256).hexdigest())):
            raise DataError('Tampered or mismatched host approval')
        return approval

    def apply(self, bundle_path):
        with self.operator(bundle_path) as journal:
            return self._apply(bundle_path, journal)

    def _apply(self, bundle_path, journal):
        bundle, task, workspace = self.reviewed(bundle_path)
        approval = self.verified_approval(bundle, task, workspace)
        if approval['status'] != 'approved': raise DataError('Rejected approval cannot apply Canon')
        self.record_decision(journal, task, workspace, approval)
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
        self.audit_prepared(journal, task, committed, workspace)
        # Validate again immediately before publishing. CAS verifies the named base
        # branch and atomically creates a previously nonexistent Canon branch.
        self.check_base(bundle["base_git_sha"], task["canon_snapshot"])
        if self.base_ref() != bundle["base_ref"]: raise DataError("Current base branch changed")
        transaction = f"start\nverify {bundle['base_ref']} {bundle['base_git_sha']}\ncreate refs/heads/{bundle['branch']} {commit}\nprepare\ncommit\n"
        self.git("update-ref", "--stdin", raw=transaction.encode("ascii"))
        path = Workspace(self.repo / ".axiom/local/tasks" / task["task_id"]).write_json("committed.json", committed)
        self.audit_committed(journal, committed)
        return {"status": "committed", "branch": bundle["branch"], "commit_sha": commit,
                "state_path": str(path), "new_canon_version": new_snapshot["canon_version"]}

    def audit_prepared(self, journal, task, committed, workspace):
        if journal is None: return
        data = {'prepared_path': workspace.path('commit-prepared.json').relative_to(self.repo).as_posix(),
                'prepared_sha256': digest(committed), 'commit_sha': committed['canon_commit']['commit_sha']}
        events = [e for e in journal.events() if e['event_type'] == 'CanonPrepared']
        if events:
            if len(events) != 1 or events[0]['data'] != data: raise DataError('Prepared commit audit differs')
            return
        latest = journal.latest()
        if latest['status'] != 'approved': raise DataError('Commit preparation requires recorded approval')
        journal.append(task, latest['control'], 'applying', [('CanonPrepared', data)])

    def audit_committed(self, journal, committed):
        if journal is None: return
        latest = journal.latest()
        if latest['status'] == 'committed':
            if latest['task_state'] != committed: raise DataError('Committed checkpoint differs')
            return
        if latest['status'] != 'applying': raise DataError('Commit requires prepared checkpoint')
        journal.append(committed, latest['control'], 'committed', [
            ('CanonCommitted', {'commit_sha': committed['canon_commit']['commit_sha'],
                                'branch': committed['canon_commit']['branch']}),
            ('LifecycleChanged', {'lifecycle': 'COMMITTED'})])

    def recover(self, bundle_path):
        """Reconcile signed approval/prepared Git commit, without research or reapproval."""
        with self.operator(bundle_path) as journal:
            bundle, task, workspace = self.reviewed(bundle_path, verify_base=False)
            approval = self.verified_approval(bundle, task, workspace)
            self.record_decision(journal, task, workspace, approval)
            if approval['status'] == 'rejected': return {'status': 'rejected', 'task_id': task['task_id']}
            if not workspace.path('commit-prepared.json').exists():
                return {'status': 'approved', 'task_id': task['task_id'], 'next_action': 'canon apply --bundle <same bundle>'}
            committed = document(workspace.path('commit-prepared.json'))
            validate_task(committed, self.schemas)
            control = committed.get('canon_commit', {})
            commit = control.get('commit_sha')
            expected = copy.deepcopy(task)
            expected.update(lifecycle='COMMITTED', approval_status='approved', final_result=commit, canon_commit=control)
            if (committed != expected or control.get('approval') != approval or control.get('branch') != bundle['branch']
                    or control.get('base_git_sha') != bundle['base_git_sha'] or control.get('task_sha256') != digest(task)):
                raise DataError('Prepared commit differs from the signed review')
            parents = self.git('rev-list', '--parents', '-n', '1', commit).decode().strip().split()
            if parents != [commit, bundle['base_git_sha']]: raise DataError('Prepared commit has different parents')
            message = 'Apply human-approved Canon ' + task['task_id'] + '\n\n' + canonical_bytes(approval).decode('utf-8') + '\n'
            if self.git('show', '-s', '--format=%B', commit).decode().rstrip('\n') != message.rstrip('\n'):
                raise DataError('Prepared Git message lacks the exact signed approval')
            def tree(sha):
                return {item.split(b'\t', 1)[1].decode('utf-8'): item.split(b'\t', 1)[0]
                        for item in self.git('ls-tree', '-r', '-z', sha).split(b'\0') if item}
            expected_tree = tree(bundle['base_git_sha'])
            for change in bundle['files']:
                if change['after'] is None: expected_tree.pop(change['path'], None)
                else:
                    oid = self.git('hash-object', '--stdin', raw=canonical_bytes(change['after']) + b'\n').strip()
                    expected_tree[change['path']] = b'100644 blob ' + oid
            if tree(commit) != expected_tree: raise DataError('Prepared Git tree differs from reviewed files/base')
            if build_snapshot(self.git_world(commit), self.schemas)['canon_version'] != control['new_canon_version']:
                raise DataError('Prepared Canon version differs')
            self.audit_prepared(journal, task, committed, workspace)
            ref = 'refs/heads/' + bundle['branch']
            refs = {line.split()[0]: line.split()[1] for line in
                    self.git('for-each-ref', '--format=%(refname) %(objectname)', ref).decode().splitlines()}
            if ref in refs:
                if refs[ref] != commit: raise DataError('Existing Canon branch points at a different commit')
            else:
                # No branch publication occurred. Recheck the base and publish by CAS.
                self.check_base(bundle['base_git_sha'], task['canon_snapshot'])
                if self.base_ref() != bundle['base_ref']: raise DataError('Current base branch changed')
                transaction = f"start\nverify {bundle['base_ref']} {bundle['base_git_sha']}\ncreate {ref} {commit}\nprepare\ncommit\n"
                self.git('update-ref', '--stdin', raw=transaction.encode('ascii'))
            path = publish(Workspace(self.repo / '.axiom/local/tasks' / task['task_id']), 'committed.json', committed)
            self.audit_committed(journal, committed)
            return {'status': 'committed', 'branch': bundle['branch'], 'commit_sha': commit,
                    'state_path': str(path), 'new_canon_version': control['new_canon_version']}
