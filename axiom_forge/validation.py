"""Offline JSON Schema validation and domain integrity checks."""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .ids import DOMAIN_PREFIXES


class DataError(ValueError):
    """Invalid JSON, schema, identity, provenance, or world relation."""


def contract_formats() -> FormatChecker:
    checker = FormatChecker()

    @checker.checks("date-time")
    def timezone_datetime(value):
        if not isinstance(value, str):
            return True  # The schema type check handles non-strings.
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value):
            return False
        try:
            return datetime.fromisoformat(value).tzinfo is not None
        except ValueError:
            return False

    @checker.checks("uri")
    def source_uri(value):
        if not isinstance(value, str):
            return True
        try:
            parsed = urlsplit(value)
            return (parsed.scheme in ("http", "https") and bool(parsed.hostname)
                    and not any(char.isspace() for char in value) and parsed.port != 0)
        except ValueError:
            return False

    return checker


def canonical_bytes(data: object) -> bytes:
    try:
        return json.dumps(data, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DataError(f"Not finite JSON data: {exc}") from exc


def digest(data: object) -> str:
    return hashlib.sha256(canonical_bytes(data)).hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DataError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise DataError(f"Non-finite JSON number: {value}")


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DataError(f"Cannot read JSON at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DataError(f"JSON document must be an object: {path}")
    return data


class SchemaStore:
    def __init__(self, directory: Path):
        self.schemas = {}
        resources = []
        for path in sorted(directory.glob("*.schema.json")):
            data = read_json(path)
            name = path.name.removesuffix(".schema.json")
            Draft202012Validator.check_schema(data)
            if data.get("$id") != f"https://axiom-forge.invalid/schemas/{path.name}":
                raise DataError(f"Unexpected schema identifier: {path}")
            self.schemas[name] = data
            resources.append((data["$id"], Resource.from_contents(data)))
        if not self.schemas:
            raise DataError("No schemas found")
        # No HTTP or filesystem fallback: references resolve only in this registry.
        self.registry = Registry().with_resources(resources)
        self._check_references()

    def _check_references(self):
        def walk(node, resolver):
            if isinstance(node, dict):
                if "$ref" in node:
                    try:
                        resolver.lookup(node["$ref"])
                    except Exception as exc:
                        raise DataError(f"Unresolved schema reference: {node['$ref']}") from exc
                for value in node.values():
                    walk(value, resolver)
            elif isinstance(node, list):
                for value in node:
                    walk(value, resolver)
        for schema in self.schemas.values():
            walk(schema, self.registry.resolver(schema["$id"]))

    def validate(self, name: str, data: dict):
        if name not in self.schemas:
            raise DataError(f"Unknown schema: {name}")
        canonical_bytes(data)
        validator = Draft202012Validator(self.schemas[name], registry=self.registry,
                                        format_checker=contract_formats())
        errors = sorted(validator.iter_errors(data), key=lambda err: str(list(err.path)))
        if errors:
            error = errors[0]
            location = "/".join(str(part) for part in error.path) or "<root>"
            raise DataError(f"{name}:{location}: {error.message}")
        if name == "canon_change":
            validate_change(data)


KNOWLEDGE_DIRECTORIES = {
    **{f"world/canon/{domain}": ("canon_entry", domain)
       for domain in list(DOMAIN_PREFIXES)[:8]},
    "world/timeline": ("timeline_event", "timeline"),
    "world/actors": ("actor", "actors"),
    "world/assumptions": ("assumption", "assumptions"),
    "world/evidence": ("evidence", None),
    "world/audits": ("audit", "audits"),
    "world/decisions": ("decision", "decisions"),
}


def record_schema(path: str) -> tuple[str, str | None]:
    pure = PurePosixPath(path)
    if "\\" in path or ":" in path or ".." in pure.parts or pure.is_absolute():
        raise DataError(f"Unsafe knowledge path: {path}")
    if pure.as_posix() != path:
        raise DataError(f"Non-canonical knowledge path: {path}")
    if path == "world/world.json":
        return "world", None
    rule = KNOWLEDGE_DIRECTORIES.get(pure.parent.as_posix())
    if not rule or pure.suffix != ".json":
        raise DataError(f"Unknown knowledge location: {path}")
    return rule


def validate_claims(claims: list, evidence: dict, entities: dict):
    for claim in claims:
        for entity_id in claim["entity_ids"]:
            if entity_id not in entities:
                raise DataError(f"Unknown claim entity: {entity_id}")
        for evidence_id in claim["evidence_ids"]:
            if evidence_id not in evidence:
                raise DataError(f"Unknown evidence: {evidence_id}")
            record = evidence[evidence_id]
            if claim["claim_id"] not in record["supported_claims"]:
                raise DataError(f"Evidence {evidence_id} does not list claim {claim['claim_id']}")
            if claim["category"] in ("FACT", "INFERENCE"):
                if (record["verification"]["status"] != "source_read"
                        or record["source"]["source_type"] == "test_fixture"):
                    raise DataError(f"{claim['category']} requires recorded source reading: {evidence_id}")


def validate_dataset(files: dict[str, dict], schemas: SchemaStore) -> dict:
    if "world/world.json" not in files:
        raise DataError("World metadata is missing")
    entities, evidence, claim_ids = {}, {}, set()
    for path, data in sorted(files.items()):
        schema, domain = record_schema(path)
        schemas.validate(schema, data)
        if schema == "world":
            continue
        id_field = "evidence_id" if schema == "evidence" else "entity_id"
        identifier = data[id_field]
        if PurePosixPath(path).stem != identifier:
            raise DataError(f"Filename must equal {id_field}: {path}")
        if domain and (data["domain"] != domain
                       or not identifier.startswith(DOMAIN_PREFIXES[domain] + "-")):
            raise DataError(f"Entity domain/prefix does not match its directory: {path}")
        catalog = evidence if schema == "evidence" else entities
        if identifier in catalog:
            raise DataError(f"Duplicate {id_field}: {identifier}")
        catalog[identifier] = data
    for entity_id, entry in entities.items():
        for target in entry["dependencies"] + entry["conflicts"]:
            if target not in entities:
                raise DataError(f"{entity_id} references unknown entity {target}")
        for evidence_id in entry["evidence_ids"]:
            if evidence_id not in evidence:
                raise DataError(f"{entity_id} references unknown evidence {evidence_id}")
        for claim in entry["claims"]:
            if claim["claim_id"] in claim_ids:
                raise DataError(f"Duplicate claim ID: {claim['claim_id']}")
            claim_ids.add(claim["claim_id"])
            if not set(claim["evidence_ids"]).issubset(entry["evidence_ids"]):
                raise DataError(f"Claim evidence omitted from Canon entry {entity_id}")
        validate_claims(entry["claims"], evidence, entities)
    for record in evidence.values():
        if record["claim_id"] not in record["supported_claims"]:
            raise DataError("Evidence claim_id must be listed in supported_claims")
        for entity_id in record["supported_entities"]:
            if entity_id not in entities:
                raise DataError(f"Evidence references unknown entity {entity_id}")
    return {"world": files["world/world.json"], "entities": entities, "evidence": evidence}


def collect_world(repo: Path, schemas: SchemaStore) -> dict[str, dict]:
    repo = repo.resolve()
    files = {}
    candidates = [repo / "world/world.json"]
    for directory in KNOWLEDGE_DIRECTORIES:
        root = repo / directory
        if not root.is_dir():
            raise DataError(f"Missing knowledge directory: {directory}")
        candidates.extend(sorted(root.rglob("*.json")))
    for path in candidates:
        if not path.resolve().is_relative_to(repo):
            raise DataError(f"Knowledge file escapes repository: {path}")
        files[path.relative_to(repo).as_posix()] = read_json(path)
    validate_dataset(files, schemas)
    return files


def validate_change(change: dict):
    for field in ("before", "after"):
        entry = change[field]
        if entry is not None and entry["entity_id"] != change["target_entity_id"]:
            raise DataError(f"CanonChange {field} identity differs from target")
    approval = change["approval"]
    if approval["status"] == "pending" and any(
        approval[key] is not None for key in ("reviewer", "reviewed_at", "decision_id")
    ):
        raise DataError("Pending approval cannot contain an approval receipt")


def validate_task(task: dict, schemas: SchemaStore):
    from .snapshots import verify_snapshot

    schemas.validate("task_state", task)
    snapshot = task["canon_snapshot"]
    dataset = verify_snapshot(snapshot, schemas)
    if (snapshot["world_id"] != task["world_id"]
            or snapshot["canon_version"] != task["canon_version"]):
        raise DataError("Task and snapshot world/version differ")
    for entity_id in task["relevant_entities"]:
        if entity_id not in dataset["entities"]:
            raise DataError(f"Unknown relevant entity: {entity_id}")
    catalogs = {}
    for field, id_field in (("runs", "run_id"), ("agent_runs", "agent_run_id"),
                            ("artifacts", "artifact_id")):
        catalog = {}
        for record in task[field]:
            identifier = record[id_field]
            if identifier in catalog:
                raise DataError(f"Duplicate {id_field}: {identifier}")
            if any(record[key] != task[key] for key in ("world_id", "task_id")):
                raise DataError(f"{field} world/task identity differs")
            if "canon_version" in record and record["canon_version"] != task["canon_version"]:
                raise DataError(f"{field} Canon version differs")
            catalog[identifier] = record
        catalogs[field] = catalog
    runs, agents, artifacts = (catalogs[key] for key in ("runs", "agent_runs", "artifacts"))
    for record in list(agents.values()) + list(artifacts.values()):
        if record["run_id"] not in runs:
            raise DataError(f"Unknown run: {record['run_id']}")
    for agent in agents.values():
        if agent["artifact_id"] not in artifacts:
            raise DataError("Agent Run output artifact is missing")
        output = artifacts[agent["artifact_id"]]
        if output["agent_run_id"] != agent["agent_run_id"] or output["run_id"] != agent["run_id"]:
            raise DataError("Agent Run and output artifact identity differ")
    for artifact in artifacts.values():
        if artifact["agent_run_id"] is not None:
            agent = agents.get(artifact["agent_run_id"])
            if agent is None or agent["run_id"] != artifact["run_id"]:
                raise DataError("Artifact and Agent Run identity differ")
    for run in runs.values():
        expected_agents = {key for key, value in agents.items() if value["run_id"] == run["run_id"]}
        expected_artifacts = {key for key, value in artifacts.items() if value["run_id"] == run["run_id"]}
        if set(run["agent_run_ids"]) != expected_agents or set(run["artifact_ids"]) != expected_artifacts:
            raise DataError("Run membership differs from Agent Run / Artifact records")
    results = []
    for field in ("research_results", "engineering_results", "economic_results",
                  "historical_results", "redteam_results"):
        results.extend(task[field])
    if task["synthesis"] is not None:
        results.append(task["synthesis"])
    proposals = list(task["proposed_changes"])
    if task["synthesis"] is not None:
        proposals.extend(task["synthesis"]["proposed_changes"])
    task_entities = dict(dataset["entities"])
    for change in proposals:
        if change["after"] is not None:
            task_entities[change["target_entity_id"]] = change["after"]
    evidence = dict(dataset["evidence"])
    for result in task["research_results"]:
        for record in result["evidence"]:
            identifier = record["evidence_id"]
            if identifier in evidence and evidence[identifier] != record:
                raise DataError(f"Conflicting evidence record: {identifier}")
            evidence[identifier] = record
    for record in evidence.values():
        if record["claim_id"] not in record["supported_claims"]:
            raise DataError("Evidence claim_id must be listed in supported_claims")
        if not set(record["supported_entities"]).issubset(task_entities):
            raise DataError("Evidence references an entity outside the task snapshot/proposals")
    result_artifacts = set()
    for result in results:
        if any(result[key] != task[key] for key in ("world_id", "task_id", "canon_version")):
            raise DataError("Result world/task/version differs")
        agent = agents.get(result["agent_run_id"])
        if agent is None or agent["run_id"] != result["run_id"] or agent["artifact_id"] != result["artifact_id"]:
            raise DataError("Result execution identity differs from Agent Run")
        expected_role = {"research": "researcher", "engineering": "engineering_auditor",
                         "economic": "economic_auditor", "historical": "historical_analyst",
                         "redteam": "redteam", "synthesis": "integrator"}[result["result_type"]]
        if agent["role"] != expected_role:
            raise DataError("Result type differs from Agent Run role")
        if artifacts[result["artifact_id"]]["sha256"] != digest(result):
            raise DataError("Result content differs from its output artifact hash")
        if result["artifact_id"] in result_artifacts:
            raise DataError("Multiple results share one output artifact")
        result_artifacts.add(result["artifact_id"])
        validate_claims(result["claims"], evidence, task_entities)
        for calculation in result.get("calculations", []):
            artifact = artifacts.get(calculation["artifact_id"])
            if artifact is None or artifact["run_id"] != result["run_id"]:
                raise DataError("Calculation artifact is missing or belongs to another Run")
        for chain in result.get("causal_chains", []):
            if not set(chain["evidence_ids"]).issubset(evidence):
                raise DataError("Historical causal chain references unknown evidence")
    for record in list(runs.values()) + list(agents.values()):
        if record["finished_at"] is not None:
            if datetime.fromisoformat(record["finished_at"]) < datetime.fromisoformat(record["started_at"]):
                raise DataError("Execution finished before it started")
        if record["status"] in ("completed", "failed", "cancelled") and record["finished_at"] is None:
            raise DataError("Finished execution requires finished_at")
    conflicts = list(task["contradictions"])
    for result in results:
        conflicts.extend(result.get("contradictions", []))
    for conflict in conflicts:
        if not set(conflict["entity_ids"]).issubset(task_entities):
            raise DataError("Conflict references an entity outside the task snapshot/proposals")
        if not set(conflict["evidence_ids"]).issubset(evidence):
            raise DataError("Conflict references unknown evidence")
    by_id = {}
    for change in proposals:
        validate_change(change)
        if change["proposal_id"] in by_id and by_id[change["proposal_id"]] != change:
            raise DataError("Conflicting CanonChange proposal copies")
        by_id[change["proposal_id"]] = change
        if (change["world_id"] != task["world_id"] or change["task_id"] != task["task_id"]
                or change["base_canon_version"] != task["canon_version"] or change["run_id"] not in runs):
            raise DataError("CanonChange world/task/run/version differs")
        before = dataset["entities"].get(change["target_entity_id"])
        if before != change["before"]:
            raise DataError("CanonChange before does not match the fixed snapshot")
        if not set(change["provenance"]["evidence_ids"]).issubset(evidence):
            raise DataError("CanonChange provenance references unknown evidence")
    projected_files = {record["path"]: record["data"] for record in snapshot["files"]}
    for record in evidence.values():
        projected_files[f"world/evidence/{record['evidence_id']}.json"] = record
    targets = set()
    for change in by_id.values():
        target = change["target_entity_id"]
        if target in targets:
            raise DataError("Multiple proposals modify the same entity")
        targets.add(target)
        if change["before"] is not None:
            original_path = next(path for path, record in projected_files.items()
                                 if record.get("entity_id") == target)
            del projected_files[original_path]
        if change["after"] is not None:
            entry = change["after"]
            directory = next(directory for directory, (_, domain) in KNOWLEDGE_DIRECTORIES.items()
                             if domain == entry["domain"])
            projected_files[f"{directory}/{target}.json"] = entry
    # Validate the whole proposed state, in memory only. This is not Canon Apply.
    validate_dataset(projected_files, schemas)
    if task["lifecycle"] == "WAITING_APPROVAL" and task["approval_status"] != "pending":
        raise DataError("WAITING_APPROVAL requires pending approval")
    if task["lifecycle"] == "COMMITTED":
        if task["approval_status"] != "approved" or task["final_result"] is None:
            raise DataError("COMMITTED requires approval and a final result")
        if any(change["approval"]["status"] != "approved" for change in by_id.values()):
            raise DataError("COMMITTED cannot contain unapproved CanonChanges")
