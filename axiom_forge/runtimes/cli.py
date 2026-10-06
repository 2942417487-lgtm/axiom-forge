"""Explicit operator entrypoint. SDK execution is disabled without --allow-live."""

import asyncio
import math

from .core import AgentRuntime, RuntimeLimits
from .endpoints import host_endpoint, host_proxy
from ..tools.host import session_from_config
from ..tools.storage import read_bounded
from ..validation import DataError, canonical_bytes, read_json


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


def validate_host_config(config):
    allowed = {"provider", "model", "limits", "tools", "max_cost_usd", "input_usd_per_million",
               "output_usd_per_million", "claude_cli_path", "base_url", "claude_auth_mode",
               "claude_disable_experimental_betas", "claude_https_proxy"}
    if (not isinstance(config, dict) or set(config) - allowed or config.get("provider") not in ("claude", "openai")
            or not isinstance(config.get("model"), str) or not config["model"]):
        raise DataError("Explicit provider/model and closed host Runtime config required")
    canonical_bytes(config)
    limits = config.get("limits", {})
    if not isinstance(limits, dict) or set(limits) - set(RuntimeLimits.__dataclass_fields__):
        raise DataError("Closed host Runtime limits required")
    RuntimeLimits(**limits)
    if not isinstance(config.get("tools", {}), dict):
        raise DataError("Host tool grants must be an object")
    for field in ("max_cost_usd", "input_usd_per_million", "output_usd_per_million"):
        value = config.get(field)
        if field in config and (type(value) not in (int, float) or not math.isfinite(value) or value <= 0):
            raise DataError("Positive finite host budget/price required")
    if config["provider"] == "openai" and "max_cost_usd" in config and not all(field in config for field in ("input_usd_per_million", "output_usd_per_million")):
        raise DataError("Budgeted OpenAI profile requires verified token prices")
    host_endpoint(config.get("base_url"), "https://api.openai.com/v1" if config["provider"] == "openai" else "https://api.anthropic.com", config["model"])
    if "claude_https_proxy" in config: host_proxy(config["claude_https_proxy"])
    if config.get("claude_auth_mode", "api_key") not in ("api_key", "auth_token") or type(config.get("claude_disable_experimental_betas", False)) is not bool:
        raise DataError("Invalid host Claude options")
    if "claude_cli_path" in config and not isinstance(config["claude_cli_path"], str):
        raise DataError("Claude CLI path must be a host-selected string")
    return config


def runtime_from_config(repo, config, keys):
    """Shared trusted host factory; callers gate live authorization before reading keys."""
    validate_host_config(config)
    provider = config["provider"]
    if provider == "claude":
        from .claude_adapter import ClaudeAdapter
        cli_path = config.get("claude_cli_path")
        if cli_path is not None:
            cli_path = str((repo / cli_path).absolute())
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
    return AgentRuntime(repo, adapter, limits=limits, session_factory=lambda data:
                         session_from_config(repo, data, config.get("tools", {})))


def run(args):
    if not args.allow_live:
        raise DataError("Runtime execution requires the operator's --allow-live flag")
    config = validate_host_config(read_json(args.config))
    keys = credentials(args.credentials)
    runtime = runtime_from_config(args.repo, config, keys)
    return asyncio.run(runtime.run_input(read_json(args.context)))
