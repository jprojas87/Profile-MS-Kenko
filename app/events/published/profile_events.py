import uuid
from datetime import date

from app.core.time import UtcDatetime
from app.db.models.profile import Profile
from app.domain.enums import DocumentType
from app.events.envelope import EventModel, PublishedEvent, build_event

PROFILE_SOURCE = "kenko.profile"
PROFILE_UPDATED = "ProfileUpdated"

# Columna editable -> campo del evento. "department" no viaja en los eventos por ahora.
_EVENT_FIELD_BY_COLUMN = {
    "phone": "phone",
    "address_line": "address",
    "city": "address",
    "emergency_contact_name": "emergencyContact",
    "emergency_contact_phone": "emergencyContact",
}
_EVENT_FIELD_ORDER = ("phone", "address", "emergencyContact")


def changed_event_fields(changed_columns: set[str]) -> list[str]:
    fields = {
        _EVENT_FIELD_BY_COLUMN[column]
        for column in changed_columns
        if column in _EVENT_FIELD_BY_COLUMN
    }
    return [field for field in _EVENT_FIELD_ORDER if field in fields]


class EventAddress(EventModel):
    line: str
    city: str


class EventEmergencyContact(EventModel):
    name: str | None
    phone: str | None


class ProfileUpdatedData(EventModel):
    user_id: uuid.UUID
    profile_id: uuid.UUID
    document_type: DocumentType
    document_number: str
    first_name: str
    last_name: str
    birth_date: date
    gender: str
    email: str
    phone: str
    address: EventAddress
    emergency_contact: EventEmergencyContact | None
    changed_fields: list[str]
    updated_at: UtcDatetime


def build_profile_updated_event(
    profile: Profile,
    changed_fields: list[str],
    correlation_id: uuid.UUID,
) -> PublishedEvent:
    has_emergency_contact = (
        profile.emergency_contact_name is not None or profile.emergency_contact_phone is not None
    )
    data = ProfileUpdatedData(
        user_id=profile.user_id,
        profile_id=profile.profile_id,
        document_type=profile.document_type,
        document_number=profile.document_number,
        first_name=profile.first_name,
        last_name=profile.last_name,
        birth_date=profile.birth_date,
        gender=profile.gender,
        email=profile.email,
        phone=profile.phone,
        address=EventAddress(line=profile.address_line, city=profile.city),
        emergency_contact=(
            EventEmergencyContact(
                name=profile.emergency_contact_name,
                phone=profile.emergency_contact_phone,
            )
            if has_emergency_contact
            else None
        ),
        changed_fields=changed_fields,
        updated_at=profile.updated_at,
    )
    return build_event(
        source=PROFILE_SOURCE,
        detail_type=PROFILE_UPDATED,
        data=data,
        correlation_id=correlation_id,
    )
