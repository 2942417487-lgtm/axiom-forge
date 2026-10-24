"""Endpoint selection belongs to the trusted operator, never to AgentInput."""

from urllib.parse import urlsplit


def host_proxy(proxy_url):
    if proxy_url is None:
        return None
    if (not isinstance(proxy_url, str) or len(proxy_url) > 2048 or not proxy_url
            or any(character.isspace() or ord(character) < 32 for character in proxy_url)
            or "\\" in proxy_url):
        raise ValueError("Invalid host HTTPS proxy")
    try:
        parsed = urlsplit(proxy_url)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid host HTTPS proxy") from exc
    if (parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in ("", "/") or "?" in proxy_url or "#" in proxy_url or port == 0):
        raise ValueError("Host proxy requires HTTP(S) server without credentials or extra URL fields")
    return proxy_url.rstrip("/")


def host_endpoint(base_url, default, model):
    if base_url is None:
        if "/" in model:
            raise ValueError("Provider-qualified model requires an explicit host endpoint")
        return default
    if (not isinstance(base_url, str) or not base_url or len(base_url) > 2048
            or any(character.isspace() or ord(character) < 32 for character in base_url)
            or "\\" in base_url):
        raise ValueError("Invalid host API endpoint")
    try:
        parsed = urlsplit(base_url)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid host API endpoint") from exc
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment
            or "?" in base_url or "#" in base_url or port == 0):
        raise ValueError("Host API endpoint requires HTTPS without credentials, query or fragment")
    return base_url.rstrip("/")
