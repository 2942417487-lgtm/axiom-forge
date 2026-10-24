"""Actual official SDK objects with fake models/clients; no paid calls."""

import importlib.metadata
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tests import test_runtimes as runtime_fixtures
from tests.test_runtimes import ROOT
from axiom_forge.ids import new_id
from axiom_forge.runtimes import AgentRuntime, RuntimeLimits
from axiom_forge.runtimes.core import ToolBinding
from axiom_forge.runtimes.claude_adapter import ClaudeAdapter
from axiom_forge.runtimes.codex_adapter import CodexRuntime
from axiom_forge.runtimes.openai_adapter import OpenAIAdapter
from axiom_forge.tools import ToolSession
from axiom_forge.tools.storage import strict_json
from axiom_forge.validation import DataError


def sdk_installed():
    try:
        for name in ("openai-agents", "claude-agent-sdk", "openai-codex"):
            importlib.metadata.version(name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


async def mcp_read(options):
    """Exercise the real in-memory MCP transport and SDK server handler."""
    import anyio
    from mcp import ClientSession
    from mcp.shared.memory import create_client_server_memory_streams
    server = options.mcp_servers["axiom"]["instance"]
    async with create_client_server_memory_streams() as (client_streams, server_streams):
        async with anyio.create_task_group() as group:
            group.start_soon(server.run, *server_streams, server.create_initialization_options())
            async with ClientSession(*client_streams) as client:
                await client.initialize()
                listed = await client.list_tools()
                assert {tool.name for tool in listed.tools} == {"canon__read", "evidence__read"}
                result = await client.call_tool("canon__read", {"entity_id": "TECH-001"})
                text = result.content[0].text
            group.cancel_scope.cancel()
    return strict_json(text)


@unittest.skipUnless(sdk_installed(), "Install optional runtimes/requirements.txt for SDK tests")
class SDKTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(runtime_fixtures.RuntimeTests.setUpClass.__func__)
    tearDownClass = classmethod(runtime_fixtures.RuntimeTests.tearDownClass.__func__)
    invocation = runtime_fixtures.RuntimeTests.invocation

    def model(self, output, *, call_tool=True):
        from agents import Model
        from agents.models.interface import ModelResponse
        from agents.usage import Usage
        from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText
        class FakeModel(Model):
            count = 0
            async def get_response(model_self, **kwargs):
                model_self.count += 1
                assert kwargs["model_settings"].store is False
                assert kwargs["model_settings"].parallel_tool_calls is False
                if call_tool and model_self.count == 1:
                    content = [ResponseFunctionToolCall(type="function_call", name="canon__read",
                               arguments='{"entity_id":"TECH-001"}', call_id="synthetic-tool", id="synthetic-fc")]
                else:
                    content = [ResponseOutputMessage(type="message", role="assistant", status="completed", id="synthetic-msg",
                               content=[ResponseOutputText(type="output_text", text=json.dumps(output), annotations=[])])]
                return ModelResponse(content, Usage(requests=1, input_tokens=10, output_tokens=20, total_tokens=30),
                                     response_id="synthetic-response")
            async def stream_response(model_self, *args, **kwargs):
                raise AssertionError("Unexpected stream")
                yield
        return FakeModel()

    async def test_openai_real_runner_calls_scoped_tool_and_validates_result(self):
        data, output = self.invocation()
        model = self.model(output)
        adapter = OpenAIAdapter("TEST-FIXTURE", sdk_model=model)
        runtime = AgentRuntime(self.workspace, adapter, session_factory=lambda data: ToolSession(self.workspace, data, capabilities=["canon_read"]))
        packet = await runtime.run_input(data)
        self.assertEqual(packet["agent_run"]["status"], "completed")
        self.assertEqual(model.count, 2)
        self.assertEqual(packet["agent_run"]["metadata"]["input_tokens"], 20)
        self.assertEqual(packet["tool_artifacts"][0]["metadata"]["tool_name"], "canon.read")

    async def test_openai_budget_blocks_before_model_request(self):
        data, output = self.invocation()
        model = self.model(output, call_tool=False)
        runtime = AgentRuntime(self.workspace, OpenAIAdapter("TEST-FIXTURE", sdk_model=model,
                  max_cost_usd=0.000001, input_usd_per_million=2, output_usd_per_million=10))
        packet = await runtime.run_input(data)
        self.assertEqual(packet["agent_run"]["status"], "failed")
        self.assertEqual(model.count, 0)

    async def test_openai_budget_accepts_known_bounded_request(self):
        data, output = self.invocation()
        model = self.model(output, call_tool=False)
        runtime = AgentRuntime(self.workspace, OpenAIAdapter("TEST-FIXTURE", sdk_model=model,
                  max_cost_usd=0.5, input_usd_per_million=2, output_usd_per_million=10))
        packet = await runtime.run_input(data)
        self.assertEqual(packet["agent_run"]["status"], "completed")
        self.assertEqual(model.count, 1)

    async def test_relay_endpoints_route_only_to_explicit_host(self):
        data, output = self.invocation()
        upstream = self.model(output, call_tool=False)
        owner = self
        class FakeClient:
            def __init__(self, **kwargs):
                owner.assertEqual(kwargs["base_url"], "https://zenmux.ai/api/v1")
                owner.assertEqual(kwargs["api_key"], "TEST-RELAY-KEY")
                owner.assertEqual(kwargs["max_retries"], 0)
            async def close(self):
                pass
        with patch("openai.AsyncOpenAI", FakeClient), patch(
                "agents.models.openai_responses.OpenAIResponsesModel", return_value=upstream) as constructor:
            runtime = AgentRuntime(self.workspace, OpenAIAdapter("openai/gpt-6.1-sol",
                api_key="TEST-RELAY-KEY", base_url="https://zenmux.ai/api/v1"))
            packet = await runtime.run_input(data)
        self.assertEqual(packet["agent_run"]["status"], "completed")
        self.assertEqual(constructor.call_args.kwargs["model"], "openai/gpt-6.1-sol")
        session = ToolSession(self.workspace, data, capabilities=["canon_read"])
        options = ClaudeAdapter("anthropic/claude-sonnet-5.5", api_key="TEST-RELAY-KEY",
            base_url="https://zenmux.ai/api/anthropic").build_options("test", ToolBinding(session, RuntimeLimits()), RuntimeLimits())
        self.assertEqual(options.model, "anthropic/claude-sonnet-5.5")
        self.assertEqual(options.env["ANTHROPIC_BASE_URL"], "https://zenmux.ai/api/anthropic")
        self.assertEqual(options.env["ANTHROPIC_API_KEY"], "TEST-RELAY-KEY")
        gateway = ClaudeAdapter("anthropic/claude-sonnet-5.5", api_key="TEST-RELAY-KEY",
            base_url="https://zenmux.ai/api/anthropic", auth_mode="auth_token",
            disable_experimental_betas=True, https_proxy="http://127.0.0.1:10081").build_options("test", ToolBinding(session, RuntimeLimits()), RuntimeLimits())
        self.assertEqual(gateway.env["ANTHROPIC_API_KEY"], "")
        self.assertEqual(gateway.env["ANTHROPIC_AUTH_TOKEN"], "TEST-RELAY-KEY")
        self.assertEqual(gateway.env["CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS"], "1")
        self.assertEqual(gateway.env["CLAUDE_CODE_ATTRIBUTION_HEADER"], "0")
        self.assertEqual(gateway.env["CLAUDE_CODE_MAX_RETRIES"], "0")
        self.assertEqual(gateway.env["CLAUDE_CODE_NONSTREAMING_TIMEOUT_RETRIES"], "0")
        self.assertEqual(gateway.env["API_TIMEOUT_MS"], "120000")
        self.assertEqual(gateway.env["HTTPS_PROXY"], "http://127.0.0.1:10081")

    async def test_endpoint_validation_prevents_implicit_relay_routing(self):
        self.assertEqual(OpenAIAdapter("gpt-6.1-sol").base_url, "https://api.openai.com/v1")
        self.assertEqual(ClaudeAdapter("claude-sonnet-5-5").base_url, "https://api.anthropic.com")
        for adapter in (OpenAIAdapter, ClaudeAdapter):
            with self.assertRaises(ValueError):
                adapter("vendor/model")
            for url in ("http://relay.example/v1", "https://key@relay.example/v1",
                        "https://relay.example/v1?token=secret", "https://relay.example/v1#key",
                        "https://relay.example\\@other.example", "https://relay.example:invalid",
                        "https://relay.example/\n", "https:///v1", 123):
                with self.subTest(adapter=adapter.provider, url=url), self.assertRaises(ValueError):
                    adapter("vendor/model", base_url=url)
        with self.assertRaises(ValueError):
            ClaudeAdapter("fixture", auth_mode="automatic")
        with self.assertRaises(ValueError):
            ClaudeAdapter("fixture", disable_experimental_betas="yes")
        for proxy in ("socks5://127.0.0.1:10081", "http://key@proxy.example", "http://proxy.example/path",
                      "http://proxy.example?token=x", "http://proxy.example:bad", False):
            with self.subTest(proxy=proxy), self.assertRaises(ValueError):
                ClaudeAdapter("fixture", https_proxy=proxy)

    async def test_claude_sdk_tools_have_real_mcp_transport_and_deny_native_tools(self):
        from claude_agent_sdk import ResultMessage
        data, output = self.invocation()
        owner = self
        class FakeClient:
            def __init__(self, options):
                self.options = options
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return False
            async def query(self, prompt):
                owner.assertEqual(self.options.tools, [])
                owner.assertEqual(self.options.skills, [])
                owner.assertEqual(self.options.setting_sources, [])
                owner.assertTrue(self.options.strict_mcp_config)
                owner.assertIsNone(self.options.resume)
                denied = await self.options.can_use_tool("Bash", {}, None)
                owner.assertEqual(denied.behavior, "deny")
                hook = self.options.hooks["PreToolUse"][0].hooks[0]
                verdict = await hook({"tool_name": "Read"}, "fake", {})
                owner.assertEqual(verdict["hookSpecificOutput"]["permissionDecision"], "deny")
                result = await mcp_read(self.options)
                owner.assertEqual(result["status"], "completed")
            async def receive_response(self):
                yield ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
                                    num_turns=2, session_id="synthetic-claude", result=json.dumps(output),
                                    usage={"input_tokens": 10, "output_tokens": 20,
                                           "cache_creation_input_tokens": 100, "cache_read_input_tokens": 200}, total_cost_usd=0)
        adapter = ClaudeAdapter("TEST-FIXTURE", client_factory=FakeClient)
        runtime = AgentRuntime(self.workspace, adapter, session_factory=lambda data: ToolSession(self.workspace, data, capabilities=["canon_read"]))
        packet = await runtime.run_input(data)
        self.assertEqual(packet["agent_run"]["status"], "completed")
        self.assertEqual(len(packet["tool_artifacts"]), 1)
        self.assertEqual(packet["agent_run"]["metadata"]["provider_session_id"], "synthetic-claude")
        self.assertEqual(packet["agent_run"]["metadata"]["input_tokens"], 310)
        self.assertEqual(packet["agent_run"]["metadata"]["cache_creation_input_tokens"], 100)
        self.assertEqual(packet["agent_run"]["metadata"]["cache_read_input_tokens"], 200)

    async def test_codex_scope_permissions_and_sdk_metadata(self):
        from openai_codex import ApprovalMode, Sandbox
        from openai_codex.types import ThreadTokenUsage
        owner = self
        class FakeCodex:
            def __init__(self, config):
                owner.assertEqual(config.env.get("ANTHROPIC_API_KEY"), "")
                owner.assertEqual(config.env["CODEX_INTERNAL_ORIGINATOR_OVERRIDE"], "axiom_forge_runtime")
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def thread_start(self, **kwargs):
                owner.assertTrue(kwargs["ephemeral"])
                owner.assertEqual(kwargs["sandbox"], Sandbox.read_only)
                owner.assertEqual(kwargs["approval_mode"], ApprovalMode.deny_all)
                usage = {"inputTokens": 10, "outputTokens": 20, "cachedInputTokens": 0,
                         "reasoningOutputTokens": 0, "totalTokens": 30}
                async def run(issue):
                    return SimpleNamespace(status="completed", error=None, id="synthetic-turn",
                        final_response="TEST FIXTURE engineering answer", usage=ThreadTokenUsage(total=usage, last=usage))
                return SimpleNamespace(id="synthetic-thread", run=run)
        runtime = CodexRuntime(self.engine, allow_login_reuse=True, sdk_factory=FakeCodex)
        task = {"task_id": new_id("task"), "issue": "TEST FIXTURE engineering issue", "files": {"fixture.py": "# fixture"}}
        state = {key: new_id(key.removesuffix("_id")) for key in ("run_id", "agent_run_id", "artifact_id")}
        with self.assertRaises(DataError):
            await runtime.run("engineering_auditor", task, state)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "TEST-SECRET"}):
            packet = await runtime.run("software_engineer", task, state)
        self.assertEqual(packet["status"], "completed")
        self.assertEqual(packet["metadata"]["provider_thread_id"], "synthetic-thread")
        self.assertEqual(packet["metadata"]["input_tokens"], 10)
        self.assertNotIn("TEST-SECRET", json.dumps(packet))

    async def test_codex_unsafe_job_paths_and_login_gate_rejected_before_sdk(self):
        task = {"task_id": new_id("task"), "issue": "test", "files": {"../world/world.json": "unsafe"}}
        state = {key: new_id(key.removesuffix("_id")) for key in ("run_id", "agent_run_id", "artifact_id")}
        with self.assertRaises(DataError):
            await CodexRuntime(self.engine).run("software_engineer", task, state)
        with self.assertRaises(DataError):
            await CodexRuntime(self.engine, allow_login_reuse=True).run("software_engineer", task, state)
