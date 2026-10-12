import uuid
from datetime import UTC, datetime

from app.db.models.profile import Profile
from app.events.envelope import EVENT_VERSION
from app.events.published.profile_events import (
    build_profile_updated_event,
    changed_event_fields,
)
from tests.factories import make_profile


def test_changed_event_fields_maps_columns_to_contract_fields() -> None:
    assert changed_event_fields({"phone"}) == ["phone"]
    assert changed_event_fields({"city"}) == ["address"]
    assert changed_event_fields({"address_line", "city"}) == ["address"]
    assert changed_event_fields({"emergency_contact_phone"}) == ["emergencyContact"]


def test_changed_event_fields_is_ordered_and_ignores_department() -> None:
    fields = changed_event_fields({"emergency_contact_name", "department", "phone", "city"})

    assert fields == ["phone", "address", "emergencyContact"]
    assert changed_event_fields({"department"}) == []


def _profile() -> Profile:
    now = datetime(2026, 10, 6, 18, 45, 0, tzinfo=UTC)
    return make_profile(
        profile_id=uuid.UUID("0192b3c4-8a0f-7b32-9c1d-2e3f4a5b6c7d"),
        user_id=uuid.UUID("0192b3c4-7d8e-7f10-a2b3-4c5d6e7f8000"),
        phone="+573109876543",
        address_line="Cra 7 # 45-12 Apto 301",
        emergency_contact_name="Luis Gómez",
        emergency_contact_phone="+573151112233",
        created_at=now,
        updated_at=now,
    )


def test_profile_updated_envelope_follows_contract() -> None:
    correlation_id = uuid.uuid4()
    event = build_profile_updated_event(_profile(), ["phone"], correlation_id)

    assert event.source == "kenko.profile"
    assert event.detail_type == "ProfileUpdated"

    metadata = event.detail["metadata"]
    assert metadata["eventVersion"] == EVENT_VERSION == "1"
    assert metadata["correlationId"] == str(correlation_id)
    assert metadata["occurredAt"].endswith("Z")
    assert uuid.UUID(metadata["eventId"]).version == 7
    assert uuid.UUID(metadata["eventId"]) == event.event_id


def test_profile_updated_data_has_full_state_and_no_department() -> None:
    event = build_profile_updated_event(_profile(), ["phone", "address"], uuid.uuid4())

    data = event.detail["data"]
    assert data["userId"] == "0192b3c4-7d8e-7f10-a2b3-4c5d6e7f8000"
    assert data["profileId"] == "0192b3c4-8a0f-7b32-9c1d-2e3f4a5b6c7d"
    assert data["documentType"] == "CC"
    assert data["birthDate"] == "1995-03-21"
    assert data["phone"] == "+573109876543"
    assert data["address"] == {"line": "Cra 7 # 45-12 Apto 301", "city": "Bogotá"}
    assert data["emergencyContact"] == {"name": "Luis Gómez", "phone": "+573151112233"}
    assert data["changedFields"] == ["phone", "address"]
    assert data["updatedAt"] == "2026-10-06T18:45:00Z"
    assert "department" not in data


def test_emergency_contact_is_null_when_not_set() -> None:
    profile = make_profile(
        profile_id=uuid.uuid4(),
        emergency_contact_name=None,
        emergency_contact_phone=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    event = build_profile_updated_event(profile, ["emergencyContact"], uuid.uuid4())

    assert event.detail["data"]["emergencyContact"] is None
