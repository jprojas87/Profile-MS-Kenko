import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.ids import new_uuid7
from app.core.logging import correlation_id_var, user_id_var
from app.core.security import decode_access_token
from app.domain.exceptions import AuthenticationFailedError
from app.events.publisher import EventPublisher

_bearer = HTTPBearer(auto_error=False)


def get_db_session(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> uuid.UUID:
    if credentials is None:
        raise AuthenticationFailedError("Autenticación requerida")
    user_id = decode_access_token(credentials.credentials, get_settings())
    user_id_var.set(str(user_id))
    return user_id


def get_correlation_id() -> uuid.UUID:
    value = correlation_id_var.get()
    return uuid.UUID(value) if value else new_uuid7()


def get_event_publisher(request: Request) -> EventPublisher:
    publisher: EventPublisher = request.app.state.event_publisher
    return publisher


DbSession = Annotated[Session, Depends(get_db_session)]
CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]
CorrelationId = Annotated[uuid.UUID, Depends(get_correlation_id)]
EventPublisherDep = Annotated[EventPublisher, Depends(get_event_publisher)]
