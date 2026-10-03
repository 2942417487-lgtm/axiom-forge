"""Vendor-neutral role contracts and local input/output checks, without execution."""

import copy
from datetime import datetime
from pathlib import Path

from .snapshots import verify_snapshot
from .validation import (
    DataError, KNOWLEDGE_DIRECTORIES, SchemaStore, digest, read_json,
    validate_claims, validate_dataset, validate_task,
)


SPECIALISTS = ("researcher", "engineering_auditor", "economic_auditor", "historical_analyst")
OUTPUTS = {
    "lead": "lead_plan", "researcher": "research_result",
    "engineering_auditor": "engineering_result", "economic_auditor": "economic_result",
    "historical_analyst": "historical_result", "redteam": "redteam_result",
    "integrator": "synthesis_result",
}
STAGES = {
    "lead": ("planning",),
    **{role: ("independent", "cross_review") for role in SPECIALISTS},
    "redteam": ("redteam",),
    "integrator": ("draft_synthesis", "final_synthesis"),
}
IDENTITY = ("world_id", "task_id", "run_id", "agent_run_id", "artifact_id", "canon_version")
FORBIDDEN = ["canon_write", "canon_apply", "human_approval", "git_mutation"]


class ContractStore:
    def __init__(self, repo: Path, schemas: SchemaStore | None = None):
        self.schemas = schemas or SchemaStore(repo / "schemas")
        self.contracts = {}
        paths = sorted((repo / "agents/contracts").glob("*.json"))
        for path in paths:
            contract = read_json(path)
            self.schemas.validate("agent_contract", contract)
            role = contract["role"]
            if path.stem != role or role in self.contracts:
                raise DataError("Duplicate or misnamed role contract")
            if (contract["output_schema"] != OUTPUTS[role]
                    or contract["stages"] != list(STAGES[role])
                    or contract["forbidden_capabilities"] != FORBIDDEN):
                raise DataError(f"Contract changes a protected role boundary: {role}")
            for field, expected in (("prompt_file", f"agents/{role}.md"),
                                    ("claude_file", f".claude/agents/{role.replace('_', '-')}.md")):
                if contract[field] != expected:
                    raise DataError(f"Unexpected {field}: {role}")
                target = repo / expected
                if not target.resolve().is_relative_to(repo.resolve()) or not target.is_file():
                    raise DataError(f"Missing or unsafe {field}: {role}")
            self.contracts[role] = contract
        if set(self.contracts) != set(OUTPUTS):
            raise DataError("Exactly seven role contracts are required")

    def validate_input(self, data: dict):
        validate_agent_input(data, self.schemas)

    def validate_output(self, data: dict, result: dict):
        validate_agent_output(data, result, self.schemas)


def project_input(task: dict, execution: dict, role: str, stage: str,
                  selected_specialists: list[str], schemas: SchemaStore,
                  *, prior_results=None, supporting_artifacts=None) -> dict:
    """Copy an explicit allowlist; never automatically forward TaskState results/metadata."""
    validate_task(task, schemas)
    if set(execution) != {"run_id", "agent_run_id", "artifact_id"}:
        raise DataError("Execution must contain only three system-generated business IDs")
    data = {key: copy.deepcopy(task[key]) for key in (
        "world_id", "task_id", "canon_version", "canon_snapshot",
        "user_question", "task_type", "relevant_entities",
    )}
    data.update(copy.deepcopy(execution))
    data.update(schema_version="1.0", role=role, stage=stage,
                selected_specialists=copy.deepcopy(selected_specialists),
                prior_results=copy.deepcopy(prior_results or []),
                supporting_artifacts=copy.deepcopy(supporting_artifacts or []))
    validate_agent_input(data, schemas)
    return data


def _same_context(record, data):
    if any(record[key] != data[key] for key in ("world_id", "task_id", "run_id")):
        raise DataError("Prior record world/task/run differs")
    if "canon_version" in record and record["canon_version"] != data["canon_version"]:
        raise DataError("Prior record snapshot version differs")


def _validate_packets(data, schemas):
    roles, agents, artifacts, first_completed = set(), set(), {}, set()
    for artifact in data["supporting_artifacts"]:
        _same_context(artifact, data)
        if artifact["artifact_id"] in artifacts or artifact["artifact_id"] == data["artifact_id"]:
            raise DataError("Duplicate or current output supporting artifact")
        artifacts[artifact["artifact_id"]] = artifact
    for packet in data["prior_results"]:
        agent, artifact, result = (packet[key] for key in ("agent_run", "artifact", "result"))
        role = agent["role"]
        if role == "lead":
            raise DataError("Planning output is not a prior scientific result")
        if packet["stage"] not in STAGES[role] or (role == "integrator" and packet["stage"] != "draft_synthesis"):
            raise DataError("Prior result has an invalid role/stage")
        schemas.validate(OUTPUTS[role], result)
        for record in (agent, artifact, result):
            _same_context(record, data)
        if (agent["status"] != "completed" or agent["finished_at"] is None
                or datetime.fromisoformat(agent["finished_at"]) < datetime.fromisoformat(agent["started_at"])):
            raise DataError("Prior result requires a completed execution receipt")
        if any(agent[key] != result[key] or artifact[key] != result[key]
               for key in ("agent_run_id", "artifact_id")):
            raise DataError("Prior result execution/artifact identity differs")
        if artifact["sha256"] != digest(result):
            raise DataError("Prior result artifact hash differs")
        if (agent["agent_run_id"] in agents or agent["agent_run_id"] == data["agent_run_id"]
                or artifact["artifact_id"] in artifacts or artifact["artifact_id"] == data["artifact_id"]):
            raise DataError("Duplicate or current output prior execution")
        agents.add(agent["agent_run_id"])
        artifacts[artifact["artifact_id"]] = artifact
        roles.add(role)
        if packet["stage"] == "independent":
            first_completed.add(role)
    return roles, artifacts, first_completed


def _validate_relations(data, results, schemas, artifacts, current_output=None):
    dataset = verify_snapshot(data["canon_snapshot"], schemas)
    entities, evidence = dict(dataset["entities"]), dict(dataset["evidence"])
    proposals = {}
    for result in results:
        for record in result.get("evidence", []):
            identifier = record["evidence_id"]
            if identifier in evidence and evidence[identifier] != record:
                raise DataError("Conflicting evidence records")
            evidence[identifier] = record
    # A final Integrator may revise or withdraw a draft proposal. Historical drafts
    # have already been validated as input; they are not simultaneous Apply requests.
    proposal_results = ([current_output] if current_output is not None
                        and current_output["result_type"] == "synthesis" else results)
    for result in proposal_results:
        for change in result.get("proposed_changes", []):
            schemas.validate("canon_change", change)
            if change["approval"]["status"] != "pending":
                raise DataError("Agent can only propose pending CanonChanges")
            if (change["world_id"] != data["world_id"] or change["task_id"] != data["task_id"]
                    or change["run_id"] != data["run_id"]
                    or change["base_canon_version"] != data["canon_version"]
                    or change["before"] != dataset["entities"].get(change["target_entity_id"])):
                raise DataError("CanonChange context/before differs from fixed snapshot")
            identifier = change["proposal_id"]
            if identifier in proposals and proposals[identifier] != change:
                raise DataError("Conflicting CanonChange copies")
            proposals[identifier] = change
            if change["after"] is not None:
                entities[change["target_entity_id"]] = change["after"]
    files = {record["path"]: record["data"] for record in data["canon_snapshot"]["files"]}
    files.update({f"world/evidence/{key}.json": value for key, value in evidence.items()})
    targets = set()
    for change in proposals.values():
        target = change["target_entity_id"]
        if target in targets:
            raise DataError("Multiple proposals modify the same entity")
        targets.add(target)
        if not set(change["provenance"]["evidence_ids"]).issubset(evidence):
            raise DataError("CanonChange provenance references unknown evidence")
        if change["before"] is not None:
            original = next(path for path, record in files.items() if record.get("entity_id") == target)
            del files[original]
        if change["after"] is not None:
            entry = change["after"]
            directory = next(directory for directory, (_, domain) in KNOWLEDGE_DIRECTORIES.items()
                             if domain == entry["domain"])
            files[f"{directory}/{target}.json"] = entry
    validate_dataset(files, schemas)  # In-memory proposal checks; never Canon Apply.
    checked_results = [current_output] if current_output is not None else results
    for result in checked_results:
        validate_claims(result["claims"], evidence, entities)
        for calculation in result.get("calculations", []):
            artifact = artifacts.get(calculation["artifact_id"])
            if artifact is None:
                raise DataError("Calculation supporting artifact is missing")
        for chain in result.get("causal_chains", []):
            if not set(chain["evidence_ids"]).issubset(evidence):
                raise DataError("Causal chain references unknown evidence")
        for conflict in result.get("contradictions", []):
            if (not set(conflict["entity_ids"]).issubset(entities)
                    or not set(conflict["evidence_ids"]).issubset(evidence)):
                raise DataError("Conflict references unknown entity/evidence")


def validate_agent_input(data: dict, schemas: SchemaStore):
    schemas.validate("agent_input", data)
    role, stage = data["role"], data["stage"]
    if stage not in STAGES[role]:
        raise DataError("Role is not allowed in this stage")
    snapshot = data["canon_snapshot"]
    dataset = verify_snapshot(snapshot, schemas)
    if any(snapshot[key] != data[key] for key in ("world_id", "canon_version")):
        raise DataError("Input and fixed snapshot world/version differ")
    if not set(data["relevant_entities"]).issubset(dataset["entities"]):
        raise DataError("Relevant entity is outside the fixed snapshot")
    selected = set(data["selected_specialists"])
    if stage != "planning" and not selected:
        raise DataError("At least one selected Specialist is required")
    if role in SPECIALISTS and role not in selected:
        raise DataError("Specialist is not selected for this task")
    if stage in ("planning", "independent"):
        if data["prior_results"] or data["supporting_artifacts"]:
            raise DataError("Planning/independent input cannot read prior results or artifacts")
        return
    completed, artifacts, first_completed = _validate_packets(data, schemas)
    if not selected.issubset(first_completed):
        raise DataError("All selected Specialists must complete before review/synthesis")
    allowed = selected | ({"integrator"} if stage in ("redteam", "final_synthesis") else set())
    if stage == "final_synthesis":
        allowed.add("redteam")
        if "redteam" not in completed:
            raise DataError("Final synthesis requires Red Team")
    if not completed.issubset(allowed):
        raise DataError("Stage contains an unselected or premature role result")
    _validate_relations(data, [packet["result"] for packet in data["prior_results"]], schemas, artifacts)


def validate_agent_output(data: dict, result: dict, schemas: SchemaStore):
    validate_agent_input(data, schemas)
    schemas.validate(OUTPUTS[data["role"]], result)
    if any(result[key] != data[key] for key in IDENTITY):
        raise DataError("Output identity/version differs from its invocation")
    if data["role"] == "lead":
        selected = [assignment["role"] for assignment in result["assignments"]]
        if len(selected) != len(set(selected)):
            raise DataError("Lead plan contains duplicate Specialist assignments")
        for assignment in result["assignments"]:
            if not set(assignment["entity_ids"]).issubset(data["relevant_entities"]):
                raise DataError("Lead assignment references an entity outside task scope")
        return
    _, artifacts, _ = _validate_packets(data, schemas)
    # Output calculations may refer to independently produced supporting artifacts.
    # Input independent stage forbids them: provide receipts separately at validation time
    # through validate_output_artifacts rather than exposing them to the model.
    results = [packet["result"] for packet in data["prior_results"]] + [result]
    _validate_relations(data, results, schemas, artifacts, current_output=result)


def validate_output_artifacts(data: dict, result: dict, schemas: SchemaStore,
                              supporting_artifacts: list[dict]):
    """Validate post-execution calculation receipts without leaking them into first input."""
    validate_agent_input(data, schemas)
    schemas.validate(OUTPUTS[data["role"]], result)
    if any(result[key] != data[key] for key in IDENTITY):
        raise DataError("Output identity/version differs from its invocation")
    if data["role"] == "lead":
        if supporting_artifacts:
            raise DataError("Lead planning does not accept calculation artifacts")
        return validate_agent_output(data, result, schemas)
    receipt_context = copy.deepcopy(data)
    receipt_context["supporting_artifacts"].extend(copy.deepcopy(supporting_artifacts))
    for artifact in supporting_artifacts:
        schemas.validate("artifact", artifact)
        if artifact["agent_run_id"] != data["agent_run_id"]:
            raise DataError("Output calculation receipt belongs to another Agent Run")
    _, artifacts, _ = _validate_packets(receipt_context, schemas)
    _validate_relations(data, [packet["result"] for packet in data["prior_results"]] + [result],
                        schemas, artifacts, current_output=result)
