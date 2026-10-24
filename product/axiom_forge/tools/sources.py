"""Search/metadata and source reading, without inferring scientific Evidence."""

import io
import re
import zipfile
from html.parser import HTMLParser
from urllib.parse import quote, urlencode
from xml.etree import ElementTree

from .storage import MAX_BYTES, ToolError, strict_json


class _HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "template"):
            self.hidden += 1
        elif not self.hidden and tag in ("p", "br", "div", "li", "h1", "h2", "h3", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def html_text(value):
    parser = _HTMLText()
    parser.feed(value)
    return re.sub(r"[ \t]+", " ", "".join(parser.parts)).strip()


def web_read(client, url):
    response = client.get(url)
    kind = response.content_type.split(";", 1)[0].strip().lower()
    if kind not in ("text/html", "text/plain", "application/json", "application/xhtml+xml"):
        raise ToolError("unsupported_document", "Web reader supports HTML/text/JSON; use the document reader for PDF")
    try:
        encoding = re.search(r"charset=[\"']?([\w-]+)", response.content_type, re.I)
        text = response.body.decode(encoding.group(1) if encoding else "utf-8")
        if kind in ("text/html", "application/xhtml+xml"):
            text = html_text(text)
    except (UnicodeError, LookupError) as exc:
        raise ToolError("unsupported_encoding", "Cannot decode source with its declared encoding") from exc
    return {"text": text, "source": response.provenance(), "trust": "untrusted_source_content"}


def _crossref_work(work):
    if not isinstance(work, dict) or not work.get("DOI"):
        raise ToolError("invalid_response", "Crossref work missing DOI")
    date = work.get("published", {}).get("date-parts", [[]])[0]
    authors = [" ".join(filter(None, [author.get("given"), author.get("family")]))
               or author.get("name", "") for author in work.get("author", [])]
    return {"doi": work["DOI"], "title": " ".join(work.get("title", [])),
            "authors": [name for name in authors if name],
            "journal_or_conference": "; ".join(work.get("container-title", [])) or None,
            "year": date[0] if date else None, "url": work.get("URL"),
            "abstract": html_text(work.get("abstract", "")) or None,
            "verification_scope": "bibliographic_metadata_only"}


def crossref(client, *, query=None, doi=None, limit=5):
    if doi is not None:
        doi = doi.removeprefix("https://doi.org/")
        if not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
            raise ToolError("invalid_doi", "Expected a DOI starting with 10.<registrant>/")
        url = "https://api.crossref.org/works/" + quote(doi, safe="")
    else:
        url = "https://api.crossref.org/works?" + urlencode({"query": query, "rows": limit})
    response = client.get(url)
    data = strict_json(response.body)
    if not isinstance(data, dict) or data.get("status") != "ok":
        raise ToolError("invalid_response", "Invalid Crossref response")
    message = data.get("message")
    if doi is not None:
        items = [_crossref_work(message)]
        if items[0]["doi"].lower() != doi.lower():
            raise ToolError("invalid_response", "Crossref returned a different DOI")
    else:
        if not isinstance(message, dict) or not isinstance(message.get("items"), list):
            raise ToolError("invalid_response", "Crossref search missing items")
        items = [_crossref_work(work) for work in message["items"][:limit]]
    return {"items": items, "source": response.provenance(), "trust": "untrusted_source_content"}


def arxiv(client, query, limit=5):
    response = client.get("https://export.arxiv.org/api/query?" + urlencode({
        "search_query": query, "start": 0, "max_results": limit}))
    if b"<!DOCTYPE" in response.body.upper() or b"<!ENTITY" in response.body.upper():
        raise ToolError("invalid_response", "XML declarations are not accepted")
    try:
        root = ElementTree.fromstring(response.body)
    except ElementTree.ParseError as exc:
        raise ToolError("invalid_response", "Invalid arXiv Atom XML") from exc
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    if root.tag != "{http://www.w3.org/2005/Atom}feed":
        raise ToolError("invalid_response", "Expected arXiv Atom feed")
    items = []
    for entry in root.findall("a:entry", ns)[:limit]:
        identifier = entry.findtext("a:id", "", ns)
        if "api/errors" in identifier:
            raise ToolError("invalid_query", "arXiv rejected the query")
        items.append({"url": identifier, "title": " ".join(entry.findtext("a:title", "", ns).split()),
                      "authors": [node.findtext("a:name", "", ns) for node in entry.findall("a:author", ns)],
                      "abstract": entry.findtext("a:summary", "", ns).strip(),
                      "published": entry.findtext("a:published", None, ns),
                      "doi": entry.findtext("x:doi", None, ns),
                      "verification_scope": "metadata_and_abstract_only"})
    return {"items": items, "source": response.provenance(), "trust": "untrusted_source_content"}


def document_text(raw, suffix, *, first_page=1, max_pages=20):
    if not 1 <= first_page <= 10000 or not 1 <= max_pages <= 50:
        raise ToolError("invalid_arguments", "Invalid page range")
    if suffix in (".txt", ".md", ".json", ".csv"):
        try:
            text = raw.decode("utf-8")
        except UnicodeError as exc:
            raise ToolError("unsupported_encoding", "Text documents must be UTF-8") from exc
        return {"text": text, "pages": [], "limitations": ["Text only; content is not a verified scientific claim."]}
    if suffix == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                info = archive.getinfo("word/document.xml")
                if info.file_size > MAX_BYTES:
                    raise ToolError("size_limit", "DOCX XML exceeds size limit")
                xml = archive.read(info)
                if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                    raise ToolError("invalid_document", "XML declarations are not accepted")
                root = ElementTree.fromstring(xml)
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                text = "\n".join(
                    "".join(node.text or "" for node in paragraph.findall(".//w:t", ns))
                    for paragraph in root.findall(".//w:p", ns))
                return {"text": text, "pages": [], "limitations": ["DOCX body text only; no layout, images, comments or pagination."]}
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError, RuntimeError) as exc:
            raise ToolError("invalid_document", "Invalid or unsupported DOCX") from exc
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ToolError("unavailable", "Install the locked pypdf dependency") from exc
        try:
            reader = PdfReader(io.BytesIO(raw), strict=True)
            if reader.is_encrypted:
                raise ToolError("encrypted_document", "Encrypted PDF is not enabled")
            if first_page > len(reader.pages):
                raise ToolError("invalid_arguments", "First page exceeds PDF length")
            pages = []
            for index in range(first_page - 1, min(len(reader.pages), first_page - 1 + max_pages)):
                page = reader.pages[index]
                stream = page.get_contents()
                if stream is not None and len(stream.get_data()) > 8 * MAX_BYTES:
                    raise ToolError("size_limit", "Decoded PDF page stream is too large")
                text = page.extract_text() or ""
                pages.append({"page": index + 1, "text": text})
            text = "\n".join(page["text"] for page in pages)
            if len(text.encode("utf-8")) > MAX_BYTES:
                raise ToolError("size_limit", "Extracted text exceeds size limit")
            return {"text": text, "pages": pages, "total_pages": len(reader.pages),
                    "limitations": ["No OCR; scanned pages may be empty. Equations, tables and reading order need source inspection.",
                                    "PDF parser is not an OS sandbox; only host-approved documents are accepted."]}
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError("invalid_document", "Cannot extract the requested PDF pages") from exc
    raise ToolError("unsupported_document", "Supported formats: UTF-8 text, Markdown, JSON, CSV, PDF and DOCX")
