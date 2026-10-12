import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.enums import DocumentType
from app.repositories.profile_repository import ProfileRepository
from tests.factories import make_profile


def test_add_and_get_by_user_id(db_session: Session) -> None:
    repository = ProfileRepository(db_session)
    profile = make_profile()

    repository.add(profile)

    found = repository.get_by_user_id(profile.user_id)
    assert found is not None
    assert found.profile_id == profile.profile_id


def test_get_by_user_id_returns_none_when_missing(db_session: Session) -> None:
    assert ProfileRepository(db_session).get_by_user_id(uuid.uuid4()) is None


def test_get_by_document(db_session: Session) -> None:
    repository = ProfileRepository(db_session)
    repository.add(make_profile(document_type=DocumentType.TI, document_number="123"))

    found = repository.get_by_document(DocumentType.TI, "123")

    assert found is not None
    assert repository.get_by_document(DocumentType.CC, "123") is None


def test_duplicate_user_id_is_rejected(db_session: Session) -> None:
    repository = ProfileRepository(db_session)
    user_id = uuid.uuid4()
    repository.add(make_profile(user_id=user_id))

    with pytest.raises(IntegrityError):
        repository.add(make_profile(user_id=user_id, document_number="999"))
    db_session.rollback()


def test_duplicate_document_is_rejected(db_session: Session) -> None:
    repository = ProfileRepository(db_session)
    repository.add(make_profile(document_number="555"))

    with pytest.raises(IntegrityError):
        repository.add(make_profile(document_number="555"))
    db_session.rollback()
