from app.events.envelope import PublishedEvent


class FakePublisher:
    """Guarda los eventos en memoria. Solo para pruebas."""

    def __init__(self) -> None:
        self.events: list[PublishedEvent] = []

    def publish(self, event: PublishedEvent) -> None:
        self.events.append(event)
