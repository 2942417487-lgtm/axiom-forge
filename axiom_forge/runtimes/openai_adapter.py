"""OpenAI official Agents SDK adapter. No vendor imports in role/business code."""

import os
from decimal import Decimal

from .core import AdapterReply
from .endpoints import host_endpoint
from ..tools.storage import strict_json


class OpenAIAdapter:
    provider = "openai"

    def __init__(self, model, *, api_key=None, base_url=None, sdk_model=None, max_cost_usd=None,
                 input_usd_per_million=None, output_usd_per_million=None):
        if not isinstance(model, str) or not model or len(model) > 200:
            raise ValueError("An explicit model ID is required")
        self.model, self._api_key, self._sdk_model = model, api_key, sdk_model
        self.base_url = host_endpoint(base_url, "https://api.openai.com/v1", model)
        self.budget = None
        if max_cost_usd is not None:
            try:
                values = [Decimal(str(value)) for value in
                          (max_cost_usd, input_usd_per_million, output_usd_per_million)]
            except (ArithmeticError, ValueError) as exc:
                raise ValueError("Host budget requires valid verified token prices") from exc
            if any(not value.is_finite() or value <= 0 for value in values):
                raise ValueError("Positive finite host budget and verified token prices required")
            self.budget = tuple(values)

    def build_agent(self, instructions, tools, limits, model):
        from agents import Agent, FunctionTool, ModelSettings
        bound = []
        for item in tools.definitions:
            name = item["name"].replace(".", "__")
            async def invoke(context, raw, tool_name=name):
                return await tools.call(tool_name, strict_json(raw))
            bound.append(FunctionTool(name=name, description="Host-scoped Axiom Forge " + item["name"],
                                      params_json_schema=item["input_schema"], on_invoke_tool=invoke,
                                      strict_json_schema=False))
        return Agent(name="axiom_" + tools.session.context["role"], instructions=instructions,
                     model=model, tools=bound, handoffs=[],
                     model_settings=ModelSettings(max_tokens=limits.max_output_tokens,
                                                  parallel_tool_calls=False, store=False))

    async def execute(self, instructions, prompt, output_schema, tools, limits):
        from agents import Runner, RunConfig
        from agents.models.openai_responses import OpenAIResponsesModel
        from openai import AsyncOpenAI
        client = None
        try:
            model = self._sdk_model
            if model is None:
                key = self._api_key or os.environ.get("OPENAI_API_KEY")
                if not key:
                    raise ValueError("OpenAI credential is not configured")
                # Explicit trusted host endpoint; no agent-selected endpoint, automatic
                # retry, shared session or SDK global credential mutation.
                client = AsyncOpenAI(api_key=key, base_url=self.base_url,
                                     max_retries=0, timeout=limits.timeout_seconds)
                model = OpenAIResponsesModel(model=self.model, openai_client=client)
            agent = self.build_agent(instructions, tools, limits, model)
            if self.budget:
                agent.model = budget_model(model, self.budget)
            result = await Runner.run(agent, input=prompt, max_turns=limits.max_turns,
                                      run_config=RunConfig(tracing_disabled=True,
                                                           trace_include_sensitive_data=False))
            usage = result.context_wrapper.usage
            response_id = result.raw_responses[-1].response_id if result.raw_responses else None
            return AdapterReply(result.final_output, session_id=response_id, input_tokens=usage.input_tokens,
                                output_tokens=usage.output_tokens)
        finally:
            if client is not None:
                await client.close()


def budget_model(upstream, budget):
    """Reserve a conservative text request allowance before each SDK model call.

    This is a local estimate using host-verified prices, not a billing authority.
    No hosted paid tools, server continuation, images or automatic retries here.
    """
    from agents import Model
    from ..validation import canonical_bytes
    maximum, input_rate, output_rate = budget

    class BudgetModel(Model):
        def __init__(self):
            self.reserved = Decimal(0)

        async def get_response(self, system_instructions, input, model_settings, tools,
                               output_schema, handoffs, tracing, **kwargs):
            if kwargs.get("previous_response_id") or kwargs.get("conversation_id") or kwargs.get("prompt"):
                raise ValueError("Budgeted runtime cannot use hidden server-managed context")
            schemas = [{"name": item.name, "schema": item.params_json_schema} for item in tools]
            # UTF-8 bytes deliberately overestimate text tokens; reserve additional
            # protocol overhead. Keep unused reservations for the entire invocation.
            size = len(canonical_bytes({"instructions": system_instructions, "input": input,
                                        "tools": schemas})) + 32768
            if not model_settings.max_tokens:
                raise ValueError("Budgeted invocation requires an output token cap")
            allowance = (Decimal(size) * input_rate + Decimal(model_settings.max_tokens) * output_rate) / 1000000
            if self.reserved + allowance > maximum:
                raise ValueError("Local conservative API allowance exhausted")
            self.reserved += allowance
            return await upstream.get_response(system_instructions=system_instructions, input=input,
                         model_settings=model_settings, tools=tools, output_schema=output_schema,
                         handoffs=handoffs, tracing=tracing, **kwargs)

        async def stream_response(self, *args, **kwargs):
            raise ValueError("Budgeted adapter does not expose streaming execution")
            yield  # SDK abstract async-generator contract.

    return BudgetModel()
