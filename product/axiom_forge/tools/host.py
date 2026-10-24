"""Tool configuration for trusted operators, never model-controlled arguments."""

from .network import PublicHTTPS
from .python_backend import TrustedPython
from .session import ToolSession
from ..workspaces import require_world
from ..validation import DataError, read_json


def session_from_config(repo, context, config):
    world = require_world(repo)
    engine = world.engine.root
    allowed = {"capabilities", "network_hosts", "documents", "contact", "enable_trusted_python", "python_timeout"}
    if (not isinstance(config, dict) or set(config) - allowed
            or not isinstance(config.get("capabilities", []), list)
            or not isinstance(config.get("network_hosts", []), list)
            or not isinstance(config.get("documents", {}), dict)
            or type(config.get("enable_trusted_python", False)) is not bool):
        raise DataError("Invalid trusted Tool Layer config")
    network = PublicHTTPS(config["network_hosts"], contact=config.get("contact")) if config.get("network_hosts") else None
    backend = TrustedPython(engine, read_json(engine / "resources/tools/python-scripts/manifest.json"),
                            enabled=config.get("enable_trusted_python", False), timeout=config.get("python_timeout", 10))
    return ToolSession(world, context, capabilities=config.get("capabilities", []),
                       documents=config.get("documents", {}), network=network, python_backend=backend)
