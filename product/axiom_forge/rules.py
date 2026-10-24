"""Trusted product policy locations and bounded research instruction assembly."""

from .tools.storage import read_bounded

POLICY_FILES = tuple("resources/policies/" + name + ".md" for name in ("common", "research", "host"))


def research_instructions(root, data):
    paths = [*POLICY_FILES[:2], "resources/agents/" + data["role"] + ".md"]
    if data["role"] in ("engineering_auditor", "economic_auditor"):
        paths.append("resources/calculations/protocol.md")
    if data.get("mode_protocol") == "1.0":
        paths.append("resources/modes/" + data["task_type"] + ".md")
    return "\n\n".join(read_bounded(root / path).decode("utf-8") for path in paths)
