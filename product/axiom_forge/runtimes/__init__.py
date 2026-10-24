"""Vendor-neutral runtime contract; optional SDKs load only in adapters."""

from .core import AgentRuntime, AdapterReply, RuntimeLimits, as_prior_result

__all__ = ["AgentRuntime", "AdapterReply", "RuntimeLimits", "as_prior_result"]
