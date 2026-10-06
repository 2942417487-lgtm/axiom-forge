"""Explicit operator entrypoint. SDK execution is disabled without --allow-live."""

import asyncio

from .core import AgentRuntime, RuntimeLimits
from ..tools.host import session_from_config
from ..tools.storage import read_bounded
from ..validation import DataError, read_json


def credentials(path):
    """Read only a caller-selected file; do not eval shell syntax or export secrets."""
    if path is None:
        return {}
    result = {}
    for line in read_bounded(path, limit=16384).decode("utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise DataError("Credential file requires KEY=value lines")
        key, value = key.strip(), value.strip()
        if key not in {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"}:
            continue
        if key in result:
            raise DataError("Duplicate credential variable")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result


def run(args):
    if not args.allow_live:
        raise DataError("Runtime execution requires the operator's --allow-live flag")
    config = read_json(args.config)
    allowed = {"provider", "model", "limits", "tools", "max_cost_usd", "input_usd_per_million",
               "output_usd_per_million", "claude_cli_path", "base_url", "claude_auth_mode",
               "claude_disable_experimental_betas", "claude_https_proxy"}
    if (set(config) - allowed or config.get("provider") not in ("claude", "openai")
            or not isinstance(config.get("model"), str) or not config["model"]):
        raise DataError("Explicit provider/model and closed host Runtime config required")
    keys = credentials(args.credentials)
    provider = config["provider"]
    if provider == "claude":
        from .claude_adapter import ClaudeAdapter
        cli_path = config.get("claude_cli_path")
        if cli_path is not None:
            cli_path = str((args.repo / cli_path).absolute())
        adapter = ClaudeAdapter(config["model"], api_key=keys.get("ANTHROPIC_API_KEY"),
                                base_url=config.get("base_url"),
                                auth_mode=config.get("claude_auth_mode", "api_key"),
                                disable_experimental_betas=config.get("claude_disable_experimental_betas", False),
                                https_proxy=config.get("claude_https_proxy"),
                                cli_path=cli_path, max_budget_usd=config.get("max_cost_usd"))
    else:
        from .openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(config["model"], api_key=keys.get("OPENAI_API_KEY"),
                               base_url=config.get("base_url"),
                               max_cost_usd=config.get("max_cost_usd"),
                               input_usd_per_million=config.get("input_usd_per_million"),
                               output_usd_per_million=config.get("output_usd_per_million"))
    limits = RuntimeLimits(**config.get("limits", {}))
    runtime = AgentRuntime(args.repo, adapter, limits=limits, session_factory=lambda data:
                           session_from_config(args.repo, data, config.get("tools", {})))
    return asyncio.run(runtime.run_input(read_json(args.context)))
