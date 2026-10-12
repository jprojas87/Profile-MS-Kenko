import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    get_settings.cache_clear()


def test_health_returns_ok() -> None:
    from app.main import create_app

    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_correlation_id_is_echoed_when_valid() -> None:
    from app.main import create_app

    client = TestClient(create_app())
    correlation_id = str(uuid.uuid4())

    response = client.get("/health", headers={"X-Correlation-Id": correlation_id})

    assert response.headers["X-Correlation-Id"] == correlation_id


def test_correlation_id_is_generated_when_invalid() -> None:
    from app.main import create_app

    client = TestClient(create_app())

    response = client.get("/health", headers={"X-Correlation-Id": "no-es-uuid"})

    assert uuid.UUID(response.headers["X-Correlation-Id"])
    assert response.headers["X-Correlation-Id"] != "no-es-uuid"
