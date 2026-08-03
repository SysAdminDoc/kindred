"""Dramatiq actors for work that should not run in API request processes."""

from __future__ import annotations

import dramatiq

from app.database import (
    get_profile,
    init_db,
    submit_photo_for_moderation,
    update_profile_embedding,
)
from app.engine import generate_embedding
from app.job_queue import job_queue
from app.questions import build_profile_text

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
