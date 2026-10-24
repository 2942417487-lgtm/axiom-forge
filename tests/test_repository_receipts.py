"""Offline receipt data tests. All records and claimed effects are synthetic."""

import copy
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from axiom_forge.__main__ import main
from axiom_forge.ids import new_id
from axiom_forge.repository_receipts import (
    RECEIPT_SCHEMAS, check_receipt_file, parse_receipt, validate_content_reference,
    validate_git_commit_reference, validate_receipt_chain,
)
from axiom_forge.validation import DataError, SchemaStore


ROOT = Path(__file__).resolve().parents[1]


def encode(data):
    return (json.dumps(data, indent=2, allow_nan=False) + "\n").encode("utf-8")


def receipt_ref(data, raw):
    return {"receipt_id": data["receipt_id"], "sha256": hashlib.sha256(raw).hexdigest()}


def fixtures(action="update"):
    documents = [json.loads((ROOT / "examples" / (name + ".json")).read_bytes())
                 for name in RECEIPT_SCHEMAS.values()]
    preparation, inspection, acceptance, result = [d["payload"] for d in documents]
    preparation["requested_action"] = result["requested_action"] = action
    if action == "register":
        acceptance["acceptance_scope"] = "register_baseline"
        result["outcome"] = "registered"
    if action == "inspect":
        inspection["write_projection_ref"] = None
        result["execution_intent_ref"] = None
        result["outcome"] = "inspected"
        documents.pop(2)
    return documents


def bind(documents):
    """Rebuild references so a test can isolate semantic drift from byte drift."""
    raw, refs = [], {}
    for i, document in enumerate(documents, 1):
        document["sequence"] = i
        document["predecessor"] = refs[documents[i - 2]["receipt_kind"]] if i > 1 else None
        payload = document["payload"]
        for field, kind in (("preparation_ref", "preparation"), ("inspection_ref", "inspection"),
                            ("acceptance_ref", "acceptance")):
            if field in payload:
                payload[field] = refs.get(kind)
        current = encode(document)
        refs[document["receipt_kind"]] = receipt_ref(document, current)
        raw.append(current)
    return raw


class RepositoryReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = SchemaStore(ROOT / "schemas")

    def assert_bad(self, documents):
        with self.assertRaises(DataError):
            validate_receipt_chain(bind(documents), self.schemas)

    def test_committed_synthetic_examples_form_a_byte_bound_chain(self):
        raw = [(ROOT / "examples" / (n + ".json")).read_bytes() for n in RECEIPT_SCHEMAS.values()]
        report = validate_receipt_chain(raw, self.schemas)
        self.assertEqual(report, {
            "status": "receipt_chain_data_valid", "scope": "receipt_data_and_chain_bindings",
            "receipt_count": 4, "terminal": True, "content_records_verified": False,
            "execution_authorized": False,
        })

    def test_register_update_inspect_and_unfinished_prefixes(self):
        for action in ("register", "update", "inspect"):
            raw = bind(fixtures(action))
            for length in range(1, len(raw) + 1):
                with self.subTest(action=action, length=length):
                    report = validate_receipt_chain(raw[:length], self.schemas)
                    self.assertEqual(report["terminal"], length == len(raw))
                    self.assertFalse(report["execution_authorized"])

    def test_early_stop_after_preparation_or_inspection(self):
        for length in (1, 2):
            for outcome in ("blocked", "cancelled", "failed", "interrupted_unknown"):
                documents = fixtures()
                result = documents[-1]
                payload = result["payload"]
                payload.update(outcome=outcome, execution_intent_ref=None, after_ref=None,
                               diagnostics_ref=payload["effects_ref"],
                               followup="manual_reconcile" if outcome == "interrupted_unknown" else "needs_input")
                if length == 1:
                    payload["before_ref"] = None
                raw = bind(documents[:length] + [result])
                self.assertTrue(validate_receipt_chain(raw, self.schemas)["terminal"])

    def test_rejected_decision_and_cancel_after_saved_intent(self):
        documents = fixtures()
        documents[2]["payload"]["decision"] = "rejected"
        documents[3]["payload"].update(outcome="rejected", execution_intent_ref=None,
                                       after_ref=None, diagnostics_ref=documents[3]["payload"]["effects_ref"])
        validate_receipt_chain(bind(documents), self.schemas)
        documents = fixtures()
        documents[-1]["payload"].update(outcome="cancelled", after_ref=None,
                                        diagnostics_ref=documents[-1]["payload"]["effects_ref"])
        validate_receipt_chain(bind(documents), self.schemas)

    def test_already_current_can_reference_existing_host_baseline_without_new_acceptance(self):
        documents = fixtures()
        documents[-1]["payload"].update(outcome="already_current", execution_intent_ref=None)
        # Existing acceptance truth is a future host check, outside this data API.
        validate_receipt_chain(bind(documents[:2] + documents[3:]), self.schemas)

    def test_json_sequence_must_be_actual_integer(self):
        for value in (True, False, 1.0, 0, -1, 9007199254740992, "1"):
            data = fixtures()[0]
            data["sequence"] = value
            with self.subTest(value=value), self.assertRaises(DataError):
                parse_receipt(encode(data), self.schemas)

    def test_strict_json_bytes_encoding_and_size(self):
        raw = encode(fixtures()[0])
        for candidate in (
            raw.decode(), bytearray(raw), b"[]", b"null", b"\xef\xbb\xbf" + raw,
            raw.decode().encode("utf-16"), raw.decode().encode("utf-32"), b"\xff",
            raw.replace(b'"sequence": 1', b'"sequence": 1, "sequence": 1'),
            raw.replace(b'"sequence": 1', b'"sequence": NaN'),
            raw.replace(b'"sequence": 1', b'"sequence": Infinity'),
            raw.replace(b'"sequence": 1', b'"sequence": 1e999'),
            raw.replace(b'"1.0"', b'"\\ud800"'), b" " * (2 * 1024 * 1024 + 1),
            b"[" * 2000 + b"]" * 2000,
        ):
            with self.subTest(type=type(candidate), size=len(candidate)), self.assertRaises(DataError):
                parse_receipt(candidate, self.schemas)

    def test_all_fields_required_and_no_unknown_fields(self):
        for original in fixtures():
            for field in original:
                data = copy.deepcopy(original)
                del data[field]
                with self.subTest(kind=original["receipt_kind"], missing=field), self.assertRaises(DataError):
                    parse_receipt(encode(data), self.schemas)
            for field in original["payload"]:
                data = copy.deepcopy(original)
                del data["payload"][field]
                with self.subTest(kind=original["receipt_kind"], missing=field), self.assertRaises(DataError):
                    parse_receipt(encode(data), self.schemas)
            for location in ("top", "payload", "reference"):
                data = copy.deepcopy(original)
                target = data if location == "top" else data["payload"]
                if location == "reference":
                    target = next(v for v in target.values() if isinstance(v, dict))
                target["unknown"] = "value"
                with self.assertRaises(DataError):
                    parse_receipt(encode(data), self.schemas)

    def test_only_explicitly_nullable_fields_accept_null(self):
        nullable = {
            "preparation": {"sensitive_preflight_ref", "retry_of_operation_id"},
            "inspection": {"write_projection_ref", "merge_verification_ref"},
            "acceptance": set(),
            "operation_result": {"inspection_ref", "acceptance_ref", "execution_intent_ref",
                                 "before_ref", "after_ref", "diagnostics_ref"},
        }
        for original in fixtures():
            for field in set(original["payload"]) - nullable[original["receipt_kind"]]:
                data = copy.deepcopy(original)
                data["payload"][field] = None
                with self.subTest(kind=original["receipt_kind"], field=field), self.assertRaises(DataError):
                    parse_receipt(encode(data), self.schemas)

    def test_version_ids_and_utc_timestamp(self):
        for field, bad in (
            ("receipt_format_version", "2.0"), ("receipt_kind", "unknown"),
            ("operation_id", "RUN-00000001-0000-4000-8000-000000000000"),
            ("receipt_id", "RRC-00000001-0000-5000-8000-000000000000"),
            ("receipt_id", "RRC-0000000A-0000-4000-8000-000000000000"),
            ("receipt_id", "RRC-00000001-0000-4000-7000-000000000000"),
            ("receipt_id", fixtures()[0]["receipt_id"] + "\n"),
            ("recorded_at", "2026-10-23T00:00:00+00:00"),
            ("recorded_at", "2026-02-30T00:00:00Z"),
            ("recorded_at", "2026-10-23t00:00:00z"),
            ("recorded_at", "2026-10-23T00:00:60Z"),
        ):
            data = fixtures()[0]
            data[field] = bad
            with self.subTest(field=field, value=bad), self.assertRaises(DataError):
                parse_receipt(encode(data), self.schemas)
        data = fixtures()[0]
        data["recorded_at"] = "2026-10-23T00:00:00.123Z"
        parse_receipt(encode(data), self.schemas)

    def test_new_identifiers_have_independent_namespaces(self):
        for kind, prefix, field in (("repository_operation", "RPO-", "operation_id"),
                                    ("repository_receipt", "RRC-", "receipt_id")):
            data = fixtures()[0]
            value = new_id(kind)
            self.assertTrue(value.startswith(prefix))
            data[field] = value
            parse_receipt(encode(data), self.schemas)

    def test_retry_cannot_reuse_own_operation(self):
        data = fixtures()[0]
        data["payload"]["retry_of_operation_id"] = data["operation_id"]
        with self.assertRaises(DataError):
            parse_receipt(encode(data), self.schemas)
        data["payload"]["retry_of_operation_id"] = new_id("repository_operation")
        parse_receipt(encode(data), self.schemas)

    def test_chain_rejects_empty_unordered_and_overlong_input(self):
        raw = bind(fixtures())
        for candidate in ([], raw[0], iter(raw), raw + raw[:1], list(reversed(raw)), raw[1:]):
            with self.assertRaises(DataError):
                validate_receipt_chain(candidate, self.schemas)

    def test_original_byte_identity_not_canonical_reserialization(self):
        raw = bind(fixtures())
        raw[0] = json.dumps(json.loads(raw[0]), separators=(",", ":")).encode()
        with self.assertRaises(DataError):
            validate_receipt_chain(raw, self.schemas)
        raw = bind(fixtures())
        raw[1] += b"\n"
        with self.assertRaises(DataError):
            validate_receipt_chain(raw, self.schemas)

    def test_sequence_operation_and_receipt_identity_constraints(self):
        for field, value in (("sequence", 4), ("operation_id", new_id("repository_operation")),
                             ("receipt_id", fixtures()[0]["receipt_id"])):
            raw = bind(fixtures())
            data = json.loads(raw[1])
            data[field] = value
            raw[1] = encode(data)
            with self.subTest(field=field), self.assertRaises(DataError):
                validate_receipt_chain(raw, self.schemas)

    def test_predecessor_and_stage_receipt_references_must_match(self):
        for index, field in ((1, "preparation_ref"), (2, "inspection_ref"),
                             (3, "inspection_ref"), (3, "acceptance_ref")):
            raw = bind(fixtures())
            data = json.loads(raw[index])
            data["payload"][field]["sha256"] = "a" * 64
            raw[index] = encode(data)
            with self.subTest(index=index, field=field), self.assertRaises(DataError):
                validate_receipt_chain(raw, self.schemas)
        raw = bind(fixtures())
        data = json.loads(raw[-1])
        data["predecessor"]["sha256"] = "a" * 64
        raw[-1] = encode(data)
        with self.assertRaises(DataError):
            validate_receipt_chain(raw, self.schemas)

    def test_stage_order_duplicates_and_append_after_terminal(self):
        documents = fixtures()
        self.assert_bad([documents[0], documents[2]])
        self.assert_bad([documents[0], documents[1], copy.deepcopy(documents[1])])
        documents = fixtures("inspect")
        self.assert_bad(documents + [copy.deepcopy(documents[-1])])

    def test_inspect_never_has_acceptance_or_write_projection(self):
        documents = fixtures()
        documents[0]["payload"]["requested_action"] = "inspect"
        self.assert_bad(documents)
        documents[1]["payload"]["write_projection_ref"] = None
        self.assert_bad(documents[:3])
        documents = fixtures()
        documents[1]["payload"]["write_projection_ref"] = None
        self.assert_bad(documents[:2])

    def test_noneligible_inspection_cannot_support_acceptance_or_positive_result(self):
        for status in ("blocked", "incomplete"):
            documents = fixtures()
            documents[1]["payload"]["inspection_status"] = status
            self.assert_bad(documents[:3])
            documents = fixtures("inspect")
            documents[1]["payload"]["inspection_status"] = status
            self.assert_bad(documents)

    def test_acceptance_scope_and_all_content_bindings(self):
        for field in ("review_view_ref", "source_capture_ref", "target_before_ref", "coverage_ref",
                      "write_projection_ref", "policy_ref"):
            documents = fixtures()
            documents[2]["payload"][field] = documents[2]["payload"]["actor_ref"]
            with self.subTest(field=field):
                self.assert_bad(documents)
        documents = fixtures()
        documents[2]["payload"]["acceptance_scope"] = "register_baseline"
        self.assert_bad(documents)

    def test_same_content_id_with_different_hashes_rejected(self):
        documents = fixtures()
        documents[1]["payload"]["checks_ref"] = copy.deepcopy(documents[0]["payload"]["limits_ref"])
        documents[1]["payload"]["checks_ref"]["sha256"] = "b" * 64
        self.assert_bad(documents)

    def test_result_cannot_omit_existing_inspection_or_acceptance(self):
        for field in ("inspection_ref", "acceptance_ref"):
            raw = bind(fixtures())
            data = json.loads(raw[-1])
            data["payload"].update(outcome="cancelled", diagnostics_ref=data["payload"]["effects_ref"],
                                   execution_intent_ref=None)
            data["payload"][field] = None
            raw[-1] = encode(data)
            with self.assertRaises(DataError):
                validate_receipt_chain(raw, self.schemas)

    def test_result_action_before_and_outcome_must_match_chain(self):
        for field, value in (("requested_action", "register"), ("outcome", "registered")):
            documents = fixtures()
            documents[-1]["payload"][field] = value
            self.assert_bad(documents)

    def test_result_can_reference_a_new_record_of_the_actual_baseline(self):
        documents = fixtures()
        payload = documents[-1]["payload"]
        payload["before_ref"] = {**payload["before_ref"],
                                 "record_id": "000000ff-0000-4000-8000-000000000000"}
        report = validate_receipt_chain(bind(documents), self.schemas)
        self.assertFalse(report["execution_authorized"])

    def test_stopped_result_can_record_a_changed_target_baseline(self):
        documents = fixtures()
        payload = documents[-1]["payload"]
        payload.update(outcome="blocked", before_ref=payload["effects_ref"], after_ref=None,
                       diagnostics_ref=payload["effects_ref"], followup="new_inspection")
        validate_receipt_chain(bind(documents), self.schemas)

    def test_write_success_requires_accepted_decision_and_intent(self):
        documents = fixtures()
        self.assert_bad(documents[:2] + documents[3:])
        documents[2]["payload"]["decision"] = "rejected"
        self.assert_bad(documents)
        documents = fixtures()
        documents[-1]["payload"]["execution_intent_ref"] = None
        self.assert_bad(documents)

    def test_unknown_result_requires_manual_followup_and_diagnostics(self):
        for field, value in (("followup", "none"), ("diagnostics_ref", None)):
            documents = fixtures()
            payload = documents[-1]["payload"]
            payload.update(outcome="interrupted_unknown", followup="manual_reconcile",
                           diagnostics_ref=payload["effects_ref"], after_ref=None)
            payload[field] = value
            self.assert_bad(documents)

    def test_content_reference_uses_known_sha256_of_supplied_raw_bytes(self):
        reference = {"record_id": "00000001-0000-4000-8000-000000000000",
                     "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}
        validate_content_reference(reference, b"abc", self.schemas)
        for raw in (b"abc\n", "abc", b"a" * (2 * 1024 * 1024 + 1)):
            with self.assertRaises(DataError):
                validate_content_reference(reference, raw, self.schemas)
        for field, value in (("sha256", reference["sha256"].upper()),
                             ("record_id", new_id("repository_receipt"))):
            bad = {**reference, field: value}
            with self.assertRaises(DataError):
                validate_content_reference(bad, b"abc", self.schemas)

    def test_git_commit_reference_shape_and_wrong_reference_kinds(self):
        for algorithm, size in (("sha1", 40), ("sha256", 64)):
            reference = {"object_format": algorithm, "commit_oid": "a" * size}
            validate_git_commit_reference(reference, self.schemas)
            for oid in ("a" * (size - 1), "A" * size, "a" * size + "\n"):
                with self.assertRaises(DataError):
                    validate_git_commit_reference({**reference, "commit_oid": oid}, self.schemas)
        for bad in ({"object_format": "sha512", "commit_oid": "a" * 64},
                    fixtures()[1]["payload"]["preparation_ref"],
                    fixtures()[0]["payload"]["limits_ref"], None, []):
            with self.assertRaises(DataError):
                validate_git_commit_reference(bad, self.schemas)
        with self.assertRaises(DataError):
            validate_content_reference({"object_format": "sha1", "commit_oid": "a" * 40}, b"", self.schemas)

    def test_safe_schema_and_parse_diagnostics(self):
        secret = "SYNTHETIC_SECRET_DO_NOT_ECHO"
        for original in fixtures():
            for field in ("receipt_format_version", "unknown", "payload"):
                data = copy.deepcopy(original)
                data[secret if field == "unknown" else field] = secret
                for check in (lambda: parse_receipt(encode(data), self.schemas),
                              lambda: self.schemas.validate(RECEIPT_SCHEMAS[original["receipt_kind"]], data)):
                    with self.assertRaises(DataError) as caught:
                        check()
                    self.assertNotIn(secret, str(caught.exception))

    def test_single_file_cli_is_safe_strict_read_only_and_not_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SYNTHETIC_SECRET_PATH.json"
            raw = encode(fixtures()[0])
            path.write_bytes(raw)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["validate", "repository_preparation_receipt", str(path)]), 0)
            report = json.loads(output.getvalue())
            self.assertFalse(report["execution_authorized"])
            self.assertEqual(report["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(list(Path(directory).iterdir()), [path])
            self.assertNotIn(path.name, output.getvalue())
            for invalid in (b' {"SYNTHETIC_SECRET_VALUE": NaN}', raw.decode().encode("utf-16"),
                            raw.replace(b'"sequence": 1', b'"sequence": 1.0')):
                path.write_bytes(invalid)
                errors = io.StringIO()
                with redirect_stderr(errors):
                    self.assertEqual(main(["validate", "repository_preparation_receipt", str(path)]), 1)
                self.assertNotIn("SYNTHETIC_SECRET", errors.getvalue())
            with self.assertRaises(DataError):
                check_receipt_file(path, "repository_acceptance_receipt", self.schemas)
