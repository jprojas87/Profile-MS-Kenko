import uuid

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.db.models.profile import Profile
from app.domain.exceptions import ProfileNotFoundError
from app.events.published.profile_events import (
    build_profile_updated_event,
    changed_event_fields,
)
from app.events.publisher import EventPublisher
from app.repositories.profile_repository import ProfileRepository

EDITABLE_FIELDS = frozenset(
    {
        "phone",
        "address_line",
        "city",
        "department",
        "emergency_contact_name",
        "emergency_contact_phone",
    }
)


def _apply_changes(profile: Profile, changes: dict[str, str | None]) -> set[str]:
    changed_columns: set[str] = set()
    for column, value in changes.items():
        if getattr(profile, column) != value:
            setattr(profile, column, value)
            changed_columns.add(column)
    return changed_columns


class ProfileService:
    def __init__(self, session: Session, publisher: EventPublisher) -> None:
        self._session = session
        self._profiles = ProfileRepository(session)
        self._publisher = publisher

    def get_my_profile(self, user_id: uuid.UUID) -> Profile:
        profile = self._profiles.get_by_user_id(user_id)
        if profile is None:
            raise ProfileNotFoundError("Perfil no encontrado")
        return profile

    def update_my_profile(
        self,
        user_id: uuid.UUID,
        changes: dict[str, str | None],
        correlation_id: uuid.UUID,
    ) -> Profile:
        unknown = set(changes) - EDITABLE_FIELDS
        if unknown:
            raise ValueError(f"Campos no editables: {sorted(unknown)}")

        profile = self.get_my_profile(user_id)
        changed_columns = _apply_changes(profile, changes)
        if not changed_columns:
            return profile

        profile.updated_at = utc_now()
        self._session.commit()

        # Se publica solo después de confirmar la transacción.
        fields = changed_event_fields(changed_columns)
        if fields:
            event = build_profile_updated_event(profile, fields, correlation_id)
            self._publisher.publish(event)
        return profile
