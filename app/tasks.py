"""Dramatiq actors for work that should not run in API request processes."""

from __future__ import annotations

import dramatiq

from app.database import (
    get_profile,
    get_voice_message,
    init_db,
    submit_photo_for_moderation,
    update_voice_transcription,
    update_profile_embedding,
)
from app.engine import generate_embedding
from app.job_queue import job_queue
from app.object_storage import object_storage
from app.questions import build_profile_text
from app.transcription import transcribe_and_store

job_queue.initialize()


@dramatiq.actor(
    queue_name="kindred-embeddings",
    max_retries=3,
    min_backoff=15_000,
    max_backoff=300_000,
    time_limit=600_000,
)
def generate_profile_embedding(profile_id: str) -> str:
    """Generate and persist one profile embedding, safely repeatable on retry."""
    init_db()
    profile = get_profile(profile_id)
    if not profile:
        return "profile-missing"
    if profile.get("embedding"):
        return "embedding-already-present"
    embedding = generate_embedding(build_profile_text(profile))
    update_profile_embedding(profile_id, embedding.tobytes())
    return "embedding-ready"


@dramatiq.actor(
    queue_name="kindred-moderation",
    max_retries=3,
    min_backoff=5_000,
    max_backoff=120_000,
    time_limit=60_000,
)
def queue_photo_moderation(profile_id: str, filename: str) -> str:
    """Create the manual-review record outside the upload request process."""
    init_db()
    return submit_photo_for_moderation(profile_id, filename)


@dramatiq.actor(
    queue_name="kindred-transcription",
    max_retries=3,
    min_backoff=15_000,
    max_backoff=300_000,
    time_limit=600_000,
)
def transcribe_voice_message(voice_id: str, filename: str) -> str:
    """Read stored audio and persist its transcript outside the API process."""

    init_db()
    voice = get_voice_message(voice_id)
    if not voice:
        return "voice-message-missing"
    try:
        stored = object_storage.get_object(filename)
    except Exception:
        update_voice_transcription(
            voice_id,
            "unavailable",
            error="voice media is temporarily unavailable",
        )
        raise
    result = transcribe_and_store(
        voice_id,
        stored.content,
        filename=filename,
        content_type=voice.get("mime_type") or stored.metadata.content_type,
    )
    return result.status
