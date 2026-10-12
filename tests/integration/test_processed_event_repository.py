import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.processed_event_repository import ProcessedEventRepository


def test_event_is_not_processed_until_added(db_session: Session) -> None:
    repository = ProcessedEventRepository(db_session)
    event_id = uuid.uuid4()

    assert repository.exists(event_id) is False

    repository.add(event_id, "UserRegistered")

    assert repository.exists(event_id) is True


def test_duplicate_event_is_rejected(db_session: Session) -> None:
    repository = ProcessedEventRepository(db_session)
    event_id = uuid.uuid4()
    repository.add(event_id, "UserRegistered")

    with pytest.raises(IntegrityError):
        repository.add(event_id, "UserRegistered")
    db_session.rollback()
