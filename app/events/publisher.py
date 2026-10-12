from typing import Protocol

from app.events.envelope import PublishedEvent


class EventPublisher(Protocol):
    def publish(self, event: PublishedEvent) -> None: ...
