"""Runtime tests use synthetic providers; no credentials or paid requests."""

import asyncio
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from axiom_forge.contracts import IDENTITY, OUTPUTS
from axiom_forge.ids import new_id
from axiom_forge.runtimes import AdapterReply, AgentRuntime, RuntimeLimits
from axiom_forge.runtimes.core import ToolBinding, expanded_schema
from axiom_forge.tools import ToolSession
from axiom_forge.tools.storage import ToolError, strict_json
from axiom_forge.validation import DataError, SchemaStore, digest, read_json

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / ".cache/test-runs"


class FakeAdapter:
    provider, model = "openai", "TEST-FIXTURE-NOT-A-MODEL"
    def __init__(self, output, behavior=None):
        self.output, self.behavior, self.count = output, behavior, 0
        self.prompt = self.instructions = self.tools = None

    async def execute(self, instructions, prompt, output_schema, tools, limits):
        self.count += 1
        self.prompt, self.instructions, self.tools = prompt, instructions, tools
        if self.behavior:
            await self.behavior(tools)
        return AdapterReply(self.output, "synthetic-session", 11, 12, 0)


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=SCRATCH)
        cls.repo = Path(cls.temporary.name).absolute()
        for path in ("schemas", "agents", ".claude"):
            shutil.copytree(ROOT / path, cls.repo / path)
        shutil.copyfile(ROOT / "AGENTS.md", cls.repo / "AGENTS.md")
        cls.schemas = SchemaStore(cls.repo / "schemas")

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def invocation(self, role="researcher"):
        data = read_json(ROOT / ("examples/agent_input.json" if role == "lead" else f"examples/agents/{role}-input.json"))
        data["agent_run_id"], data["artifact_id"] = new_id("agent_run"), new_id("artifact")
        output = read_json(ROOT / ("examples/" + OUTPUTS[role] + ".json"))
        output.update({key: data[key] for key in IDENTITY})
        return data, output

    def runtime(self, output, behavior=None, capabilities=(), **kwargs):
        adapter = FakeAdapter(output, behavior)
        runtime = AgentRuntime(self.repo, adapter, session_factory=lambda data:
                               ToolSession(self.repo, data, capabilities=capabilities), **kwargs)
        return runtime, adapter

    async def test_all_role_outputs_saved_with_real_runtime_hashes(self):
        for role in OUTPUTS:
            with self.subTest(role=role):
                data, output = self.invocation(role)
                runtime, adapter = self.runtime(output)
                packet = await runtime.run_input(data)
                self.assertEqual(packet["agent_run"]["status"], "completed")
                self.assertEqual(packet["artifact"]["sha256"], digest(output))
                self.assertEqual(read_json(self.repo / packet["artifact"]["path"]), output)
                self.assertEqual(packet["agent_run"]["metadata"]["provider_session_id"], "synthetic-session")
                self.assertEqual(strict_json(adapter.prompt)["agent_input"], data)
                self.assertTrue(adapter.tools.closed)

    async def test_unified_run_projects_task_and_excludes_task_metadata(self):
        data, output = self.invocation("lead")
        task = read_json(ROOT / "examples/task_state.json")
        task["metadata"]["PRIVATE_PEER_RESULT"] = "DO_NOT_FORWARD"
        state = {"execution": {key: data[key] for key in ("run_id", "agent_run_id", "artifact_id")},
                 "stage": "planning", "selected_specialists": [], "prior_results": [], "supporting_artifacts": []}
        runtime, adapter = self.runtime(output)
        packet = await runtime.run("lead", task, state)
        self.assertEqual(packet["agent_run"]["status"], "completed")
        self.assertNotIn("DO_NOT_FORWARD", adapter.prompt)
        self.assertNotIn("TaskState", strict_json(adapter.prompt))
        with self.assertRaises(DataError):
            await runtime.run("lead", task, {**state, "config": {"canon_write": True}})

    async def test_invalid_input_does_not_invoke_provider(self):
        data, output = self.invocation()
        data["prior_results"] = read_json(ROOT / "examples/agents/redteam-input.json")["prior_results"]
        runtime, adapter = self.runtime(output)
        with self.assertRaises(DataError):
            await runtime.run_input(data)
        self.assertEqual(adapter.count, 0)

    async def test_wrong_identity_malformed_json_and_nonfinite_fail_without_artifact(self):
        for mode in ("identity", "duplicate", "nonfinite", "markdown", "fields"):
            data, output = self.invocation()
            if mode == "identity":
                output["agent_run_id"] = new_id("agent_run")
            elif mode == "duplicate":
                output = '{"a":1,"a":2}'
            elif mode == "nonfinite":
                output["metadata"]["bad"] = float("nan")
            elif mode == "markdown":
                output = "```json\n" + json.dumps(output) + "\n```"
            else:
                output["approved"] = True
            runtime, _ = self.runtime(output)
            packet = await runtime.run_input(data)
            self.assertEqual(packet["agent_run"]["status"], "failed")
            self.assertIsNone(packet["artifact"])
            self.assertIsNone(packet["result"])
            self.assertFalse((self.repo / ".cache/runtime-runs" / data["agent_run_id"] / "output.json").exists())

    async def test_same_agent_run_cannot_be_reused(self):
        data, output = self.invocation()
        runtime, adapter = self.runtime(output)
        await runtime.run_input(data)
        with self.assertRaises(ToolError):
            await runtime.run_input(data)
        self.assertEqual(adapter.count, 1)

    async def test_tool_binding_filtered_and_lifetime_call_limits(self):
        data, output = self.invocation()
        async def calls(tools):
            self.assertEqual(set(tools.names), {"canon__read", "evidence__read"})
            hidden = strict_json(await tools.call("filesystem__read", {"path": "secret"}))
            self.assertEqual(hidden["status"], "denied")
            result = strict_json(await tools.call("canon__read", {"entity_id": "TECH-001"}))
            self.assertEqual(result["status"], "completed")
            self.assertEqual(strict_json(await tools.call("canon__read", {"entity_id": "TECH-001"}))["status"], "denied")
        runtime, adapter = self.runtime(output, calls, ["canon_read"], limits=RuntimeLimits(max_tool_calls=1))
        packet = await runtime.run_input(data)
        self.assertEqual(packet["agent_run"]["status"], "completed")
        self.assertEqual(len(packet["tool_artifacts"]), 1)
        receipt = read_json(self.repo / packet["tool_artifacts"][0]["path"])
        self.assertEqual(receipt["agent_run_id"], data["agent_run_id"])
        self.assertEqual(packet["tool_artifacts"][0]["sha256"], digest(receipt))
        self.assertEqual(strict_json(await adapter.tools.call("canon__read", {"entity_id": "TECH-001"}))["status"], "denied")

    async def test_source_read_claim_needs_live_receipt(self):
        data, output = self.invocation()
        evidence = output["evidence"][0]
        evidence["evidence_id"] = new_id("evidence")
        evidence["verification"] = {"status": "source_read", "accessed_at": "2026-10-06T00:00:00Z",
                                    "method": "web.read", "locator": "p1", "excerpt": "fake"}
        runtime, _ = self.runtime(output)
        packet = await runtime.run_input(data)
        self.assertEqual(packet["agent_run"]["status"], "failed")

    async def test_sdk_exception_is_not_logged_as_secret(self):
        data, output = self.invocation()
        async def fail(tools):
            raise RuntimeError("SECRET_TEST_KEY do not persist")
        runtime, _ = self.runtime(output, fail)
        packet = await runtime.run_input(data)
        self.assertEqual(packet["agent_run"]["status"], "failed")
        stored = (self.repo / ".cache/runtime-runs" / data["agent_run_id"] / "completion.json").read_text()
        self.assertNotIn("SECRET_TEST_KEY", stored)

    async def test_timeout_and_cancellation_record_failure_and_close_tools(self):
        for cancelled in (False, True):
            data, output = self.invocation()
            async def fail(tools):
                if cancelled:
                    raise asyncio.CancelledError()
                await asyncio.sleep(2)
            runtime, adapter = self.runtime(output, fail, limits=RuntimeLimits(timeout_seconds=1))
            packet = await runtime.run_input(data)
            self.assertEqual(packet["agent_run"]["status"], "cancelled" if cancelled else "failed")
            self.assertTrue(adapter.tools.closed)

    async def test_session_bound_to_other_input_rejected(self):
        data, output = self.invocation()
        other, _ = self.invocation()
        runtime = AgentRuntime(self.repo, FakeAdapter(output), session_factory=lambda ignored: ToolSession(self.repo, other))
        with self.assertRaises(DataError):
            await runtime.run_input(data)

    async def test_calculation_requests_get_reusable_files_and_context_checks(self):
        for foreign in (False, True):
            data, output = self.invocation("engineering_auditor")
            output = read_json(ROOT / "examples/calculations/engineering_result-with-request.json")
            output.update({key: data[key] for key in IDENTITY})
            request = output["calculation_requests"][0]
            request.update({key: data[key] for key in (*IDENTITY[:4], "canon_version", "role")})
            request["request_id"] = new_id("artifact")
            if foreign:
                request["task_id"] = new_id("task")
            runtime, _ = self.runtime(output)
            packet = await runtime.run_input(data)
            self.assertEqual(packet["agent_run"]["status"], "failed" if foreign else "completed")
            if not foreign:
                artifact = packet["calculation_request_artifacts"][0]
                self.assertEqual(read_json(self.repo / artifact["path"]), request)
                self.assertEqual(artifact["sha256"], digest(request))

    async def test_review_packet_projection_does_not_forward_runtime_fields(self):
        from axiom_forge.runtimes import as_prior_result
        data, output = self.invocation()
        runtime, _ = self.runtime(output)
        packet = await runtime.run_input(data)
        projected = as_prior_result(packet)
        self.assertEqual(set(projected), {"stage", "agent_run", "artifact", "result"})
        projected["result"]["summary"] = "changed"
        self.assertNotEqual(projected["result"], packet["result"])
        packet["agent_run"]["status"] = "failed"
        with self.assertRaises(DataError):
            as_prior_result(packet)

    async def test_current_calculation_numbers_must_equal_program_output(self):
        class FakePython:
            def execute(self, script_id, data, workspace, call_id):
                return {"output": copy.deepcopy(data), "program": {"script_id": script_id, "sha256": "0"*64,
                        "interpreter": "TEST-FIXTURE", "exit_code": 0}}
        for tampered in (False, True):
            data, output = self.invocation("engineering_auditor")
            expected = {"inputs": [{"name": "fixture", "value": 1, "unit": "1"}],
                        "outputs": [{"name": "fixture", "value": 1, "unit": "1"}], "assumptions": ["Synthetic echo"]}
            async def calculate(tools):
                receipt = strict_json(await tools.call("python__run_reviewed", {"script_id": "synthetic", "input": {"calculation": expected}}))
                output["calculations"] = [{**copy.deepcopy(expected), "artifact_id": receipt["result_id"],
                                          "tool": "python.run_reviewed", "description": "TEST FIXTURE",
                                          "reproducible_code": "TEST FIXTURE: fake backend, not scientific computation"}]
                if tampered:
                    output["calculations"][0]["outputs"][0]["value"] = 999
            runtime = AgentRuntime(self.repo, FakeAdapter(output, calculate), session_factory=lambda data:
                                   ToolSession(self.repo, data, capabilities=["python_call"], python_backend=FakePython()))
            packet = await runtime.run_input(data)
            self.assertEqual(packet["agent_run"]["status"], "failed" if tampered else "completed")

    def test_credential_parser_does_not_evaluate_shell_syntax(self):
        from axiom_forge.runtimes.cli import credentials
        path = self.repo / ".env.fixture"
        path.write_text('OPENAI_API_KEY="TEST$(never execute)"\nANTHROPIC_API_KEY=TEST\n', encoding="utf-8")
        values = credentials(path)
        self.assertEqual(values["OPENAI_API_KEY"], "TEST$(never execute)")
        path.write_text('OPENAI_API_KEY=TEST\nOPENAI_API_KEY=OTHER\n', encoding="utf-8")
        with self.assertRaises(DataError):
            credentials(path)

    def test_expanded_schemas_are_offline_and_have_no_references(self):
        from jsonschema import Draft202012Validator
        for name in OUTPUTS.values():
            schema = expanded_schema(self.schemas, name)
            Draft202012Validator.check_schema(schema)
            self.assertNotIn('"$ref"', json.dumps(schema))

    def test_research_runtime_rejects_codex_and_invalid_limits(self):
        adapter = FakeAdapter({})
        adapter.provider = "codex"
        with self.assertRaises(ValueError):
            AgentRuntime(self.repo, adapter)
        for values in ({"max_turns": True}, {"timeout_seconds": 0}, {"max_tool_calls": 101}):
            with self.assertRaises(ValueError):
                RuntimeLimits(**values)
