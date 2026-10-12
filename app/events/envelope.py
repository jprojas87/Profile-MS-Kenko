import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.core.ids import new_uuid7
from app.core.time import to_zulu, utc_now

EVENT_VERSION = "1"


class EventModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PublishedEvent(BaseModel):
    source: str
    detail_type: str
    event_id: uuid.UUID
    detail: dict[str, Any]


def build_event(
    *,
    source: str,
    detail_type: str,
    data: EventModel,
    correlation_id: uuid.UUID,
) -> PublishedEvent:
    event_id = new_uuid7()
    metadata = {
        "eventId": str(event_id),
        "eventVersion": EVENT_VERSION,
        "occurredAt": to_zulu(utc_now()),
        "correlationId": str(correlation_id),
    }
    return PublishedEvent(
        source=source,
        detail_type=detail_type,
        event_id=event_id,
        detail={
            "metadata": metadata,
            "data": data.model_dump(by_alias=True, mode="json"),
        },
    )
