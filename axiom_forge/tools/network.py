"""Small public HTTPS GET client; exact host grants, pinned DNS and bounded reads."""

import hashlib
import http.client
import ipaddress
import socket
import ssl
import threading
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

from ..snapshots import utc_now
from .storage import MAX_BYTES, ToolError


@dataclass(frozen=True)
class Response:
    url: str
    content_type: str
    body: bytes
    accessed_at: str

    def provenance(self):
        return {"url": self.url, "accessed_at": self.accessed_at,
                "sha256": hashlib.sha256(self.body).hexdigest(),
                "bytes": len(self.body), "content_type": self.content_type,
                "verification_scope": "retrieved_bytes_only"}


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        connection = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(connection, server_hostname=self.host)
        except Exception:
            connection.close()
            raise


class PublicHTTPS:
    def __init__(self, allowed_hosts, *, timeout=10, max_bytes=MAX_BYTES, contact=None):
        if not 0 < timeout <= 30 or not 0 < max_bytes <= MAX_BYTES:
            raise ValueError("Invalid HTTP limits")
        self.hosts = frozenset(allowed_hosts)
        if any(not isinstance(host, str) or not host or host != host.lower()
               or any(c in host for c in '/:@?#') for host in self.hosts):
            raise ValueError("Expected exact lowercase HTTPS host names")
        if contact is not None and (not isinstance(contact, str) or len(contact) > 200 or '\n' in contact or '\r' in contact):
            raise ValueError("Invalid contact")
        self.contact = contact
        self.timeout, self.max_bytes = timeout, max_bytes
        self._last, self._lock = {}, threading.Lock()

    def address(self, url):
        try:
            parsed = urlsplit(url)
            if (parsed.scheme != "https" or parsed.hostname not in self.hosts
                    or parsed.username is not None or parsed.password is not None
                    or parsed.port not in (None, 443) or parsed.fragment
                    or any(ord(c) < 33 or c == '\\' for c in url)):
                raise ValueError()
            addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
                raise ValueError()
            return parsed, addresses[0][4][0]
        except ValueError as exc:
            raise ToolError("network_denied", "URL must use an allowed HTTPS host and public address") from exc
        except OSError as exc:
            raise ToolError("network_error", "Public HTTPS DNS lookup failed") from exc

    def _throttle(self, host):
        # One client serializes arXiv requests with >= 3 s spacing; Crossref >= 1 s.
        gap = 3 if host == "export.arxiv.org" else 1
        with self._lock:
            delay = self._last.get(host, 0) + gap - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self._last[host] = time.monotonic()

    def get(self, url):
        if not isinstance(url, str) or len(url) > 4096:
            raise ToolError("network_denied", "Invalid URL")
        for _ in range(5):
            parsed, address = self.address(url)
            self._throttle(parsed.hostname)
            connection = _PinnedHTTPS(parsed.hostname, address, self.timeout)
            try:
                headers = {"User-Agent": "AxiomForge/0.5" + (f" (mailto:{self.contact})" if self.contact else ""),
                           "Accept-Encoding": "identity", "Accept": "application/json, application/atom+xml, text/html, text/plain"}
                target = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
                connection.request("GET", target, headers=headers)
                response = connection.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader("Location")
                    if not location:
                        raise ToolError("http_error", "Redirect has no location")
                    url = urljoin(url, location)
                    continue  # Revalidate grant and public DNS on each hop.
                if response.status != 200:
                    raise ToolError("http_error", f"HTTP {response.status}; no automatic retry")
                if response.getheader("Content-Encoding", "identity").lower() != "identity":
                    raise ToolError("unsupported_encoding", "Compressed HTTP responses are not enabled")
                raw = response.read(self.max_bytes + 1)
                if len(raw) > self.max_bytes:
                    raise ToolError("size_limit", "HTTP response exceeds size limit")
                return Response(url, response.getheader("Content-Type", ""), raw, utc_now())
            except (OSError, http.client.HTTPException) as exc:
                raise ToolError("network_error", "HTTPS request failed; no source was retrieved") from exc
            finally:
                connection.close()
        raise ToolError("redirect_limit", "Too many redirects")
