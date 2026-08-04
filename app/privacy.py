"""Privacy metadata and scheduled account-retention enforcement.

SQLite has no portable column-comment facility, so the privacy audit is stored
next to the schema in two metadata tables.  Every discovered table/column gets
an entry: sensitive fields receive a conservative classification and all other
fields are explicitly marked ``not_pii``.  This keeps the audit machine-
checkable while allowing the account purge and retention scheduler to share the
same inventory.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from app.config import (
    INACTIVE_ACCOUNT_HARD_DELETE_MONTHS,
    PRIVACY_RETENTION_INTERVAL_HOURS,
)


log = logging.getLogger("kindred.privacy")


@dataclass(frozen=True)
class RetentionPolicy:
    retention_days: int | None
    timestamp_column: str | None
    automatic_cleanup: bool
    deletion_strategy: str


# These are the short-lived operational records.  Account/profile content is
# retained for the lifetime of the account and is removed by hard deletion.
TABLE_POLICY_OVERRIDES: dict[str, RetentionPolicy] = {
    "email_verifications": RetentionPolicy(2, "created_at", True, "token_expiry"),
    "password_resets": RetentionPolicy(2, "created_at", True, "token_expiry"),
    "message_cooldowns": RetentionPolicy(2, "window_start", True, "rate_limit_state"),
    "undo_blocks": RetentionPolicy(7, "created_at", True, "temporary_safety_state"),
    "refresh_tokens": RetentionPolicy(30, "created_at", True, "expired_session"),
    "request_logs": RetentionPolicy(30, "created_at", True, "operational_log"),
    "rate_limit_log": RetentionPolicy(30, "created_at", True, "operational_log"),
    "user_sessions": RetentionPolicy(90, "last_active", True, "expired_session"),
    "stories": RetentionPolicy(2, "created_at", True, "ephemeral_content"),
    "analytics_events": RetentionPolicy(730, "created_at", True, "aggregate_analytics"),
    "behavioral_events": RetentionPolicy(730, "created_at", True, "aggregate_analytics"),
    "content_filter_log": RetentionPolicy(730, "created_at", True, "moderation_audit"),
    "retention_emails": RetentionPolicy(730, "sent_at", True, "retention_audit"),
    "vacuum_log": RetentionPolicy(730, "ran_at", True, "operations_audit"),
    "privacy_cleanup_runs": RetentionPolicy(365, "completed_at", True, "operations_audit"),
    "audit_log": RetentionPolicy(2555, "created_at", False, "moderation_audit"),
    "safety_reports": RetentionPolicy(2555, "created_at", False, "safety_record"),
    "photo_safety_events": RetentionPolicy(2555, "created_at", False, "safety_record"),
}


# Tables without an explicit override receive this policy.  The row still
# exists in privacy_table_policies, so adding a new table cannot silently skip
# the audit.
DEFAULT_TABLE_POLICY = RetentionPolicy(
    None,
    None,
    False,
    "account_lifetime_or_manual_review",
)


PROFILE_PURGE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("activity_feed", "profile_id"),
    ("analytics_events", "profile_id"),
    ("availability_status", "profile_id"),
    ("behavioral_events", "profile_id"),
    ("blind_dates", "initiator_id"),
    ("blind_dates", "target_id"),
    ("blocks", "blocker_id"),
    ("blocks", "blocked_id"),
    ("calendar_feeds", "profile_a"),
    ("calendar_feeds", "profile_b"),
    ("calendar_feeds", "created_by"),
    ("compat_games", "profile_a"),
    ("compat_games", "profile_b"),
    ("compatibility_history", "profile_id_1"),
    ("compatibility_history", "profile_id_2"),
    ("conversation_starters", "from_id"),
    ("conversation_starters", "to_id"),
    ("daily_suggestions", "profile_id"),
    ("daily_suggestions", "suggested_id"),
    ("date_feedback", "profile_id"),
    ("date_feedback", "partner_id"),
    ("date_plans", "profile_a"),
    ("date_plans", "profile_b"),
    ("date_schedules", "profile_a"),
    ("date_schedules", "profile_b"),
    ("date_schedules", "scheduled_by"),
    ("endorsements", "endorser_id"),
    ("endorsements", "endorsed_id"),
    ("event_messages", "sender_id"),
    ("event_photos", "profile_id"),
    ("event_rsvps", "profile_id"),
    ("events", "creator_id"),
    ("feedback", "profile_a"),
    ("feedback", "profile_b"),
    ("flagged_content", "reporter_id"),
    ("game_turns", "profile_id"),
    ("group_members", "profile_id"),
    ("group_messages", "from_id"),
    ("group_polls", "profile_id"),
    ("group_post_reactions", "profile_id"),
    ("group_posts", "profile_id"),
    ("groups", "creator_id"),
    ("harassment_events", "from_id"),
    ("harassment_events", "to_id"),
    ("harassment_mutes", "owner_profile_id"),
    ("harassment_mutes", "muted_profile_id"),
    ("icebreaker_games", "profile_a"),
    ("icebreaker_games", "profile_b"),
    ("invites", "created_by"),
    ("invites", "used_by"),
    ("likes", "from_id"),
    ("likes", "target_id"),
    ("message_cooldowns", "from_id"),
    ("message_cooldowns", "to_id"),
    ("message_reactions", "profile_id"),
    ("messages", "from_id"),
    ("messages", "to_id"),
    ("music_preferences", "profile_id"),
    ("passed_profiles", "profile_id"),
    ("passed_profiles", "passed_id"),
    ("photo_hashes", "profile_id"),
    ("photo_moderation", "profile_id"),
    ("photo_safety_events", "profile_id"),
    ("photos", "profile_id"),
    ("pinned_messages", "pinned_by"),
    ("playlist_songs", "added_by"),
    ("poll_votes", "profile_id"),
    ("profile_badges", "profile_id"),
    ("profile_blog_posts", "profile_id"),
    ("profile_comments", "profile_id"),
    ("profile_comments", "from_id"),
    ("profile_friends", "profile_id"),
    ("profile_friends", "friend_id"),
    ("profile_prompts", "profile_id"),
    ("profile_reveal_stages", "viewer_id"),
    ("profile_reveal_stages", "target_id"),
    ("report_cooling_off", "reporter_id"),
    ("report_cooling_off", "reported_id"),
    ("safety_reports", "reporter_id"),
    ("safety_reports", "reported_id"),
    ("saved_searches", "profile_id"),
    ("selfie_verifications", "profile_id"),
    ("shared_playlists", "profile_a"),
    ("shared_playlists", "profile_b"),
    ("status_updates", "profile_id"),
    ("stories", "profile_id"),
    ("story_reactions", "profile_id"),
    ("story_views", "viewer_id"),
    ("super_likes", "from_id"),
    ("super_likes", "to_id"),
    ("undo_blocks", "blocker_id"),
    ("video_calls", "caller_id"),
    ("video_calls", "callee_id"),
    ("video_intros", "profile_id"),
    ("voice_messages", "from_id"),
    ("voice_messages", "to_id"),
    ("weight_learning_events", "profile_id"),
    ("weight_learning_events", "partner_id"),
)


USER_PURGE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("admin_messages", "from_admin_id"),
    ("admin_messages", "to_user_id"),
    ("ai_suggestions", "user_id"),
    ("announcements", "created_by"),
    ("audit_log", "admin_user_id"),
    ("canned_responses", "created_by"),
    ("compatibility_recalcs", "user_id"),
    ("email_verifications", "user_id"),
    ("oauth_accounts", "user_id"),
    ("password_resets", "user_id"),
    ("premium_subscriptions", "user_id"),
    ("push_subscriptions", "user_id"),
    ("questionnaire_progress", "user_id"),
    ("rate_limit_log", "user_id"),
    ("recovery_codes", "user_id"),
    ("refresh_tokens", "user_id"),
    ("request_logs", "user_id"),
    ("retention_emails", "user_id"),
    ("safety_checkins", "user_id"),
    ("shadow_bans", "user_id"),
    ("shadow_bans", "banned_by"),
    ("suspensions", "user_id"),
    ("suspensions", "suspended_by"),
    ("totp_secrets", "user_id"),
    ("user_locations", "user_id"),
    ("user_sessions", "user_id"),
    ("profile_boosts", "user_id"),
)


_PROFILE_DATA_FIELDS = {
    "name", "age", "gender", "seeking", "big_five", "big_five_raw",
    "attachment", "values_data", "tradeoffs", "self_disclosure",
    "love_language", "dealbreakers", "open_ended", "scenario_answers",
    "behavioral_answers", "photo", "weight_prefs", "learned_weight_prefs",
    "privacy", "invite_code", "communication_style", "financial_values",
    "dating_energy", "dating_pace", "relationship_intent", "country",
    "location", "headline", "about_me", "who_id_like_to_meet", "interests",
    "heroes", "mood", "music_embeds", "video_embeds", "profile_song",
    "profile_theme", "latitude", "longitude", "availability_text",
    "ip_fingerprint",
}

_USER_CONTENT_FIELDS = {
    "answer", "answer_a", "answer_b", "appeal_text", "artist", "background",
    "body", "caption", "categories", "city", "content", "description",
    "detail", "emergency_contact", "emergency_email", "filters", "flagged_text",
    "genre", "heroes", "metadata", "mood", "name", "notes", "old_content",
    "new_content", "options", "partner_name", "question", "reason", "resolution",
    "room_id", "safety_contact", "secret", "song_title", "spotify_url", "subject",
    "suggestion", "title", "transcript", "url", "venue", "email",
}

_CONTACT_FIELDS = {"email", "emergency_email", "endpoint", "p256dh", "auth"}
_LOCATION_FIELDS = {"location", "latitude", "longitude", "city", "venue"}
_SECRET_FIELDS = {
    "access_token", "refresh_token", "token", "token_hash", "password_hash",
    "secret", "key_hash", "code_hash", "api_key",
}
_NETWORK_FIELDS = {"ip_address", "ip_fingerprint"}


def _field_classification(table_name: str, column_name: str) -> str:
    if table_name == "profiles" and column_name in _PROFILE_DATA_FIELDS:
        if column_name in _LOCATION_FIELDS:
            return "location"
        if column_name in _NETWORK_FIELDS:
            return "network_identifier"
        if column_name in {"photo", "music_embeds", "video_embeds", "profile_song"}:
            return "profile_media"
        return "profile_attribute"
    if column_name in _SECRET_FIELDS:
        return "auth_secret"
    if column_name in _NETWORK_FIELDS:
        return "network_identifier"
    if column_name in _CONTACT_FIELDS:
        return "contact"
    if column_name in _LOCATION_FIELDS:
        return "location"
    if column_name in _USER_CONTENT_FIELDS:
        return "user_content"
    if column_name == "id" or column_name.endswith("_id"):
        return "pseudonymous_identifier"
    if column_name in {"filename", "selfie_photo", "photo"}:
        return "profile_media"
    return "not_pii"


def _policy_for(table_name: str) -> RetentionPolicy:
    return TABLE_POLICY_OVERRIDES.get(table_name, DEFAULT_TABLE_POLICY)


def ensure_privacy_metadata(conn) -> None:
    """Create and synchronize the machine-readable privacy inventory."""

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS privacy_field_tags (
            table_name TEXT NOT NULL,
            column_name TEXT NOT NULL,
            classification TEXT NOT NULL,
            is_pii INTEGER NOT NULL DEFAULT 0,
            retention_strategy TEXT NOT NULL,
            subject_scope TEXT NOT NULL DEFAULT 'none',
            notes TEXT,
            PRIMARY KEY(table_name, column_name)
        );
        CREATE TABLE IF NOT EXISTS privacy_table_policies (
            table_name TEXT PRIMARY KEY,
            retention_days INTEGER,
            timestamp_column TEXT,
            automatic_cleanup INTEGER NOT NULL DEFAULT 0,
            deletion_strategy TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS privacy_cleanup_runs (
            run_key TEXT PRIMARY KEY,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            deleted_accounts INTEGER DEFAULT 0,
            pruned_rows INTEGER DEFAULT 0
        );
        """
    )
    table_rows = conn.execute(
        """SELECT name FROM sqlite_master
           WHERE type='table' AND name NOT LIKE 'sqlite_%'
           ORDER BY name"""
    ).fetchall()
    profile_scope = set(PROFILE_PURGE_COLUMNS)
    user_scope = set(USER_PURGE_COLUMNS)
    for (table_name,) in table_rows:
        policy = _policy_for(table_name)
        conn.execute(
            """INSERT INTO privacy_table_policies
               (table_name, retention_days, timestamp_column, automatic_cleanup,
                deletion_strategy, updated_at)
               VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(table_name) DO UPDATE SET
                 retention_days=excluded.retention_days,
                 timestamp_column=excluded.timestamp_column,
                 automatic_cleanup=excluded.automatic_cleanup,
                 deletion_strategy=excluded.deletion_strategy,
                 updated_at=CURRENT_TIMESTAMP""",
            (
                table_name,
                policy.retention_days,
                policy.timestamp_column,
                int(policy.automatic_cleanup),
                policy.deletion_strategy,
            ),
        )
        columns = conn.execute(
            "PRAGMA table_info(\"" + table_name.replace('"', '""') + "\")"
        ).fetchall()
        for column in columns:
            column_name = column[1]
            classification = _field_classification(table_name, column_name)
            subject_scope = "profile" if (table_name, column_name) in profile_scope else "user" if (table_name, column_name) in user_scope else "none"
            conn.execute(
                """INSERT INTO privacy_field_tags
                   (table_name, column_name, classification, is_pii,
                    retention_strategy, subject_scope, notes)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(table_name, column_name) DO UPDATE SET
                     classification=excluded.classification,
                     is_pii=excluded.is_pii,
                     retention_strategy=excluded.retention_strategy,
                     subject_scope=excluded.subject_scope,
                     notes=excluded.notes""",
                (
                    table_name,
                    column_name,
                    classification,
                    int(classification != "not_pii"),
                    policy.deletion_strategy,
                    subject_scope,
                    "Account-linked data" if subject_scope != "none" else None,
                ),
            )


def get_privacy_field_tags() -> list[dict]:
    from app.database import get_db

    rows = get_db().execute(
        "SELECT * FROM privacy_field_tags ORDER BY table_name, column_name"
    ).fetchall()
    return [dict(row) for row in rows]


def get_privacy_retention_policies() -> list[dict]:
    from app.database import get_db

    rows = get_db().execute(
        "SELECT * FROM privacy_table_policies ORDER BY table_name"
    ).fetchall()
    return [dict(row) for row in rows]


def get_privacy_audit() -> dict:
    """Return coverage metrics without returning any user values."""

    from app.database import get_db

    conn = get_db()
    expected_fields: set[tuple[str, str]] = set()
    for (table_name,) in conn.execute(
        """SELECT name FROM sqlite_master
           WHERE type='table' AND name NOT LIKE 'sqlite_%'"""
    ).fetchall():
        for column in conn.execute(
            "PRAGMA table_info(\"" + table_name.replace('"', '""') + "\")"
        ).fetchall():
            expected_fields.add((table_name, column[1]))
    tags = {
        (row["table_name"], row["column_name"])
        for row in conn.execute(
            "SELECT table_name, column_name FROM privacy_field_tags"
        ).fetchall()
    }
    policy_tables = {
        row[0]
        for row in conn.execute("SELECT table_name FROM privacy_table_policies").fetchall()
    }
    untagged = sorted(expected_fields - tags)
    table_names = {table for table, _ in expected_fields}
    missing_policies = sorted(table_names - policy_tables)
    pii_count = conn.execute(
        "SELECT COUNT(*) FROM privacy_field_tags WHERE is_pii=1"
    ).fetchone()[0]
    return {
        "field_count": len(expected_fields),
        "tagged_field_count": len(tags & expected_fields),
        "pii_field_count": pii_count,
        "table_count": len(table_names),
        "policy_count": len(policy_tables & table_names),
        "untagged_fields": [
            {"table_name": table, "column_name": column}
            for table, column in untagged
        ],
        "missing_table_policies": missing_policies,
        "coverage_complete": not untagged and not missing_policies,
    }


def _quote_identifier(value: str) -> str:
    if not value.replace("_", "").isalnum():
        raise ValueError("Unsafe privacy metadata identifier")
    return '"' + value.replace('"', '""') + '"'


def purge_inactive_accounts(
    *,
    months: int = INACTIVE_ACCOUNT_HARD_DELETE_MONTHS,
    media_deleter: Callable[[str], None] | None = None,
) -> dict:
    """Hard-delete deactivated accounts past the configured inactivity window."""

    from app.database import delete_account, get_inactive_accounts_for_hard_delete, get_profile_media_keys
    from app.object_storage import object_storage

    deleter = media_deleter or object_storage.delete
    accounts = get_inactive_accounts_for_hard_delete(max(1, int(months)))
    deleted = 0
    media_deleted = 0
    media_errors: list[dict] = []
    for account in accounts:
        profile_id = account.get("profile_id") or ""
        media_keys = get_profile_media_keys(profile_id)
        if not delete_account(account["user_id"]):
            continue
        deleted += 1
        for media_key in media_keys:
            try:
                deleter(media_key)
                media_deleted += 1
            except Exception as exc:  # pragma: no cover - backend-specific outage
                log.error("Unable to remove media %s after account purge: %s", media_key, exc)
                media_errors.append({"key": media_key, "error": "media deletion failed"})
    return {
        "deleted_accounts": deleted,
        "media_deleted": media_deleted,
        "media_errors": media_errors,
    }


def prune_retention_rows() -> int:
    """Apply only the explicitly automatic short-lived table policies."""

    from app.database import get_db

    conn = get_db()
    policies = conn.execute(
        """SELECT table_name, retention_days, timestamp_column
           FROM privacy_table_policies
           WHERE automatic_cleanup=1 AND retention_days IS NOT NULL"""
    ).fetchall()
    deleted = 0
    for table_name, retention_days, timestamp_column in policies:
        if not timestamp_column:
            continue
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(\"" + table_name.replace('"', '""') + "\")"
            ).fetchall()
        }
        if timestamp_column not in columns:
            continue
        cursor = conn.execute(
            f"DELETE FROM {_quote_identifier(table_name)} "
            f"WHERE {_quote_identifier(timestamp_column)} < datetime('now', ? || ' days')",
            (f"-{int(retention_days)}",),
        )
        if cursor.rowcount > 0:
            deleted += cursor.rowcount
    conn.commit()
    return deleted


def _claim_cleanup_run(run_key: str) -> bool:
    from app.database import get_db

    conn = get_db()
    cursor = conn.execute(
        "INSERT OR IGNORE INTO privacy_cleanup_runs (run_key) VALUES (?)",
        (run_key,),
    )
    conn.commit()
    return cursor.rowcount == 1


def _finish_cleanup_run(run_key: str, deleted_accounts: int, pruned_rows: int) -> None:
    from app.database import get_db

    conn = get_db()
    conn.execute(
        """UPDATE privacy_cleanup_runs
           SET completed_at=CURRENT_TIMESTAMP, deleted_accounts=?, pruned_rows=?
           WHERE run_key=?""",
        (deleted_accounts, pruned_rows, run_key),
    )
    conn.commit()


def run_scheduled_privacy_cleanup(now: datetime | None = None) -> dict:
    """Run at most once per configured interval across all API workers."""

    from app.database import init_db

    init_db()
    current = now or datetime.now(timezone.utc)
    interval_seconds = max(1, int(PRIVACY_RETENTION_INTERVAL_HOURS)) * 3600
    bucket = int(current.timestamp()) // interval_seconds
    run_key = f"utc-bucket-{bucket}"
    if not _claim_cleanup_run(run_key):
        return {"claimed": False, "run_key": run_key}
    result = purge_inactive_accounts()
    pruned_rows = prune_retention_rows()
    _finish_cleanup_run(run_key, result["deleted_accounts"], pruned_rows)
    return {"claimed": True, "run_key": run_key, **result, "pruned_rows": pruned_rows}


_scheduler_thread: threading.Thread | None = None
_scheduler_stop = threading.Event()


def _privacy_scheduler_loop() -> None:
    while not _scheduler_stop.wait(60):
        try:
            run_scheduled_privacy_cleanup()
        except Exception:
            log.exception("Scheduled privacy cleanup failed")


def start_privacy_scheduler() -> None:
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _scheduler_stop.clear()
    _scheduler_thread = threading.Thread(
        target=_privacy_scheduler_loop,
        name="kindred-privacy-retention",
        daemon=True,
    )
    _scheduler_thread.start()


def stop_privacy_scheduler() -> None:
    _scheduler_stop.set()
