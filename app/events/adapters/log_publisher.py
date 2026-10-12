import logging

from app.events.envelope import PublishedEvent

logger = logging.getLogger(__name__)


class LogEventPublisher:
    """Publicador temporal hasta tener EventBridge: solo registra metadatos del evento.

    No registra el detalle porque contiene datos personales.
    """

    def publish(self, event: PublishedEvent) -> None:
        logger.info(
            "event_published",
            extra={
                "extra_fields": {
                    "eventId": str(event.event_id),
                    "eventType": event.detail_type,
                    "source": event.source,
                }
            },
        )
