import uuid

from sqlalchemy.orm import Session

from app.db.models.processed_event import ProcessedEvent


class ProcessedEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def exists(self, event_id: uuid.UUID) -> bool:
        return self._session.get(ProcessedEvent, event_id) is not None

    def add(self, event_id: uuid.UUID, event_type: str) -> None:
        self._session.add(ProcessedEvent(event_id=event_id, event_type=event_type))
        self._session.flush()
