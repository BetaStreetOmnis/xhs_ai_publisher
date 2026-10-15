"""Access checks for the local Web API, before account/browser operations."""

import ipaddress
import os
import secrets
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse


def _origin(value: str) -> tuple:
    parsed = urlsplit(value)
    return parsed.scheme, parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)


def check_web_access(request: Request):
    """Require a token when configured; otherwise accept only local callers."""
    if not request.url.path.startswith("/api/"):
        return None

    # Browsers must use this server's own origin, even for local requests.
    origin = request.headers.get("origin")
    try:
        if origin and _origin(origin) != _origin(str(request.base_url)):
            return JSONResponse(status_code=403, content={"detail": "Cross-origin API access is disabled"})
    except ValueError:
        return JSONResponse(status_code=403, content={"detail": "Invalid request origin"})

    token = os.getenv("XHS_WEB_API_TOKEN", "").strip()
    if token:
        scheme, _, supplied = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not secrets.compare_digest(supplied.encode(), token.encode()):
            return JSONResponse(status_code=401, content={"detail": "A valid API bearer token is required"},
                                headers={"WWW-Authenticate": "Bearer"})
        return None

    local_client = False
    local_host = False
    try:
        local_client = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
        local_host = request.url.hostname == "localhost" or ipaddress.ip_address(request.url.hostname).is_loopback
    except ValueError:
        local_host = request.url.hostname == "localhost"
    if not local_client or not local_host:
        return JSONResponse(status_code=403, content={"detail": "Remote API access requires XHS_WEB_API_TOKEN"})
    return None
