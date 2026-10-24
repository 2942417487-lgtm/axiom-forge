"""Regression coverage for the omissions found by separation re-audit."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import source_boundary
import check as development_check
from axiom_forge.__main__ import main
from axiom_forge.rules import research_instructions
from axiom_forge.tools.host import session_from_config
from axiom_forge.validation import DataError, read_json
from examples.offline_task_manager import initialize_fixture
from support import PRODUCT_ROOT, EXAMPLES_ROOT


class SourceBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="axiom-source-guard-")
        self.root = Path(self.temporary.name)
        (self.root / ".git").mkdir()
        (self.root / "product").mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def test_guard_checks_source_index_without_product_git(self):
        with patch.object(source_boundary, "git", return_value=b"AGENTS.md\0product/run.py\0development/test.py\0.env.example\0") as git:
            self.assertEqual(source_boundary.check_source_boundary(self.root), 4)
        git.assert_called_once_with(self.root, "ls-files", "-z", "--", engine_listing=True)

    def test_guard_rejects_private_paths_without_reading_values(self):
        for name in (".env", "deep/.ENV.APPROVAL", ".cache/run.json", "development/.axiom/local/task.json",
                     "WORLD/world.json", "private.pem", "nested/credentials.json", ".venv/lib/module.py"):
            with self.subTest(name=name), patch.object(source_boundary, "git", return_value=name.encode() + b"\0"):
                with self.assertRaises(DataError):
                    source_boundary.check_source_boundary(self.root)

    def test_guard_rejects_root_world_even_when_untracked(self):
        (self.root / "world").mkdir()
        with patch.object(source_boundary, "git") as git, self.assertRaises(DataError):
            source_boundary.check_source_boundary(self.root)
        git.assert_not_called()

    def test_missing_git_or_failed_listing_cannot_report_success(self):
        with patch.object(source_boundary, "git", side_effect=DataError("SYNTHETIC unavailable")), self.assertRaises(DataError):
            source_boundary.check_source_boundary(self.root)
        (self.root / ".git").rmdir()
        with self.assertRaises(DataError):
            source_boundary.check_source_boundary(self.root)

    def test_development_entry_stops_before_tests_on_failed_source_guard(self):
        with patch.object(source_boundary, "check_source_boundary", side_effect=DataError("SYNTHETIC rejected")), \
                patch.object(development_check.unittest, "main") as tests, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(development_check.main(["--boundary-only"]), 1)
        tests.assert_not_called()


class ResearchRuleRepairTests(unittest.TestCase):
    def test_all_specialist_instructions_include_assignment_obligations(self):
        for role in ("researcher", "engineering_auditor", "economic_auditor", "historical_analyst"):
            with self.subTest(role=role):
                text = research_instructions(PRODUCT_ROOT, {"role": role})
                for required in ("planning_assignment.question", "required_checks", "覆盖原用户问题"):
                    self.assertIn(required, text)
                self.assertNotIn("python run.py", text)

    def test_integrator_final_proposal_rules_are_actually_loaded(self):
        text = research_instructions(PRODUCT_ROOT, {"role": "integrator"})
        for required in ("修订或撤回", "最终提案集合", "不得引用已撤回", "pending"):
            self.assertIn(required, text)

    def test_manual_auditors_allow_complete_protocol_and_real_schema_paths(self):
        for name in ("engineering-auditor", "economic-auditor"):
            text = (PRODUCT_ROOT / ".claude/agents" / (name + ".md")).read_text(encoding="utf-8")
            self.assertIn("tools: Read", text)
            for required in ("resources/calculations/protocol.md", "resources/schemas/calculation_request.schema.json",
                             "resources/schemas/calculation_result.schema.json", "resources/schemas/calculation_model.schema.json"):
                self.assertIn("- `" + required + "`", text)
                self.assertTrue((PRODUCT_ROOT / required).is_file())
            self.assertNotIn("`calculations/README.md`", text)
            self.assertNotIn("`schemas/", text)


class ToolConfigurationRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="axiom-cli-config-")
        cls.base = Path(cls.temporary.name)
        cls.host = initialize_fixture(cls.base)
        cls.config = cls.base / "tool-config.json"
        cls.context = cls.base / "context.json"
        cls.arguments = cls.base / "arguments.json"
        cls.context.write_text(json.dumps(read_json(EXAMPLES_ROOT / "agents/researcher-input.json")), encoding="utf-8")
        cls.arguments.write_text('{"entity_id":"TECH-001"}', encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def invoke(self, configuration):
        self.config.write_text(json.dumps(configuration), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(["--engine-root", str(self.host.world.engine.root), "--world", str(self.host.repo),
                         "--host-root", str(self.base / "host"), "tools", "call", "canon.read",
                         "--input", str(self.arguments), "--context", str(self.context), "--config", str(self.config)])

    def test_cli_uses_shared_session_builder(self):
        with patch("axiom_forge.tools.host.session_from_config", wraps=session_from_config) as builder:
            self.assertEqual(self.invoke({"capabilities": ["canon_read"]}), 0)
        self.assertEqual(builder.call_count, 1)

    def test_cli_and_runtime_reject_the_same_invalid_config_shapes(self):
        context = read_json(self.context)
        for configuration in (["capabilities"], {"enable_trusted_python": "true"}, {"capabilities": "canon_read"}, {"unknown": True}):
            with self.subTest(configuration=configuration):
                with self.assertRaises(DataError):
                    session_from_config(self.host.world, context, configuration)
                self.assertEqual(self.invoke(configuration), 1)
