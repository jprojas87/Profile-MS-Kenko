from datetime import UTC, datetime
from typing import Annotated

from pydantic import PlainSerializer


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_zulu(value: datetime) -> str:
    """ISO-8601 en UTC con sufijo Z y sin microsegundos (formato de los eventos)."""
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


UtcDatetime = Annotated[datetime, PlainSerializer(to_zulu, return_type=str)]
