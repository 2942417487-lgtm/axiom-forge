"""Product independence, trusted rule scope and migration compatibility."""

import io
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from support import PRODUCT_ROOT, EXAMPLES_ROOT
from axiom_forge.journal import source_fingerprint
from axiom_forge.__main__ import main
from axiom_forge.rules import research_instructions
from axiom_forge.tasks import TaskManager
from axiom_forge.validation import DataError, read_json
from axiom_forge.workspaces import EngineResources
from examples.offline_task_manager import initialize_fixture


class ProductLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="axiom-product-layout-")
        self.base = Path(self.temporary.name).resolve()
        self.product = self.base / "standalone-product"
        shutil.copytree(PRODUCT_ROOT, self.product, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        self.environment = {key: value for key, value in os.environ.items() if key.upper() in
                            ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC")}

    def tearDown(self):
        self.temporary.cleanup()

    def command(self, *args):
        return subprocess.run([sys.executable, str(self.product / "run.py"), *args], cwd=self.base,
                              env=self.environment, capture_output=True, text=True, timeout=45)

    def test_standalone_product_checks_without_development_or_pythonpath(self):
        self.assertFalse((self.product / "AGENTS.md").exists())
        self.assertFalse((self.product / "development").exists())
        for args in (("check-schemas",), ("check-contracts",), ("routing", "check"), ("check-system-boundary",)):
            with self.subTest(args=args):
                result = self.command(*args)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_development_entries_and_docs_do_not_change_research_fingerprint(self):
        before = source_fingerprint(self.product)
        for name in ("AGENTS.md", "CLAUDE.md"):
            (self.base / name).write_text("UNTRUSTED_DEVELOPMENT_SENTINEL", encoding="utf-8")
        (self.product / "docs/README.md").write_text("Operator usage changed", encoding="utf-8")
        self.assertEqual(source_fingerprint(self.product), before)
        policy = self.product / "resources/policies/research.md"
        policy.write_text(policy.read_text(encoding="utf-8") + "\nChanged rule\n", encoding="utf-8")
        self.assertNotEqual(source_fingerprint(self.product), before)

    def test_missing_product_policy_has_no_development_fallback(self):
        (self.product / "resources/policies/research.md").unlink()
        (self.product / "AGENTS.md").write_text("Legacy developer policy", encoding="utf-8")
        with self.assertRaises((DataError, OSError)):
            EngineResources(self.product)

    def test_release_boundary_rejects_development_and_private_files(self):
        for relative in ("AGENTS.md", "CLAUDE.md", ".env.private", ".ENV.APPROVAL",
                         "resources/.EnV.PrIvAtE", "resources/.env.approval", "Development/test.txt"):
            with self.subTest(relative=relative):
                path = self.product / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("SYNTHETIC_NOT_A_SECRET", encoding="utf-8")
                self.assertNotEqual(self.command("check-system-boundary").returncode, 0)
                path.unlink()
                if path.parent.name.casefold() == "development":
                    path.parent.rmdir()

    def test_unreadable_product_subdirectory_is_incomplete(self):
        real_scandir = os.scandir
        def denied(path):
            if Path(path) == self.product / "docs":
                raise PermissionError("SYNTHETIC denied directory")
            return real_scandir(path)
        with patch("os.scandir", side_effect=denied), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--engine-root", str(self.product), "check-system-boundary"]), 1)

    def test_auditor_protocol_contains_no_development_commands(self):
        data = read_json(EXAMPLES_ROOT / "agents/engineering_auditor-input.json")
        instructions = research_instructions(self.product, data)
        self.assertIn("CalculationRequest", instructions)
        self.assertIn("cost_basis", instructions)
        self.assertNotIn("python run.py", instructions)
        self.assertNotIn("development/examples", instructions)

    def test_old_version_checkpoint_stops_before_runtime_without_rewriting(self):
        fixture = self.base / "legacy-checkpoint-fixture"
        fixture.mkdir()
        host = initialize_fixture(fixture)
        config = read_json(EXAMPLES_ROOT / "mode-host.json")
        calls = []
        def forbidden(*args):
            calls.append(args)
            raise AssertionError("Legacy records must stop before model construction")
        manager = TaskManager(host.world, config, runtime_factory=forbidden)
        async def stop_after_checkpoint(initial, task, control, journal):
            return journal
        with patch("axiom_forge.tasks.__version__", "0.2.0"), patch("axiom_forge.journal.__version__", "0.2.0"), \
                patch.object(manager, "_execute", side_effect=stop_after_checkpoint):
            journal = asyncio.run(manager.run("SYNTHETIC legacy version", "court", ["TECH-001"]))
        files = {path: path.read_bytes() for path in journal.records.root.glob("*.json")}
        with self.assertRaisesRegex(DataError, "Legacy|incompatible"):
            asyncio.run(manager.resume(journal.task_id))
        self.assertEqual(calls, [])
        self.assertEqual(files, {path: path.read_bytes() for path in journal.records.root.glob("*.json")})

    def test_research_invocation_uses_only_internal_rules(self):
        fixture = self.base / "fixture"
        fixture.mkdir()
        host = initialize_fixture(fixture)
        for name in ("AGENTS.md", "CLAUDE.md"):
            (self.base / name).write_text("UNTRUSTED_DEVELOPMENT_SENTINEL", encoding="utf-8")
            (host.repo / name).write_text("UNTRUSTED_WORLD_SENTINEL", encoding="utf-8")
        data = read_json(EXAMPLES_ROOT / "agents/researcher-input.json")
        inputs = self.base / "synthetic-inputs.json"
        inputs.write_text(json.dumps({"input": data, "output": read_json(EXAMPLES_ROOT / "research_result.json")}), encoding="utf-8")
        program = '''import asyncio, json, sys
from pathlib import Path
from axiom_forge.runtimes.core import AdapterReply, AgentRuntime
from axiom_forge.workspaces import EngineResources, WorldWorkspace
values = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
class SyntheticAdapter:
    provider, model = "openai", "SYNTHETIC-NO-API"
    async def execute(self, instructions, prompt, schema, tools, limits):
        assert "产品通用可信原则" in instructions and "世界观研究规则" in instructions
        assert "SENTINEL" not in instructions and "系统开发规则" not in instructions
        return AdapterReply(values["output"], "SYNTHETIC", 0, 0, 0)
world = WorldWorkspace(Path(sys.argv[2]), EngineResources.default(), host_root=Path(sys.argv[3]))
packet = asyncio.run(AgentRuntime(world, SyntheticAdapter()).run_input(values["input"]))
assert packet["agent_run"]["status"] == "completed"
assert not any(name in sys.modules for name in ("examples", "tests", "support"))
print("SYNTHETIC_STANDALONE_COMPLETED")
'''
        result = subprocess.run([sys.executable, "-c", program, str(inputs), str(host.repo), str(fixture / "host")],
                                cwd=self.product, env=self.environment, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SYNTHETIC_STANDALONE_COMPLETED", result.stdout)
