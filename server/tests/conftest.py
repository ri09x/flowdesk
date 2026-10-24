import os
import sys
import tempfile

# Isolate tests in a temp database before importing the app.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["FLOWDESK_DB"] = _tmp.name
os.environ["FLOWDESK_SECRET"] = "test-secret"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _schema():
    init_db()


@pytest.fixture()
def client():
    return TestClient(app)


def register(client: TestClient, email: str, name: str = "Test User", password: str = "password-123"):
    res = client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    assert res.status_code == 201, res.text
    return res.json()


@pytest.fixture()
def alice(client):
    import uuid

    email = f"alice-{uuid.uuid4().hex[:8]}@example.com"
    data = register(client, email, "Alice")
    data["email"] = email
    return data


@pytest.fixture()
def bob(client):
    import uuid

    email = f"bob-{uuid.uuid4().hex[:8]}@example.com"
    data = register(client, email, "Bob")
    data["email"] = email
    return data


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
