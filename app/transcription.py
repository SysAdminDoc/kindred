"""Optional server-side transcription for voice messages.

Kindred keeps voice delivery independent from transcription.  When enabled,
this adapter sends the stored audio to an OpenAI-compatible
``/audio/transcriptions`` endpoint and persists the returned text.  A local
development install can leave the adapter disabled, while self-hosters may
point it at a local Whisper service or an approved hosted provider.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.config import (
    TRANSCRIPTION_API_KEY,
    TRANSCRIPTION_ENABLED,
    TRANSCRIPTION_MODEL,
    TRANSCRIPTION_TIMEOUT_SECONDS,
    TRANSCRIPTION_URL,
)


log = logging.getLogger("kindred.transcription")


class TranscriptionError(RuntimeError):
    """Base error for the optional transcription adapter."""


class TranscriptionConfigurationError(TranscriptionError):
    """The enabled transcription adapter is not configured safely."""


@dataclass(frozen=True)
class TranscriptionResult:
    """The durable outcome of one transcription attempt."""

    status: str
    text: str | None = None
    provider: str | None = None
    error: str | None = None


def _safe_header(value: str) -> str:
    """Prevent configured or uploaded values from adding header newlines."""

    return str(value or "").replace("\r", "").replace("\n", "")


def _multipart_body(
    *,
    content: bytes,
    filename: str,
    content_type: str,
    model: str,
    boundary: str,
) -> bytes:
    """Build the small multipart request without adding a runtime dependency."""

    safe_filename = Path(filename).name or "voice.webm"
    safe_filename = _safe_header(safe_filename)
    safe_content_type = _safe_header(content_type) or "application/octet-stream"
    safe_model = _safe_header(model) or "whisper-1"
    delimiter = boundary.encode("ascii")
    parts = [
        b"--" + delimiter,
        b'Content-Disposition: form-data; name="model"',
        b"",
        safe_model.encode("utf-8"),
        b"--" + delimiter,
        (
            'Content-Disposition: form-data; name="file"; filename="'
            + safe_filename
            + '"'
        ).encode("utf-8"),
        ("Content-Type: " + safe_content_type).encode("ascii", errors="ignore"),
        b"",
        content,
        b"--" + delimiter + b"--",
        b"",
    ]
    return b"\r\n".join(parts)


class OpenAICompatibleTranscriber:
    """Call an OpenAI-compatible audio transcription endpoint."""

    provider_name = "openai-compatible"

    def __init__(
        self,
        *,
        enabled: bool = TRANSCRIPTION_ENABLED,
        url: str = TRANSCRIPTION_URL,
        api_key: str = TRANSCRIPTION_API_KEY,
        model: str = TRANSCRIPTION_MODEL,
        timeout_seconds: float = TRANSCRIPTION_TIMEOUT_SECONDS,
        opener: Callable[..., Any] | None = None,
    ):
        self.enabled = enabled
        self.url = url.strip()
        self.api_key = api_key.strip()
        self.model = model.strip() or "whisper-1"
        self.timeout_seconds = timeout_seconds
        self.opener = opener
        self._initialized = False

    @property
    def ready(self) -> bool:
        return bool(self.enabled and self.url)

    def initialize(self) -> str:
        if self.enabled and not self.url:
            raise TranscriptionConfigurationError(
                "KINDRED_TRANSCRIPTION_URL is required when transcription is enabled"
            )
        self._initialized = True
        return self.provider_name if self.enabled else "disabled"

    def health(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "configured": bool(self.url),
            "ready": self.ready,
            "provider": self.provider_name if self.enabled else None,
            "model": self.model if self.enabled else None,
        }

    @staticmethod
    def _response_text(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        for key in ("text", "transcript"):
            value = payload.get(key)
            if isinstance(value, str):
                text = value.strip()
                if text:
                    return text[:20_000]
        return None

    def transcribe(
        self,
        content: bytes,
        *,
        filename: str,
        content_type: str,
    ) -> TranscriptionResult:
        if not self.enabled:
            return TranscriptionResult(status="disabled")
        if not self.url:
            return TranscriptionResult(
                status="unavailable",
                provider=self.provider_name,
                error="transcription endpoint is not configured",
            )
        if not content:
            return TranscriptionResult(
                status="failed",
                provider=self.provider_name,
                error="voice file is empty",
            )

        boundary = "kindred-" + uuid.uuid4().hex
        body = _multipart_body(
            content=content,
            filename=filename,
            content_type=content_type,
            model=self.model,
            boundary=boundary,
        )
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            "User-Agent": "Kindred voice transcription",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {_safe_header(self.api_key)}"
        request = Request(self.url, data=body, headers=headers, method="POST")
        try:
            opener = self.opener or urlopen
            with opener(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, TypeError, URLError, UnicodeError, ValueError, TimeoutError) as exc:
            log.warning("Voice transcription endpoint unavailable: %s", exc)
            return TranscriptionResult(
                status="unavailable",
                provider=self.provider_name,
                error="transcription endpoint unavailable",
            )

        text = self._response_text(payload)
        if text is None:
            return TranscriptionResult(
                status="empty",
                provider=self.provider_name,
                error="transcription returned no speech text",
            )
        return TranscriptionResult(
            status="transcribed",
            text=text,
            provider=self.provider_name,
        )


def transcribe_and_store(
    voice_id: str,
    content: bytes,
    *,
    filename: str,
    content_type: str,
) -> TranscriptionResult:
    """Transcribe one stored voice payload and persist its safe status."""

    from app.database import update_voice_transcription

    update_voice_transcription(voice_id, "processing")
    try:
        result = transcription_service.transcribe(
            content,
            filename=filename,
            content_type=content_type,
        )
    except Exception:  # pragma: no cover - defensive provider boundary
        log.exception("Voice transcription failed for %s", voice_id)
        result = TranscriptionResult(
            status="failed",
            provider=transcription_service.provider_name,
            error="transcription failed",
        )
    update_voice_transcription(
        voice_id,
        result.status,
        transcript=result.text,
        provider=result.provider,
        error=result.error,
    )
    return result


transcription_service = OpenAICompatibleTranscriber()
