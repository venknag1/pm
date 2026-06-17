import os

import pytest
from fastapi.testclient import TestClient

# DB_PATH is read lazily (each call to _db_path()), so setting the env var
# before the TestClient lifespan runs is sufficient.
from backend.main import app


@pytest.fixture
def client(tmp_path):
    os.environ["DB_PATH"] = str(tmp_path / "test.db")
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client(client):
    resp = client.post(
        "/api/auth/login", json={"username": "user", "password": "password"}
    )
    assert resp.status_code == 200
    return client
