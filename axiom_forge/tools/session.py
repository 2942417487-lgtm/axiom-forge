"""Runtime-neutral tools scoped by a trusted host to one validated AgentInput."""

import copy
import hashlib
from pathlib import Path
from typing import Protocol

from jsonschema import Draft202012Validator

from ..contracts import validate_agent_input
from ..ids import new_id
from ..snapshots import utc_now, verify_snapshot
from ..validation import DataError, SchemaStore, canonical_bytes, digest
from .git_read import git_read
from .sources import arxiv, crossref, document_text, web_read
from .storage import MAX_BYTES, ToolError, Workspace, read_bounded, strict_json


class SearchBackend(Protocol):
    """Host-injected adapter; results need items and a source retrieval receipt."""
    def search(self, query: str, limit: int) -> dict: ...


def obj(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required,
            "additionalProperties": False}


TEXT = {"type": "string", "minLength": 1, "maxLength": 1000}
PATH = {"type": "string", "minLength": 1, "maxLength": 240}
LIMIT = {"type": "integer", "minimum": 1, "maximum": 20}
RECORD = {"type": "object"}
DEFINITIONS = {
    "web.read": ("web_read", obj({"url": {**TEXT, "maxLength": 4096}})),
    "web.search": ("web_search", obj({"query": TEXT, "limit": LIMIT})),
    "papers.crossref.search": ("papers_read", obj({"query": TEXT, "limit": LIMIT})),
    "papers.crossref.doi": ("papers_read", obj({"doi": {**TEXT, "maxLength": 500}})),
    "papers.arxiv.search": ("papers_read", obj({"query": TEXT, "limit": LIMIT})),
    "documents.read": ("documents_read", obj({"reference_id": PATH,
        "first_page": {"type": "integer", "minimum": 1, "maximum": 10000},
        "max_pages": {"type": "integer", "minimum": 1, "maximum": 50}})),
    "filesystem.read": ("workspace", obj({"path": PATH})),
    "filesystem.write": ("workspace", obj({"path": PATH, "text": {"type": "string", "maxLength": MAX_BYTES}})),
    "canon.read": ("canon_read", obj({"entity_id": TEXT})),
    "evidence.read": ("canon_read", obj({"evidence_id": TEXT})),
    "evidence.stage": ("draft_write", obj({"record": RECORD,
        "source_receipt_id": {"type": ["string", "null"]}})),
    "canon.propose": ("draft_write", obj({"record": RECORD})),
    "git.inspect": ("git_read", obj({"action": {"enum": ["status", "head", "diff"]},
        "path": {"type": ["string", "null"], "maxLength": 240}})),
    "python.run_reviewed": ("python_call", obj({"script_id": TEXT, "input": RECORD})),
}
CAPABILITIES = frozenset(item[0] for item in DEFINITIONS.values())


def definitions():
    return [{"name": name, "capability": capability, "input_schema": copy.deepcopy(schema)}
            for name, (capability, schema) in DEFINITIONS.items()]


class ToolSession:
    def __init__(self, repo, agent_input, *, capabilities=(), documents=None,
                 network=None, search_backend=None, python_backend=None):
        # This constructor belongs to the trusted operator/Runtime, not the model.
        from ..workspaces import require_world
        self.world = require_world(repo)
        self.repo = self.world.root
        self.engine_root = self.world.engine.root
        self.schemas = self.world.schemas
        validate_agent_input(agent_input, self.schemas)
        self.world.validate_world(agent_input["world_id"])
        self.context = copy.deepcopy(agent_input)
        self.capabilities = frozenset(capabilities)
        if not self.capabilities <= CAPABILITIES:
            raise ValueError("Unknown tool capability")
        self.documents = copy.deepcopy(documents or {})
        for key, grant in self.documents.items():
            if (not isinstance(key, str) or not isinstance(grant, dict)
                    or set(grant) - {"path", "url"} or "path" not in grant
                    or not isinstance(grant["path"], str)
                    or not Path(grant["path"]).is_absolute()):
                raise ValueError("Documents require explicit named absolute-path grants")
        self.network, self.search_backend, self.python_backend = network, search_backend, python_backend
        dataset = verify_snapshot(self.context["canon_snapshot"], self.schemas)
        self.entities = {identifier: dataset["entities"][identifier]
                         for identifier in self.context["relevant_entities"]}
        evidence_ids = {identifier for entity in self.entities.values() for identifier in entity["evidence_ids"]}
        evidence_ids.update(identifier for identifier, record in dataset["evidence"].items()
                            if set(record["supported_entities"]) & set(self.entities))
        self.evidence = {identifier: dataset["evidence"][identifier] for identifier in evidence_ids}
        # UUID AgentRun names keep Windows process working directories short.
        # An immutable full-context binding prevents cross-task/stage reuse.
        self.workspace = Workspace(self.repo / ".axiom/local/tool-runs" / self.context["agent_run_id"])
        binding = {"input_sha256": digest(self.context), "workspace_binding": self.world.binding}
        try:
            self.workspace.write_json("context.json", binding)
        except ToolError as exc:
            if exc.code != "already_exists" or strict_json(self.workspace.read("context.json")) != binding:
                raise ToolError("context_mismatch", "AgentRun workspace is bound to another input") from exc
        self.files = Workspace(self.workspace.root / "files")
        self._receipts = {}

    def _client(self):
        if self.network is None:
            raise ToolError("unavailable", "No public HTTPS client was enabled by the host")
        return self.network

    def _document(self, args):
        grant = self.documents.get(args["reference_id"])
        if grant is None:
            raise ToolError("denied", "Document was not granted to this AgentRun")
        path = Path(grant["path"])
        raw = read_bounded(path)
        output = document_text(raw, path.suffix.lower(), first_page=args["first_page"], max_pages=args["max_pages"])
        output["source"] = {"reference_id": args["reference_id"], "url": grant.get("url"),
                            "accessed_at": utc_now(), "sha256": hashlib.sha256(raw).hexdigest(),
                            "bytes": len(raw), "verification_scope": "selected_document_text_only"}
        output["trust"] = "untrusted_source_content"
        return output

    def _stage_evidence(self, args):
        record = args["record"]
        self.schemas.validate("evidence", record)
        if not set(record["supported_entities"]) <= set(self.entities):
            raise ToolError("denied", "Evidence may only reference entities visible in this input")
        receipt_id = args["source_receipt_id"]
        if record["verification"]["status"] == "source_read":
            receipt = self._receipts.get(receipt_id)
            if (receipt is None or receipt["status"] != "completed"
                    or receipt["tool_name"] not in ("web.read", "documents.read")):
                raise ToolError("source_not_read", "A successful source-reading receipt from this live session is required")
            source, verification = receipt["data"]["source"], record["verification"]
            if (source.get("url") != record["source"]["url"]
                    or source["accessed_at"] != verification["accessed_at"]
                    or verification["method"] != receipt["tool_name"]
                    or verification["excerpt"] not in receipt["data"]["text"]):
                raise ToolError("source_mismatch", "Evidence source, time, method or excerpt differs from retrieved content")
        elif receipt_id is not None:
            raise ToolError("source_mismatch", "Unverified/synthetic Evidence must not claim a reading receipt")
        path = "drafts/evidence/" + record["evidence_id"] + ".json"
        self.workspace.write_json(path, record)
        return {"path": path, "sha256": digest(record), "status": "staged_only",
                "verification_scope": "retrieval_consistency_only_not_scientific_validation"}

    def _propose(self, record):
        if self.context["role"] != "integrator":
            raise ToolError("denied", "Canon proposals belong to the Integrator role")
        self.schemas.validate("canon_change", record)
        if record["approval"]["status"] != "pending":
            raise ToolError("denied", "Only pending proposals can be staged")
        expected = {key: self.context[key] for key in ("world_id", "task_id", "run_id")}
        expected["base_canon_version"] = self.context["canon_version"]
        if any(record[key] != value for key, value in expected.items()):
            raise ToolError("context_mismatch", "Proposal context differs from fixed AgentInput")
        target = record["target_entity_id"]
        dataset = verify_snapshot(self.context["canon_snapshot"], self.schemas)
        if target in dataset["entities"] and target not in self.entities:
            raise ToolError("denied", "Proposal target is outside the visible entity selection")
        if record["before"] != self.entities.get(target):
            raise ToolError("context_mismatch", "Proposal before differs from the selected snapshot entity")
        path = "drafts/proposals/" + record["proposal_id"] + ".json"
        self.workspace.write_json(path, record)
        return {"path": path, "sha256": digest(record), "status": "pending",
                "limitations": ["Staging is not full future-state validation, approval or Canon Apply."]}

    def _execute(self, name, args, call_id):
        if name == "web.read":
            return web_read(self._client(), args["url"])
        if name == "web.search":
            if self.search_backend is None:
                raise ToolError("unavailable", "No general Web search service has been selected")
            output = self.search_backend.search(args["query"], args["limit"])
            if (not isinstance(output, dict) or not isinstance(output.get("items"), list)
                    or not isinstance(output.get("source"), dict)):
                raise ToolError("invalid_response", "Search adapter must return items and retrieval provenance")
            return output
        if name == "papers.crossref.search":
            return crossref(self._client(), query=args["query"], limit=args["limit"])
        if name == "papers.crossref.doi":
            return crossref(self._client(), doi=args["doi"])
        if name == "papers.arxiv.search":
            return arxiv(self._client(), args["query"], args["limit"])
        if name == "documents.read":
            return self._document(args)
        if name == "filesystem.read":
            try:
                return {"path": args["path"], "text": self.files.read(args["path"]).decode("utf-8")}
            except UnicodeError as exc:
                raise ToolError("unsupported_encoding", "Workspace files must be UTF-8") from exc
        if name == "filesystem.write":
            self.files.write(args["path"], args["text"].encode("utf-8"))
            return {"path": args["path"], "sha256": hashlib.sha256(args["text"].encode("utf-8")).hexdigest()}
        if name == "canon.read":
            record = self.entities.get(args["entity_id"])
            if record is None:
                raise ToolError("denied", "Entity is outside the selected fixed snapshot")
            return {"record": copy.deepcopy(record), "canon_version": self.context["canon_version"]}
        if name == "evidence.read":
            record = self.evidence.get(args["evidence_id"])
            if record is None:
                raise ToolError("denied", "Evidence is outside the selected fixed snapshot")
            return {"record": copy.deepcopy(record), "canon_version": self.context["canon_version"]}
        if name == "evidence.stage":
            return self._stage_evidence(args)
        if name == "canon.propose":
            return self._propose(args["record"])
        if name == "git.inspect":
            if args["action"] == "diff":
                raise ToolError("denied", "World Git diff is unavailable; use the granted fixed Canon snapshot")
            return git_read(self.repo, args["action"], args["path"])
        if name == "python.run_reviewed":
            if self.python_backend is None:
                raise ToolError("unavailable", "No reviewed-script backend enabled")
            return self.python_backend.execute(args["script_id"], args["input"], self.workspace, call_id)
        raise ToolError("unknown_tool", "Unknown tool name")

    def call(self, name, arguments):
        # Reject malformed invocation before dispatch. These are not tool executions.
        if not isinstance(name, str) or not isinstance(arguments, dict):
            raise ToolError("invalid_arguments", "Tool name and JSON argument object required")
        arguments = copy.deepcopy(arguments)
        raw = canonical_bytes({"name": name, "arguments": arguments})
        if len(raw) > MAX_BYTES:
            raise ToolError("size_limit", "Tool arguments exceed size limit")
        started, call_id = utc_now(), new_id("artifact")
        data, error, status = None, None, "completed"
        try:
            if name not in DEFINITIONS:
                raise ToolError("denied", "Tool is not registered")
            capability, schema = DEFINITIONS[name]
            if capability not in self.capabilities:
                raise ToolError("denied", "Host did not grant this capability")
            if not Draft202012Validator(schema).is_valid(arguments):
                raise ToolError("invalid_arguments", "Arguments do not match the tool input schema")
            data = self._execute(name, arguments, call_id)
            if not isinstance(data, dict) or len(canonical_bytes(data)) > MAX_BYTES - 8192:
                raise ToolError("size_limit", "Tool result exceeds size limit")
        except Exception as exc:
            code = getattr(exc, "code", "tool_failed")
            status = "denied" if code in ("denied", "network_denied", "unsafe_path") else "unavailable" if code in ("unavailable", "needs_implementation") else "failed"
            # Raw provider/subprocess exceptions may contain paths or credentials.
            error = {"code": code, "message": str(exc) if isinstance(exc, ToolError) else "Tool failed validation or execution; no successful output"}
            data = None
        result = {"schema_version": "1.0", "result_id": new_id("artifact"), "call_id": call_id,
                  **{key: self.context[key] for key in ("world_id", "task_id", "run_id", "agent_run_id", "canon_version")},
                  "tool_name": name, "status": status, "data": data, "error": error,
                  "receipt": {"started_at": started, "finished_at": utc_now(),
                              "arguments_sha256": hashlib.sha256(raw).hexdigest(),
                              "payload_sha256": digest({"status": status, "data": data, "error": error})}}
        self.schemas.validate("tool_result", result)
        self.workspace.write_json("receipts/" + result["result_id"] + ".json", result)
        self._receipts[result["result_id"]] = copy.deepcopy(result)
        return result
