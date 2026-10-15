"""API access must be rejected before account or browser work starts."""

import httpx
import pytest
from fastapi import FastAPI, Request

from src.core.services.web_access import check_web_access


@pytest.mark.asyncio
@pytest.mark.parametrize("host,client,token,supplied,origin,expected", [
    ("localhost", "127.0.0.1", "", "", "", 200),
    ("127.0.0.1", "127.0.0.1", "", "", "http://127.0.0.1", 200),
    ("localhost", "::1", "", "", "", 200),
    ("localhost", "192.0.2.1", "", "", "", 403),
    ("attacker.example", "127.0.0.1", "", "", "", 403),
    ("localhost", "127.0.0.1", "", "", "https://attacker.example", 403),
    ("localhost", "127.0.0.1", "", "", "null", 403),
    ("localhost", "127.0.0.1", "secret", "", "", 401),
    ("localhost", "127.0.0.1", "secret", "wrong", "", 401),
    ("localhost", "127.0.0.1", "secret", "secret", "", 200),
    ("example.com", "192.0.2.1", "secret", "secret", "http://example.com", 200),
])
async def test_access_rejects_requests_before_handler(monkeypatch, host, client, token, supplied, origin, expected):
    monkeypatch.setenv("XHS_WEB_API_TOKEN", token)
    app = FastAPI()
    calls = []

    @app.middleware("http")
    async def protect(request: Request, call_next):
        rejection = check_web_access(request)
        return rejection if rejection is not None else await call_next(request)

    @app.post("/api/publish")
    async def publish():
        calls.append(True)
        return {"ok": True}

    headers = {}
    if supplied:
        headers["Authorization"] = f"Bearer {supplied}"
    if origin:
        headers["Origin"] = origin
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(client, 1234)),
                                 base_url=f"http://{host}") as session:
        response = await session.post("/api/publish", headers=headers)
    assert response.status_code == expected
    assert bool(calls) == (expected == 200)
