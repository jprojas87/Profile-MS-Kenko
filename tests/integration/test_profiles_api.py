import uuid
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.enums import DocumentType
from app.main import create_app
from app.repositories.profile_repository import ProfileRepository
from tests.factories import make_profile, make_token

BASE = "/api/v1/profiles/me"


@pytest.fixture
def client(migrated_database: str) -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def _auth(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(user_id)}"}


def test_get_my_profile_returns_camel_case_body(client: TestClient, db_session: Session) -> None:
    user_id = uuid.uuid4()
    ProfileRepository(db_session).add(
        make_profile(
            user_id=user_id,
            emergency_contact_name="Luis Gómez",
            emergency_contact_phone="+573151112233",
            department="Cundinamarca",
        )
    )
    db_session.commit()

    response = client.get(BASE, headers=_auth(user_id))

    assert response.status_code == 200
    body = response.json()
    assert body["userId"] == str(user_id)
    assert body["firstName"] == "María Fernanda"
    assert body["documentType"] == "CC"
    assert body["birthDate"] == "1995-03-21"
    assert body["address"] == {"line": "Cra 15 # 93-60 Apto 402", "city": "Bogotá"}
    assert body["department"] == "Cundinamarca"
    assert body["emergencyContact"] == {"name": "Luis Gómez", "phone": "+573151112233"}
    assert "password" not in body


def test_emergency_contact_is_null_when_not_set(client: TestClient, db_session: Session) -> None:
    user_id = uuid.uuid4()
    ProfileRepository(db_session).add(make_profile(user_id=user_id))
    db_session.commit()

    body = client.get(BASE, headers=_auth(user_id)).json()

    assert body["emergencyContact"] is None
    assert body["department"] is None


def test_user_only_sees_own_profile(client: TestClient, db_session: Session) -> None:
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    ProfileRepository(db_session).add(
        make_profile(user_id=owner_id, document_type=DocumentType.CC, document_number="1")
    )
    db_session.commit()

    response = client.get(BASE, headers=_auth(other_id))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROFILE_NOT_FOUND"


def test_missing_token_returns_401(client: TestClient) -> None:
    response = client.get(BASE)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_non_bearer_scheme_returns_401(client: TestClient) -> None:
    response = client.get(BASE, headers={"Authorization": "Basic abc"})

    assert response.status_code == 401


def test_invalid_token_returns_401(client: TestClient) -> None:
    response = client.get(BASE, headers={"Authorization": "Bearer no.es.un.jwt"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_expired_token_returns_401(client: TestClient) -> None:
    token = make_token(uuid.uuid4(), expires_in=timedelta(minutes=-5))

    response = client.get(BASE, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_profile_not_found_returns_404(client: TestClient) -> None:
    response = client.get(BASE, headers=_auth(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROFILE_NOT_FOUND"


def test_user_id_in_body_or_query_is_ignored(client: TestClient, db_session: Session) -> None:
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    ProfileRepository(db_session).add(make_profile(user_id=owner_id))
    db_session.commit()

    response = client.get(f"{BASE}?user_id={owner_id}", headers=_auth(other_id))

    assert response.status_code == 404
