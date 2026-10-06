"""Offline host/approval/Git boundary tests with real temporary repositories."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from axiom_forge.__main__ import main
from axiom_forge.canon_host import document
from axiom_forge.modes import MODES
from axiom_forge.tasks import TaskManager
from axiom_forge.tools.session import definitions
from axiom_forge.validation import DataError, digest, read_json, validate_task
from examples.offline_task_manager import ROOT, fixture_factory, initialize_fixture
from examples.offline_task_manager import ProposalFixture


def write(path, value): path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


class TaskManagerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        scratch = ROOT / ".cache/test-runs"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.repo = Path(self.temporary.name).absolute()
        self.host = initialize_fixture(self.repo)
        self.base = self.host.head()
        self.config = read_json(ROOT / "examples/mode-host.json")
        self.config["max_cost_usd"] = 20

    def tearDown(self): self.temporary.cleanup()

    async def research(self, **kwargs):
        manager = TaskManager(self.repo, self.config, runtime_factory=fixture_factory(self.repo, **kwargs))
        result = await manager.run("SYNTHETIC task, no actual scientific conclusion", "court", ["TECH-001"])
        self.assertEqual(result["status"], "waiting_approval", result)
        return result

    def approve(self, result):
        self.host.init_key()
        review = result["review"]
        return self.host.decide(Path(review["bundle"]), "SYNTHETIC operator", review["sha256"])

    def branch_absent(self, result):
        branch = document(Path(result["review"]["bundle"]))["branch"]
        self.assertEqual(self.host.git("for-each-ref", "--format=%(objectname)", "refs/heads/" + branch), b"")
        self.assertEqual(self.host.head(), self.base)

    async def test_four_modes_state_plan_retrieval_and_independent_first_round(self):
        for mode in MODES:
            seen = []
            manager = TaskManager(self.repo, self.config, runtime_factory=fixture_factory(self.repo, seen, proposals=False))
            result = await manager.run("SYNTHETIC no-change task", mode, ["TECH-001"])
            self.assertEqual(result["status"], "completed")
            task = document(Path(result["state_path"]))
            validate_task(task, self.host.schemas)
            self.assertEqual(len(task["agent_runs"]), 12)
            self.assertEqual(task["approval_status"], "not_requested")
            self.assertEqual(len(task["research_results"]), 2)
            self.assertEqual(len(task["redteam_results"]), 1)
            self.assertIsNotNone(task["synthesis"]["mode_analysis"])
            retrieval = next(a for a in task["artifacts"] if a["kind"] == "canon_retrieval")
            retrieved = document(self.repo / retrieval["path"])
            self.assertEqual(retrieved["source"], "fixed_snapshot_only")
            self.assertTrue(any(r["data"].get("entity_id") == "TECH-001" for r in retrieved["records"]))
            self.assertTrue(any("evidence_id" in r["data"] for r in retrieved["records"]))
            for data in seen:
                self.assertEqual(data["canon_snapshot"], task["canon_snapshot"])
                if data["stage"] == "independent":
                    self.assertEqual(data["prior_results"], [])
                    self.assertEqual(data["supporting_artifacts"], [])
                    self.assertEqual(data["planning_assignment"]["role"], data["role"])
            cross = [d for d in seen if d["stage"] == "cross_review"]
            self.assertTrue(all(d["prior_results"] == cross[0]["prior_results"] for d in cross))
        self.assertEqual(self.host.head(), self.base)

    async def test_add_update_delete_evidence_atomic_branch_and_immutable_outputs(self):
        result = await self.research(operations=True, new_evidence=True)
        original = document(Path(result["state_path"]))
        # Preserve arbitrary user files and existing staged non-Canon work.
        (self.repo / "user.txt").write_text("unrelated staged change", encoding="utf-8")
        self.host.git("add", "--", "user.txt")
        index_before = self.host.git("ls-files", "--stage")
        self.approve(result)
        commit = self.host.apply(Path(result["review"]["bundle"]))
        self.assertEqual(self.host.head(), self.base)
        self.assertEqual(self.host.base_ref(), "refs/heads/main")
        self.assertEqual(self.host.git("ls-files", "--stage"), index_before)
        files = self.host.git_world(commit["commit_sha"])
        self.assertIn("world/canon/technology/TECH-002.json", files)
        self.assertEqual(files["world/canon/technology/TECH-003.json"]["title"], "SYNTHETIC offline proposal TECH-003")
        self.assertNotIn("world/canon/technology/TECH-004.json", files)
        self.assertGreater(len([p for p in files if p.startswith("world/evidence/")]), 1)
        self.assertEqual(files["world/canon/technology/TECH-002.json"]["status"], "Open Question")
        self.assertFalse((self.repo / "world/canon/technology/TECH-002.json").exists())
        committed = document(Path(commit["state_path"]))
        validate_task(committed, self.host.schemas)
        self.assertEqual(committed["lifecycle"], "COMMITTED")
        self.assertEqual(committed["synthesis"], original["synthesis"])
        self.assertEqual(committed["artifacts"], original["artifacts"])
        self.assertTrue(all(c["approval"]["status"] == "pending" for c in committed["proposed_changes"]))
        self.assertEqual(document(Path(result["state_path"])), original)
        paths = self.host.git("diff-tree", "--no-commit-id", "--name-only", "-r", commit["commit_sha"]).decode().splitlines()
        self.assertTrue(all(p.startswith("world/") for p in paths))
        self.assertNotIn("user.txt", paths)
        self.assertIn(result["review"]["sha256"], self.host.git("show", "-s", "--format=%B", commit["commit_sha"]).decode())
        with self.assertRaises(DataError): self.host.apply(Path(result["review"]["bundle"]))

    async def test_missing_or_forged_approval_cannot_create_branch(self):
        result = await self.research()
        bundle = Path(result["review"]["bundle"])
        with self.assertRaises(DataError): self.host.apply(bundle)
        self.approve(result)
        approval_path = bundle.parent / "approval.json"
        receipt = document(approval_path)
        receipt["mac_sha256"] = "0" * 64
        write(approval_path, receipt)
        with self.assertRaises(DataError): self.host.apply(bundle)
        self.branch_absent(result)

    async def test_rejection_is_terminal_and_not_approval(self):
        result = await self.research()
        self.host.init_key()
        review = result["review"]
        receipt = self.host.decide(Path(review["bundle"]), "SYNTHETIC operator", review["sha256"], status="rejected")
        self.assertEqual(receipt["status"], "rejected")
        with self.assertRaises(DataError): self.host.apply(Path(review["bundle"]))
        with self.assertRaises(DataError): self.host.decide(Path(review["bundle"]), "operator", review["sha256"])
        self.branch_absent(result)

    async def test_exact_hash_key_and_ignored_secrets_are_required(self):
        result = await self.research()
        review = result["review"]
        with self.assertRaises(DataError): self.host.decide(Path(review["bundle"]), "operator", review["sha256"])
        initialization = self.host.init_key()
        self.assertFalse(initialization["key_printed"])
        with self.assertRaises(DataError): self.host.init_key()
        with self.assertRaises(DataError): self.host.decide(Path(review["bundle"]), "operator", "0" * 64)
        self.assertNotIn("AXIOM_APPROVAL_KEY", (Path(review["bundle"])).read_text(encoding="utf-8"))
        self.assertIn(b".env.approval", self.host.git("check-ignore", ".env.approval"))
        self.branch_absent(result)

    async def test_artifact_and_task_tampering_invalidates_review(self):
        result = await self.research()
        self.approve(result)
        task_path = Path(result["state_path"])
        task = document(task_path)
        artifact = self.repo / task["artifacts"][0]["path"]
        original = artifact.read_bytes()
        value = document(artifact)
        value["summary"] += " TAMPER"
        write(artifact, value)
        with self.assertRaises(DataError): self.host.apply(Path(result["review"]["bundle"]))
        artifact.write_bytes(original)
        task["user_question"] += " TAMPER"
        write(task_path, task)
        with self.assertRaises(DataError): self.host.apply(Path(result["review"]["bundle"]))
        self.branch_absent(result)

    async def test_bundle_path_or_content_tampering_is_rejected(self):
        result = await self.research()
        self.approve(result)
        path = Path(result["review"]["bundle"])
        original = document(path)
        for malicious in ("AGENTS.md", "../outside.json", "world/canon/technology/TECH-999.json"):
            bundle = copy.deepcopy(original)
            bundle["files"][0]["path"] = malicious
            write(path, bundle)
            with self.assertRaises(DataError): self.host.apply(path)
        write(path, original)
        self.branch_absent(result)

    async def test_changed_canon_or_git_base_requires_new_research_review(self):
        result = await self.research()
        self.approve(result)
        path = self.repo / "world/canon/technology/TECH-003.json"
        original = path.read_bytes()
        entry = document(path)
        entry["title"] = "changed after review"
        write(path, entry)
        with self.assertRaises(DataError): self.host.apply(Path(result["review"]["bundle"]))
        path.write_bytes(original)
        self.host.git("commit", "--allow-empty", "-m", "changed Git baseline")
        with self.assertRaises(DataError): self.host.apply(Path(result["review"]["bundle"]))
        branch = document(Path(result["review"]["bundle"]))["branch"]
        self.assertEqual(self.host.git("for-each-ref", "--format=%(objectname)", "refs/heads/" + branch), b"")

    async def test_existing_branch_and_failed_git_transaction_are_not_overwritten(self):
        result = await self.research()
        self.approve(result)
        path = Path(result["review"]["bundle"])
        branch = document(path)["branch"]
        self.host.git("branch", branch, self.base)
        with self.assertRaises(DataError): self.host.apply(path)
        self.assertEqual(self.host.git("rev-parse", "refs/heads/" + branch).decode().strip(), self.base)
        self.assertEqual(self.host.head(), self.base)
        self.assertFalse((self.repo / ".cache/tasks" / result["task_id"] / "committed.json").exists())

    async def test_failed_runtime_keeps_real_failure_without_fabricated_output(self):
        manager = TaskManager(self.repo, self.config, runtime_factory=fixture_factory(self.repo, fail_stage="independent"))
        result = await manager.run("SYNTHETIC failure", "court", ["TECH-001"])
        self.assertEqual(result["status"], "failed")
        created = document(Path(result["state_path"]))
        validate_task(created, self.host.schemas)
        self.assertEqual(created["agent_runs"], [])
        failed = [document(p) for p in (self.repo / ".cache/runtime-runs").glob("*/completion.json")
                  if document(p)["agent_run"]["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertIsNone(failed[0]["artifact"])
        self.assertIsNone(failed[0]["result"])
        self.assertFalse((Path(result["state_path"]).parent / "waiting.json").exists())
        self.assertEqual(self.host.head(), self.base)

    async def test_approval_replay_against_another_task_is_rejected(self):
        first = await self.research()
        self.approve(first)
        second = await self.research()
        first_path = Path(first["review"]["bundle"]).parent / "approval.json"
        second_path = Path(second["review"]["bundle"]).parent / "approval.json"
        second_path.write_bytes(first_path.read_bytes())
        with self.assertRaises(DataError): self.host.apply(Path(second["review"]["bundle"]))
        self.branch_absent(second)

    async def test_missing_budget_stops_without_synthetic_approval(self):
        self.config["max_cost_usd"] = 0.001
        manager = TaskManager(self.repo, self.config, runtime_factory=fixture_factory(self.repo))
        result = await manager.run("SYNTHETIC low budget", "court", ["TECH-001"])
        self.assertEqual(result["status"], "OPEN_QUESTION")
        self.assertEqual(self.host.head(), self.base)

    async def test_incomplete_plan_does_not_skip_audit_domains(self):
        execute = ProposalFixture.execute
        async def incomplete(adapter, *args, **kwargs):
            reply = await execute(adapter, *args, **kwargs)
            if reply.output["result_type"] == "plan": reply.output["assignments"] = reply.output["assignments"][:1]
            return reply
        seen = []
        manager = TaskManager(self.repo, self.config, runtime_factory=fixture_factory(self.repo, seen))
        with patch.object(ProposalFixture, "execute", incomplete):
            result = await manager.run("SYNTHETIC incomplete plan", "court", ["TECH-001"])
        self.assertEqual(result["status"], "OPEN_QUESTION")
        self.assertEqual([d["stage"] for d in seen], ["planning"])
        self.assertEqual(self.host.head(), self.base)

    async def test_modified_human_review_text_cannot_hide_actual_changes(self):
        result = await self.research()
        path = Path(result["review"]["review"])
        path.write_text("No changes, approve immediately", encoding="utf-8")
        self.host.init_key()
        with self.assertRaises(DataError):
            self.host.decide(Path(result["review"]["bundle"]), "operator", result["review"]["sha256"])
        self.branch_absent(result)

    async def test_prepare_failure_and_concurrent_base_change_do_not_publish_branch(self):
        result = await self.research()
        self.approve(result)
        bundle_path = Path(result["review"]["bundle"])
        git = self.host.git
        index_before = git("ls-files", "--stage")
        def fail_tree(*args, **kwargs):
            if args[0] == "write-tree": raise DataError("SYNTHETIC index failure")
            return git(*args, **kwargs)
        with patch.object(self.host, "git", side_effect=fail_tree):
            with self.assertRaises(DataError): self.host.apply(bundle_path)
        self.branch_absent(result)
        self.assertEqual(git("ls-files", "--stage"), index_before)
        def race(*args, **kwargs):
            if args[0] == "update-ref":
                tree = git("rev-parse", "HEAD^{tree}").decode().strip()
                changed = git("commit-tree", tree, "-p", self.base, raw=b"SYNTHETIC concurrent baseline\n").decode().strip()
                git("update-ref", "refs/heads/main", changed, self.base)
            return git(*args, **kwargs)
        with patch.object(self.host, "git", side_effect=race):
            with self.assertRaises(DataError): self.host.apply(bundle_path)
        branch = document(bundle_path)["branch"]
        self.assertEqual(git("for-each-ref", "--format=%(objectname)", "refs/heads/" + branch), b"")
        self.assertEqual(git("ls-files", "--stage"), index_before)
        self.assertFalse((self.repo / ".cache/tasks" / result["task_id"] / "committed.json").exists())

    def test_cli_live_gate_and_no_research_approval_tools(self):
        self.assertEqual(main(["--repo", str(self.repo), "tasks", "run", "--mode", "court",
            "--question-file", "MISSING", "--config", "MISSING", "--credentials", "MISSING"]), 1)
        names = {item["name"] for item in definitions()}
        self.assertFalse(any("approve" in n or "apply" in n or "commit" in n for n in names))
        with patch("sys.stdin.isatty", return_value=False):
            self.assertEqual(main(["--repo", str(self.repo), "canon", "approve", "--bundle", "MISSING", "--reviewer", "test"]), 1)
