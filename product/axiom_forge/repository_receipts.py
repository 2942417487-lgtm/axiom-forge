"""Offline repository receipt data checks; never an execution authority.

Callers supply raw bytes and trusted engine schemas. No content resolution,
host verification, persistence, Git access or repository mutation occurs here.
"""

import hashlib

from .tools.storage import MAX_BYTES, read_bounded, strict_json
from .validation import DataError


RECEIPT_SCHEMAS = {
    "preparation": "repository_preparation_receipt",
    "inspection": "repository_inspection_receipt",
    "acceptance": "repository_acceptance_receipt",
    "operation_result": "repository_operation_receipt",
}


def _require(condition, message):
    if not condition:
        raise DataError(message)


def _raw_bytes(raw):
    _require(isinstance(raw, bytes) and len(raw) <= MAX_BYTES,
             "Expected raw bytes within the receipt data size limit")
    return raw


def _validate_receipt_semantics(data):
    """Called by SchemaStore after shape validation, including generic callers."""
    _require(type(data["sequence"]) is int, "Receipt sequence must be a JSON integer")
    kind, payload = data["receipt_kind"], data["payload"]
    if kind == "preparation":
        _require(payload["retry_of_operation_id"] != data["operation_id"],
                 "A retry must use a new operation identity")
    if kind != "operation_result":
        return
    outcome = payload["outcome"]
    action = payload["requested_action"]
    if outcome in ("registered", "updated"):
        _require(action == {"registered": "register", "updated": "update"}[outcome],
                 "Result outcome conflicts with requested action")
        _require(all(payload[field] is not None for field in (
            "inspection_ref", "acceptance_ref", "execution_intent_ref", "before_ref", "after_ref")),
            "A write success requires inspection, acceptance, intent and before/after references")
    if outcome in ("inspected", "already_current"):
        _require(all(payload[field] is not None for field in (
            "inspection_ref", "before_ref", "after_ref")),
            "A completed check requires inspection and before/after references")
    if outcome == "inspected" or action == "inspect":
        _require(payload["acceptance_ref"] is None and payload["execution_intent_ref"] is None,
                 "Inspection cannot carry acceptance or write intent")
    if outcome == "already_current":
        _require(action != "inspect", "Already-current requires a registration or update request")
    if outcome == "rejected":
        _require(payload["acceptance_ref"] is not None, "Rejection requires a decision reference")
    if outcome in ("rejected", "blocked", "cancelled", "failed", "interrupted_unknown"):
        _require(payload["diagnostics_ref"] is not None, "A stopped result requires diagnostics")
    if outcome == "interrupted_unknown":
        _require(payload["followup"] == "manual_reconcile",
                 "An unknown result requires manual reconciliation")


def _parse_data(raw):
    try:
        data = strict_json(_raw_bytes(raw).decode("utf-8", errors="strict"))
    except (DataError, ValueError, TypeError, RecursionError):
        raise DataError("Expected bounded UTF-8 receipt JSON with unique keys and valid Unicode") from None
    _require(isinstance(data, dict), "Receipt or reference must be an object")
    return data


def parse_receipt(raw, schemas):
    """Return a validated data object, with no host trust attached to its fields."""
    data = _parse_data(raw)
    kind = data.get("receipt_kind")
    _require(isinstance(kind, str) and kind in RECEIPT_SCHEMAS, "Unsupported receipt kind")
    schemas.validate(RECEIPT_SCHEMAS[kind], data)
    return data


def check_receipt_file(path, schema_name, schemas):
    """Bounded single-file CLI check; no chain or host records are resolved."""
    try:
        raw = read_bounded(path)
    except (DataError, OSError, ValueError):
        raise DataError("Receipt file cannot be read within path and size limits") from None
    data = _parse_data(raw)
    _require(schema_name in (*RECEIPT_SCHEMAS.values(), "repository_receipt_common"),
             "Unsupported repository receipt schema")
    schemas.validate(schema_name, data)
    return {"status": "receipt_data_valid", "scope": "single_receipt_or_reference_format",
            "sha256": hashlib.sha256(raw).hexdigest(), "execution_authorized": False}


def validate_content_reference(reference, raw, schemas):
    """Check shape and the supplied bytes only; do not resolve a host record."""
    schemas.validate("repository_receipt_common", reference)
    _require(set(reference) == {"record_id", "sha256"}, "Expected a ContentRef")
    _require(hashlib.sha256(_raw_bytes(raw)).hexdigest() == reference["sha256"],
             "Content reference does not match supplied bytes")


def validate_git_commit_reference(reference, schemas):
    """Check sha1/sha256 OID shape only, without checking a Git object."""
    schemas.validate("repository_receipt_common", reference)
    _require(set(reference) == {"object_format", "commit_oid"}, "Expected a GitCommitRef")


def _receipt_ref(data, raw):
    return {"receipt_id": data["receipt_id"], "sha256": hashlib.sha256(raw).hexdigest()}


def _validate_inspection(payload, preparation, preparation_ref):
    _require(payload["preparation_ref"] == preparation_ref,
             "Inspection does not reference this preparation's raw bytes")
    write_required = preparation["requested_action"] != "inspect"
    _require((payload["write_projection_ref"] is not None) == write_required,
             "Inspection write projection conflicts with requested action")


def _validate_acceptance(payload, preparation, inspection, inspection_ref):
    action = preparation["requested_action"]
    _require(action in ("register", "update"), "Inspection-only operations cannot have acceptance")
    _require(inspection["inspection_status"] == "eligible", "Acceptance requires eligible inspection")
    _require(payload["inspection_ref"] == inspection_ref,
             "Acceptance does not reference this inspection's raw bytes")
    _require(payload["acceptance_scope"] == {
        "register": "register_baseline", "update": "sync_baseline"}[action],
        "Acceptance scope conflicts with requested action")
    for target, source in (
        ("review_view_ref", "comparison_ref"), ("source_capture_ref", "source_capture_ref"),
        ("target_before_ref", "target_before_ref"), ("coverage_ref", "coverage_ref"),
        ("write_projection_ref", "write_projection_ref"),
    ):
        _require(payload[target] == inspection[source], "Acceptance inspection content binding differs")
    _require(payload["policy_ref"] == preparation["policy_ref"], "Acceptance policy binding differs")


def _validate_result(payload, preparation, inspection, inspection_ref, acceptance, acceptance_ref):
    _require(payload["requested_action"] == preparation["requested_action"],
             "Result requested action differs from preparation")
    _require(payload["inspection_ref"] == inspection_ref,
             "Result must reference exactly the inspection present in this chain")
    _require(payload["acceptance_ref"] == acceptance_ref,
             "Result must reference exactly the acceptance present in this chain")
    outcome = payload["outcome"]
    completed = outcome in ("inspected", "registered", "updated", "already_current")
    if completed:
        _require(inspection is not None and inspection["inspection_status"] == "eligible",
                 "A positive result requires eligible inspection")
    if outcome in ("registered", "updated") or payload["execution_intent_ref"] is not None:
        _require(acceptance is not None and acceptance["decision"] == "accepted",
                 "Write success or intent requires an accepted decision in this chain")
    if acceptance is not None and acceptance["decision"] == "rejected":
        _require(not completed, "A rejected decision cannot support a positive result")
    if outcome == "rejected":
        _require(acceptance is not None and acceptance["decision"] == "rejected",
                 "Rejected result requires a rejected decision in this chain")


def validate_receipt_chain(raw_receipts, schemas):
    """Validate an ordered chain or prefix of 1–4 raw byte documents.

    ReceiptRef checks use the original supplied bytes, never canonical JSON.
    ContentRef shapes and cross-stage equality are checked; record metadata,
    content bytes, host decisions, effects and persistence remain unverified.
    """
    _require(isinstance(raw_receipts, (list, tuple)) and 1 <= len(raw_receipts) <= 4,
             "Expected an ordered receipt chain of one to four documents")
    documents = [parse_receipt(raw, schemas) for raw in raw_receipts]
    first = documents[0]
    _require(first["receipt_kind"] == "preparation", "Chain must start with preparation")
    preparation = first["payload"]
    preparation_ref = _receipt_ref(first, raw_receipts[0])
    seen_ids, content_hashes = set(), {}
    inspection = inspection_ref = acceptance = acceptance_ref = None
    previous = None
    allowed = {
        None: {"preparation"}, "preparation": {"inspection", "operation_result"},
        "inspection": {"acceptance", "operation_result"}, "acceptance": {"operation_result"},
        "operation_result": set(),
    }
    for sequence, (data, raw) in enumerate(zip(documents, raw_receipts), start=1):
        kind, payload = data["receipt_kind"], data["payload"]
        _require(kind in allowed[previous], "Illegal receipt stage transition")
        _require(data["operation_id"] == first["operation_id"], "Receipt operation identity differs")
        _require(data["sequence"] == sequence, "Receipt sequence is not contiguous")
        _require(data["receipt_id"] not in seen_ids, "Receipt identity is reused")
        seen_ids.add(data["receipt_id"])
        expected_predecessor = None if sequence == 1 else _receipt_ref(
            documents[sequence - 2], raw_receipts[sequence - 2])
        _require(data["predecessor"] == expected_predecessor,
                 "Predecessor does not match the previous receipt's raw bytes")
        for value in payload.values():
            if isinstance(value, dict) and set(value) == {"record_id", "sha256"}:
                record_id = value["record_id"]
                _require(record_id not in content_hashes or content_hashes[record_id] == value["sha256"],
                         "Content record identity has conflicting byte hashes")
                content_hashes[record_id] = value["sha256"]
        if kind == "inspection":
            _validate_inspection(payload, preparation, preparation_ref)
            inspection, inspection_ref = payload, _receipt_ref(data, raw)
        elif kind == "acceptance":
            _validate_acceptance(payload, preparation, inspection, inspection_ref)
            acceptance, acceptance_ref = payload, _receipt_ref(data, raw)
        elif kind == "operation_result":
            _validate_result(payload, preparation, inspection, inspection_ref, acceptance, acceptance_ref)
        previous = kind
    return {"status": "receipt_chain_data_valid", "scope": "receipt_data_and_chain_bindings",
            "receipt_count": len(documents), "terminal": previous == "operation_result",
            "content_records_verified": False, "execution_authorized": False}
