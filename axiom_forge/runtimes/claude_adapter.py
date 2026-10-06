"""Official Claude Agent SDK with a private in-process SDK MCP binding."""

import math
import os

from .core import AdapterReply
from ..tools.storage import MAX_BYTES


class ClaudeAdapter:
    provider = "claude"

    def __init__(self, model, *, api_key=None, cli_path=None, max_budget_usd=None, client_factory=None):
        if not isinstance(model, str) or not model or len(model) > 200:
            raise ValueError("An explicit Claude model ID is required")
        if max_budget_usd is not None and (type(max_budget_usd) not in (int, float)
                or not math.isfinite(max_budget_usd) or max_budget_usd <= 0):
            raise ValueError("Invalid Claude budget")
        self.model, self._api_key, self.cli_path = model, api_key, cli_path
        self.max_budget_usd, self._client_factory = max_budget_usd, client_factory

    def build_options(self, instructions, tools, limits):
        from claude_agent_sdk import (ClaudeAgentOptions, HookMatcher, PermissionResultDeny,
                                      create_sdk_mcp_server, tool)
        bound = []
        for item in tools.definitions:
            name = item["name"].replace(".", "__")
            async def invoke(arguments, tool_name=name):
                text = await tools.call(tool_name, arguments)
                return {"content": [{"type": "text", "text": text}]}
            bound.append(tool(name, "Host-scoped Axiom Forge " + item["name"], item["input_schema"])(invoke))
        names = {"mcp__axiom__" + name for name in tools.names}
        async def deny_other(tool_name, arguments, context):
            return PermissionResultDeny(message="Only host-bound Axiom Forge tools are authorized")
        async def before_tool(event, tool_use_id, context):
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                      "permissionDecision": "allow" if event.get("tool_name") in names else "deny",
                      "permissionDecisionReason": "Fixed host tool grant"}}
        preserved = {"SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "USERPROFILE", "HOME", "HOMEDRIVE",
                     "HOMEPATH", "TEMP", "TMP", "TMPDIR", "COMSPEC", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY"}
        # SDK merges this over its inherited environment. Blank unrelated values
        # without changing the host environment or exposing them to MCP tools.
        environment = {key: "" for key in os.environ if key.upper() not in preserved}
        environment.update(ANTHROPIC_API_KEY=self._api_key or os.environ.get("ANTHROPIC_API_KEY", ""),
                           ANTHROPIC_BASE_URL="https://api.anthropic.com",
                           CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1", DISABLE_AUTOUPDATER="1",
                           CLAUDE_CODE_MAX_OUTPUT_TOKENS=str(limits.max_output_tokens))
        directory = tools.session.workspace.path("claude")
        directory.mkdir(parents=True, exist_ok=True)
        return ClaudeAgentOptions(model=self.model, system_prompt=instructions, tools=[], skills=[], agents={},
                    allowed_tools=sorted(names), disallowed_tools=["Bash", "PowerShell", "Read", "Write", "Edit",
                    "Glob", "Grep", "Agent", "Task", "WebFetch", "WebSearch", "Skill"],
                    mcp_servers={"axiom": create_sdk_mcp_server(name="axiom", version="1.0.0", tools=bound)},
                    strict_mcp_config=True, setting_sources=[], plugins=[], permission_mode="default",
                    can_use_tool=deny_other, hooks={"PreToolUse": [HookMatcher(hooks=[before_tool])]},
                    cwd=directory, cli_path=self.cli_path, env=environment, max_turns=limits.max_turns,
                    max_budget_usd=self.max_budget_usd, max_buffer_size=MAX_BYTES,
                    continue_conversation=False, resume=None, stderr=lambda line: None,
                    extra_args={"no-session-persistence": None})

    async def execute(self, instructions, prompt, output_schema, tools, limits):
        from claude_agent_sdk import ClaudeSDKClient, ResultMessage
        options = self.build_options(instructions, tools, limits)
        if not options.env["ANTHROPIC_API_KEY"] and self._client_factory is None:
            raise ValueError("Claude API credential is not configured")
        factory = self._client_factory or ClaudeSDKClient
        terminal = None
        async with factory(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                # Do not collect intermediate text, thinking blocks or raw SDK errors.
                if isinstance(message, ResultMessage):
                    terminal = message
        if terminal is None or terminal.is_error or terminal.subtype != "success" or not terminal.result:
            raise ValueError("Claude did not return a successful final result")
        usage = terminal.usage or {}
        return AdapterReply(terminal.result, terminal.session_id, usage.get("input_tokens"),
                            usage.get("output_tokens"), terminal.total_cost_usd)
