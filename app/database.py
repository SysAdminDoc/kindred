"""
Kindred v1.5.0 - Database Layer
SQLite storage for users, profiles, messages, invites, feedback,
date plans, behavioral events, safety reports,
profile pages (blog, comments, friends), notifications,
likes, status updates, activity feed, groups, events,
blocks, password resets, notification preferences,
message reactions, daily suggestions, TOTP 2FA, push subscriptions,
group messages, content filtering, premium subscriptions, analytics.
"""

import json
import sqlite3
import threading
import uuid
from pathlib import Path

from app.config import DB_PATH, UPLOAD_DIR, SCHEMA_VERSION

# Thread-local connection pool
_local = threading.local()


def get_db() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        _local.conn = conn
    return conn


def init_db():
    """Create all tables if they don't exist."""
    UPLOAD_DIR.mkdir(exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            seeking TEXT,
            big_five TEXT,
            attachment TEXT,
            values_data TEXT,
            tradeoffs TEXT,
            self_disclosure TEXT,
            love_language TEXT,
            dealbreakers TEXT,
            open_ended TEXT,
            scenario_answers TEXT,
            behavioral_answers TEXT,
            embedding BLOB,
            photo TEXT,
            weight_prefs TEXT,
            privacy TEXT,
            invite_code TEXT,
            communication_style TEXT,
            financial_values TEXT,
            dating_energy TEXT,
            dating_pace TEXT,
            relationship_intent TEXT,
            verified INTEGER DEFAULT 0,
            trust_score REAL DEFAULT 1.0,
            last_active TEXT DEFAULT (datetime('now')),
            daily_views INTEGER DEFAULT 0,
            daily_view_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            from_id TEXT NOT NULL,
            to_id TEXT NOT NULL,
            content TEXT NOT NULL,
            read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (to_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_messages_conv
            ON messages(from_id, to_id, created_at);

        CREATE TABLE IF NOT EXISTS invites (
            code TEXT PRIMARY KEY,
            created_by TEXT,
            used_by TEXT,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES profiles(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY,
            profile_a TEXT NOT NULL,
            profile_b TEXT NOT NULL,
            went_on_date INTEGER DEFAULT 0,
            rating INTEGER,
            safety_rating INTEGER,
            would_meet_again INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_a) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_b) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS date_plans (
            id TEXT PRIMARY KEY,
            profile_a TEXT NOT NULL,
            profile_b TEXT NOT NULL,
            proposed_by TEXT NOT NULL,
            suggestion TEXT,
            proposed_time TEXT,
            status TEXT DEFAULT 'proposed',
            location_shared INTEGER DEFAULT 0,
            safety_contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_a) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_b) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS behavioral_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            target_id TEXT,
            duration_ms INTEGER,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_behavioral_profile
            ON behavioral_events(profile_id, event_type);

        CREATE TABLE IF NOT EXISTS safety_reports (
            id TEXT PRIMARY KEY,
            reporter_id TEXT NOT NULL,
            reported_id TEXT NOT NULL,
            report_type TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reporter_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (reported_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS profile_blog_posts (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_blog_profile
            ON profile_blog_posts(profile_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS profile_comments (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            from_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (from_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_comments_profile
            ON profile_comments(profile_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            profile_id TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            link TEXT,
            read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_notifications_user
            ON notifications(user_id, read, created_at DESC);

        CREATE TABLE IF NOT EXISTS photos (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            caption TEXT,
            is_primary INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_photos_profile
            ON photos(profile_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS likes (
            id TEXT PRIMARY KEY,
            from_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            reaction TEXT DEFAULT 'like',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(from_id, target_type, target_id)
        );
        CREATE INDEX IF NOT EXISTS idx_likes_target
            ON likes(target_type, target_id);

        CREATE TABLE IF NOT EXISTS status_updates (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            content TEXT NOT NULL,
            mood TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_status_profile
            ON status_updates(profile_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS profile_friends (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            friend_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (friend_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(profile_id, friend_id)
        );

        CREATE TABLE IF NOT EXISTS activity_feed (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id TEXT,
            detail TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_activity_profile
            ON activity_feed(profile_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS groups (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            photo TEXT,
            creator_id TEXT NOT NULL,
            privacy TEXT DEFAULT 'public',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (creator_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS group_members (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            role TEXT DEFAULT 'member',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(group_id, profile_id)
        );

        CREATE TABLE IF NOT EXISTS group_posts (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            location TEXT,
            event_date TEXT,
            event_time TEXT,
            creator_id TEXT NOT NULL,
            group_id TEXT,
            max_attendees INTEGER DEFAULT 0,
            photo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (creator_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS event_rsvps (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            status TEXT DEFAULT 'going',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(event_id, profile_id)
        );

        CREATE TABLE IF NOT EXISTS compat_games (
            id TEXT PRIMARY KEY,
            profile_a TEXT NOT NULL,
            profile_b TEXT NOT NULL,
            question TEXT NOT NULL,
            answer_a TEXT,
            answer_b TEXT,
            matched INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_a) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_b) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS video_intros (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            duration INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS music_preferences (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            song_title TEXT NOT NULL,
            artist TEXT NOT NULL,
            genre TEXT,
            spotify_url TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_music_profile ON music_preferences(profile_id);

        CREATE TABLE IF NOT EXISTS selfie_verifications (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL UNIQUE,
            selfie_photo TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            reviewed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS blocks (
            id TEXT PRIMARY KEY,
            blocker_id TEXT NOT NULL,
            blocked_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (blocker_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (blocked_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(blocker_id, blocked_id)
        );
        CREATE INDEX IF NOT EXISTS idx_blocks_blocker ON blocks(blocker_id);
        CREATE INDEX IF NOT EXISTS idx_blocks_blocked ON blocks(blocked_id);

        CREATE TABLE IF NOT EXISTS password_resets (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            used INTEGER DEFAULT 0,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS notification_preferences (
            user_id TEXT PRIMARY KEY,
            messages INTEGER DEFAULT 1,
            friend_requests INTEGER DEFAULT 1,
            likes INTEGER DEFAULT 1,
            comments INTEGER DEFAULT 1,
            group_posts INTEGER DEFAULT 1,
            events INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS schema_versions (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS email_verifications (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            verified INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS photo_moderation (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            photo_filename TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            reviewed_by TEXT,
            reviewed_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS questionnaire_progress (
            user_id TEXT PRIMARY KEY,
            progress_data TEXT NOT NULL,
            current_index INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS message_reactions (
            id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            reaction TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(message_id, profile_id, reaction),
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS daily_suggestions (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            suggested_id TEXT NOT NULL,
            score REAL NOT NULL,
            date TEXT NOT NULL,
            seen INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (suggested_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_daily_suggestions_date ON daily_suggestions(profile_id, date);

        CREATE TABLE IF NOT EXISTS totp_secrets (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            secret TEXT NOT NULL,
            verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS group_messages (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL,
            from_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            FOREIGN KEY (from_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_group_messages ON group_messages(group_id, created_at);

        CREATE TABLE IF NOT EXISTS content_filter_log (
            id TEXT PRIMARY KEY,
            content_type TEXT NOT NULL,
            content_id TEXT,
            profile_id TEXT,
            flagged_text TEXT,
            reason TEXT,
            filter_type TEXT,
            action TEXT DEFAULT 'censored',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS premium_subscriptions (
            user_id TEXT PRIMARY KEY,
            tier TEXT NOT NULL DEFAULT 'free',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS analytics_events (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            profile_id TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_analytics_events ON analytics_events(event_type, created_at);
    """)

    # Migration: add columns that may not exist in older databases
    _migrate(conn)

    # Track schema version
    current = conn.execute("SELECT MAX(version) FROM schema_versions").fetchone()[0] or 0
    if current < SCHEMA_VERSION:
        conn.execute("INSERT OR IGNORE INTO schema_versions (version) VALUES (?)", (SCHEMA_VERSION,))

    conn.commit()


def _migrate(conn):
    """Add new columns to existing databases. Silently ignores if already present."""
    migrations = [
        "ALTER TABLE profiles ADD COLUMN communication_style TEXT",
        "ALTER TABLE profiles ADD COLUMN financial_values TEXT",
        "ALTER TABLE profiles ADD COLUMN dating_energy TEXT",
        "ALTER TABLE profiles ADD COLUMN dating_pace TEXT",
        "ALTER TABLE profiles ADD COLUMN relationship_intent TEXT",
        "ALTER TABLE profiles ADD COLUMN verified INTEGER DEFAULT 0",
        "ALTER TABLE profiles ADD COLUMN trust_score REAL DEFAULT 1.0",
        "ALTER TABLE profiles ADD COLUMN last_active TEXT",
        "ALTER TABLE profiles ADD COLUMN daily_views INTEGER DEFAULT 0",
        "ALTER TABLE profiles ADD COLUMN daily_view_date TEXT",
        "ALTER TABLE feedback ADD COLUMN safety_rating INTEGER",
        "ALTER TABLE feedback ADD COLUMN would_meet_again INTEGER",
        # Profile page fields
        "ALTER TABLE profiles ADD COLUMN location TEXT",
        "ALTER TABLE profiles ADD COLUMN headline TEXT",
        "ALTER TABLE profiles ADD COLUMN about_me TEXT",
        "ALTER TABLE profiles ADD COLUMN who_id_like_to_meet TEXT",
        "ALTER TABLE profiles ADD COLUMN interests TEXT",
        "ALTER TABLE profiles ADD COLUMN heroes TEXT",
        "ALTER TABLE profiles ADD COLUMN mood TEXT",
        "ALTER TABLE profiles ADD COLUMN music_embeds TEXT",
        "ALTER TABLE profiles ADD COLUMN video_embeds TEXT",
        "ALTER TABLE profiles ADD COLUMN profile_song TEXT",
        "ALTER TABLE profiles ADD COLUMN profile_views INTEGER DEFAULT 0",
        "ALTER TABLE profiles ADD COLUMN profile_theme TEXT",
        "ALTER TABLE messages ADD COLUMN photo TEXT",
        # v1.3.0
        "ALTER TABLE profiles ADD COLUMN deactivated INTEGER DEFAULT 0",
        "ALTER TABLE messages ADD COLUMN read_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN deactivated INTEGER DEFAULT 0",
        "ALTER TABLE groups ADD COLUMN moderators TEXT DEFAULT '[]'",
        # v1.4.0
        "ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0",
        # v1.5.0
        "ALTER TABLE users ADD COLUMN subscription_tier TEXT DEFAULT 'free'",
        "ALTER TABLE users ADD COLUMN onboarding_completed INTEGER DEFAULT 0",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # Column already exists


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

def save_profile(data: dict) -> str:
    conn = get_db()
    profile_id = data.get("id") or str(uuid.uuid4())[:8]
    conn.execute("""
        INSERT OR REPLACE INTO profiles
        (id, name, age, gender, seeking, big_five, attachment, values_data,
         tradeoffs, self_disclosure, love_language, dealbreakers, open_ended,
         scenario_answers, behavioral_answers, embedding, photo,
         weight_prefs, privacy, invite_code,
         communication_style, financial_values, dating_energy, dating_pace,
         relationship_intent)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        profile_id,
        data.get("name", "Anonymous"),
        data.get("age"),
        data.get("gender"),
        data.get("seeking"),
        json.dumps(data.get("big_five", {})),
        json.dumps(data.get("attachment", {})),
        json.dumps(data.get("values", {})),
        json.dumps(data.get("tradeoffs", {})),
        json.dumps(data.get("self_disclosure", {})),
        data.get("love_language"),
        json.dumps(data.get("dealbreakers", [])),
        json.dumps(data.get("open_ended", {})),
        json.dumps(data.get("scenario_answers", {})),
        json.dumps(data.get("behavioral_answers", {})),
        data.get("embedding"),
        data.get("photo"),
        json.dumps(data.get("weight_prefs", {})),
        json.dumps(data.get("privacy", {})),
        data.get("invite_code"),
        json.dumps(data.get("communication_style", {})),
        json.dumps(data.get("financial_values", {})),
        data.get("dating_energy"),
        data.get("dating_pace"),
        data.get("relationship_intent"),
    ))
    conn.commit()
    conn.close()
    return profile_id


def update_profile_field(profile_id: str, field: str, value) -> bool:
    allowed = {"photo", "weight_prefs", "privacy", "name", "age",
               "dating_energy", "verified", "last_active", "daily_views", "daily_view_date",
               "location", "headline", "about_me", "who_id_like_to_meet", "interests",
               "heroes", "mood", "music_embeds", "video_embeds", "profile_song", "profile_views"}
    if field not in allowed:
        return False
    conn = get_db()
    if field in ("weight_prefs", "privacy"):
        value = json.dumps(value)
    conn.execute(f"UPDATE profiles SET {field} = ? WHERE id = ?", (value, profile_id))
    conn.commit()
    conn.close()
    return True


def get_profile(profile_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_dict(row)


def get_all_profiles() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM profiles ORDER BY created_at DESC").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def delete_profile(profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def _row_to_dict(row: sqlite3.Row) -> dict:
    def _json(val, default):
        try:
            return json.loads(val) if val else default
        except (json.JSONDecodeError, TypeError):
            return default

    def _col(name, default=None):
        try:
            return row[name]
        except (IndexError, KeyError):
            return default

    return {
        "id": row["id"],
        "name": row["name"],
        "age": row["age"],
        "gender": row["gender"],
        "seeking": row["seeking"],
        "big_five": _json(row["big_five"], {}),
        "attachment": _json(row["attachment"], {}),
        "values": _json(row["values_data"], {}),
        "tradeoffs": _json(row["tradeoffs"], {}),
        "self_disclosure": _json(row["self_disclosure"], {}),
        "love_language": row["love_language"],
        "dealbreakers": _json(row["dealbreakers"], []),
        "open_ended": _json(row["open_ended"], {}),
        "scenario_answers": _json(row["scenario_answers"], {}),
        "behavioral_answers": _json(row["behavioral_answers"], {}),
        "embedding": row["embedding"],
        "photo": row["photo"],
        "weight_prefs": _json(row["weight_prefs"], {}),
        "privacy": _json(row["privacy"], {}),
        "invite_code": row["invite_code"],
        "communication_style": _json(_col("communication_style"), {}),
        "financial_values": _json(_col("financial_values"), {}),
        "dating_energy": _col("dating_energy"),
        "dating_pace": _col("dating_pace"),
        "relationship_intent": _col("relationship_intent"),
        "verified": _col("verified", 0),
        "trust_score": _col("trust_score", 1.0),
        "last_active": _col("last_active"),
        "location": _col("location"),
        "headline": _col("headline"),
        "about_me": _col("about_me"),
        "who_id_like_to_meet": _col("who_id_like_to_meet"),
        "interests": _col("interests"),
        "heroes": _col("heroes"),
        "mood": _col("mood"),
        "music_embeds": _json(_col("music_embeds"), []),
        "video_embeds": _json(_col("video_embeds"), []),
        "profile_song": _col("profile_song"),
        "profile_views": _col("profile_views", 0),
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def send_message(from_id: str, to_id: str, content: str, photo: str = "") -> str:
    conn = get_db()
    msg_id = str(uuid.uuid4())[:12]
    conn.execute(
        "INSERT INTO messages (id, from_id, to_id, content, photo) VALUES (?,?,?,?,?)",
        (msg_id, from_id, to_id, content, photo or None)
    )
    conn.commit()
    conn.close()
    return msg_id


def get_conversation(id_a: str, id_b: str, limit: int = 100) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM messages
        WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)
        ORDER BY created_at ASC
        LIMIT ?
    """, (id_a, id_b, id_b, id_a, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_conversation_count(id_a: str, id_b: str) -> int:
    conn = get_db()
    row = conn.execute("""
        SELECT COUNT(*) as c FROM messages
        WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)
    """, (id_a, id_b, id_b, id_a)).fetchone()
    conn.close()
    return row["c"]


def get_last_message_sender(id_a: str, id_b: str) -> str | None:
    conn = get_db()
    row = conn.execute("""
        SELECT from_id FROM messages
        WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)
        ORDER BY created_at DESC LIMIT 1
    """, (id_a, id_b, id_b, id_a)).fetchone()
    conn.close()
    return row["from_id"] if row else None


def get_conversations_for(profile_id: str) -> list[dict]:
    """Get list of unique conversation partners with last message."""
    conn = get_db()
    rows = conn.execute("""
        SELECT
            CASE WHEN from_id=? THEN to_id ELSE from_id END as partner_id,
            content as last_message,
            created_at as last_time,
            from_id as last_sender,
            SUM(CASE WHEN to_id=? AND read=0 THEN 1 ELSE 0 END) as unread
        FROM messages
        WHERE from_id=? OR to_id=?
        GROUP BY partner_id
        ORDER BY last_time DESC
    """, (profile_id, profile_id, profile_id, profile_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_messages_read(from_id: str, to_id: str):
    conn = get_db()
    conn.execute(
        "UPDATE messages SET read=1 WHERE from_id=? AND to_id=? AND read=0",
        (from_id, to_id)
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Invites
# ---------------------------------------------------------------------------

def create_invite(created_by: str | None = None) -> str:
    conn = get_db()
    code = str(uuid.uuid4())[:8].upper()
    conn.execute(
        "INSERT INTO invites (code, created_by) VALUES (?,?)",
        (code, created_by)
    )
    conn.commit()
    conn.close()
    return code


def use_invite(code: str, used_by: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM invites WHERE code=? AND used_by IS NULL", (code,)
    ).fetchone()
    if row is None:
        conn.close()
        return False
    conn.execute(
        "UPDATE invites SET used_by=?, used_at=CURRENT_TIMESTAMP WHERE code=?",
        (used_by, code)
    )
    conn.commit()
    conn.close()
    return True


def get_all_invites() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM invites ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

def save_feedback(profile_a: str, profile_b: str, went_on_date: bool,
                  rating: int | None, notes: str | None,
                  safety_rating: int | None = None,
                  would_meet_again: bool | None = None) -> str:
    conn = get_db()
    fb_id = str(uuid.uuid4())[:8]
    conn.execute(
        """INSERT INTO feedback
        (id, profile_a, profile_b, went_on_date, rating, notes, safety_rating, would_meet_again)
        VALUES (?,?,?,?,?,?,?,?)""",
        (fb_id, profile_a, profile_b, int(went_on_date), rating, notes,
         safety_rating, int(would_meet_again) if would_meet_again is not None else None)
    )
    conn.commit()
    conn.close()
    return fb_id


def get_feedback_for(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM feedback WHERE profile_a=? OR profile_b=? ORDER BY created_at DESC",
        (profile_id, profile_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Date Plans
# ---------------------------------------------------------------------------

def create_date_plan(profile_a: str, profile_b: str, proposed_by: str,
                     suggestion: str, proposed_time: str | None = None) -> str:
    conn = get_db()
    plan_id = str(uuid.uuid4())[:8]
    conn.execute(
        """INSERT INTO date_plans
        (id, profile_a, profile_b, proposed_by, suggestion, proposed_time)
        VALUES (?,?,?,?,?,?)""",
        (plan_id, profile_a, profile_b, proposed_by, suggestion, proposed_time)
    )
    conn.commit()
    conn.close()
    return plan_id


def update_date_plan(plan_id: str, status: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "UPDATE date_plans SET status=?, updated_at=datetime('now') WHERE id=?",
        (status, plan_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def get_date_plans(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM date_plans
        WHERE profile_a=? OR profile_b=?
        ORDER BY created_at DESC""",
        (profile_id, profile_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_date_plans_between(id_a: str, id_b: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM date_plans
        WHERE (profile_a=? AND profile_b=?) OR (profile_a=? AND profile_b=?)
        ORDER BY created_at DESC""",
        (id_a, id_b, id_b, id_a)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Behavioral Events
# ---------------------------------------------------------------------------

def log_behavioral_event(profile_id: str, event_type: str,
                         target_id: str | None = None,
                         duration_ms: int | None = None,
                         metadata: dict | None = None):
    conn = get_db()
    conn.execute(
        """INSERT INTO behavioral_events
        (profile_id, event_type, target_id, duration_ms, metadata)
        VALUES (?,?,?,?,?)""",
        (profile_id, event_type, target_id, duration_ms,
         json.dumps(metadata) if metadata else None)
    )
    conn.commit()
    conn.close()


def get_behavioral_profile(profile_id: str) -> dict:
    """Get revealed preference signals for a user."""
    conn = get_db()
    views = conn.execute(
        "SELECT target_id, COUNT(*) as c FROM behavioral_events WHERE profile_id=? AND event_type='profile_view' GROUP BY target_id ORDER BY c DESC LIMIT 20",
        (profile_id,)
    ).fetchall()
    msg_first = conn.execute(
        "SELECT target_id, COUNT(*) as c FROM behavioral_events WHERE profile_id=? AND event_type='message_first' GROUP BY target_id",
        (profile_id,)
    ).fetchall()
    revisits = conn.execute(
        "SELECT target_id, COUNT(*) as c FROM behavioral_events WHERE profile_id=? AND event_type='profile_revisit' GROUP BY target_id ORDER BY c DESC LIMIT 20",
        (profile_id,)
    ).fetchall()
    conn.close()
    return {
        "frequent_views": {r["target_id"]: r["c"] for r in views},
        "messaged_first": {r["target_id"]: r["c"] for r in msg_first},
        "revisits": {r["target_id"]: r["c"] for r in revisits},
    }


# ---------------------------------------------------------------------------
# Safety Reports
# ---------------------------------------------------------------------------

def create_safety_report(reporter_id: str, reported_id: str,
                         report_type: str, notes: str | None = None) -> str:
    conn = get_db()
    report_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO safety_reports (id, reporter_id, reported_id, report_type, notes) VALUES (?,?,?,?,?)",
        (report_id, reporter_id, reported_id, report_type, notes)
    )
    conn.commit()
    conn.close()
    return report_id


def get_safety_reports_for(profile_id: str) -> int:
    """Count safety reports against a user."""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM safety_reports WHERE reported_id=?",
        (profile_id,)
    ).fetchone()
    conn.close()
    return row["c"]


def get_all_safety_reports() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM safety_reports ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Profile Page - Blog Posts
# ---------------------------------------------------------------------------

def create_blog_post(profile_id: str, title: str, content: str) -> str:
    conn = get_db()
    post_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO profile_blog_posts (id, profile_id, title, content) VALUES (?,?,?,?)",
        (post_id, profile_id, title, content)
    )
    conn.commit()
    conn.close()
    return post_id


def get_blog_posts(profile_id: str, limit: int = 20) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM profile_blog_posts WHERE profile_id=? ORDER BY created_at DESC LIMIT ?",
        (profile_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_blog_post(post_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM profile_blog_posts WHERE id=? AND profile_id=?",
        (post_id, profile_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Profile Page - Comments
# ---------------------------------------------------------------------------

def create_profile_comment(profile_id: str, from_id: str, content: str) -> str:
    conn = get_db()
    comment_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO profile_comments (id, profile_id, from_id, content) VALUES (?,?,?,?)",
        (comment_id, profile_id, from_id, content)
    )
    conn.commit()
    conn.close()
    return comment_id


def get_profile_comments(profile_id: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM profile_comments WHERE profile_id=? ORDER BY created_at DESC LIMIT ?",
        (profile_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_profile_comment(comment_id: str, profile_id: str) -> bool:
    """Profile owner can delete comments on their page."""
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM profile_comments WHERE id=? AND profile_id=?",
        (comment_id, profile_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Profile Page - Friends
# ---------------------------------------------------------------------------

def send_friend_request(profile_id: str, friend_id: str) -> str:
    conn = get_db()
    req_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT OR IGNORE INTO profile_friends (id, profile_id, friend_id, status) VALUES (?,?,?,?)",
        (req_id, profile_id, friend_id, "pending")
    )
    conn.commit()
    conn.close()
    return req_id


def respond_friend_request(profile_id: str, friend_id: str, accept: bool) -> bool:
    """Accept or decline a pending friend request FROM friend_id TO profile_id."""
    conn = get_db()
    if accept:
        conn.execute(
            "UPDATE profile_friends SET status='accepted' WHERE profile_id=? AND friend_id=? AND status='pending'",
            (friend_id, profile_id)
        )
        # Create the reciprocal record
        rec_id = str(uuid.uuid4())[:8]
        conn.execute(
            "INSERT OR IGNORE INTO profile_friends (id, profile_id, friend_id, status) VALUES (?,?,?,?)",
            (rec_id, profile_id, friend_id, "accepted")
        )
    else:
        conn.execute(
            "DELETE FROM profile_friends WHERE profile_id=? AND friend_id=? AND status='pending'",
            (friend_id, profile_id)
        )
    conn.commit()
    conn.close()
    return True


def get_friends(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT pf.friend_id, pf.status, pf.created_at,
                  p.name, p.photo, p.age
           FROM profile_friends pf
           JOIN profiles p ON p.id = pf.friend_id
           WHERE pf.profile_id=? AND pf.status='accepted'
           ORDER BY pf.created_at DESC""",
        (profile_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_friend_requests(profile_id: str) -> list[dict]:
    """Get pending requests where someone wants to be friends WITH profile_id."""
    conn = get_db()
    rows = conn.execute(
        """SELECT pf.profile_id as from_id, pf.created_at,
                  p.name, p.photo, p.age
           FROM profile_friends pf
           JOIN profiles p ON p.id = pf.profile_id
           WHERE pf.friend_id=? AND pf.status='pending'
           ORDER BY pf.created_at DESC""",
        (profile_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def remove_friend(profile_id: str, friend_id: str) -> bool:
    conn = get_db()
    conn.execute(
        "DELETE FROM profile_friends WHERE profile_id=? AND friend_id=?",
        (profile_id, friend_id)
    )
    conn.execute(
        "DELETE FROM profile_friends WHERE profile_id=? AND friend_id=?",
        (friend_id, profile_id)
    )
    conn.commit()
    conn.close()
    return True


def are_friends(id_a: str, id_b: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM profile_friends WHERE profile_id=? AND friend_id=? AND status='accepted'",
        (id_a, id_b)
    ).fetchone()
    conn.close()
    return row is not None


def increment_profile_views(profile_id: str):
    conn = get_db()
    conn.execute("UPDATE profiles SET profile_views = COALESCE(profile_views, 0) + 1 WHERE id=?", (profile_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Admin Stats
# ---------------------------------------------------------------------------

def get_stats() -> dict:
    conn = get_db()
    profiles = conn.execute("SELECT COUNT(*) as c FROM profiles").fetchone()["c"]
    messages = conn.execute("SELECT COUNT(*) as c FROM messages").fetchone()["c"]
    invites_total = conn.execute("SELECT COUNT(*) as c FROM invites").fetchone()["c"]
    invites_used = conn.execute("SELECT COUNT(*) as c FROM invites WHERE used_by IS NOT NULL").fetchone()["c"]
    feedback_count = conn.execute("SELECT COUNT(*) as c FROM feedback").fetchone()["c"]
    dates = conn.execute("SELECT COUNT(*) as c FROM feedback WHERE went_on_date=1").fetchone()["c"]
    avg_rating = conn.execute("SELECT AVG(rating) as a FROM feedback WHERE rating IS NOT NULL").fetchone()["a"]

    # Date plans
    date_plans_count = conn.execute("SELECT COUNT(*) as c FROM date_plans").fetchone()["c"]
    dates_completed = conn.execute("SELECT COUNT(*) as c FROM date_plans WHERE status='completed'").fetchone()["c"]

    # Safety
    safety_count = conn.execute("SELECT COUNT(*) as c FROM safety_reports").fetchone()["c"]

    # Groups + Events
    groups_count = conn.execute("SELECT COUNT(*) as c FROM groups").fetchone()["c"]
    events_count = conn.execute("SELECT COUNT(*) as c FROM events").fetchone()["c"]

    gender_dist = {}
    for row in conn.execute("SELECT gender, COUNT(*) as c FROM profiles GROUP BY gender").fetchall():
        gender_dist[row["gender"] or "unset"] = row["c"]

    age_dist = {}
    for row in conn.execute("""
        SELECT
            CASE
                WHEN age < 25 THEN '18-24'
                WHEN age < 30 THEN '25-29'
                WHEN age < 35 THEN '30-34'
                WHEN age < 40 THEN '35-39'
                WHEN age < 50 THEN '40-49'
                ELSE '50+'
            END as bracket,
            COUNT(*) as c
        FROM profiles WHERE age IS NOT NULL GROUP BY bracket
    """).fetchall():
        age_dist[row["bracket"]] = row["c"]

    conn.close()
    return {
        "profiles": profiles,
        "messages": messages,
        "invites_total": invites_total,
        "invites_used": invites_used,
        "feedback": feedback_count,
        "dates_reported": dates,
        "avg_rating": round(avg_rating, 1) if avg_rating else None,
        "date_plans": date_plans_count,
        "dates_completed": dates_completed,
        "safety_reports": safety_count,
        "groups": groups_count,
        "events": events_count,
        "gender_distribution": gender_dist,
        "age_distribution": age_dist,
    }


# ---------------------------------------------------------------------------
# Users (Auth)
# ---------------------------------------------------------------------------

def create_user(email: str, password_hash: str, display_name: str = "",
                is_admin: bool = False) -> str:
    conn = get_db()
    user_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO users (id, email, password_hash, display_name, is_admin) VALUES (?,?,?,?,?)",
        (user_id, email.lower().strip(), password_hash, display_name or email.split("@")[0], int(is_admin))
    )
    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def link_profile_to_user(user_id: str, profile_id: str):
    conn = get_db()
    conn.execute("UPDATE users SET profile_id = ? WHERE id = ?", (profile_id, user_id))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def create_notification(user_id: str, ntype: str, title: str,
                        body: str = "", link: str = "") -> str:
    conn = get_db()
    nid = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO notifications (id, user_id, type, title, body, link) VALUES (?,?,?,?,?,?)",
        (nid, user_id, ntype, title, body, link)
    )
    conn.commit()
    conn.close()
    return nid


def get_notifications(user_id: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unread_notification_count(user_id: str) -> int:
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM notifications WHERE user_id=? AND read=0",
        (user_id,)
    ).fetchone()
    conn.close()
    return row["c"]


def mark_notifications_read(user_id: str):
    conn = get_db()
    conn.execute("UPDATE notifications SET read=1 WHERE user_id=? AND read=0", (user_id,))
    conn.commit()
    conn.close()


def mark_notification_read(notification_id: str):
    conn = get_db()
    conn.execute("UPDATE notifications SET read=1 WHERE id=?", (notification_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Likes / Reactions
# ---------------------------------------------------------------------------

def toggle_like(from_id: str, target_type: str, target_id: str,
                reaction: str = "like") -> bool:
    """Toggle a like. Returns True if liked, False if unliked."""
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM likes WHERE from_id=? AND target_type=? AND target_id=?",
        (from_id, target_type, target_id)
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM likes WHERE id=?", (existing["id"],))
        conn.commit()
        conn.close()
        return False
    else:
        like_id = str(uuid.uuid4())[:8]
        conn.execute(
            "INSERT INTO likes (id, from_id, target_type, target_id, reaction) VALUES (?,?,?,?,?)",
            (like_id, from_id, target_type, target_id, reaction)
        )
        conn.commit()
        conn.close()
        return True


def get_likes(target_type: str, target_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT l.*, p.name as from_name FROM likes l JOIN profiles p ON p.id=l.from_id WHERE l.target_type=? AND l.target_id=? ORDER BY l.created_at DESC",
        (target_type, target_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_like_count(target_type: str, target_id: str) -> int:
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM likes WHERE target_type=? AND target_id=?",
        (target_type, target_id)
    ).fetchone()
    conn.close()
    return row["c"]


def has_liked(from_id: str, target_type: str, target_id: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM likes WHERE from_id=? AND target_type=? AND target_id=?",
        (from_id, target_type, target_id)
    ).fetchone()
    conn.close()
    return row is not None


# ---------------------------------------------------------------------------
# Status Updates
# ---------------------------------------------------------------------------

def create_status_update(profile_id: str, content: str, mood: str = "") -> str:
    conn = get_db()
    sid = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO status_updates (id, profile_id, content, mood) VALUES (?,?,?,?)",
        (sid, profile_id, content, mood or None)
    )
    conn.commit()
    conn.close()
    return sid


def get_status_updates(profile_id: str, limit: int = 20) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM status_updates WHERE profile_id=? ORDER BY created_at DESC LIMIT ?",
        (profile_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_friend_status_feed(profile_id: str, limit: int = 50) -> list[dict]:
    """Get status updates from friends."""
    conn = get_db()
    rows = conn.execute(
        """SELECT s.*, p.name, p.photo FROM status_updates s
           JOIN profiles p ON p.id = s.profile_id
           WHERE s.profile_id IN (
               SELECT friend_id FROM profile_friends
               WHERE profile_id=? AND status='accepted'
           ) OR s.profile_id=?
           ORDER BY s.created_at DESC LIMIT ?""",
        (profile_id, profile_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_status_update(status_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM status_updates WHERE id=? AND profile_id=?",
        (status_id, profile_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Online Status
# ---------------------------------------------------------------------------

def update_last_seen(profile_id: str):
    conn = get_db()
    conn.execute(
        "UPDATE profiles SET last_active=datetime('now') WHERE id=?",
        (profile_id,)
    )
    conn.commit()
    conn.close()


def get_online_status(profile_id: str, minutes: int = 5) -> bool:
    """Check if a single profile is online."""
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM profiles WHERE id=? AND last_active > datetime('now', ?)",
        (profile_id, f"-{minutes} minutes")
    ).fetchone()
    conn.close()
    return row is not None


def get_online_friends(profile_id: str, minutes: int = 5) -> list[dict]:
    """Get friends who were active in the last N minutes."""
    conn = get_db()
    rows = conn.execute(
        """SELECT p.id, p.name, p.photo, p.last_active
           FROM profiles p
           JOIN profile_friends pf ON pf.friend_id = p.id
           WHERE pf.profile_id=? AND pf.status='accepted'
             AND p.last_active > datetime('now', ?)
           ORDER BY p.last_active DESC""",
        (profile_id, f"-{minutes} minutes")
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Photo Gallery
# ---------------------------------------------------------------------------

def add_photo(profile_id: str, filename: str, caption: str = "",
              is_primary: bool = False) -> str:
    conn = get_db()
    photo_id = str(uuid.uuid4())[:8]
    if is_primary:
        conn.execute("UPDATE photos SET is_primary=0 WHERE profile_id=?", (profile_id,))
    conn.execute(
        "INSERT INTO photos (id, profile_id, filename, caption, is_primary) VALUES (?,?,?,?,?)",
        (photo_id, profile_id, filename, caption or None, int(is_primary))
    )
    conn.commit()
    conn.close()
    return photo_id


def get_photos(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM photos WHERE profile_id=? ORDER BY is_primary DESC, created_at DESC",
        (profile_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_photo(photo_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM photos WHERE id=? AND profile_id=?",
        (photo_id, profile_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def set_primary_photo(photo_id: str, profile_id: str) -> bool:
    conn = get_db()
    conn.execute("UPDATE photos SET is_primary=0 WHERE profile_id=?", (profile_id,))
    cursor = conn.execute(
        "UPDATE photos SET is_primary=1 WHERE id=? AND profile_id=?",
        (photo_id, profile_id)
    )
    row = conn.execute("SELECT filename FROM photos WHERE id=?", (photo_id,)).fetchone()
    if row:
        conn.execute("UPDATE profiles SET photo=? WHERE id=?", (row["filename"], profile_id))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Search / Discover
# ---------------------------------------------------------------------------

def search_profiles(query: str = "", gender: str = "", seeking: str = "",
                    age_min: int = 0, age_max: int = 999,
                    location: str = "", limit: int = 50) -> list[dict]:
    conn = get_db()
    sql = "SELECT * FROM profiles WHERE 1=1"
    params = []
    if query:
        sql += " AND (name LIKE ? OR about_me LIKE ? OR headline LIKE ? OR interests LIKE ?)"
        q = f"%{query}%"
        params.extend([q, q, q, q])
    if gender:
        sql += " AND gender = ?"
        params.append(gender)
    if seeking:
        sql += " AND seeking = ?"
        params.append(seeking)
    if age_min > 0:
        sql += " AND age >= ?"
        params.append(age_min)
    if age_max < 999:
        sql += " AND age <= ?"
        params.append(age_max)
    if location:
        sql += " AND location LIKE ?"
        params.append(f"%{location}%")
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Activity Feed
# ---------------------------------------------------------------------------

def log_activity(profile_id: str, action: str, target_type: str = "",
                 target_id: str = "", detail: str = "") -> str:
    conn = get_db()
    aid = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO activity_feed (id, profile_id, action, target_type, target_id, detail) VALUES (?,?,?,?,?,?)",
        (aid, profile_id, action, target_type or None, target_id or None, detail or None)
    )
    conn.commit()
    conn.close()
    return aid


def get_activity_feed(profile_id: str, limit: int = 50) -> list[dict]:
    """Get activity from friends and self."""
    conn = get_db()
    rows = conn.execute(
        """SELECT a.*, p.name, p.photo FROM activity_feed a
           JOIN profiles p ON p.id = a.profile_id
           WHERE a.profile_id IN (
               SELECT friend_id FROM profile_friends
               WHERE profile_id=? AND status='accepted'
           ) OR a.profile_id=?
           ORDER BY a.created_at DESC LIMIT ?""",
        (profile_id, profile_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_explore_profiles(limit: int = 20) -> list[dict]:
    """Get profiles for the explore page - most viewed, recently active."""
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM profiles
           ORDER BY profile_views DESC, last_active DESC
           LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_recent_profiles(limit: int = 10) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM profiles ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Groups / Communities
# ---------------------------------------------------------------------------

def create_group(name: str, description: str, creator_id: str,
                 privacy: str = "public") -> str:
    conn = get_db()
    gid = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO groups (id, name, description, creator_id, privacy) VALUES (?,?,?,?,?)",
        (gid, name, description, creator_id, privacy)
    )
    # Creator auto-joins as admin
    mid = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO group_members (id, group_id, profile_id, role) VALUES (?,?,?,?)",
        (mid, gid, creator_id, "admin")
    )
    conn.commit()
    conn.close()
    return gid


def get_group(group_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM groups WHERE id=?", (group_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_groups(limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT g.*, COUNT(gm.id) as member_count
           FROM groups g LEFT JOIN group_members gm ON gm.group_id = g.id
           GROUP BY g.id ORDER BY member_count DESC, g.created_at DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_my_groups(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT g.*, gm.role, COUNT(gm2.id) as member_count
           FROM group_members gm
           JOIN groups g ON g.id = gm.group_id
           LEFT JOIN group_members gm2 ON gm2.group_id = g.id
           WHERE gm.profile_id=?
           GROUP BY g.id ORDER BY g.created_at DESC""",
        (profile_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def join_group(group_id: str, profile_id: str) -> str:
    conn = get_db()
    mid = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT OR IGNORE INTO group_members (id, group_id, profile_id) VALUES (?,?,?)",
        (mid, group_id, profile_id)
    )
    conn.commit()
    conn.close()
    return mid


def leave_group(group_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM group_members WHERE group_id=? AND profile_id=?",
        (group_id, profile_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def is_group_member(group_id: str, profile_id: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM group_members WHERE group_id=? AND profile_id=?",
        (group_id, profile_id)
    ).fetchone()
    conn.close()
    return row is not None


def get_group_members(group_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT gm.*, p.name, p.photo, p.age
           FROM group_members gm JOIN profiles p ON p.id = gm.profile_id
           WHERE gm.group_id=? ORDER BY gm.joined_at""",
        (group_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_group_post(group_id: str, profile_id: str, content: str) -> str:
    conn = get_db()
    pid = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO group_posts (id, group_id, profile_id, content) VALUES (?,?,?,?)",
        (pid, group_id, profile_id, content)
    )
    conn.commit()
    conn.close()
    return pid


def get_group_posts(group_id: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT gp.*, p.name, p.photo FROM group_posts gp
           JOIN profiles p ON p.id = gp.profile_id
           WHERE gp.group_id=? ORDER BY gp.created_at DESC LIMIT ?""",
        (group_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_group_post(post_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM group_posts WHERE id=? AND profile_id=?",
        (post_id, profile_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def delete_group(group_id: str) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM group_posts WHERE group_id=?", (group_id,))
    conn.execute("DELETE FROM group_members WHERE group_id=?", (group_id,))
    cursor = conn.execute("DELETE FROM groups WHERE id=?", (group_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def create_event(title: str, description: str, creator_id: str,
                 location: str = "", event_date: str = "",
                 event_time: str = "", group_id: str = "",
                 max_attendees: int = 0) -> str:
    conn = get_db()
    eid = str(uuid.uuid4())[:8]
    conn.execute(
        """INSERT INTO events (id, title, description, creator_id, location,
           event_date, event_time, group_id, max_attendees) VALUES (?,?,?,?,?,?,?,?,?)""",
        (eid, title, description, creator_id, location or None,
         event_date or None, event_time or None, group_id or None, max_attendees)
    )
    # Creator auto-RSVPs
    rid = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO event_rsvps (id, event_id, profile_id, status) VALUES (?,?,?,?)",
        (rid, eid, creator_id, "going")
    )
    conn.commit()
    conn.close()
    return eid


def get_event(event_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_events(limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT e.*, COUNT(r.id) as attendee_count, p.name as creator_name
           FROM events e
           LEFT JOIN event_rsvps r ON r.event_id = e.id AND r.status='going'
           JOIN profiles p ON p.id = e.creator_id
           GROUP BY e.id
           ORDER BY e.event_date ASC, e.created_at DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def rsvp_event(event_id: str, profile_id: str, status: str = "going") -> str:
    conn = get_db()
    # Upsert
    existing = conn.execute(
        "SELECT id FROM event_rsvps WHERE event_id=? AND profile_id=?",
        (event_id, profile_id)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE event_rsvps SET status=? WHERE id=?",
            (status, existing["id"])
        )
        rid = existing["id"]
    else:
        rid = str(uuid.uuid4())[:8]
        conn.execute(
            "INSERT INTO event_rsvps (id, event_id, profile_id, status) VALUES (?,?,?,?)",
            (rid, event_id, profile_id, status)
        )
    conn.commit()
    conn.close()
    return rid


def get_event_rsvps(event_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT r.*, p.name, p.photo FROM event_rsvps r
           JOIN profiles p ON p.id = r.profile_id
           WHERE r.event_id=? ORDER BY r.created_at""",
        (event_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_my_events(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT e.*, r.status as my_status, COUNT(r2.id) as attendee_count
           FROM event_rsvps r
           JOIN events e ON e.id = r.event_id
           LEFT JOIN event_rsvps r2 ON r2.event_id = e.id AND r2.status='going'
           WHERE r.profile_id=?
           GROUP BY e.id ORDER BY e.event_date ASC""",
        (profile_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_event(event_id: str) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM event_rsvps WHERE event_id=?", (event_id,))
    cursor = conn.execute("DELETE FROM events WHERE id=?", (event_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Compatibility Games
# ---------------------------------------------------------------------------

COMPAT_QUESTIONS = [
    "Beach vacation or Mountain retreat?",
    "Early bird or Night owl?",
    "Cook at home or Eat out?",
    "City living or Country living?",
    "Spontaneous trips or Planned itineraries?",
    "Cats or Dogs?",
    "Movies at home or Cinema?",
    "Books or Podcasts?",
    "Big wedding or Small elopement?",
    "Save money or Enjoy now?",
    "Text all day or Quality calls?",
    "Road trip or Fly there?",
    "Stay in or Go out on weekends?",
    "Sweet or Savory?",
    "Adventure sports or Spa day?",
    "Social butterfly or Homebody?",
    "Clean as you go or Big cleanup?",
    "Morning coffee or Morning tea?",
    "Board games or Video games?",
    "Live music or Quiet dinner?",
]


def get_or_create_game(profile_a: str, profile_b: str) -> dict:
    """Get next unanswered game question for a pair, or create new ones."""
    conn = get_db()
    # Find a question where this user hasn't answered yet
    pending = conn.execute(
        """SELECT * FROM compat_games
           WHERE ((profile_a=? AND profile_b=?) OR (profile_a=? AND profile_b=?))
           AND ((profile_a=? AND answer_a IS NULL) OR (profile_b=? AND answer_b IS NULL))
           ORDER BY created_at LIMIT 1""",
        (profile_a, profile_b, profile_b, profile_a,
         profile_a, profile_a)
    ).fetchone()

    if pending:
        conn.close()
        return dict(pending)

    # Check how many questions already exist for this pair
    existing_qs = conn.execute(
        """SELECT question FROM compat_games
           WHERE (profile_a=? AND profile_b=?) OR (profile_a=? AND profile_b=?)""",
        (profile_a, profile_b, profile_b, profile_a)
    ).fetchall()
    used = {r["question"] for r in existing_qs}
    available = [q for q in COMPAT_QUESTIONS if q not in used]

    if not available:
        conn.close()
        return None  # All questions exhausted

    import random
    question = random.choice(available)
    gid = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO compat_games (id, profile_a, profile_b, question) VALUES (?,?,?,?)",
        (gid, profile_a, profile_b, question)
    )
    conn.commit()
    game = dict(conn.execute("SELECT * FROM compat_games WHERE id=?", (gid,)).fetchone())
    conn.close()
    return game


def answer_game(game_id: str, profile_id: str, answer: str) -> dict:
    conn = get_db()
    game = conn.execute("SELECT * FROM compat_games WHERE id=?", (game_id,)).fetchone()
    if not game:
        conn.close()
        return None
    g = dict(game)
    if profile_id == g["profile_a"]:
        conn.execute("UPDATE compat_games SET answer_a=? WHERE id=?", (answer, game_id))
    elif profile_id == g["profile_b"]:
        conn.execute("UPDATE compat_games SET answer_b=? WHERE id=?", (answer, game_id))
    else:
        conn.close()
        return None

    # Check if both answered, mark match
    updated = dict(conn.execute("SELECT * FROM compat_games WHERE id=?", (game_id,)).fetchone())
    if updated["answer_a"] and updated["answer_b"]:
        matched = 1 if updated["answer_a"] == updated["answer_b"] else 0
        conn.execute("UPDATE compat_games SET matched=? WHERE id=?", (matched, game_id))
        updated["matched"] = matched
    conn.commit()
    conn.close()
    return updated


def get_game_history(profile_a: str, profile_b: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM compat_games
           WHERE ((profile_a=? AND profile_b=?) OR (profile_a=? AND profile_b=?))
           AND answer_a IS NOT NULL AND answer_b IS NOT NULL
           ORDER BY created_at DESC""",
        (profile_a, profile_b, profile_b, profile_a)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_game_score(profile_a: str, profile_b: str) -> dict:
    history = get_game_history(profile_a, profile_b)
    total = len(history)
    matched = sum(1 for g in history if g["matched"])
    return {"total": total, "matched": matched, "pct": round(matched / total * 100) if total else 0}


# ---------------------------------------------------------------------------
# Selfie Verification
# ---------------------------------------------------------------------------

def submit_selfie_verification(profile_id: str, selfie_photo: str) -> str:
    conn = get_db()
    vid = str(uuid.uuid4())[:8]
    # Upsert - replace any existing pending verification
    conn.execute("DELETE FROM selfie_verifications WHERE profile_id=?", (profile_id,))
    conn.execute(
        "INSERT INTO selfie_verifications (id, profile_id, selfie_photo) VALUES (?,?,?)",
        (vid, profile_id, selfie_photo)
    )
    conn.commit()
    conn.close()
    return vid


def get_pending_verifications() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT v.*, p.name, p.photo FROM selfie_verifications v
           JOIN profiles p ON p.id = v.profile_id
           WHERE v.status='pending' ORDER BY v.created_at"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def review_verification(verification_id: str, approved: bool) -> bool:
    conn = get_db()
    v = conn.execute("SELECT * FROM selfie_verifications WHERE id=?", (verification_id,)).fetchone()
    if not v:
        conn.close()
        return False
    status = "approved" if approved else "rejected"
    conn.execute(
        "UPDATE selfie_verifications SET status=?, reviewed_at=datetime('now') WHERE id=?",
        (status, verification_id)
    )
    if approved:
        conn.execute("UPDATE profiles SET verified=1 WHERE id=?", (v["profile_id"],))
    conn.commit()
    conn.close()
    return True


def get_verification_status(profile_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM selfie_verifications WHERE profile_id=? ORDER BY created_at DESC LIMIT 1",
        (profile_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Video Intros
# ---------------------------------------------------------------------------

def save_video_intro(profile_id: str, filename: str, duration: int = 0) -> str:
    conn = get_db()
    vid = str(uuid.uuid4())[:8]
    # Replace existing
    conn.execute("DELETE FROM video_intros WHERE profile_id=?", (profile_id,))
    conn.execute(
        "INSERT INTO video_intros (id, profile_id, filename, duration) VALUES (?,?,?,?)",
        (vid, profile_id, filename, duration)
    )
    conn.commit()
    conn.close()
    return vid


def get_video_intro(profile_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM video_intros WHERE profile_id=? LIMIT 1", (profile_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_video_intro(profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute("DELETE FROM video_intros WHERE profile_id=?", (profile_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Music Preferences
# ---------------------------------------------------------------------------

def add_music_pref(profile_id: str, song_title: str, artist: str,
                   genre: str = "", spotify_url: str = "") -> str:
    conn = get_db()
    mid = str(uuid.uuid4())[:8]
    count = conn.execute(
        "SELECT COUNT(*) as c FROM music_preferences WHERE profile_id=?", (profile_id,)
    ).fetchone()["c"]
    conn.execute(
        """INSERT INTO music_preferences (id, profile_id, song_title, artist, genre, spotify_url, sort_order)
           VALUES (?,?,?,?,?,?,?)""",
        (mid, profile_id, song_title, artist, genre or None, spotify_url or None, count)
    )
    conn.commit()
    conn.close()
    return mid


def get_music_prefs(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM music_preferences WHERE profile_id=? ORDER BY sort_order",
        (profile_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_music_pref(pref_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM music_preferences WHERE id=? AND profile_id=?",
        (pref_id, profile_id)
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def compute_music_compatibility(profile_a: str, profile_b: str) -> dict:
    """Compare music preferences between two profiles."""
    prefs_a = get_music_prefs(profile_a)
    prefs_b = get_music_prefs(profile_b)
    if not prefs_a or not prefs_b:
        return {"score": 0, "shared_artists": [], "shared_genres": []}

    artists_a = {p["artist"].lower() for p in prefs_a}
    artists_b = {p["artist"].lower() for p in prefs_b}
    shared_artists = artists_a & artists_b

    genres_a = {p["genre"].lower() for p in prefs_a if p.get("genre")}
    genres_b = {p["genre"].lower() for p in prefs_b if p.get("genre")}
    shared_genres = genres_a & genres_b

    # Score: artist matches worth more, genre matches supplement
    max_possible = max(len(artists_a), len(artists_b)) or 1
    artist_score = len(shared_artists) / max_possible * 70
    genre_score = (len(shared_genres) / max(len(genres_a | genres_b), 1)) * 30 if genres_a or genres_b else 0
    score = min(round(artist_score + genre_score), 100)

    return {
        "score": score,
        "shared_artists": sorted(shared_artists),
        "shared_genres": sorted(shared_genres),
        "a_count": len(prefs_a),
        "b_count": len(prefs_b),
    }


# ---------------------------------------------------------------------------
# Blocking
# ---------------------------------------------------------------------------

def block_profile(blocker_id: str, blocked_id: str) -> str:
    conn = get_db()
    bid = str(uuid.uuid4())[:8]
    try:
        conn.execute(
            "INSERT INTO blocks (id, blocker_id, blocked_id) VALUES (?,?,?)",
            (bid, blocker_id, blocked_id)
        )
        # Also remove friendship if exists
        conn.execute(
            "DELETE FROM profile_friends WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)",
            (blocker_id, blocked_id, blocked_id, blocker_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Already blocked
    return bid


def unblock_profile(blocker_id: str, blocked_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM blocks WHERE blocker_id=? AND blocked_id=?",
        (blocker_id, blocked_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def is_blocked(blocker_id: str, blocked_id: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM blocks WHERE blocker_id=? AND blocked_id=?",
        (blocker_id, blocked_id)
    ).fetchone()
    return row is not None


def is_blocked_either(profile_a: str, profile_b: str) -> bool:
    conn = get_db()
    row = conn.execute(
        """SELECT 1 FROM blocks
           WHERE (blocker_id=? AND blocked_id=?) OR (blocker_id=? AND blocked_id=?)""",
        (profile_a, profile_b, profile_b, profile_a)
    ).fetchone()
    return row is not None


def get_blocked_profiles(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT b.*, p.name, p.photo FROM blocks b
           JOIN profiles p ON p.id = b.blocked_id
           WHERE b.blocker_id=? ORDER BY b.created_at DESC""",
        (profile_id,)
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------

def create_password_reset(user_id: str) -> str:
    import secrets
    from datetime import datetime, timedelta, timezone
    conn = get_db()
    token = secrets.token_urlsafe(32)
    rid = str(uuid.uuid4())[:8]
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    conn.execute(
        "INSERT INTO password_resets (id, user_id, token, expires_at) VALUES (?,?,?,?)",
        (rid, user_id, token, expires)
    )
    conn.commit()
    return token


def use_password_reset(token: str, new_password_hash: str) -> bool:
    from datetime import datetime, timezone
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM password_resets WHERE token=? AND used=0", (token,)
    ).fetchone()
    if not row:
        return False
    now = datetime.now(timezone.utc).isoformat()
    if now > row["expires_at"]:
        return False
    conn.execute("UPDATE password_resets SET used=1 WHERE id=?", (row["id"],))
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_password_hash, row["user_id"]))
    conn.commit()
    return True


# ---------------------------------------------------------------------------
# Notification Preferences
# ---------------------------------------------------------------------------

def get_notification_prefs(user_id: str) -> dict:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM notification_preferences WHERE user_id=?", (user_id,)
    ).fetchone()
    if not row:
        return {"messages": 1, "friend_requests": 1, "likes": 1,
                "comments": 1, "group_posts": 1, "events": 1}
    return dict(row)


def update_notification_prefs(user_id: str, prefs: dict) -> None:
    conn = get_db()
    conn.execute(
        """INSERT INTO notification_preferences (user_id, messages, friend_requests,
           likes, comments, group_posts, events)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET
           messages=excluded.messages, friend_requests=excluded.friend_requests,
           likes=excluded.likes, comments=excluded.comments,
           group_posts=excluded.group_posts, events=excluded.events""",
        (user_id, prefs.get("messages", 1), prefs.get("friend_requests", 1),
         prefs.get("likes", 1), prefs.get("comments", 1),
         prefs.get("group_posts", 1), prefs.get("events", 1))
    )
    conn.commit()


def should_notify(user_id: str, notif_type: str) -> bool:
    prefs = get_notification_prefs(user_id)
    type_map = {
        "message": "messages", "friend_request": "friend_requests",
        "like": "likes", "comment": "comments",
        "group_post": "group_posts", "event": "events",
    }
    key = type_map.get(notif_type, notif_type)
    return bool(prefs.get(key, 1))


# ---------------------------------------------------------------------------
# Message Pagination & Read Receipts
# ---------------------------------------------------------------------------

def get_conversation_paginated(id_a: str, id_b: str, limit: int = 50,
                                before_id: str = None) -> list[dict]:
    conn = get_db()
    if before_id:
        rows = conn.execute(
            """SELECT * FROM messages
               WHERE ((from_id=? AND to_id=?) OR (from_id=? AND to_id=?))
               AND created_at < (SELECT created_at FROM messages WHERE id=?)
               ORDER BY created_at DESC LIMIT ?""",
            (id_a, id_b, id_b, id_a, before_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM messages
               WHERE ((from_id=? AND to_id=?) OR (from_id=? AND to_id=?))
               ORDER BY created_at DESC LIMIT ?""",
            (id_a, id_b, id_b, id_a, limit)
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def mark_messages_read_with_timestamp(to_id: str, from_id: str) -> int:
    conn = get_db()
    cursor = conn.execute(
        """UPDATE messages SET read=1, read_at=datetime('now')
           WHERE from_id=? AND to_id=? AND read=0""",
        (from_id, to_id)
    )
    conn.commit()
    return cursor.rowcount


# ---------------------------------------------------------------------------
# Profile Deactivation
# ---------------------------------------------------------------------------

def deactivate_profile(profile_id: str) -> bool:
    conn = get_db()
    conn.execute("UPDATE profiles SET deactivated=1 WHERE id=?", (profile_id,))
    conn.commit()
    return True


def reactivate_profile(profile_id: str) -> bool:
    conn = get_db()
    conn.execute("UPDATE profiles SET deactivated=0 WHERE id=?", (profile_id,))
    conn.commit()
    return True


# ---------------------------------------------------------------------------
# Group Moderation
# ---------------------------------------------------------------------------

def add_group_moderator(group_id: str, profile_id: str) -> bool:
    conn = get_db()
    group = conn.execute("SELECT moderators FROM groups WHERE id=?", (group_id,)).fetchone()
    if not group:
        return False
    mods = json.loads(group["moderators"] or "[]")
    if profile_id not in mods:
        mods.append(profile_id)
        conn.execute("UPDATE groups SET moderators=? WHERE id=?", (json.dumps(mods), group_id))
        conn.commit()
    return True


def remove_group_moderator(group_id: str, profile_id: str) -> bool:
    conn = get_db()
    group = conn.execute("SELECT moderators FROM groups WHERE id=?", (group_id,)).fetchone()
    if not group:
        return False
    mods = json.loads(group["moderators"] or "[]")
    if profile_id in mods:
        mods.remove(profile_id)
        conn.execute("UPDATE groups SET moderators=? WHERE id=?", (json.dumps(mods), group_id))
        conn.commit()
    return True


def is_group_moderator(group_id: str, profile_id: str) -> bool:
    conn = get_db()
    group = conn.execute("SELECT moderators, creator_id FROM groups WHERE id=?", (group_id,)).fetchone()
    if not group:
        return False
    if group["creator_id"] == profile_id:
        return True
    mods = json.loads(group["moderators"] or "[]")
    return profile_id in mods


# ---------------------------------------------------------------------------
# Refresh Tokens
# ---------------------------------------------------------------------------

def create_refresh_token(user_id: str, token_hash: str, expires_at: str) -> str:
    token_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)",
        (token_id, user_id, token_hash, expires_at),
    )
    conn.commit()
    return token_id


def get_refresh_token(token_hash: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM refresh_tokens WHERE token_hash = ? AND revoked = 0 AND expires_at > datetime('now')",
        (token_hash,),
    ).fetchone()
    return dict(row) if row else None


def revoke_refresh_token(token_hash: str):
    conn = get_db()
    conn.execute("UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?", (token_hash,))
    conn.commit()


def revoke_all_user_tokens(user_id: str):
    conn = get_db()
    conn.execute("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (user_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

def create_email_verification(user_id: str, token: str, expires_at: str) -> str:
    vid = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO email_verifications (id, user_id, token, expires_at) VALUES (?, ?, ?, ?)",
        (vid, user_id, token, expires_at),
    )
    conn.commit()
    return vid


def verify_email_token(token: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM email_verifications WHERE token = ? AND verified = 0 AND expires_at > datetime('now')",
        (token,),
    ).fetchone()
    if row:
        conn.execute("UPDATE email_verifications SET verified = 1 WHERE id = ?", (row["id"],))
        conn.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (row["user_id"],))
        conn.commit()
        return dict(row)
    return None


# ---------------------------------------------------------------------------
# Photo Moderation
# ---------------------------------------------------------------------------

def submit_photo_for_moderation(profile_id: str, filename: str) -> str:
    mod_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO photo_moderation (id, profile_id, photo_filename) VALUES (?, ?, ?)",
        (mod_id, profile_id, filename),
    )
    conn.commit()
    return mod_id


def get_pending_photo_moderations() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT pm.*, p.name as profile_name FROM photo_moderation pm
           LEFT JOIN profiles p ON pm.profile_id = p.id
           WHERE pm.status = 'pending' ORDER BY pm.created_at ASC"""
    ).fetchall()
    return [dict(r) for r in rows]


def review_photo_moderation(mod_id: str, approved: bool, reviewer_id: str = None) -> bool:
    conn = get_db()
    status = "approved" if approved else "rejected"
    cur = conn.execute(
        "UPDATE photo_moderation SET status = ?, reviewed_by = ?, reviewed_at = datetime('now') WHERE id = ?",
        (status, reviewer_id, mod_id),
    )
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Questionnaire Progress
# ---------------------------------------------------------------------------

def save_questionnaire_progress(user_id: str, progress_data: str, current_index: int):
    conn = get_db()
    conn.execute(
        """INSERT INTO questionnaire_progress (user_id, progress_data, current_index, updated_at)
           VALUES (?, ?, ?, datetime('now'))
           ON CONFLICT(user_id) DO UPDATE SET progress_data=excluded.progress_data,
           current_index=excluded.current_index, updated_at=datetime('now')""",
        (user_id, progress_data, current_index),
    )
    conn.commit()


def get_questionnaire_progress(user_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM questionnaire_progress WHERE user_id = ?", (user_id,)
    ).fetchone()
    return dict(row) if row else None


def delete_questionnaire_progress(user_id: str):
    conn = get_db()
    conn.execute("DELETE FROM questionnaire_progress WHERE user_id = ?", (user_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Message Reactions
# ---------------------------------------------------------------------------

def add_message_reaction(message_id: str, profile_id: str, reaction: str) -> str:
    conn = get_db()
    reaction_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT OR IGNORE INTO message_reactions (id, message_id, profile_id, reaction) VALUES (?, ?, ?, ?)",
        (reaction_id, message_id, profile_id, reaction),
    )
    conn.commit()
    return reaction_id


def remove_message_reaction(message_id: str, profile_id: str, reaction: str) -> bool:
    conn = get_db()
    cur = conn.execute(
        "DELETE FROM message_reactions WHERE message_id = ? AND profile_id = ? AND reaction = ?",
        (message_id, profile_id, reaction),
    )
    conn.commit()
    return cur.rowcount > 0


def get_message_reactions(message_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT mr.*, p.name as profile_name, p.photo as profile_photo
           FROM message_reactions mr
           LEFT JOIN profiles p ON mr.profile_id = p.id
           WHERE mr.message_id = ?
           ORDER BY mr.created_at ASC""",
        (message_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Daily Suggestions
# ---------------------------------------------------------------------------

def save_daily_suggestions(profile_id: str, suggestions: list[dict]):
    from datetime import date
    conn = get_db()
    today = date.today().isoformat()
    conn.execute("DELETE FROM daily_suggestions WHERE profile_id = ?", (profile_id,))
    for s in suggestions:
        sid = str(uuid.uuid4())[:8]
        conn.execute(
            "INSERT INTO daily_suggestions (id, profile_id, suggested_id, score, date) VALUES (?, ?, ?, ?, ?)",
            (sid, profile_id, s["suggested_id"], s["score"], today),
        )
    conn.commit()


def get_daily_suggestions(profile_id: str) -> list[dict]:
    from datetime import date
    conn = get_db()
    today = date.today().isoformat()
    rows = conn.execute(
        """SELECT ds.*, p.name, p.photo, p.age, p.gender
           FROM daily_suggestions ds
           LEFT JOIN profiles p ON ds.suggested_id = p.id
           WHERE ds.profile_id = ? AND ds.date = ?
           ORDER BY ds.score DESC""",
        (profile_id, today),
    ).fetchall()
    return [dict(r) for r in rows]


def mark_suggestion_seen(suggestion_id: str):
    conn = get_db()
    conn.execute("UPDATE daily_suggestions SET seen = 1 WHERE id = ?", (suggestion_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Who Viewed Me
# ---------------------------------------------------------------------------

def get_profile_viewers(profile_id: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT be.profile_id, MAX(be.created_at) as last_viewed,
                  p.name, p.photo, p.age, p.gender
           FROM behavioral_events be
           LEFT JOIN profiles p ON be.profile_id = p.id
           WHERE be.event_type = 'profile_view' AND be.target_id = ?
           GROUP BY be.profile_id
           ORDER BY last_viewed DESC
           LIMIT ?""",
        (profile_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Who Liked You
# ---------------------------------------------------------------------------

def get_who_liked_me(profile_id: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT l.*, p.name, p.photo, p.age, p.gender
           FROM likes l
           LEFT JOIN profiles p ON l.from_id = p.id
           WHERE l.target_id = ? AND l.target_type = 'profile'
           ORDER BY l.created_at DESC
           LIMIT ?""",
        (profile_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# TOTP 2FA
# ---------------------------------------------------------------------------

def save_totp_secret(user_id: str, secret: str) -> str:
    conn = get_db()
    totp_id = str(uuid.uuid4())[:8]
    conn.execute(
        """INSERT INTO totp_secrets (id, user_id, secret)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET secret=excluded.secret, verified=0,
           created_at=CURRENT_TIMESTAMP""",
        (totp_id, user_id, secret),
    )
    conn.commit()
    return totp_id


def get_totp_secret(user_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM totp_secrets WHERE user_id = ?", (user_id,)
    ).fetchone()
    return dict(row) if row else None


def verify_totp_setup(user_id: str) -> bool:
    conn = get_db()
    cur = conn.execute(
        "UPDATE totp_secrets SET verified = 1 WHERE user_id = ?", (user_id,)
    )
    conn.commit()
    return cur.rowcount > 0


def delete_totp_secret(user_id: str):
    conn = get_db()
    conn.execute("DELETE FROM totp_secrets WHERE user_id = ?", (user_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Push Subscriptions
# ---------------------------------------------------------------------------

def save_push_subscription(user_id: str, endpoint: str, p256dh: str, auth: str) -> str:
    conn = get_db()
    sub_id = str(uuid.uuid4())[:8]
    conn.execute(
        """INSERT INTO push_subscriptions (id, user_id, endpoint, p256dh, auth)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(endpoint) DO UPDATE SET user_id=excluded.user_id,
           p256dh=excluded.p256dh, auth=excluded.auth""",
        (sub_id, user_id, endpoint, p256dh, auth),
    )
    conn.commit()
    return sub_id


def get_push_subscriptions(user_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM push_subscriptions WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_push_subscription(endpoint: str):
    conn = get_db()
    conn.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
    conn.commit()


# ---------------------------------------------------------------------------
# Group Messages
# ---------------------------------------------------------------------------

def send_group_message(group_id: str, from_id: str, content: str) -> str:
    conn = get_db()
    msg_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO group_messages (id, group_id, from_id, content) VALUES (?, ?, ?, ?)",
        (msg_id, group_id, from_id, content),
    )
    conn.commit()
    return msg_id


def get_group_messages(group_id: str, limit: int = 100, before: str = None) -> list[dict]:
    conn = get_db()
    if before:
        rows = conn.execute(
            """SELECT gm.*, p.name as from_name, p.photo as from_photo
               FROM group_messages gm
               LEFT JOIN profiles p ON gm.from_id = p.id
               WHERE gm.group_id = ? AND gm.created_at < ?
               ORDER BY gm.created_at DESC LIMIT ?""",
            (group_id, before, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT gm.*, p.name as from_name, p.photo as from_photo
               FROM group_messages gm
               LEFT JOIN profiles p ON gm.from_id = p.id
               WHERE gm.group_id = ?
               ORDER BY gm.created_at DESC LIMIT ?""",
            (group_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Content Filter Log
# ---------------------------------------------------------------------------

def log_content_filter(content_type: str, content_id: str, profile_id: str,
                       flagged_text: str, reason: str, filter_type: str,
                       action: str = "censored") -> str:
    conn = get_db()
    log_id = str(uuid.uuid4())[:8]
    conn.execute(
        """INSERT INTO content_filter_log
           (id, content_type, content_id, profile_id, flagged_text, reason, filter_type, action)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (log_id, content_type, content_id, profile_id, flagged_text, reason, filter_type, action),
    )
    conn.commit()
    return log_id


def get_content_filter_logs(limit: int = 100) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT cfl.*, p.name as profile_name
           FROM content_filter_log cfl
           LEFT JOIN profiles p ON cfl.profile_id = p.id
           ORDER BY cfl.created_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Premium Subscriptions
# ---------------------------------------------------------------------------

def get_subscription(user_id: str) -> dict:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM premium_subscriptions WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row:
        return dict(row)
    return {"user_id": user_id, "tier": "free", "started_at": None, "expires_at": None}


def update_subscription(user_id: str, tier: str, expires_at: str = None):
    conn = get_db()
    conn.execute(
        """INSERT INTO premium_subscriptions (user_id, tier, expires_at)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET tier=excluded.tier,
           expires_at=excluded.expires_at, started_at=CURRENT_TIMESTAMP""",
        (user_id, tier, expires_at),
    )
    conn.commit()


def is_premium(user_id: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT tier, expires_at FROM premium_subscriptions WHERE user_id = ?", (user_id,)
    ).fetchone()
    if not row or row["tier"] == "free":
        return False
    if row["expires_at"]:
        from datetime import datetime, timezone
        try:
            expires = datetime.fromisoformat(row["expires_at"])
            if expires < datetime.now(timezone.utc):
                return False
        except (ValueError, TypeError):
            pass
    return True


# ---------------------------------------------------------------------------
# Analytics Events
# ---------------------------------------------------------------------------

def log_analytics_event(event_type: str, profile_id: str = None, metadata: str = None):
    conn = get_db()
    event_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO analytics_events (id, event_type, profile_id, metadata) VALUES (?, ?, ?, ?)",
        (event_id, event_type, profile_id, metadata),
    )
    conn.commit()


def get_analytics_summary(days: int = 30) -> dict:
    conn = get_db()
    rows = conn.execute(
        """SELECT event_type, DATE(created_at) as day, COUNT(*) as count
           FROM analytics_events
           WHERE created_at >= datetime('now', ? || ' days')
           GROUP BY event_type, DATE(created_at)
           ORDER BY day ASC""",
        (f"-{days}",),
    ).fetchall()
    summary = {}
    daily = {}
    for r in rows:
        et = r["event_type"]
        summary[et] = summary.get(et, 0) + r["count"]
        day = r["day"]
        if day not in daily:
            daily[day] = {}
        daily[day][et] = r["count"]
    # Daily active users
    dau_rows = conn.execute(
        """SELECT DATE(created_at) as day, COUNT(DISTINCT profile_id) as dau
           FROM analytics_events
           WHERE created_at >= datetime('now', ? || ' days') AND profile_id IS NOT NULL
           GROUP BY DATE(created_at)""",
        (f"-{days}",),
    ).fetchall()
    dau = {r["day"]: r["dau"] for r in dau_rows}
    return {"totals": summary, "daily": daily, "daily_active_users": dau}


def get_engagement_metrics(days: int = 7) -> dict:
    conn = get_db()
    # Average messages per active user
    msg_row = conn.execute(
        """SELECT COUNT(*) as total_messages, COUNT(DISTINCT from_id) as active_senders
           FROM messages
           WHERE created_at >= datetime('now', ? || ' days')""",
        (f"-{days}",),
    ).fetchone()
    total_messages = msg_row["total_messages"] if msg_row else 0
    active_senders = msg_row["active_senders"] if msg_row else 0
    avg_messages = round(total_messages / max(active_senders, 1), 2)
    # Response rate: messages that got a reply
    reply_row = conn.execute(
        """SELECT COUNT(DISTINCT m1.id) as sent,
                  COUNT(DISTINCT m2.id) as replied
           FROM messages m1
           LEFT JOIN messages m2 ON m2.from_id = m1.to_id AND m2.to_id = m1.from_id
                AND m2.created_at > m1.created_at
           WHERE m1.created_at >= datetime('now', ? || ' days')""",
        (f"-{days}",),
    ).fetchone()
    sent = reply_row["sent"] if reply_row else 0
    replied = reply_row["replied"] if reply_row else 0
    response_rate = round(replied / max(sent, 1) * 100, 1)
    return {
        "total_messages": total_messages,
        "active_senders": active_senders,
        "avg_messages_per_user": avg_messages,
        "response_rate_pct": response_rate,
        "period_days": days,
    }


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

def mark_onboarding_completed(user_id: str):
    conn = get_db()
    conn.execute("UPDATE users SET onboarding_completed = 1 WHERE id = ?", (user_id,))
    conn.commit()


def has_completed_onboarding(user_id: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT onboarding_completed FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return bool(row and row["onboarding_completed"])
