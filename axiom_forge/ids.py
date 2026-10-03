"""Project-owned identifiers; never use vendor sessions as business keys."""

from uuid import uuid4


DOMAIN_PREFIXES = {
    "physics": "PHY", "astronomy": "AST", "technology": "TECH",
    "engineering": "ENG", "economy": "ECO", "society": "SOC",
    "politics": "POL", "history": "HIS", "timeline": "TML",
    "actors": "ACT", "assumptions": "ASM", "audits": "AUD", "decisions": "DEC",
}
ID_PREFIXES = {
    "world": "WLD", "task": "TSK", "run": "RUN", "agent_run": "ARN",
    "artifact": "ART", "snapshot": "SNP", "proposal": "CHG",
    "claim": "CLM", "evidence": "EVD",
}


def new_id(kind: str, domain: str | None = None) -> str:
    if kind == "entity":
        if domain not in DOMAIN_PREFIXES:
            raise ValueError("Entity IDs require a supported domain")
        prefix = DOMAIN_PREFIXES[domain]
    else:
        if domain is not None or kind not in ID_PREFIXES:
            raise ValueError("Unsupported ID kind or unexpected domain")
        prefix = ID_PREFIXES[kind]
    return f"{prefix}-{uuid4()}"
