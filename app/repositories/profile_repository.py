import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.profile import Profile
from app.domain.enums import DocumentType


class ProfileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_user_id(self, user_id: uuid.UUID) -> Profile | None:
        return self._session.scalar(select(Profile).where(Profile.user_id == user_id))

    def get_by_document(self, document_type: DocumentType, document_number: str) -> Profile | None:
        return self._session.scalar(
            select(Profile).where(
                Profile.document_type == document_type,
                Profile.document_number == document_number,
            )
        )

    def add(self, profile: Profile) -> None:
        self._session.add(profile)
        self._session.flush()
