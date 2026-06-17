"""Live connectivity test — skipped unless OPENROUTER_API_KEY is set in the environment."""

import os

import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client(tmp_path):
    os.environ["DB_PATH"] = str(tmp_path / "test.db")
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client(client):
    resp = client.post("/api/auth/login", json={"username": "user", "password": "password"})
    assert resp.status_code == 200
    return client


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set",
)
def test_ai_live_2_plus_2(auth_client):
    resp = auth_client.post("/api/ai", json={"message": "What is 2+2? Reply with only the number."})
    assert resp.status_code == 200
    reply = resp.json()["reply"]
    assert reply is not None
    assert "4" in reply, f"Unexpected reply: {reply!r}"
