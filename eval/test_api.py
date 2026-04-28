"""Integration tests against a running FastAPI server on localhost:8000.
Run: `uvicorn main:app` in another terminal, then `pytest eval/test_api.py`."""
import os
import uuid
import pytest
import httpx

BASE = os.environ.get("FELO_API", "http://localhost:8000")


@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_models_lists_at_least_one_provider():
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/models")
        assert r.status_code == 200
        assert len(r.json()["models"]) >= 1


@pytest.mark.asyncio
async def test_unknown_provider_returns_400():
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE}/api/chat", json={
            "message": "hi", "session_id": str(uuid.uuid4()),
            "user_id": "u-test", "provider": "bogus", "model": "claude-sonnet-4-6",
        })
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_quota_endpoint():
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/quota/u-test")
        assert r.status_code == 200
        body = r.json()
        assert body["limit"] >= body["used"]


@pytest.mark.asyncio
async def test_clear_session():
    sid = str(uuid.uuid4())
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE}/api/chat/{sid}")
        assert r.status_code == 200
