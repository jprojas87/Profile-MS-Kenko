import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    # Sin contexto de lifespan no hay engine: /health responde 503, pero el middleware
    # de correlación debe funcionar igual.
    return TestClient(create_app())


def test_correlation_id_is_echoed_when_valid(client: TestClient) -> None:
    correlation_id = str(uuid.uuid4())

    response = client.get("/health", headers={"X-Correlation-Id": correlation_id})

    assert response.headers["X-Correlation-Id"] == correlation_id


def test_correlation_id_is_generated_when_invalid(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Correlation-Id": "no-es-uuid"})

    generated = response.headers["X-Correlation-Id"]
    assert uuid.UUID(generated)
    assert generated != "no-es-uuid"
