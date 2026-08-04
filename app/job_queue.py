"""Dramatiq broker setup and safe queue submission helpers."""

from __future__ import annotations

import logging
from typing import Any

from app.config import (
    QUEUE_ENABLED,
    QUEUE_NAMESPACE,
    QUEUE_REQUIRED,
    REDIS_URL,
)

logger = logging.getLogger(__name__)


class QueueConfigurationError(RuntimeError):
    """Raised when a required background-job broker cannot be used."""


class JobQueue:
    """Configure Dramatiq once and expose an inline development fallback."""

    def __init__(
        self,
        redis_url: str = "",
        enabled: bool = False,
        required: bool = False,
        namespace: str = "kindred:jobs",
    ):
        self.redis_url = redis_url.strip()
        self.enabled_requested = enabled
        self.required = required
        self.namespace = namespace
        self._backend = "uninitialized"
        self.broker: Any = None

    def initialize(self) -> str:
        if self._backend != "uninitialized":
            return self._backend

        import dramatiq
        from dramatiq.brokers.stub import StubBroker

        if not self.enabled_requested:
            self.broker = StubBroker()
            dramatiq.set_broker(self.broker)
            self._backend = "inline"
            return self._backend

        if not self.redis_url:
            if self.required:
                raise QueueConfigurationError(
                    "KINDRED_QUEUE_REQUIRED is enabled but KINDRED_REDIS_URL is empty"
                )
            logger.warning("Background queue has no Redis URL; using inline fallback")
            self.broker = StubBroker()
            dramatiq.set_broker(self.broker)
            self._backend = "inline"
            return self._backend

        try:
            from dramatiq.brokers.redis import RedisBroker

            broker = RedisBroker(url=self.redis_url, namespace=self.namespace)
            broker.client.ping()
            dramatiq.set_broker(broker)
            self.broker = broker
            self._backend = "dramatiq"
        except Exception as exc:
            if self.required:
                raise QueueConfigurationError(
                    f"Required background queue is unavailable: {exc}"
                ) from exc
            logger.warning("Background queue unavailable; using inline fallback: %s", exc)
            self.broker = StubBroker()
            dramatiq.set_broker(self.broker)
            self._backend = "inline"
        return self._backend

    @property
    def enabled(self) -> bool:
        return self.initialize() == "dramatiq"

    @property
    def backend_name(self) -> str:
        return self.initialize()

    def reset(self) -> None:
        if self.broker is not None:
            try:
                self.broker.close()
            except Exception:
                pass
        self.broker = None
        self._backend = "uninitialized"

    def health(self) -> dict[str, Any]:
        backend = self.backend_name
        return {
            "configured": self.enabled_requested,
            "required": self.required,
            "backend": backend,
            "healthy": backend == "dramatiq" or not self.required,
        }

    def enqueue_profile_embedding(self, profile_id: str) -> str | None:
        if not self.enabled:
            return None
        from app.tasks import generate_profile_embedding

        try:
            message = generate_profile_embedding.send(profile_id)
        except Exception as exc:
            if self.required:
                raise QueueConfigurationError(
                    f"Unable to enqueue profile embedding: {exc}"
                ) from exc
            logger.warning("Unable to enqueue profile embedding: %s", exc)
            return None
        return message.message_id

    def enqueue_photo_moderation(self, profile_id: str, filename: str) -> str | None:
        if not self.enabled:
            return None
        from app.tasks import queue_photo_moderation

        try:
            message = queue_photo_moderation.send(profile_id, filename)
        except Exception as exc:
            if self.required:
                raise QueueConfigurationError(
                    f"Unable to enqueue photo moderation: {exc}"
                ) from exc
            logger.warning("Unable to enqueue photo moderation: %s", exc)
            return None
        return message.message_id

    def enqueue_voice_transcription(self, voice_id: str, filename: str) -> str | None:
        if not self.enabled:
            return None
        from app.tasks import transcribe_voice_message

        try:
            message = transcribe_voice_message.send(voice_id, filename)
        except Exception as exc:
            if self.required:
                raise QueueConfigurationError(
                    f"Unable to enqueue voice transcription: {exc}"
                ) from exc
            logger.warning("Unable to enqueue voice transcription: %s", exc)
            return None
        return message.message_id


job_queue = JobQueue(
    REDIS_URL,
    enabled=QUEUE_ENABLED,
    required=QUEUE_REQUIRED,
    namespace=QUEUE_NAMESPACE,
)

# Configure the global Dramatiq broker before actors are imported. In local
# development this is a StubBroker and request handlers use inline work.
job_queue.initialize()
