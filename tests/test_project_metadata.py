"""Synthetic project format, read-only boundaries and redacted CLI diagnostics."""

import hashlib
import io
import json
import os
import tempfile
import traceback
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from axiom_forge.__main__ import main
from axiom_forge.ids import new_id
from axiom_forge.project_metadata import (
    ProjectMetadataError, check_project, check_project_file, validate_project_metadata,
)
from axiom_forge.snapshots import build_snapshot
from axiom_forge.tools.storage import MAX_BYTES, read_bounded
from axiom_forge.validation import DataError, KNOWLEDGE_DIRECTORIES, collect_world, read_json
from axiom_forge.workspaces import EngineResources


ROOT = Path(__file__).resolve().parents[1]
SENTINEL = "SYNTHETIC-SHOULD-NOT-BE-ECHOED"


class ProjectMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = EngineResources.default()
        cls.schemas = cls.engine.schemas

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="axiom-project-metadata-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.project_path = self.root / "project.json"
        self.world_path = self.root / "world/world.json"
        self.world_path.parent.mkdir()
        self.world = read_json(ROOT / "examples/world.json")
        self.project = read_json(ROOT / "examples/project_metadata.json")
        self.write(self.world_path, self.world)
        self.write(self.project_path, self.project)

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def error(self, code, call=None):
        with self.assertRaises(ProjectMetadataError) as caught:
            (call or (lambda: check_project(self.root, self.engine)))()
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def cli(self, args):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = main(args)
        return code, output.getvalue(), errors.getvalue()

    def test_valid_null_and_labels_preserve_bytes_and_report_only_input_hashes(self):
        for label in (None, "第二版", "v1.2", "😀" * 64, "\u00a0", "a\u2028b"):
            with self.subTest(label=label):
                self.project["display_version"] = label
                self.write(self.project_path, self.project)
                before = self.project_path.read_bytes()
                result = check_project(self.root, self.engine)
                self.assertEqual(result, {
                    "status": "metadata_valid", "scope": "project_metadata_and_world_identity",
                    "project_sha256": hashlib.sha256(before).hexdigest(),
                    "world_sha256": hashlib.sha256(self.world_path.read_bytes()).hexdigest(),
                })
                self.assertEqual(self.project_path.read_bytes(), before)
                self.assertFalse((self.root / ".axiom").exists())

    def test_schema_and_helper_agree_on_invalid_labels(self):
        for label in ("", 1, 1.0, False, [], {}, "a" * 65, "😀" * 65,
                      " leading", "trailing ", "\x00", "\t", "a\n", "\x1f", "\x7f", "\x9f", "\ud800", "\udfff"):
            with self.subTest(label=repr(label)):
                value = {**self.project, "display_version": label}
                self.error("metadata_invalid", lambda: validate_project_metadata(value, self.schemas))
                with self.assertRaises(DataError):
                    self.schemas.validate("project_metadata", value)

    def test_missing_fields_have_no_defaults(self):
        for field in self.project:
            value = {k: v for k, v in self.project.items() if k != field}
            self.error("metadata_invalid", lambda: validate_project_metadata(value, self.schemas))
            self.assertNotIn(field, value)
        for field in ("project_id", "world_id", "project_format_version"):
            self.error("metadata_invalid", lambda: validate_project_metadata({**self.project, field: None}, self.schemas))

    def test_versions_fields_and_case_variants_are_not_normalized(self):
        for version in ("2.0", "0.9", "1.0 ", SENTINEL):
            self.error("project_format_unsupported", lambda: validate_project_metadata({**self.project, "project_format_version": version}, self.schemas))
        for version in (1, 1.0, False):
            self.error("metadata_invalid", lambda: validate_project_metadata({**self.project, "project_format_version": version}, self.schemas))
        for field in ("workspace_id", "schema_version", "Project_id", SENTINEL):
            value = {**self.project, field: SENTINEL}
            self.error("project_fields_unsupported", lambda: validate_project_metadata(value, self.schemas))

    def test_project_and_world_ids_are_exact_lowercase_v4(self):
        for field in ("project_id", "world_id"):
            original = self.project[field]
            values = (original.lower(), original + "\n", original + " ", original.replace("-4", "-1", 1),
                      original.replace("-8", "-7", 1) if field == "project_id" else original.replace("-a", "-7", 1),
                      original[4:], "thread_vendor_123")
            for value in values:
                with self.subTest(field=field, value=value):
                    self.error("metadata_invalid", lambda: validate_project_metadata({**self.project, field: value}, self.schemas))
                    with self.assertRaises(DataError):
                        self.schemas.validate("project_metadata", {**self.project, field: value})
        generated = new_id("project")
        self.assertTrue(generated.startswith("PRJ-"))
        validate_project_metadata({**self.project, "project_id": generated}, self.schemas)
        with self.assertRaises(ValueError):
            new_id("conversation")

    def test_non_utf8_bom_duplicate_keys_nonfinite_and_nonobjects_are_rejected(self):
        valid = self.project_path.read_bytes()
        for raw in (b"\xef\xbb\xbf" + valid, valid.decode().encode("utf-16"),
                    valid.decode().encode("utf-32"), b"\xff", b"[]", b"null", b"true",
                    b"{", b'{"project_id":1,"project_id":2}', b'{"value":NaN}',
                    b'{"value":Infinity}', b'{"value":1e999}', b'{"value":"\\ud800"}'):
            with self.subTest(raw=raw[:24]):
                self.project_path.write_bytes(raw)
                self.error("metadata_invalid")
                self.assertEqual(self.project_path.read_bytes(), raw)

    def test_json_escaped_supplementary_pairs_count_as_scalars(self):
        self.project["display_version"] = "😀" * 64
        self.write(self.project_path, self.project)
        self.assertIn(b"\\ud83d\\ude00", self.project_path.read_bytes())
        self.assertEqual(check_project(self.root, self.engine)["status"], "metadata_valid")

    def test_formatting_changes_only_the_raw_input_hash(self):
        first = check_project(self.root, self.engine)
        self.project_path.write_text(json.dumps(dict(reversed(list(self.project.items())))), encoding="utf-8")
        second = check_project(self.root, self.engine)
        self.assertNotEqual(first["project_sha256"], second["project_sha256"])
        self.assertEqual(first["world_sha256"], second["world_sha256"])
        self.assertEqual(read_json(self.project_path), self.project)

    def test_identity_conflict_does_not_modify_either_file(self):
        self.project["world_id"] = new_id("world")
        self.write(self.project_path, self.project)
        before = {p: p.read_bytes() for p in (self.project_path, self.world_path)}
        self.error("identity_conflict")
        self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_missing_project_is_legacy_but_core_metadata_validation_still_works(self):
        self.project_path.unlink()
        self.error("legacy_metadata_missing")
        self.schemas.validate("world", read_json(self.world_path))
        self.assertFalse(self.project_path.exists())
        self.assertFalse((self.root / ".axiom").exists())

    def test_missing_or_invalid_world_is_incomplete_not_valid_or_legacy(self):
        self.world_path.unlink()
        self.error("inspection_incomplete")
        for mutation in (dict(schema_version="2.0"), dict(world_id=SENTINEL), dict(name=1)):
            self.write(self.world_path, {**self.world, **mutation})
            self.error("inspection_incomplete")
        self.world_path.write_bytes(b'{"description":"' + SENTINEL.encode() + b'","description":false}')
        error = self.error("inspection_incomplete")
        self.assertNotIn(SENTINEL, str(error))

    def test_directories_and_oversized_files_are_not_legacy_or_truncated(self):
        self.project_path.unlink()
        self.project_path.mkdir()
        self.error("inspection_incomplete")
        self.project_path.rmdir()
        raw = b" " * (MAX_BYTES + 1)
        self.project_path.write_bytes(raw)
        self.error("inspection_incomplete")
        self.assertEqual(self.project_path.read_bytes(), raw)

    def test_engine_overlap_and_nonexistent_roots_are_rejected(self):
        for root in (ROOT, ROOT / "examples", ROOT.parent, self.root / "missing"):
            self.error("inspection_incomplete", lambda: check_project(root, self.engine))

    def test_linked_project_cannot_read_outside_selected_directory(self):
        outside = self.root / "outside.json"
        outside.write_text(SENTINEL, encoding="utf-8")
        self.project_path.unlink()
        try:
            os.symlink(outside, self.project_path)
        except OSError:
            self.skipTest("OS does not permit a synthetic symlink")
        self.error("inspection_incomplete")
        self.assertEqual(outside.read_text(encoding="utf-8"), SENTINEL)

    def test_observed_input_change_invalidates_result(self):
        for changed in (self.project_path, self.world_path):
            counts = {}
            def changing(path):
                path = Path(path)
                counts[path] = counts.get(path, 0) + 1
                raw = read_bounded(path)
                return raw + b"\n" if path == changed and counts[path] > 1 else raw
            with patch("axiom_forge.project_metadata.read_bounded", side_effect=changing):
                self.error("baseline_changed")

    def test_private_state_user_files_git_and_host_are_never_read_or_modified(self):
        for name in (".axiom/local/workspace.json", ".env.approval", ".git/HEAD", "notes.md"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(SENTINEL, encoding="utf-8")
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with patch("axiom_forge.project_metadata.read_bounded", wraps=read_bounded) as reader:
            code, output, errors = self.cli(["--world", str(self.root), "project", "check"])
        self.assertEqual(code, 0, errors)
        self.assertEqual({Path(call.args[0]) for call in reader.call_args_list}, {self.project_path, self.world_path})
        self.assertNotIn(SENTINEL, output + errors)
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_cli_never_constructs_workspace_and_requires_explicit_world(self):
        with patch("axiom_forge.__main__.WorldWorkspace", side_effect=AssertionError("No workspace creation")):
            code, output, errors = self.cli(["--world", str(self.root), "project", "check"])
            self.assertEqual(code, 0, errors)
            self.assertEqual(json.loads(output)["scope"], "project_metadata_and_world_identity")
            code, output, errors = self.cli(["project", "check"])
            self.assertEqual(code, 1)
            self.assertEqual(output, "")
            self.assertEqual(json.loads(errors)["status"], "inspection_incomplete")

    def test_cli_and_exception_chains_never_echo_source_values_or_unknown_keys(self):
        cases = ({**self.project, "display_version": " " + SENTINEL},
                 {**self.project, SENTINEL: SENTINEL},
                 {**self.project, "project_format_version": SENTINEL})
        for value in cases:
            self.write(self.project_path, value)
            for args in (["--world", str(self.root), "project", "check"],
                         ["validate", "project_metadata", str(self.project_path)]):
                code, output, errors = self.cli(args)
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertNotIn(SENTINEL, errors)
                self.assertIn(json.loads(errors)["status"], {"metadata_invalid", "project_fields_unsupported", "project_format_unsupported"})
            try:
                check_project(self.root, self.engine)
            except ProjectMetadataError:
                self.assertNotIn(SENTINEL, traceback.format_exc())
        # A structurally valid label is still not safe to echo. No sensitive
        # detection is implemented; success means only format/association.
        self.write(self.project_path, {**self.project, "display_version": SENTINEL})
        code, output, errors = self.cli(["--world", str(self.root), "project", "check"])
        self.assertEqual(code, 0, errors)
        self.assertNotIn(SENTINEL, output)

    def test_file_only_cli_does_not_claim_world_association(self):
        self.world_path.unlink()
        code, output, errors = self.cli(["validate", "project_metadata", str(self.project_path)])
        self.assertEqual(code, 0, errors)
        self.assertEqual(json.loads(output)["scope"], "project_metadata_format")
        self.assertNotIn("world_sha256", json.loads(output))
        self.assertEqual(check_project_file(self.project_path, self.schemas), json.loads(output))

    def test_metadata_labels_do_not_enter_existing_canon_hash(self):
        for directory in KNOWLEDGE_DIRECTORIES:
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        first = build_snapshot(collect_world(self.root, self.schemas), self.schemas)["canon_version"]
        self.write(self.project_path, {**self.project, "display_version": "第二版"})
        second = build_snapshot(collect_world(self.root, self.schemas), self.schemas)["canon_version"]
        self.assertEqual(first, second)
        self.write(self.world_path, {**self.world, "description": "SYNTHETIC changed world"})
        third = build_snapshot(collect_world(self.root, self.schemas), self.schemas)["canon_version"]
        self.assertNotEqual(second, third)


if __name__ == "__main__":
    unittest.main()
