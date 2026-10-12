import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_event_publisher
from app.db.models.profile import Profile
from app.events.adapters.fake_publisher import FakePublisher
from app.main import create_app
from app.repositories.profile_repository import ProfileRepository
from tests.factories import make_profile, make_token

BASE = "/api/v1/profiles/me"
NEW_PHONE = "+573109876543"


@pytest.fixture
def publisher() -> FakePublisher:
    return FakePublisher()


@pytest.fixture
def client(migrated_database: str, publisher: FakePublisher) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_event_publisher] = lambda: publisher
    with TestClient(app) as test_client:
        yield test_client


def _auth(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(user_id)}"}


def _seed(db_session: Session, **overrides: object) -> Profile:
    profile = make_profile(**overrides)
    ProfileRepository(db_session).add(profile)
    db_session.commit()
    return profile


def test_update_phone_publishes_profile_updated(
    client: TestClient, db_session: Session, publisher: FakePublisher
) -> None:
    user_id = uuid.uuid4()
    _seed(db_session, user_id=user_id)

    response = client.put(BASE, json={"phone": NEW_PHONE}, headers=_auth(user_id))

    assert response.status_code == 200
    body = response.json()
    assert body["phone"] == NEW_PHONE

    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event.source == "kenko.profile"
    assert event.detail_type == "ProfileUpdated"
    data = event.detail["data"]
    assert data["changedFields"] == ["phone"]
    assert data["phone"] == NEW_PHONE
    assert data["address"] == {"line": "Cra 15 # 93-60 Apto 402", "city": "Bogotá"}
    assert data["userId"] == str(user_id)
    assert data["updatedAt"] == body["updatedAt"]
    assert "department" not in data


def test_event_correlation_id_comes_from_header(
    client: TestClient, db_session: Session, publisher: FakePublisher
) -> None:
    user_id = uuid.uuid4()
    _seed(db_session, user_id=user_id)
    correlation_id = str(uuid.uuid4())

    client.put(
        BASE,
        json={"phone": NEW_PHONE},
        headers={**_auth(user_id), "X-Correlation-Id": correlation_id},
    )

    assert publisher.events[0].detail["metadata"]["correlationId"] == correlation_id


def test_same_values_do_not_write_or_publish(
    client: TestClient, db_session: Session, publisher: FakePublisher
) -> None:
    user_id = uuid.uuid4()
    profile = _seed(db_session, user_id=user_id)
    before = profile.updated_at

    response = client.put(
        BASE,
        json={
            "phone": "+573001234567",
            "address": {"line": "Cra 15 # 93-60 Apto 402", "city": "Bogotá"},
        },
        headers=_auth(user_id),
    )

    assert response.status_code == 200
    db_session.expire_all()
    assert profile.updated_at == before
    assert publisher.events == []


def test_empty_body_does_not_publish(
    client: TestClient, db_session: Session, publisher: FakePublisher
) -> None:
    user_id = uuid.uuid4()
    _seed(db_session, user_id=user_id)

    response = client.put(BASE, json={}, headers=_auth(user_id))

    assert response.status_code == 200
    assert publisher.events == []


def test_department_change_persists_without_event(
    client: TestClient, db_session: Session, publisher: FakePublisher
) -> None:
    user_id = uuid.uuid4()
    profile = _seed(db_session, user_id=user_id)
    before = profile.updated_at

    response = client.put(BASE, json={"department": "Antioquia"}, headers=_auth(user_id))

    assert response.json()["department"] == "Antioquia"
    db_session.expire_all()
    assert profile.department == "Antioquia"
    assert profile.updated_at > before
    assert publisher.events == []


def test_address_change_is_published_with_full_state(
    client: TestClient, db_session: Session, publisher: FakePublisher
) -> None:
    user_id = uuid.uuid4()
    _seed(db_session, user_id=user_id)

    response = client.put(
        BASE,
        json={"address": {"line": "Cra 7 # 45-12 Apto 301", "city": "Medellín"}},
        headers=_auth(user_id),
    )

    assert response.status_code == 200
    data = publisher.events[0].detail["data"]
    assert data["changedFields"] == ["address"]
    assert data["address"] == {"line": "Cra 7 # 45-12 Apto 301", "city": "Medellín"}
    assert data["phone"] == "+573001234567"


def test_clearing_emergency_contact_is_published(
    client: TestClient, db_session: Session, publisher: FakePublisher
) -> None:
    user_id = uuid.uuid4()
    _seed(
        db_session,
        user_id=user_id,
        emergency_contact_name="Luis Gómez",
        emergency_contact_phone="+573151112233",
    )

    response = client.put(BASE, json={"emergencyContact": None}, headers=_auth(user_id))

    assert response.status_code == 200
    assert response.json()["emergencyContact"] is None
    data = publisher.events[0].detail["data"]
    assert data["changedFields"] == ["emergencyContact"]
    assert data["emergencyContact"] is None


def test_multiple_changes_list_fields_in_contract_order(
    client: TestClient, db_session: Session, publisher: FakePublisher
) -> None:
    user_id = uuid.uuid4()
    _seed(db_session, user_id=user_id)

    client.put(
        BASE,
        json={
            "emergencyContact": {"name": "Luis Gómez", "phone": "+573151112233"},
            "phone": NEW_PHONE,
        },
        headers=_auth(user_id),
    )

    assert publisher.events[0].detail["data"]["changedFields"] == [
        "phone",
        "emergencyContact",
    ]


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"email": "otro@example.com"}, "email"),
        ({"documentNumber": "999"}, "documentNumber"),
        ({"birthDate": "1990-01-01"}, "birthDate"),
        ({"phone": "3001234567"}, "phone"),
        ({"phone": None}, "phone"),
        ({"address": {"line": "Cra 1"}}, "address.city"),
        ({"emergencyContact": {"name": "Luis"}}, "emergencyContact.phone"),
    ],
)
def test_invalid_or_non_editable_fields_return_422(
    client: TestClient,
    db_session: Session,
    publisher: FakePublisher,
    body: dict[str, object],
    field: str,
) -> None:
    user_id = uuid.uuid4()
    _seed(db_session, user_id=user_id)

    response = client.put(BASE, json=body, headers=_auth(user_id))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in [detail["field"] for detail in error["details"]]
    assert publisher.events == []


def test_rejected_update_does_not_change_profile(client: TestClient, db_session: Session) -> None:
    user_id = uuid.uuid4()
    _seed(db_session, user_id=user_id)

    client.put(BASE, json={"email": "otro@example.com"}, headers=_auth(user_id))

    assert client.get(BASE, headers=_auth(user_id)).json()["email"] == "maria.gomez@example.com"


def test_update_requires_authentication(
    client: TestClient, db_session: Session, publisher: FakePublisher
) -> None:
    _seed(db_session, user_id=uuid.uuid4())

    response = client.put(BASE, json={"phone": NEW_PHONE})

    assert response.status_code == 401
    assert publisher.events == []


def test_update_of_missing_profile_returns_404(
    client: TestClient, publisher: FakePublisher
) -> None:
    response = client.put(BASE, json={"phone": NEW_PHONE}, headers=_auth(uuid.uuid4()))

    assert response.status_code == 404
    assert publisher.events == []
