"""Boundary and integrity tests; all scientific content here is synthetic."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from axiom_forge.ids import ID_PREFIXES, DOMAIN_PREFIXES, new_id
from axiom_forge.snapshots import build_snapshot, create_snapshot, verify_snapshot
from axiom_forge.validation import (
    DataError, SchemaStore, collect_world, digest, read_json, validate_dataset, validate_task,
)


ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / ".cache/test-runs"
SCRATCH.mkdir(parents=True, exist_ok=True)


def example(name):
    return read_json(ROOT / "examples" / f"{name}.json")


def fixture_files():
    return {record["path"]: record["data"] for record in example("canon_snapshot")["files"]}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class FoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = SchemaStore(ROOT / "schemas")

    def temporary_repo(self):
        directory = tempfile.TemporaryDirectory(dir=SCRATCH)
        repo = Path(directory.name).resolve()
        self.assertTrue(repo.is_relative_to(SCRATCH.resolve()))
        self.addCleanup(directory.cleanup)
        from axiom_forge.validation import KNOWLEDGE_DIRECTORIES
        for path in KNOWLEDGE_DIRECTORIES:
            (repo / path).mkdir(parents=True, exist_ok=True)
        for path, data in fixture_files().items():
            write_json(repo / path, data)
        return repo

    def test_all_schemas_and_contract_examples(self):
        examples = list((ROOT / "examples").glob("*.json"))
        self.assertEqual(len(self.schemas.schemas), 22)
        self.assertEqual(len(examples), 21)
        for path in examples:
            with self.subTest(schema=path.stem):
                self.schemas.validate(path.stem, read_json(path))
        validate_task(example("task_state"), self.schemas)

    def test_examples_never_claim_verified_science(self):
        data = example("evidence")
        self.assertEqual(data["verification"]["status"], "synthetic")
        self.assertEqual(data["source"]["source_type"], "test_fixture")
        self.assertEqual(example("claim")["category"], "OPEN QUESTION")

    def test_live_world_is_empty(self):
        files = collect_world(ROOT, self.schemas)
        self.assertEqual(set(files), {"world/world.json"})

    def test_business_ids_use_their_own_namespace(self):
        ids = [new_id(kind) for kind in ID_PREFIXES for _ in range(50)]
        self.assertEqual(len(ids), len(set(ids)))
        for kind in ID_PREFIXES:
            value = new_id(kind)
            definition = self.schemas.schemas["common"]["$defs"][kind + "_id"]
            from jsonschema import Draft202012Validator
            self.assertTrue(Draft202012Validator(definition).is_valid(value))
        for domain, prefix in DOMAIN_PREFIXES.items():
            self.assertTrue(new_id("entity", domain).startswith(prefix + "-"))
        for kind, domain in (("unknown", None), ("entity", None), ("task", "history")):
            with self.assertRaises(ValueError):
                new_id(kind, domain)

    def test_vendor_sessions_are_only_metadata(self):
        task = example("task_state")
        task["agent_runs"][0]["metadata"]["provider_thread_id"] = "thread_vendor_123"
        validate_task(task, self.schemas)
        task["task_id"] = "thread_vendor_123"
        with self.assertRaises(DataError):
            validate_task(task, self.schemas)

    def test_unknown_fields_and_invalid_statuses_are_rejected(self):
        for mutate in (lambda d: d.update(extra="typo"), lambda d: d.update(status="probably true")):
            data = example("canon_entry")
            mutate(data)
            with self.assertRaises(DataError):
                self.schemas.validate("canon_entry", data)

    def test_dates_and_confidence_are_validated(self):
        for field, value in (("last_updated", "yesterday"), ("confidence", 1.1), ("confidence", -0.1)):
            data = example("evidence")
            data[field] = value
            with self.assertRaises(DataError):
                self.schemas.validate("evidence", data)

    def test_paper_bibliography_cannot_be_empty(self):
        data = example("evidence")
        data["source"]["source_type"] = "paper"
        with self.assertRaises(DataError):
            self.schemas.validate("evidence", data)

    def test_source_read_status_requires_a_reading_receipt(self):
        data = example("evidence")
        data["source"]["source_type"] = "technical_documentation"
        data["verification"]["status"] = "source_read"
        with self.assertRaises(DataError):
            self.schemas.validate("evidence", data)

    def test_fact_requires_evidence_in_schema(self):
        data = example("claim")
        data["category"] = "FACT"
        with self.assertRaises(DataError):
            self.schemas.validate("claim", data)

    def test_synthetic_source_cannot_be_laundered_into_fact(self):
        files = fixture_files()
        entry = files["world/canon/technology/TECH-001.json"]
        evidence = next(record for path, record in files.items() if path.startswith("world/evidence/"))
        entry["evidence_ids"] = [evidence["evidence_id"]]
        entry["claims"][0].update(category="FACT", evidence_ids=entry["evidence_ids"])
        with self.assertRaisesRegex(DataError, "requires recorded source reading"):
            validate_dataset(files, self.schemas)

    def test_unknown_dependencies_and_evidence_are_rejected(self):
        for field, value in (("dependencies", "TECH-999"), ("conflicts", "TECH-999"),
                             ("evidence_ids", new_id("evidence"))):
            files = fixture_files()
            files["world/canon/technology/TECH-001.json"][field] = [value]
            with self.assertRaises(DataError):
                validate_dataset(files, self.schemas)

    def test_claim_evidence_must_be_in_entry(self):
        files = fixture_files()
        entry = files["world/canon/technology/TECH-001.json"]
        evidence = next(record for path, record in files.items() if path.startswith("world/evidence/"))
        entry["claims"][0]["evidence_ids"] = [evidence["evidence_id"]]
        with self.assertRaisesRegex(DataError, "omitted"):
            validate_dataset(files, self.schemas)

    def test_filename_and_domain_must_agree(self):
        for wrong_path in ("world/canon/physics/TECH-001.json", "world/canon/technology/TECH-002.json",
                           "world/canon/technology/nested/TECH-001.json"):
            files = fixture_files()
            files[wrong_path] = files.pop("world/canon/technology/TECH-001.json")
            with self.assertRaises(DataError):
                validate_dataset(files, self.schemas)

    def test_duplicate_claim_ids_rejected(self):
        files = fixture_files()
        record = copy.deepcopy(files["world/canon/technology/TECH-001.json"])
        record["entity_id"] = "TECH-002"
        files["world/canon/technology/TECH-002.json"] = record
        with self.assertRaisesRegex(DataError, "Duplicate claim"):
            validate_dataset(files, self.schemas)

    def test_json_duplicate_keys_and_nonfinite_numbers_rejected(self):
        repo = self.temporary_repo()
        path = repo / "bad.json"
        for content in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '[]'):
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(DataError):
                read_json(path)

    def test_hash_uses_known_canonical_json(self):
        import hashlib
        self.assertEqual(digest({"b": 2, "a": 1}), hashlib.sha256(b'{"a":1,"b":2}').hexdigest())
        with self.assertRaises(DataError):
            digest({"a": float("nan")})

    def test_snapshot_version_is_independent_of_input_order(self):
        files = fixture_files()
        first = build_snapshot(files, self.schemas)
        second = build_snapshot(dict(reversed(list(files.items()))), self.schemas)
        self.assertEqual(first["canon_version"], second["canon_version"])
        self.assertNotEqual(first["snapshot_id"], second["snapshot_id"])

    def test_snapshot_is_a_deep_copy(self):
        files = fixture_files()
        first = build_snapshot(files, self.schemas)
        files["world/canon/technology/TECH-001.json"]["statement"] = "live edit"
        second = build_snapshot(files, self.schemas)
        self.assertNotEqual(first["canon_version"], second["canon_version"])
        old = verify_snapshot(first, self.schemas)
        self.assertNotEqual(old["entities"]["TECH-001"]["statement"], "live edit")

    def test_snapshot_reuse_is_byte_identical(self):
        repo = self.temporary_repo()
        path = create_snapshot(repo, self.schemas)
        before = path.read_bytes()
        self.assertEqual(create_snapshot(repo, self.schemas), path)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_concurrent_snapshot_publish_is_complete_and_immutable(self):
        repo = self.temporary_repo()
        with ThreadPoolExecutor(max_workers=6) as pool:
            paths = list(pool.map(lambda _: create_snapshot(repo, self.schemas), range(12)))
        self.assertEqual(len(set(paths)), 1)
        verify_snapshot(read_json(paths[0]), self.schemas)
        self.assertEqual(list(paths[0].parent.glob("*.tmp")), [])

    def test_snapshot_remains_usable_after_live_data_changes(self):
        repo = self.temporary_repo()
        first = create_snapshot(repo, self.schemas)
        old_bytes = first.read_bytes()
        path = repo / "world/canon/technology/TECH-001.json"
        entity = read_json(path)
        entity["statement"] = "new live version"
        write_json(path, entity)
        second = create_snapshot(repo, self.schemas)
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), old_bytes)
        self.assertNotEqual(verify_snapshot(read_json(first), self.schemas)["entities"]["TECH-001"]["statement"],
                            "new live version")

    def test_snapshot_tampering_detected(self):
        for mutate in (lambda d: d["files"][0]["data"].update(statement="tampered"),
                       lambda d: d.update(canon_version="CANON-" + "0" * 64),
                       lambda d: d["files"].append(copy.deepcopy(d["files"][0]))):
            snapshot = example("canon_snapshot")
            mutate(snapshot)
            with self.assertRaises(DataError):
                verify_snapshot(snapshot, self.schemas)

    def test_corrupt_existing_snapshot_is_not_replaced(self):
        repo = self.temporary_repo()
        path = create_snapshot(repo, self.schemas)
        path.write_text('{"incomplete":true}', encoding="utf-8")
        before = path.read_bytes()
        with self.assertRaises(DataError):
            create_snapshot(repo, self.schemas)
        self.assertEqual(path.read_bytes(), before)

    def test_snapshot_paths_reject_traversal(self):
        from axiom_forge.validation import record_schema
        for path in ("../world/world.json", "world/../world/world.json", "world\\world.json",
                     "/world/world.json", "world//world.json"):
            with self.assertRaises(DataError):
                record_schema(path)

    def test_task_execution_identities_cannot_be_mixed(self):
        for mutate in (lambda t: t.update(world_id=new_id("world")),
                       lambda t: t["runs"][0].update(task_id=new_id("task")),
                       lambda t: t["agent_runs"][0].update(run_id=new_id("run")),
                       lambda t: t["artifacts"][0].update(agent_run_id=new_id("agent_run")),
                       lambda t: t["research_results"][0].update(run_id=new_id("run")),
                       lambda t: t["agent_runs"].append(copy.deepcopy(t["agent_runs"][0]))):
            task = example("task_state")
            mutate(task)
            with self.assertRaises(DataError):
                validate_task(task, self.schemas)

    def test_task_run_membership_must_match(self):
        task = example("task_state")
        task["runs"][0]["agent_run_ids"].pop()
        with self.assertRaisesRegex(DataError, "membership"):
            validate_task(task, self.schemas)

    def test_result_artifact_detects_result_tampering(self):
        task = example("task_state")
        task["research_results"][0]["summary"] = "Changed after artifact hash was stored"
        with self.assertRaisesRegex(DataError, "artifact hash"):
            validate_task(task, self.schemas)

    def test_result_role_must_match(self):
        task = example("task_state")
        task["agent_runs"][0]["role"] = "integrator"
        with self.assertRaisesRegex(DataError, "role"):
            validate_task(task, self.schemas)

    def test_execution_time_and_completion_receipt(self):
        for value in (None, "2000-01-01T00:00:00Z"):
            task = example("task_state")
            task["runs"][0]["finished_at"] = value
            with self.assertRaises(DataError):
                validate_task(task, self.schemas)

    def test_conflicts_cannot_point_to_unknown_entities(self):
        task = example("task_state")
        task["contradictions"] = [dict(conflict_id=new_id("claim"), description="TEST FIXTURE",
                                       entity_ids=["TECH-999"], evidence_ids=[], severity="high", resolution=None)]
        with self.assertRaisesRegex(DataError, "Conflict"):
            validate_task(task, self.schemas)

    def test_canon_change_operation_and_identity(self):
        for mutate in (lambda d: d.update(operation="delete"),
                       lambda d: d.update(target_entity_id="TECH-999"),
                       lambda d: d["approval"].update(status="approved")):
            change = example("canon_change")
            mutate(change)
            with self.assertRaises(DataError):
                self.schemas.validate("canon_change", change)

    def test_pending_change_cannot_forge_a_receipt(self):
        change = example("canon_change")
        change["approval"]["reviewer"] = "not-yet-approved"
        with self.assertRaisesRegex(DataError, "Pending"):
            self.schemas.validate("canon_change", change)

    def test_task_change_matches_snapshot_version_and_before(self):
        task = example("task_state")
        task["proposed_changes"][0]["base_canon_version"] = "CANON-" + "0" * 64
        with self.assertRaises(DataError):
            validate_task(task, self.schemas)

    def test_proposed_state_must_have_valid_dependencies(self):
        task = example("task_state")
        task["proposed_changes"][0]["after"]["dependencies"] = ["TECH-999"]
        task["synthesis"]["proposed_changes"] = copy.deepcopy(task["proposed_changes"])
        task["artifacts"][-1]["sha256"] = digest(task["synthesis"])
        with self.assertRaisesRegex(DataError, "unknown entity"):
            validate_task(task, self.schemas)

    def test_proposals_validate_in_memory_without_changing_snapshot(self):
        task = example("task_state")
        task["proposed_changes"][0]["after"]["dependencies"] = ["TECH-001"]
        task["synthesis"]["proposed_changes"] = copy.deepcopy(task["proposed_changes"])
        task["artifacts"][-1]["sha256"] = digest(task["synthesis"])
        before = copy.deepcopy(task["canon_snapshot"])
        validate_task(task, self.schemas)
        self.assertEqual(task["canon_snapshot"], before)
        self.assertNotIn("TECH-002", verify_snapshot(task["canon_snapshot"], self.schemas)["entities"])

    def test_uri_and_timezone_are_checked_without_optional_plugins(self):
        for field, value in (("last_updated", "2026-10-03T12:00:00"),
                             ("last_updated", "2026-02-30T12:00:00Z"),
                             ("last_updated", "2026-10-03T25:00:00Z")):
            data = example("evidence")
            data[field] = value
            with self.assertRaises(DataError):
                self.schemas.validate("evidence", data)
        data = example("evidence")
        data["source"]["url"] = "https://example.invalid/ bad url"
        with self.assertRaises(DataError):
            self.schemas.validate("evidence", data)

    def test_committed_state_requires_approved_proposals(self):
        task = example("task_state")
        task.update(lifecycle="COMMITTED", approval_status="approved", final_result="TEST FIXTURE")
        with self.assertRaisesRegex(DataError, "unapproved"):
            validate_task(task, self.schemas)

    def test_cli_success_and_failure_exit_codes(self):
        for arguments, expected in ((["check-schemas"], 0), (["validate-world"], 0),
                                    (["validate", "task_state", "examples/task_state.json"], 0),
                                    (["validate", "missing_schema", "examples/task_state.json"], 1),
                                    (["new-id", "entity"], 1), (["snapshot", "verify"], 1)):
            completed = subprocess.run([sys.executable, "-m", "axiom_forge", *arguments],
                                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(completed.returncode, expected, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
