"""Tool Layer boundaries. Provider payloads and script jobs here are synthetic."""

import copy
import hashlib
import io
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pypdf import PdfWriter

from examples.offline_task_manager import initialize_fixture
from axiom_forge.ids import new_id
from axiom_forge.tools import ToolSession, definitions
from axiom_forge.tools.git_read import git_read
from axiom_forge.tools.network import PublicHTTPS, Response
from axiom_forge.tools.python_backend import TrustedPython
from axiom_forge.tools.sources import arxiv, crossref, document_text, web_read
from axiom_forge.tools.storage import MAX_BYTES, ToolError, Workspace, safe_relative, strict_json
from axiom_forge.validation import DataError, SchemaStore, canonical_bytes, collect_world, digest, read_json

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path(tempfile.gettempdir()) / "axiom-forge-test-runs"
SCRATCH.mkdir(parents=True, exist_ok=True)


class FakeNetwork:
    def __init__(self, body=b"TEST FIXTURE source text", kind="text/plain", url="https://example.invalid/source"):
        self.response = Response(url, kind, body, "2026-10-04T00:00:00Z")
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return self.response


class ToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = SchemaStore(ROOT / "schemas")

    def temporary(self):
        temporary = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name).resolve()

    def session(self, capabilities=(), *, role="engineering_auditor", **kwargs):
        context = read_json(ROOT / f"examples/agents/{role}-input.json")
        context["agent_run_id"] = new_id("agent_run")
        repo = self.temporary()
        world = initialize_fixture(repo).world
        result = ToolSession(world, context, capabilities=capabilities, **kwargs)
        return result

    def test_catalog_is_independent_and_has_closed_argument_schemas(self):
        catalog = definitions()
        self.assertEqual(len(catalog), 14)
        self.assertEqual(len({item["name"] for item in catalog}), 14)
        self.assertTrue(all(item["input_schema"]["additionalProperties"] is False for item in catalog))
        catalog[0]["input_schema"]["properties"].clear()
        self.assertTrue(definitions()[0]["input_schema"]["properties"])

    def test_capabilities_and_arbitrary_tools_are_denied(self):
        session = self.session()
        for name, arguments in (("filesystem.write", {"path": "test.txt", "text": "x"}),
                                ("canon.apply", {}), ("git.push", {}), ("shell", {"command": "echo"})):
            result = session.call(name, arguments)
            self.assertEqual(result["status"], "denied")
            self.assertIsNone(result["data"])
            self.schemas.validate("tool_result", result)

    def test_closed_types_and_nonfinite_input(self):
        session = self.session(["workspace", "papers_read"])
        for name, arguments in (("filesystem.read", {"path": "a", "extra": True}),
                                ("papers.crossref.search", {"query": "test", "limit": True}),
                                ("papers.arxiv.search", {"query": "test", "limit": 100})):
            self.assertEqual(session.call(name, arguments)["error"]["code"], "invalid_arguments")
        with self.assertRaises(DataError):
            session.call("filesystem.write", {"value": float("nan")})

    def test_workspace_read_write_is_append_only_and_receipted(self):
        session = self.session(["workspace"])
        result = session.call("filesystem.write", {"path": "notes/example.txt", "text": "TEST FIXTURE"})
        self.assertEqual(result["status"], "completed")
        read = session.call("filesystem.read", {"path": "notes/example.txt"})
        self.assertEqual(read["data"]["text"], "TEST FIXTURE")
        second = session.call("filesystem.write", {"path": "notes/example.txt", "text": "overwrite"})
        self.assertEqual(second["error"]["code"], "already_exists")
        stored = read_json(session.workspace.path("receipts/" + result["result_id"] + ".json"))
        self.assertEqual(stored, result)
        self.assertEqual(result["receipt"]["payload_sha256"], digest({key: result[key] for key in ("status", "data", "error")}))

    def test_windows_and_posix_path_escapes_are_rejected(self):
        for value in ("../secret", "/absolute", "C:/secret", "C:\\secret", "a/../b", "a//b", "./x",
                      "a:stream", "CON", "aux.txt", "x/LPT1.md", "trailing.", "trailing ", "a\nfile", "a?b"):
            with self.subTest(value=value), self.assertRaises(ToolError):
                safe_relative(value)
        session = self.session(["workspace"])
        self.assertEqual(session.call("filesystem.write", {"path": "../../world/world.json", "text": "x"})["status"], "denied")

    def test_linked_storage_is_rejected(self):
        root, outside = self.temporary(), self.temporary()
        link = root / "link"
        if sys.platform == "win32":
            created = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
            if created.returncode:
                self.skipTest("Junction creation unavailable")
        else:
            link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ToolError):
            Workspace(root).write("link/file.txt", b"x")
        # Remove only the verified test link, never its target, before temp cleanup.
        self.assertTrue(link.absolute().is_relative_to(SCRATCH.resolve()))
        if sys.platform == "win32":
            link.rmdir()
        else:
            link.unlink()
        self.assertFalse((outside / "file.txt").exists())

    def test_agent_runs_cannot_read_each_others_files(self):
        first = self.session(["workspace"])
        first.call("filesystem.write", {"path": "answer.txt", "text": "PRIVATE FIRST ANSWER"})
        other = copy.deepcopy(first.context)
        other["agent_run_id"] = new_id("agent_run")
        second = ToolSession(first.world, other, capabilities=["workspace"])
        result = second.call("filesystem.read", {"path": "answer.txt"})
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("PRIVATE FIRST ANSWER", json.dumps(result))

    def test_canon_read_uses_copied_selected_snapshot_only(self):
        session = self.session(["canon_read"])
        context = session.context
        identifier = context["relevant_entities"][0]
        first = session.call("canon.read", {"entity_id": identifier})
        self.assertEqual(first["status"], "completed")
        first["data"]["record"]["title"] = "MODIFIED RETURN VALUE"
        self.assertNotEqual(session.call("canon.read", {"entity_id": identifier})["data"]["record"]["title"], "MODIFIED RETURN VALUE")
        self.assertEqual(session.call("canon.read", {"entity_id": "TECH-999"})["status"], "denied")
        evidence_id = next(iter(session.evidence))
        self.assertEqual(session.call("evidence.read", {"evidence_id": evidence_id})["status"], "completed")
        self.assertEqual(session.call("evidence.read", {"evidence_id": new_id("evidence")})["status"], "denied")

    def test_invalid_agent_input_cannot_create_session(self):
        session = self.session()
        bad = copy.deepcopy(session.context)
        bad["metadata"] = {"peer_answer": "leak"}
        with self.assertRaises(DataError):
            ToolSession(session.world, bad, capabilities=["workspace"])

    def test_same_agent_run_cannot_be_rebound_to_other_stage_or_input(self):
        session = self.session()
        bad = copy.deepcopy(session.context)
        bad["user_question"] = "different task content"
        with self.assertRaises(ToolError) as error:
            ToolSession(session.world, bad)
        self.assertEqual(error.exception.code, "context_mismatch")

    def test_link_detection_without_requiring_windows_link_privileges(self):
        root = self.temporary()
        with patch.object(Path, "is_symlink", return_value=True), self.assertRaises(ToolError):
            Workspace(root)
        if hasattr(Path, "is_junction"):
            with patch.object(Path, "is_junction", return_value=True), self.assertRaises(ToolError):
                Workspace(root)
        with ExitStack() as patches:
            patches.enter_context(patch.object(Path, "is_symlink", return_value=False))
            if hasattr(Path, "is_junction"):
                patches.enter_context(patch.object(Path, "is_junction", return_value=False))
            patches.enter_context(patch.object(Path, "lstat", return_value=SimpleNamespace(st_file_attributes=0x400)))
            with self.assertRaises(ToolError):
                Workspace(root)

    def test_bounded_reads_and_multibyte_outputs_enforce_byte_limit(self):
        session = self.session(["workspace"])
        with self.assertRaises(ToolError) as error:
            session.call("filesystem.write", {"path": "too-large.txt", "text": "中" * (MAX_BYTES // 2)})
        self.assertEqual(error.exception.code, "size_limit")
        self.assertFalse(session.files.path("too-large.txt").exists())

    def test_selected_pdf_text_is_extracted(self):
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        writer = PdfWriter()
        page = writer.add_blank_page(width=200, height=100)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 10 50 Td (TEST FIXTURE PDF TEXT) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        output = io.BytesIO()
        writer.write(output)
        self.assertIn('TEST FIXTURE PDF TEXT', document_text(output.getvalue(), '.pdf')["text"])

    def test_unverified_evidence_stays_in_private_drafts(self):
        session = self.session(["draft_write"])
        before = {path.name: path.read_bytes() for path in (session.repo / "world/evidence").iterdir()}
        record = read_json(ROOT / "examples/evidence.json")
        result = session.call("evidence.stage", {"record": record, "source_receipt_id": None})
        self.assertEqual(result["status"], "completed")
        self.assertTrue(session.workspace.path(result["data"]["path"]).is_file())
        self.assertEqual({path.name: path.read_bytes() for path in (session.repo / "world/evidence").iterdir()}, before)
        self.assertEqual(session.call("evidence.stage", {"record": record, "source_receipt_id": None})["error"]["code"], "already_exists")

    def verified_record(self, session, receipt):
        record = read_json(ROOT / "examples/evidence.json")
        record["source"]["source_type"] = "technical_documentation"
        record["source"]["url"] = receipt["data"]["source"]["url"]
        record["verification"] = {"status": "source_read", "accessed_at": receipt["data"]["source"]["accessed_at"],
                                  "method": receipt["tool_name"], "locator": "TEST FIXTURE excerpt",
                                  "excerpt": "TEST FIXTURE source text"}
        return record

    def test_source_read_requires_matching_live_receipt_and_excerpt(self):
        session = self.session(["draft_write", "web_read"], network=FakeNetwork())
        receipt = session.call("web.read", {"url": "https://example.invalid/source"})
        record = self.verified_record(session, receipt)
        original_id = record["evidence_id"]
        for key, value in (("excerpt", "not in source"), ("accessed_at", "2026-10-03T00:00:00Z"), ("method", "invented")):
            bad = copy.deepcopy(record)
            bad["verification"][key] = value
            self.assertEqual(session.call("evidence.stage", {"record": bad, "source_receipt_id": receipt["result_id"]})["error"]["code"], "source_mismatch")
        self.assertEqual(session.call("evidence.stage", {"record": record, "source_receipt_id": new_id("artifact")})["error"]["code"], "source_not_read")
        receipt["data"]["text"] = "forged external result"
        result = session.call("evidence.stage", {"record": record, "source_receipt_id": receipt["result_id"]})
        self.assertEqual(result["status"], "completed")
        self.assertEqual(read_json(session.workspace.path(result["data"]["path"]))["evidence_id"], original_id)

    def test_metadata_search_cannot_prove_full_source_read(self):
        payload = {"status": "ok", "message": {"items": [{"DOI": "10.1234/test", "title": ["TEST FIXTURE"]}]}}
        session = self.session(["papers_read", "draft_write"], network=FakeNetwork(json.dumps(payload).encode(), "application/json"))
        receipt = session.call("papers.crossref.search", {"query": "test", "limit": 1})
        record = self.verified_record(session, receipt)
        result = session.call("evidence.stage", {"record": record, "source_receipt_id": receipt["result_id"]})
        self.assertEqual(result["error"]["code"], "source_not_read")

    def test_pending_proposals_are_staged_without_apply(self):
        session = self.session(["draft_write"], role="integrator")
        record = read_json(ROOT / "examples/canon_change.json")
        record.update(world_id=session.context["world_id"], task_id=session.context["task_id"], run_id=session.context["run_id"],
                      base_canon_version=session.context["canon_version"])
        result = session.call("canon.propose", {"record": record})
        self.assertEqual(result["status"], "completed", result)
        self.assertEqual(result["data"]["status"], "pending")
        bad = copy.deepcopy(record)
        bad["approval"]["status"] = "approved"
        self.assertNotEqual(session.call("canon.propose", {"record": bad})["status"], "completed")
        specialist = self.session(["draft_write"])
        self.assertEqual(specialist.call("canon.propose", {"record": record})["status"], "denied")
        bad = copy.deepcopy(record)
        bad["before"] = read_json(ROOT / "examples/canon_entry.json")
        self.assertNotEqual(session.call("canon.propose", {"record": bad})["status"], "completed")

    def test_documents_require_explicit_named_grants(self):
        directory = self.temporary()
        document = directory / "sample.md"
        document.write_text("TEST FIXTURE source text", encoding="utf-8")
        session = self.session(["documents_read"], documents={"approved-paper": {"path": str(document), "url": "https://example.invalid/source"}})
        result = session.call("documents.read", {"reference_id": "approved-paper", "first_page": 1, "max_pages": 1})
        self.assertEqual(result["data"]["text"], "TEST FIXTURE source text")
        self.assertEqual(result["data"]["source"]["sha256"], hashlib.sha256(document.read_bytes()).hexdigest())
        self.assertEqual(session.call("documents.read", {"reference_id": str(document), "first_page": 1, "max_pages": 1})["status"], "denied")

    def test_docx_body_extraction_and_xml_entity_rejection(self):
        raw = io.BytesIO()
        xml = b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>TEST FIXTURE</w:t></w:r></w:p></w:body></w:document>'
        with zipfile.ZipFile(raw, "w") as archive:
            archive.writestr("word/document.xml", xml)
        self.assertEqual(document_text(raw.getvalue(), ".docx")["text"], "TEST FIXTURE")
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, "w") as archive:
            archive.writestr("word/document.xml", b'<!DOCTYPE doc [<!ENTITY boom "bad">]><doc/>')
        with self.assertRaises(ToolError):
            document_text(raw.getvalue(), ".docx")

    def test_pdf_selected_pages_and_scanned_page_limitations(self):
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.add_blank_page(width=72, height=72)
        output = io.BytesIO()
        writer.write(output)
        result = document_text(output.getvalue(), ".pdf", first_page=2, max_pages=1)
        self.assertEqual(result["total_pages"], 2)
        self.assertEqual(result["pages"], [{"page": 2, "text": ""}])
        self.assertIn("No OCR", result["limitations"][0])
        with self.assertRaises(ToolError):
            document_text(output.getvalue(), ".pdf", first_page=3)
        with self.assertRaises(ToolError):
            document_text(b"not a PDF", ".pdf")

    def test_html_removes_scripts_and_records_actual_bytes_hash(self):
        body = b'<html><style>BAD STYLE</style><script>BAD CODE</script><p>TEST &amp; FIXTURE</p></html>'
        result = web_read(FakeNetwork(body, "text/html; charset=utf-8"), "https://example.invalid/source")
        self.assertEqual(result["text"], "TEST & FIXTURE")
        self.assertEqual(result["source"]["sha256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(result["trust"], "untrusted_source_content")
        with self.assertRaises(ToolError):
            web_read(FakeNetwork(b"PDF", "application/pdf"), "https://example.invalid/source")

    def test_crossref_doi_and_search_encoding_and_metadata_scope(self):
        item = {"DOI": "10.1234/test", "title": ["TEST FIXTURE"], "author": [{"given": "A", "family": "B"}],
                "published": {"date-parts": [[2020, 1, 1]]}}
        client = FakeNetwork(json.dumps({"status": "ok", "message": item}).encode(), "application/json")
        result = crossref(client, doi="https://doi.org/10.1234/test")
        self.assertEqual(result["items"][0]["authors"], ["A B"])
        self.assertEqual(result["items"][0]["verification_scope"], "bibliographic_metadata_only")
        self.assertIn("10.1234%2Ftest", client.urls[0])
        with self.assertRaises(ToolError):
            crossref(client, doi="10.1234/wrong")
        with self.assertRaises(ToolError):
            crossref(client, doi="not DOI")
        client = FakeNetwork(b'{"status":"ok","message":{"items":[]}}', "application/json")
        self.assertEqual(crossref(client, query="a & b", limit=1)["items"], [])
        self.assertIn("query=a+%26+b", client.urls[0])

    def test_arxiv_atom_query_and_error_detection(self):
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/1234.5678v1</id><title>TEST FIXTURE</title><summary>TEST ONLY</summary><author><name>A B</name></author></entry></feed>'
        client = FakeNetwork(atom, "application/atom+xml")
        result = arxiv(client, "all:propulsion AND ti:efficiency", 1)
        self.assertEqual(result["items"][0]["title"], "TEST FIXTURE")
        self.assertIn("max_results=1", client.urls[0])
        with self.assertRaises(ToolError):
            arxiv(FakeNetwork(b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors#bad</id></entry></feed>'), "bad", 1)
        with self.assertRaises(ToolError):
            arxiv(FakeNetwork(b'<!DOCTYPE doc [<!ENTITY bad "bad">]><feed/>'), "test", 1)

    def test_search_service_is_not_silently_substituted(self):
        session = self.session(["web_search"])
        result = session.call("web.search", {"query": "test", "limit": 1})
        self.assertEqual(result["status"], "unavailable")
        class Backend:
            def search(self, query, limit):
                return {"items": [], "source": {"provider": "TEST FIXTURE"}}
        session = self.session(["web_search"], search_backend=Backend())
        self.assertEqual(session.call("web.search", {"query": "test", "limit": 1})["status"], "completed")

    def test_provider_failure_does_not_print_secret_exception(self):
        class Backend:
            def search(self, query, limit):
                raise RuntimeError("DO NOT EXPOSE TEST SECRET")
        session = self.session(["web_search"], search_backend=Backend())
        result = session.call("web.search", {"query": "test", "limit": 1})
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("DO NOT EXPOSE", json.dumps(result))

    def test_network_denies_private_dns_credentials_and_ungranted_hosts(self):
        client = PublicHTTPS(["example.org"])
        public = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        with patch("socket.getaddrinfo", return_value=public):
            self.assertEqual(client.address("https://example.org/path")[1], "8.8.8.8")
            for url in ("http://example.org/", "https://localhost/", "https://example.org:444/", "https://user:password@example.org/", "https://example.org/#x", "https://example.org.evil/", "https://example.org/\nx"):
                with self.subTest(url=url), self.assertRaises(ToolError):
                    client.address(url)
        for address in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "192.0.2.1"):
            with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))]), self.assertRaises(ToolError):
                client.address("https://example.org/")

    def test_network_revalidates_redirects_and_caps_reads(self):
        class HTTPResponse:
            status = 302
            def getheader(self, name, default=None):
                return {"Location": "https://localhost/"}.get(name, default)
            def read(self, limit):
                return b""
        class Connection:
            def __init__(self, *args): pass
            def request(self, *args, **kwargs): pass
            def getresponse(self): return HTTPResponse()
            def close(self): pass
        client = PublicHTTPS(["example.org"], max_bytes=3)
        public = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        with patch("socket.getaddrinfo", return_value=public), patch("axiom_forge.tools.network._PinnedHTTPS", Connection), patch.object(client, "_throttle"):
            with self.assertRaises(ToolError) as denied:
                client.get("https://example.org/")
            self.assertEqual(denied.exception.code, "network_denied")
            HTTPResponse.status = 200
            HTTPResponse.read = lambda self, limit: b"long"
            with self.assertRaises(ToolError) as limit:
                client.get("https://example.org/")
            self.assertEqual(limit.exception.code, "size_limit")

    def script_backend(self, repo, content, *, enabled=True, timeout=5):
        directory = repo / "tools/python-scripts"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "fixture.py").write_text(content, encoding="utf-8")
        manifest = {"schema_version": "1.0", "scripts": [{"script_id": "fixture.echo", "path": "fixture.py",
                    "sha256": hashlib.sha256((directory / "fixture.py").read_bytes()).hexdigest(), "description": "TEST FIXTURE, no scientific computation"}]}
        return TrustedPython(repo, manifest, enabled=enabled, timeout=timeout)

    def test_reviewed_python_reuses_json_interface_and_strips_environment(self):
        session = self.session(["python_call"])
        content = "import json,sys,os\nrequest=json.load(sys.stdin)\nprint(json.dumps({'received': request, 'secret_present': 'AXIOM_TEST_SECRET' in os.environ}))\n"
        session.python_backend = self.script_backend(session.engine_root, content)
        with patch.dict("os.environ", {"AXIOM_TEST_SECRET": "DO NOT EXPOSE"}):
            first = session.call("python.run_reviewed", {"script_id": "fixture.echo", "input": {"parameter": 1}})
            second = session.call("python.run_reviewed", {"script_id": "fixture.echo", "input": {"parameter": 2}})
        self.assertEqual(first["status"], "completed", first)
        self.assertEqual(second["data"]["output"]["received"], {"parameter": 2})
        self.assertFalse(first["data"]["output"]["secret_present"])
        self.assertEqual(first["data"]["program"]["sha256"], second["data"]["program"]["sha256"])

    def test_python_default_off_unknown_script_and_changed_program(self):
        session = self.session(["python_call"])
        session.python_backend = self.script_backend(session.engine_root, "print('{}')", enabled=False)
        args = {"script_id": "fixture.echo", "input": {}}
        self.assertEqual(session.call("python.run_reviewed", args)["status"], "unavailable")
        session.python_backend.enabled = True
        self.assertEqual(session.call("python.run_reviewed", {**args, "script_id": "missing"})["error"]["code"], "needs_implementation")
        (session.engine_root / "tools/python-scripts/fixture.py").write_text("print('changed')", encoding="utf-8")
        self.assertEqual(session.call("python.run_reviewed", args)["error"]["code"], "program_changed")

    def test_python_failure_timeout_and_invalid_outputs(self):
        cases = [("import time; time.sleep(2)", "timeout"), ("raise RuntimeError('TEST ONLY')", "program_failed"),
                 ("print('not json')", "invalid_json"), ("print('[]')", "invalid_output"),
                 ("print('{\"x\":NaN}')", "invalid_json")]
        for source, code in cases:
            with self.subTest(code=code):
                session = self.session(["python_call"])
                session.python_backend = self.script_backend(session.engine_root, source, timeout=0.3 if code == "timeout" else 5)
                result = session.call("python.run_reviewed", {"script_id": "fixture.echo", "input": {}})
                self.assertEqual(result["error"]["code"], code, result)
                self.assertIsNone(result["data"])

    def test_python_manifest_rejects_escape_and_non_python_entry(self):
        repo = self.temporary()
        for path in ("../bad.py", "a.ps1", "C:/bad.py"):
            manifest = {"schema_version": "1.0", "scripts": [{"script_id": "test", "path": path,
                        "sha256": "0" * 64, "description": "TEST"}]}
            with self.assertRaises((ToolError, ValueError)):
                TrustedPython(repo, manifest)

    def test_git_read_has_no_mutation_or_secret_path_interface(self):
        # Research Git operations target an independent synthetic world, not
        # the development checkout with its host-managed worktree settings.
        world = initialize_fixture(self.temporary()).world
        self.assertEqual(git_read(world.root, "head")["text"].strip(), subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=world.root).decode().strip())
        for action, path in (("push", None), ("reset", None), ("diff", ".env"), ("diff", "docs/.env.local"), ("diff", "../README.md")):
            with self.assertRaises(ToolError):
                git_read(world.root, action, path)

    def test_receipt_schema_does_not_allow_failed_output_as_completed(self):
        record = read_json(ROOT / "examples/tool_result.json")
        self.schemas.validate("tool_result", record)
        record["status"] = "completed"
        with self.assertRaises(DataError):
            self.schemas.validate("tool_result", record)

    def test_production_world_remains_empty(self):
        self.assertEqual(set(collect_world(ROOT / "templates/legacy-world", self.schemas)), {"world/world.json"})

    def test_json_duplicates_and_nonfinite_output_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}'):
            with self.assertRaises(ToolError):
                strict_json(raw)

    def test_cli_lists_catalog_and_reports_unavailable_service(self):
        session = self.session()
        directory = self.temporary()
        for name, data in (("context", session.context), ("config", {"capabilities": ["web_search"]}),
                           ("arguments", {"query": "TEST FIXTURE", "limit": 1})):
            (directory / (name + ".json")).write_bytes(canonical_bytes(data))
        command = [sys.executable, "-m", "axiom_forge", "--engine-root", str(session.engine_root), "--world", str(session.repo), "--host-root", str(session.world.host_root), "tools"]
        listing = subprocess.run([*command, "list"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertEqual(len(json.loads(listing.stdout)), 14)
        result = subprocess.run([*command, "call", "web.search", "--input", str(directory / "arguments.json"),
                                 "--context", str(directory / "context.json"), "--config", str(directory / "config.json")],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
