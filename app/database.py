"""
Kindred v2.2.0 - Database Layer
SQLite storage for users, profiles, messages, invites, feedback,
date plans, behavioral events, safety reports,
profile pages (blog, comments, friends), notifications,
likes, status updates, activity feed, groups, events,
blocks, password resets, notification preferences,
message reactions, daily suggestions, TOTP 2FA, push subscriptions,
group messages, content filtering, premium subscriptions, analytics,
voice messages, profile prompts, super likes, stories, polls,
user sessions, user locations, recovery codes.
"""

import json
import math
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

        CREATE TABLE IF NOT EXISTS voice_messages (
            id TEXT PRIMARY KEY,
            from_id TEXT NOT NULL,
            to_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            duration_ms INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (to_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS profile_prompts (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            prompt TEXT NOT NULL,
            answer TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_profile_prompts ON profile_prompts(profile_id);

        CREATE TABLE IF NOT EXISTS super_likes (
            id TEXT PRIMARY KEY,
            from_id TEXT NOT NULL,
            to_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (to_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(from_id, to_id)
        );

        CREATE TABLE IF NOT EXISTS stories (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT 'text',
            content TEXT NOT NULL,
            background TEXT DEFAULT '#6c7086',
            photo TEXT,
            views INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_stories_profile ON stories(profile_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_stories_expires ON stories(expires_at);

        CREATE TABLE IF NOT EXISTS story_views (
            id TEXT PRIMARY KEY,
            story_id TEXT NOT NULL,
            viewer_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
            FOREIGN KEY (viewer_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(story_id, viewer_id)
        );

        CREATE TABLE IF NOT EXISTS group_polls (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS poll_votes (
            id TEXT PRIMARY KEY,
            poll_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            option_index INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (poll_id) REFERENCES group_polls(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(poll_id, profile_id)
        );

        CREATE TABLE IF NOT EXISTS user_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            device TEXT,
            ip_address TEXT,
            last_active TEXT DEFAULT (datetime('now')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_user_sessions ON user_sessions(user_id);

        CREATE TABLE IF NOT EXISTS user_locations (
            user_id TEXT PRIMARY KEY,
            latitude REAL,
            longitude REAL,
            city TEXT,
            radius_km INTEGER DEFAULT 100,
            enabled INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS recovery_codes (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_recovery_codes ON recovery_codes(user_id);

        CREATE TABLE IF NOT EXISTS icebreaker_games (
            id TEXT PRIMARY KEY,
            profile_a TEXT NOT NULL,
            profile_b TEXT NOT NULL,
            game_type TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            current_turn TEXT,
            turn_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_a) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_b) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS game_turns (
            id TEXT PRIMARY KEY,
            game_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            content TEXT NOT NULL,
            turn_number INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES icebreaker_games(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_game_turns ON game_turns(game_id, turn_number);

        CREATE TABLE IF NOT EXISTS date_schedules (
            id TEXT PRIMARY KEY,
            profile_a TEXT NOT NULL,
            profile_b TEXT NOT NULL,
            scheduled_by TEXT NOT NULL,
            date_date TEXT NOT NULL,
            date_time TEXT,
            venue TEXT,
            notes TEXT,
            status TEXT DEFAULT 'proposed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_a) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_b) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS blind_dates (
            id TEXT PRIMARY KEY,
            initiator_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            reveal_at TIMESTAMP NOT NULL,
            revealed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (initiator_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(initiator_id, target_id)
        );

        CREATE TABLE IF NOT EXISTS passed_profiles (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            passed_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (passed_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(profile_id, passed_id)
        );

        CREATE TABLE IF NOT EXISTS threaded_replies (
            message_id TEXT PRIMARY KEY,
            reply_to_id TEXT NOT NULL,
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
            FOREIGN KEY (reply_to_id) REFERENCES messages(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS shared_playlists (
            id TEXT PRIMARY KEY,
            profile_a TEXT NOT NULL,
            profile_b TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT 'Our Playlist',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_a) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_b) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS playlist_songs (
            id TEXT PRIMARY KEY,
            playlist_id TEXT NOT NULL,
            added_by TEXT NOT NULL,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (playlist_id) REFERENCES shared_playlists(id) ON DELETE CASCADE,
            FOREIGN KEY (added_by) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_playlist_songs ON playlist_songs(playlist_id);

        CREATE TABLE IF NOT EXISTS event_photos (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            caption TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_event_photos ON event_photos(event_id);

        CREATE TABLE IF NOT EXISTS profile_badges (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            badge_type TEXT NOT NULL,
            awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(profile_id, badge_type)
        );
        CREATE INDEX IF NOT EXISTS idx_profile_badges ON profile_badges(profile_id);

        CREATE TABLE IF NOT EXISTS story_reactions (
            id TEXT PRIMARY KEY,
            story_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            reaction TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(story_id, profile_id)
        );

        CREATE TABLE IF NOT EXISTS pinned_messages (
            id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL UNIQUE,
            pinned_by TEXT NOT NULL,
            conversation_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
            FOREIGN KEY (pinned_by) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_pinned_messages ON pinned_messages(conversation_key);

        CREATE TABLE IF NOT EXISTS message_cooldowns (
            id TEXT PRIMARY KEY,
            from_id TEXT NOT NULL,
            to_id TEXT NOT NULL,
            message_count INTEGER DEFAULT 1,
            window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(from_id, to_id)
        );

        CREATE TABLE IF NOT EXISTS undo_blocks (
            id TEXT PRIMARY KEY,
            blocker_id TEXT NOT NULL,
            blocked_id TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (blocker_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS safety_checkins (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            date_schedule_id TEXT,
            partner_name TEXT,
            emergency_contact TEXT,
            emergency_email TEXT,
            check_in_at TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY,
            admin_user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_audit_log ON audit_log(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);

        CREATE TABLE IF NOT EXISTS webhooks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            events TEXT NOT NULL DEFAULT '[]',
            secret TEXT DEFAULT '',
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS rate_limit_log (
            id TEXT PRIMARY KEY,
            endpoint TEXT NOT NULL,
            ip_address TEXT,
            user_id TEXT,
            blocked INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_rate_limit_log ON rate_limit_log(endpoint, created_at);

        CREATE TABLE IF NOT EXISTS vacuum_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ran_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            db_size_bytes INTEGER
        );

        CREATE TABLE IF NOT EXISTS availability_status (
            profile_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'active',
            custom_text TEXT,
            available_until TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS conversation_starters (
            id TEXT PRIMARY KEY,
            from_id TEXT NOT NULL,
            to_id TEXT NOT NULL,
            starter_type TEXT NOT NULL DEFAULT 'interest',
            content TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (to_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_starters_pair ON conversation_starters(from_id, to_id);

        CREATE TABLE IF NOT EXISTS date_feedback (
            id TEXT PRIMARY KEY,
            date_schedule_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            partner_id TEXT NOT NULL,
            felt_safe INTEGER DEFAULT 1,
            had_fun INTEGER DEFAULT 1,
            accurate_match INTEGER DEFAULT 1,
            would_meet_again INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (date_schedule_id) REFERENCES date_schedules(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
            FOREIGN KEY (partner_id) REFERENCES profiles(id) ON DELETE CASCADE,
            UNIQUE(date_schedule_id, profile_id)
        );

        CREATE TABLE IF NOT EXISTS announcements (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            active INTEGER DEFAULT 1,
            created_by TEXT NOT NULL,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS compatibility_history (
            id TEXT PRIMARY KEY,
            profile_id_1 TEXT NOT NULL,
            profile_id_2 TEXT NOT NULL,
            overall_score REAL,
            dimension_scores TEXT,
            recorded_at TEXT DEFAULT (datetime('now')),
            UNIQUE(profile_id_1, profile_id_2, recorded_at)
        );

        CREATE TABLE IF NOT EXISTS endorsements (
            id TEXT PRIMARY KEY,
            endorser_id TEXT NOT NULL,
            endorsed_id TEXT NOT NULL,
            trait TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(endorser_id, endorsed_id, trait)
        );

        CREATE TABLE IF NOT EXISTS group_post_reactions (
            id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            emoji TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(post_id, profile_id, emoji)
        );

        CREATE TABLE IF NOT EXISTS event_messages (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_event_messages_event ON event_messages(event_id);

        CREATE TABLE IF NOT EXISTS profile_reveal_stages (
            id TEXT PRIMARY KEY,
            viewer_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            stage INTEGER DEFAULT 0,
            unlocked_at TEXT DEFAULT (datetime('now')),
            UNIQUE(viewer_id, target_id)
        );

        CREATE TABLE IF NOT EXISTS flagged_content (
            id TEXT PRIMARY KEY,
            content_type TEXT NOT NULL,
            content_id TEXT NOT NULL,
            reporter_id TEXT,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            reviewed_by TEXT,
            reviewed_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_flagged_status ON flagged_content(status);

        CREATE TABLE IF NOT EXISTS report_reasons (
            id TEXT PRIMARY KEY,
            report_id TEXT NOT NULL,
            reason_category TEXT NOT NULL,
            reason_detail TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES safety_reports(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_report_reasons_report ON report_reasons(report_id);

        CREATE TABLE IF NOT EXISTS suspensions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            suspended_by TEXT NOT NULL,
            suspension_type TEXT DEFAULT 'temporary',
            expires_at TIMESTAMP,
            appealed INTEGER DEFAULT 0,
            appeal_text TEXT,
            appeal_reviewed INTEGER DEFAULT 0,
            appeal_result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (suspended_by) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_suspensions_user ON suspensions(user_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS photo_hashes (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            photo_filename TEXT NOT NULL,
            phash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_photo_hashes_hash ON photo_hashes(phash);

        CREATE TABLE IF NOT EXISTS saved_searches (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            name TEXT NOT NULL,
            filters TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_saved_searches_profile ON saved_searches(profile_id);
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
        # v1.6.0
        "ALTER TABLE users ADD COLUMN incognito_mode INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN locale TEXT DEFAULT 'en'",
        "ALTER TABLE profiles ADD COLUMN latitude REAL",
        "ALTER TABLE profiles ADD COLUMN longitude REAL",
        "ALTER TABLE profiles ADD COLUMN location_radius_km INTEGER DEFAULT 100",
        # v1.7.0
        "ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'mocha'",
        "ALTER TABLE users ADD COLUMN typing_preview INTEGER DEFAULT 0",
        "ALTER TABLE messages ADD COLUMN reply_to TEXT",
        # v2.2.0
        "ALTER TABLE profiles ADD COLUMN availability_status TEXT DEFAULT 'active'",
        "ALTER TABLE profiles ADD COLUMN availability_text TEXT",
        # Phase 3
        "ALTER TABLE notification_preferences ADD COLUMN read_receipts_enabled INTEGER DEFAULT 1",
        # v2.2.0
        "ALTER TABLE safety_reports ADD COLUMN status TEXT DEFAULT 'open'",
        "ALTER TABLE safety_reports ADD COLUMN reason_category TEXT",
        "ALTER TABLE safety_reports ADD COLUMN reviewed_by TEXT",
        "ALTER TABLE safety_reports ADD COLUMN reviewed_at TIMESTAMP",
        "ALTER TABLE safety_reports ADD COLUMN resolution TEXT",
        "ALTER TABLE profiles ADD COLUMN response_rate REAL",
        "ALTER TABLE profiles ADD COLUMN avg_reply_minutes REAL",
        "ALTER TABLE profiles ADD COLUMN last_message_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN suspended INTEGER DEFAULT 0",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e):
                raise


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

def save_profile(data: dict) -> str:
    conn = get_db()
    profile_id = data.get("id") or uuid.uuid4().hex
    conn.execute("""
        INSERT INTO profiles
        (id, name, age, gender, seeking, big_five, attachment, values_data,
         tradeoffs, self_disclosure, love_language, dealbreakers, open_ended,
         scenario_answers, behavioral_answers, embedding, photo,
         weight_prefs, privacy, invite_code,
         communication_style, financial_values, dating_energy, dating_pace,
         relationship_intent)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
         name=excluded.name, age=excluded.age, gender=excluded.gender,
         seeking=excluded.seeking, big_five=excluded.big_five,
         attachment=excluded.attachment, values_data=excluded.values_data,
         tradeoffs=excluded.tradeoffs, self_disclosure=excluded.self_disclosure,
         love_language=excluded.love_language, dealbreakers=excluded.dealbreakers,
         open_ended=excluded.open_ended, scenario_answers=excluded.scenario_answers,
         behavioral_answers=excluded.behavioral_answers, embedding=excluded.embedding,
         photo=excluded.photo, weight_prefs=excluded.weight_prefs,
         privacy=excluded.privacy, invite_code=excluded.invite_code,
         communication_style=excluded.communication_style,
         financial_values=excluded.financial_values,
         dating_energy=excluded.dating_energy, dating_pace=excluded.dating_pace,
         relationship_intent=excluded.relationship_intent
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

    return profile_id


def update_profile_field(profile_id: str, field: str, value) -> bool:
    allowed = {"photo", "weight_prefs", "privacy", "name", "age",
               "dating_energy", "verified", "last_active", "daily_views", "daily_view_date",
               "location", "headline", "about_me", "who_id_like_to_meet", "interests",
               "heroes", "mood", "music_embeds", "video_embeds", "profile_song", "profile_views",
               "latitude", "longitude", "location_radius_km"}
    if field not in allowed:
        return False
    conn = get_db()
    if field in ("weight_prefs", "privacy"):
        value = json.dumps(value)
    conn.execute(f"UPDATE profiles SET {field} = ? WHERE id = ?", (value, profile_id))
    conn.commit()

    return True


def get_profile(profile_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()

    if row is None:
        return None
    return _row_to_dict(row)


def get_all_profiles() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM profiles ORDER BY created_at DESC").fetchall()

    return [_row_to_dict(r) for r in rows]


def delete_profile(profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    conn.commit()

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
    msg_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO messages (id, from_id, to_id, content, photo) VALUES (?,?,?,?,?)",
        (msg_id, from_id, to_id, content, photo or None)
    )
    conn.commit()

    return msg_id


def get_conversation(id_a: str, id_b: str, limit: int = 100) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM messages
        WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)
        ORDER BY created_at ASC
        LIMIT ?
    """, (id_a, id_b, id_b, id_a, limit)).fetchall()

    return [dict(r) for r in rows]


def get_conversation_count(id_a: str, id_b: str) -> int:
    conn = get_db()
    row = conn.execute("""
        SELECT COUNT(*) as c FROM messages
        WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)
    """, (id_a, id_b, id_b, id_a)).fetchone()

    return row["c"]


def get_last_message_sender(id_a: str, id_b: str) -> str | None:
    conn = get_db()
    row = conn.execute("""
        SELECT from_id FROM messages
        WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)
        ORDER BY created_at DESC LIMIT 1
    """, (id_a, id_b, id_b, id_a)).fetchone()

    return row["from_id"] if row else None


def get_conversations_for(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT m.content as last_message, m.from_id as last_sender,
               m.created_at as last_time, latest.partner_id,
               (SELECT COUNT(*) FROM messages
                WHERE from_id=latest.partner_id AND to_id=? AND read=0) as unread
        FROM messages m
        INNER JOIN (
            SELECT
                CASE WHEN from_id=? THEN to_id ELSE from_id END as partner_id,
                MAX(created_at) as max_created
            FROM messages WHERE from_id=? OR to_id=?
            GROUP BY partner_id
        ) latest ON (
            ((m.from_id=? AND m.to_id=latest.partner_id) OR (m.from_id=latest.partner_id AND m.to_id=?))
            AND m.created_at = latest.max_created
        )
        ORDER BY m.created_at DESC
    """, (profile_id, profile_id, profile_id, profile_id, profile_id, profile_id)).fetchall()

    return [dict(r) for r in rows]


def mark_messages_read(from_id: str, to_id: str):
    conn = get_db()
    conn.execute(
        "UPDATE messages SET read=1 WHERE from_id=? AND to_id=? AND read=0",
        (from_id, to_id)
    )
    conn.commit()



# ---------------------------------------------------------------------------
# Invites
# ---------------------------------------------------------------------------

def create_invite(created_by: str | None = None) -> str:
    conn = get_db()
    code = uuid.uuid4().hex.upper()
    conn.execute(
        "INSERT INTO invites (code, created_by) VALUES (?,?)",
        (code, created_by)
    )
    conn.commit()

    return code


def use_invite(code: str, used_by: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM invites WHERE code=? AND used_by IS NULL", (code,)
    ).fetchone()
    if row is None:
    
        return False
    conn.execute(
        "UPDATE invites SET used_by=?, used_at=CURRENT_TIMESTAMP WHERE code=?",
        (used_by, code)
    )
    conn.commit()

    return True


def get_all_invites() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM invites ORDER BY created_at DESC").fetchall()

    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

def save_feedback(profile_a: str, profile_b: str, went_on_date: bool,
                  rating: int | None, notes: str | None,
                  safety_rating: int | None = None,
                  would_meet_again: bool | None = None) -> str:
    conn = get_db()
    fb_id = uuid.uuid4().hex
    conn.execute(
        """INSERT INTO feedback
        (id, profile_a, profile_b, went_on_date, rating, notes, safety_rating, would_meet_again)
        VALUES (?,?,?,?,?,?,?,?)""",
        (fb_id, profile_a, profile_b, int(went_on_date), rating, notes,
         safety_rating, int(would_meet_again) if would_meet_again is not None else None)
    )
    conn.commit()

    return fb_id


def get_feedback_for(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM feedback WHERE profile_a=? OR profile_b=? ORDER BY created_at DESC",
        (profile_id, profile_id)
    ).fetchall()

    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Date Plans
# ---------------------------------------------------------------------------

def create_date_plan(profile_a: str, profile_b: str, proposed_by: str,
                     suggestion: str, proposed_time: str | None = None) -> str:
    conn = get_db()
    plan_id = uuid.uuid4().hex
    conn.execute(
        """INSERT INTO date_plans
        (id, profile_a, profile_b, proposed_by, suggestion, proposed_time)
        VALUES (?,?,?,?,?,?)""",
        (plan_id, profile_a, profile_b, proposed_by, suggestion, proposed_time)
    )
    conn.commit()

    return plan_id


def update_date_plan(plan_id: str, status: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "UPDATE date_plans SET status=?, updated_at=datetime('now') WHERE id=?",
        (status, plan_id)
    )
    conn.commit()

    return cursor.rowcount > 0


def get_date_plans(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM date_plans
        WHERE profile_a=? OR profile_b=?
        ORDER BY created_at DESC""",
        (profile_id, profile_id)
    ).fetchall()

    return [dict(r) for r in rows]


def get_date_plans_between(id_a: str, id_b: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM date_plans
        WHERE (profile_a=? AND profile_b=?) OR (profile_a=? AND profile_b=?)
        ORDER BY created_at DESC""",
        (id_a, id_b, id_b, id_a)
    ).fetchall()

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
    report_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO safety_reports (id, reporter_id, reported_id, report_type, notes) VALUES (?,?,?,?,?)",
        (report_id, reporter_id, reported_id, report_type, notes)
    )
    conn.commit()

    return report_id


def get_safety_reports_for(profile_id: str) -> int:
    """Count safety reports against a user."""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM safety_reports WHERE reported_id=?",
        (profile_id,)
    ).fetchone()

    return row["c"]


def get_all_safety_reports() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM safety_reports ORDER BY created_at DESC").fetchall()

    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Profile Page - Blog Posts
# ---------------------------------------------------------------------------

def create_blog_post(profile_id: str, title: str, content: str) -> str:
    conn = get_db()
    post_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO profile_blog_posts (id, profile_id, title, content) VALUES (?,?,?,?)",
        (post_id, profile_id, title, content)
    )
    conn.commit()

    return post_id


def get_blog_posts(profile_id: str, limit: int = 20) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM profile_blog_posts WHERE profile_id=? ORDER BY created_at DESC LIMIT ?",
        (profile_id, limit)
    ).fetchall()

    return [dict(r) for r in rows]


def delete_blog_post(post_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM profile_blog_posts WHERE id=? AND profile_id=?",
        (post_id, profile_id)
    )
    conn.commit()

    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Profile Page - Comments
# ---------------------------------------------------------------------------

def create_profile_comment(profile_id: str, from_id: str, content: str) -> str:
    conn = get_db()
    comment_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO profile_comments (id, profile_id, from_id, content) VALUES (?,?,?,?)",
        (comment_id, profile_id, from_id, content)
    )
    conn.commit()

    return comment_id


def get_profile_comments(profile_id: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM profile_comments WHERE profile_id=? ORDER BY created_at DESC LIMIT ?",
        (profile_id, limit)
    ).fetchall()

    return [dict(r) for r in rows]


def delete_profile_comment(comment_id: str, profile_id: str) -> bool:
    """Profile owner can delete comments on their page."""
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM profile_comments WHERE id=? AND profile_id=?",
        (comment_id, profile_id)
    )
    conn.commit()

    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Profile Page - Friends
# ---------------------------------------------------------------------------

def send_friend_request(profile_id: str, friend_id: str) -> str:
    conn = get_db()
    req_id = uuid.uuid4().hex
    conn.execute(
        "INSERT OR IGNORE INTO profile_friends (id, profile_id, friend_id, status) VALUES (?,?,?,?)",
        (req_id, profile_id, friend_id, "pending")
    )
    conn.commit()

    return req_id


def respond_friend_request(profile_id: str, friend_id: str, accept: bool) -> bool:
    """Accept or decline a pending friend request FROM friend_id TO profile_id."""
    conn = get_db()
    if accept:
        cursor = conn.execute(
            "UPDATE profile_friends SET status='accepted' WHERE profile_id=? AND friend_id=? AND status='pending'",
            (friend_id, profile_id)
        )
        if cursor.rowcount == 0:
            return False
        rec_id = uuid.uuid4().hex
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

    return True


def are_friends(id_a: str, id_b: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM profile_friends WHERE profile_id=? AND friend_id=? AND status='accepted'",
        (id_a, id_b)
    ).fetchone()

    return row is not None


def increment_profile_views(profile_id: str):
    conn = get_db()
    conn.execute("UPDATE profiles SET profile_views = COALESCE(profile_views, 0) + 1 WHERE id=?", (profile_id,))
    conn.commit()



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
    user_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO users (id, email, password_hash, display_name, is_admin) VALUES (?,?,?,?,?)",
        (user_id, email.lower().strip(), password_hash, display_name or email.split("@")[0], int(is_admin))
    )
    conn.commit()

    return user_id


def get_user_by_email(email: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()

    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    return dict(row) if row else None


def link_profile_to_user(user_id: str, profile_id: str):
    conn = get_db()
    conn.execute("UPDATE users SET profile_id = ? WHERE id = ?", (profile_id, user_id))
    conn.commit()



# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def create_notification(user_id: str, ntype: str, title: str,
                        body: str = "", link: str = "") -> str:
    conn = get_db()
    nid = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO notifications (id, user_id, type, title, body, link) VALUES (?,?,?,?,?,?)",
        (nid, user_id, ntype, title, body, link)
    )
    conn.commit()

    return nid


def get_notifications(user_id: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()

    return [dict(r) for r in rows]


def get_unread_notification_count(user_id: str) -> int:
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM notifications WHERE user_id=? AND read=0",
        (user_id,)
    ).fetchone()

    return row["c"]


def mark_notifications_read(user_id: str):
    conn = get_db()
    conn.execute("UPDATE notifications SET read=1 WHERE user_id=? AND read=0", (user_id,))
    conn.commit()



def mark_notification_read(notification_id: str):
    conn = get_db()
    conn.execute("UPDATE notifications SET read=1 WHERE id=?", (notification_id,))
    conn.commit()



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
    
        return False
    else:
        like_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO likes (id, from_id, target_type, target_id, reaction) VALUES (?,?,?,?,?)",
            (like_id, from_id, target_type, target_id, reaction)
        )
        conn.commit()
    
        return True


def get_likes(target_type: str, target_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT l.*, p.name as from_name FROM likes l JOIN profiles p ON p.id=l.from_id WHERE l.target_type=? AND l.target_id=? ORDER BY l.created_at DESC",
        (target_type, target_id)
    ).fetchall()

    return [dict(r) for r in rows]


def get_like_count(target_type: str, target_id: str) -> int:
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM likes WHERE target_type=? AND target_id=?",
        (target_type, target_id)
    ).fetchone()

    return row["c"]


def has_liked(from_id: str, target_type: str, target_id: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM likes WHERE from_id=? AND target_type=? AND target_id=?",
        (from_id, target_type, target_id)
    ).fetchone()

    return row is not None


# ---------------------------------------------------------------------------
# Status Updates
# ---------------------------------------------------------------------------

def create_status_update(profile_id: str, content: str, mood: str = "") -> str:
    conn = get_db()
    sid = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO status_updates (id, profile_id, content, mood) VALUES (?,?,?,?)",
        (sid, profile_id, content, mood or None)
    )
    conn.commit()

    return sid


def get_status_updates(profile_id: str, limit: int = 20) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM status_updates WHERE profile_id=? ORDER BY created_at DESC LIMIT ?",
        (profile_id, limit)
    ).fetchall()

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

    return [dict(r) for r in rows]


def delete_status_update(status_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM status_updates WHERE id=? AND profile_id=?",
        (status_id, profile_id)
    )
    conn.commit()

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



def get_online_status(profile_id: str, minutes: int = 5) -> bool:
    """Check if a single profile is online."""
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM profiles WHERE id=? AND last_active > datetime('now', ?)",
        (profile_id, f"-{minutes} minutes")
    ).fetchone()

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

    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Photo Gallery
# ---------------------------------------------------------------------------

def add_photo(profile_id: str, filename: str, caption: str = "",
              is_primary: bool = False) -> str:
    conn = get_db()
    photo_id = uuid.uuid4().hex
    if is_primary:
        conn.execute("UPDATE photos SET is_primary=0 WHERE profile_id=?", (profile_id,))
    conn.execute(
        "INSERT INTO photos (id, profile_id, filename, caption, is_primary) VALUES (?,?,?,?,?)",
        (photo_id, profile_id, filename, caption or None, int(is_primary))
    )
    conn.commit()

    return photo_id


def get_photos(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM photos WHERE profile_id=? ORDER BY is_primary DESC, created_at DESC",
        (profile_id,)
    ).fetchall()

    return [dict(r) for r in rows]


def delete_photo(photo_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM photos WHERE id=? AND profile_id=?",
        (photo_id, profile_id)
    )
    conn.commit()

    return cursor.rowcount > 0


def set_primary_photo(photo_id: str, profile_id: str) -> bool:
    conn = get_db()
    conn.execute("BEGIN")
    try:
        conn.execute("UPDATE photos SET is_primary=0 WHERE profile_id=?", (profile_id,))
        cursor = conn.execute(
            "UPDATE photos SET is_primary=1 WHERE id=? AND profile_id=?",
            (photo_id, profile_id)
        )
        row = conn.execute("SELECT filename FROM photos WHERE id=?", (photo_id,)).fetchone()
        if row:
            conn.execute("UPDATE profiles SET photo=? WHERE id=?", (row["filename"], profile_id))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Search / Discover
# ---------------------------------------------------------------------------

def search_profiles(query: str = "", gender: str = "", seeking: str = "",
                    age_min: int = 0, age_max: int = 999,
                    location: str = "", limit: int = 50) -> list[dict]:
    conn = get_db()
    sql = "SELECT * FROM profiles WHERE (deactivated IS NULL OR deactivated=0)"
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

    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Activity Feed
# ---------------------------------------------------------------------------

def log_activity(profile_id: str, action: str, target_type: str = "",
                 target_id: str = "", detail: str = "") -> str:
    conn = get_db()
    aid = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO activity_feed (id, profile_id, action, target_type, target_id, detail) VALUES (?,?,?,?,?,?)",
        (aid, profile_id, action, target_type or None, target_id or None, detail or None)
    )
    conn.commit()

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

    return [dict(r) for r in rows]


def get_explore_profiles(limit: int = 20) -> list[dict]:
    """Get profiles for the explore page - most viewed, recently active."""
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM profiles
           WHERE (deactivated IS NULL OR deactivated=0)
           ORDER BY profile_views DESC, last_active DESC
           LIMIT ?""",
        (limit,)
    ).fetchall()

    return [_row_to_dict(r) for r in rows]


def get_recent_profiles(limit: int = 10) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM profiles WHERE (deactivated IS NULL OR deactivated=0) ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()

    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Groups / Communities
# ---------------------------------------------------------------------------

def create_group(name: str, description: str, creator_id: str,
                 privacy: str = "public") -> str:
    conn = get_db()
    gid = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO groups (id, name, description, creator_id, privacy) VALUES (?,?,?,?,?)",
        (gid, name, description, creator_id, privacy)
    )
    # Creator auto-joins as admin
    mid = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO group_members (id, group_id, profile_id, role) VALUES (?,?,?,?)",
        (mid, gid, creator_id, "admin")
    )
    conn.commit()

    return gid


def get_group(group_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM groups WHERE id=?", (group_id,)).fetchone()

    return dict(row) if row else None


def get_all_groups(limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT g.*, COUNT(gm.id) as member_count
           FROM groups g LEFT JOIN group_members gm ON gm.group_id = g.id
           GROUP BY g.id ORDER BY member_count DESC, g.created_at DESC LIMIT ?""",
        (limit,)
    ).fetchall()

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

    return [dict(r) for r in rows]


def join_group(group_id: str, profile_id: str) -> str:
    conn = get_db()
    mid = uuid.uuid4().hex
    conn.execute(
        "INSERT OR IGNORE INTO group_members (id, group_id, profile_id) VALUES (?,?,?)",
        (mid, group_id, profile_id)
    )
    conn.commit()

    return mid


def leave_group(group_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM group_members WHERE group_id=? AND profile_id=?",
        (group_id, profile_id)
    )
    conn.commit()

    return cursor.rowcount > 0


def is_group_member(group_id: str, profile_id: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM group_members WHERE group_id=? AND profile_id=?",
        (group_id, profile_id)
    ).fetchone()

    return row is not None


def get_group_members(group_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT gm.*, p.name, p.photo, p.age
           FROM group_members gm JOIN profiles p ON p.id = gm.profile_id
           WHERE gm.group_id=? ORDER BY gm.joined_at""",
        (group_id,)
    ).fetchall()

    return [dict(r) for r in rows]


def create_group_post(group_id: str, profile_id: str, content: str) -> str:
    conn = get_db()
    pid = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO group_posts (id, group_id, profile_id, content) VALUES (?,?,?,?)",
        (pid, group_id, profile_id, content)
    )
    conn.commit()

    return pid


def get_group_posts(group_id: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT gp.*, p.name, p.photo FROM group_posts gp
           JOIN profiles p ON p.id = gp.profile_id
           WHERE gp.group_id=? ORDER BY gp.created_at DESC LIMIT ?""",
        (group_id, limit)
    ).fetchall()

    return [dict(r) for r in rows]


def delete_group_post(post_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM group_posts WHERE id=? AND profile_id=?",
        (post_id, profile_id)
    )
    conn.commit()

    return cursor.rowcount > 0


def delete_group(group_id: str) -> bool:
    conn = get_db()
    conn.execute("BEGIN")
    try:
        conn.execute("DELETE FROM group_posts WHERE group_id=?", (group_id,))
        conn.execute("DELETE FROM group_members WHERE group_id=?", (group_id,))
        cursor = conn.execute("DELETE FROM groups WHERE id=?", (group_id,))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def create_event(title: str, description: str, creator_id: str,
                 location: str = "", event_date: str = "",
                 event_time: str = "", group_id: str = "",
                 max_attendees: int = 0) -> str:
    conn = get_db()
    eid = uuid.uuid4().hex
    conn.execute(
        """INSERT INTO events (id, title, description, creator_id, location,
           event_date, event_time, group_id, max_attendees) VALUES (?,?,?,?,?,?,?,?,?)""",
        (eid, title, description, creator_id, location or None,
         event_date or None, event_time or None, group_id or None, max_attendees)
    )
    # Creator auto-RSVPs
    rid = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO event_rsvps (id, event_id, profile_id, status) VALUES (?,?,?,?)",
        (rid, eid, creator_id, "going")
    )
    conn.commit()

    return eid


def get_event(event_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()

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
        rid = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO event_rsvps (id, event_id, profile_id, status) VALUES (?,?,?,?)",
            (rid, event_id, profile_id, status)
        )
    conn.commit()

    return rid


def get_event_rsvps(event_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT r.*, p.name, p.photo FROM event_rsvps r
           JOIN profiles p ON p.id = r.profile_id
           WHERE r.event_id=? ORDER BY r.created_at""",
        (event_id,)
    ).fetchall()

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

    return [dict(r) for r in rows]


def delete_event(event_id: str) -> bool:
    conn = get_db()
    conn.execute("BEGIN")
    try:
        conn.execute("DELETE FROM event_rsvps WHERE event_id=?", (event_id,))
        cursor = conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
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
    
        return None  # All questions exhausted

    import random
    question = random.choice(available)
    gid = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO compat_games (id, profile_a, profile_b, question) VALUES (?,?,?,?)",
        (gid, profile_a, profile_b, question)
    )
    conn.commit()
    game = dict(conn.execute("SELECT * FROM compat_games WHERE id=?", (gid,)).fetchone())

    return game


def answer_game(game_id: str, profile_id: str, answer: str) -> dict:
    conn = get_db()
    game = conn.execute("SELECT * FROM compat_games WHERE id=?", (game_id,)).fetchone()
    if not game:
    
        return None
    g = dict(game)
    if profile_id == g["profile_a"]:
        conn.execute("UPDATE compat_games SET answer_a=? WHERE id=?", (answer, game_id))
    elif profile_id == g["profile_b"]:
        conn.execute("UPDATE compat_games SET answer_b=? WHERE id=?", (answer, game_id))
    else:
    
        return None

    # Check if both answered, mark match
    updated = dict(conn.execute("SELECT * FROM compat_games WHERE id=?", (game_id,)).fetchone())
    if updated["answer_a"] and updated["answer_b"]:
        matched = 1 if updated["answer_a"] == updated["answer_b"] else 0
        conn.execute("UPDATE compat_games SET matched=? WHERE id=?", (matched, game_id))
        updated["matched"] = matched
    conn.commit()

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
    vid = uuid.uuid4().hex
    # Upsert - replace any existing pending verification
    conn.execute("DELETE FROM selfie_verifications WHERE profile_id=?", (profile_id,))
    conn.execute(
        "INSERT INTO selfie_verifications (id, profile_id, selfie_photo) VALUES (?,?,?)",
        (vid, profile_id, selfie_photo)
    )
    conn.commit()

    return vid


def get_pending_verifications() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT v.*, p.name, p.photo FROM selfie_verifications v
           JOIN profiles p ON p.id = v.profile_id
           WHERE v.status='pending' ORDER BY v.created_at"""
    ).fetchall()

    return [dict(r) for r in rows]


def review_verification(verification_id: str, approved: bool) -> bool:
    conn = get_db()
    v = conn.execute("SELECT * FROM selfie_verifications WHERE id=?", (verification_id,)).fetchone()
    if not v:
    
        return False
    status = "approved" if approved else "rejected"
    conn.execute(
        "UPDATE selfie_verifications SET status=?, reviewed_at=datetime('now') WHERE id=?",
        (status, verification_id)
    )
    if approved:
        conn.execute("UPDATE profiles SET verified=1 WHERE id=?", (v["profile_id"],))
    conn.commit()

    return True


def get_verification_status(profile_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM selfie_verifications WHERE profile_id=? ORDER BY created_at DESC LIMIT 1",
        (profile_id,)
    ).fetchone()

    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Video Intros
# ---------------------------------------------------------------------------

def save_video_intro(profile_id: str, filename: str, duration: int = 0) -> str:
    conn = get_db()
    vid = uuid.uuid4().hex
    # Replace existing
    conn.execute("DELETE FROM video_intros WHERE profile_id=?", (profile_id,))
    conn.execute(
        "INSERT INTO video_intros (id, profile_id, filename, duration) VALUES (?,?,?,?)",
        (vid, profile_id, filename, duration)
    )
    conn.commit()

    return vid


def get_video_intro(profile_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM video_intros WHERE profile_id=? LIMIT 1", (profile_id,)
    ).fetchone()

    return dict(row) if row else None


def delete_video_intro(profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute("DELETE FROM video_intros WHERE profile_id=?", (profile_id,))
    conn.commit()

    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Music Preferences
# ---------------------------------------------------------------------------

def add_music_pref(profile_id: str, song_title: str, artist: str,
                   genre: str = "", spotify_url: str = "") -> str:
    conn = get_db()
    mid = uuid.uuid4().hex
    count = conn.execute(
        "SELECT COUNT(*) as c FROM music_preferences WHERE profile_id=?", (profile_id,)
    ).fetchone()["c"]
    conn.execute(
        """INSERT INTO music_preferences (id, profile_id, song_title, artist, genre, spotify_url, sort_order)
           VALUES (?,?,?,?,?,?,?)""",
        (mid, profile_id, song_title, artist, genre or None, spotify_url or None, count)
    )
    conn.commit()

    return mid


def get_music_prefs(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM music_preferences WHERE profile_id=? ORDER BY sort_order",
        (profile_id,)
    ).fetchall()

    return [dict(r) for r in rows]


def delete_music_pref(pref_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM music_preferences WHERE id=? AND profile_id=?",
        (pref_id, profile_id)
    )
    conn.commit()

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
    bid = uuid.uuid4().hex
    try:
        conn.execute("BEGIN")
        conn.execute(
            "INSERT INTO blocks (id, blocker_id, blocked_id) VALUES (?,?,?)",
            (bid, blocker_id, blocked_id)
        )
        conn.execute(
            "DELETE FROM profile_friends WHERE (profile_id=? AND friend_id=?) OR (profile_id=? AND friend_id=?)",
            (blocker_id, blocked_id, blocked_id, blocker_id)
        )
        conn.execute("COMMIT")
    except sqlite3.IntegrityError:
        conn.execute("ROLLBACK")
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
    rid = uuid.uuid4().hex
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
        "SELECT * FROM password_resets WHERE token=? AND used=0 AND expires_at > datetime('now')",
        (token,)
    ).fetchone()
    if not row:
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
    cursor = conn.execute("UPDATE profiles SET deactivated=1 WHERE id=?", (profile_id,))
    conn.commit()
    return cursor.rowcount > 0


def reactivate_profile(profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute("UPDATE profiles SET deactivated=0 WHERE id=?", (profile_id,))
    conn.commit()
    return cursor.rowcount > 0


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
    token_id = uuid.uuid4().hex
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
    vid = uuid.uuid4().hex
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
    mod_id = uuid.uuid4().hex
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
    reaction_id = uuid.uuid4().hex
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
    conn.execute("DELETE FROM daily_suggestions WHERE profile_id=? AND date=?", (profile_id, today))
    for s in suggestions:
        sid = uuid.uuid4().hex
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
    totp_id = uuid.uuid4().hex
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
    sub_id = uuid.uuid4().hex
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
    msg_id = uuid.uuid4().hex
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
    return [dict(r) for r in reversed(rows)]


# ---------------------------------------------------------------------------
# Content Filter Log
# ---------------------------------------------------------------------------

def log_content_filter(content_type: str, content_id: str, profile_id: str,
                       flagged_text: str, reason: str, filter_type: str,
                       action: str = "censored") -> str:
    conn = get_db()
    log_id = uuid.uuid4().hex
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
            return False
    return True


# ---------------------------------------------------------------------------
# Analytics Events
# ---------------------------------------------------------------------------

def log_analytics_event(event_type: str, profile_id: str = None, metadata: str = None):
    conn = get_db()
    event_id = uuid.uuid4().hex
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


# ---------------------------------------------------------------------------
# Voice Messages
# ---------------------------------------------------------------------------

def save_voice_message(from_id: str, to_id: str, filename: str, duration_ms: int = 0) -> str:
    conn = get_db()
    msg_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO voice_messages (id, from_id, to_id, filename, duration_ms) VALUES (?,?,?,?,?)",
        (msg_id, from_id, to_id, filename, duration_ms),
    )
    conn.commit()
    return msg_id


def get_voice_messages(id_a: str, id_b: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM voice_messages
           WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)
           ORDER BY created_at ASC LIMIT ?""",
        (id_a, id_b, id_b, id_a, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Profile Prompts
# ---------------------------------------------------------------------------

def save_profile_prompt(profile_id: str, prompt: str, answer: str, sort_order: int = 0) -> str:
    conn = get_db()
    prompt_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO profile_prompts (id, profile_id, prompt, answer, sort_order) VALUES (?,?,?,?,?)",
        (prompt_id, profile_id, prompt, answer, sort_order),
    )
    conn.commit()
    return prompt_id


def get_profile_prompts(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM profile_prompts WHERE profile_id=? ORDER BY sort_order ASC",
        (profile_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_profile_prompt(prompt_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM profile_prompts WHERE id=? AND profile_id=?",
        (prompt_id, profile_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def update_profile_prompt(prompt_id: str, profile_id: str, answer: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "UPDATE profile_prompts SET answer=? WHERE id=? AND profile_id=?",
        (answer, prompt_id, profile_id),
    )
    conn.commit()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Super Likes
# ---------------------------------------------------------------------------

def create_super_like(from_id: str, to_id: str) -> str:
    conn = get_db()
    sl_id = uuid.uuid4().hex
    conn.execute(
        "INSERT OR IGNORE INTO super_likes (id, from_id, to_id) VALUES (?,?,?)",
        (sl_id, from_id, to_id),
    )
    conn.commit()
    return sl_id


def has_super_liked(from_id: str, to_id: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM super_likes WHERE from_id=? AND to_id=?",
        (from_id, to_id),
    ).fetchone()
    return row is not None


def get_super_likes_for(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT sl.*, p.name as from_name, p.photo as from_photo
           FROM super_likes sl
           JOIN profiles p ON p.id = sl.from_id
           WHERE sl.to_id = ?
           ORDER BY sl.created_at DESC""",
        (profile_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_super_like_count(profile_id: str) -> int:
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM super_likes WHERE to_id=?", (profile_id,)
    ).fetchone()
    return row["c"]


# ---------------------------------------------------------------------------
# Stories / Moments
# ---------------------------------------------------------------------------

def create_story(profile_id: str, content_type: str, content: str,
                 background: str = "#6c7086", photo: str = None,
                 expiry_hours: int = 24) -> str:
    conn = get_db()
    story_id = uuid.uuid4().hex
    conn.execute(
        """INSERT INTO stories (id, profile_id, content_type, content, background, photo, expires_at)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now', ? || ' hours'))""",
        (story_id, profile_id, content_type, content, background, photo, str(expiry_hours)),
    )
    conn.commit()
    return story_id


def get_stories_feed(profile_id: str) -> list[dict]:
    """Get active stories from friends and self."""
    conn = get_db()
    rows = conn.execute(
        """SELECT s.*, p.name, p.photo as author_photo,
                  (SELECT COUNT(*) FROM story_views sv WHERE sv.story_id = s.id) as view_count,
                  (SELECT 1 FROM story_views sv WHERE sv.story_id = s.id AND sv.viewer_id = ?) as viewed
           FROM stories s
           JOIN profiles p ON p.id = s.profile_id
           WHERE s.expires_at > datetime('now')
             AND (s.profile_id IN (
                 SELECT friend_id FROM profile_friends
                 WHERE profile_id=? AND status='accepted'
             ) OR s.profile_id = ?)
           ORDER BY s.created_at DESC""",
        (profile_id, profile_id, profile_id),
    ).fetchall()
    return [dict(r) for r in rows]


def get_story(story_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        """SELECT s.*, p.name, p.photo as author_photo
           FROM stories s JOIN profiles p ON p.id = s.profile_id
           WHERE s.id = ?""",
        (story_id,),
    ).fetchone()
    return dict(row) if row else None


def view_story(story_id: str, viewer_id: str):
    conn = get_db()
    view_id = uuid.uuid4().hex
    cursor = conn.execute(
        "INSERT OR IGNORE INTO story_views (id, story_id, viewer_id) VALUES (?,?,?)",
        (view_id, story_id, viewer_id),
    )
    if cursor.rowcount > 0:
        conn.execute(
            "UPDATE stories SET views = views + 1 WHERE id = ?", (story_id,)
        )
    conn.commit()


def delete_story(story_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM stories WHERE id=? AND profile_id=?", (story_id, profile_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def cleanup_expired_stories():
    """Remove expired stories."""
    conn = get_db()
    conn.execute("DELETE FROM stories WHERE expires_at <= datetime('now')")
    conn.commit()


def get_all_active_stories(limit: int = 100) -> list[dict]:
    """Admin: get all active stories."""
    conn = get_db()
    rows = conn.execute(
        """SELECT s.*, p.name, p.photo as author_photo
           FROM stories s JOIN profiles p ON p.id = s.profile_id
           WHERE s.expires_at > datetime('now')
           ORDER BY s.created_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Group Polls
# ---------------------------------------------------------------------------

def create_group_poll(group_id: str, profile_id: str, question: str, options: list[str]) -> str:
    conn = get_db()
    poll_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO group_polls (id, group_id, profile_id, question, options) VALUES (?,?,?,?,?)",
        (poll_id, group_id, profile_id, question, json.dumps(options)),
    )
    conn.commit()
    return poll_id


def get_group_polls(group_id: str, limit: int = 20) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT gp.*, p.name as author_name, p.photo as author_photo
           FROM group_polls gp
           JOIN profiles p ON p.id = gp.profile_id
           WHERE gp.group_id = ?
           ORDER BY gp.created_at DESC LIMIT ?""",
        (group_id, limit),
    ).fetchall()
    polls = []
    for r in rows:
        d = dict(r)
        d["options"] = json.loads(d["options"]) if d["options"] else []
        # Get vote counts
        votes = conn.execute(
            "SELECT option_index, COUNT(*) as c FROM poll_votes WHERE poll_id=? GROUP BY option_index",
            (d["id"],),
        ).fetchall()
        d["votes"] = {v["option_index"]: v["c"] for v in votes}
        d["total_votes"] = sum(v["c"] for v in votes)
        polls.append(d)
    return polls


def vote_poll(poll_id: str, profile_id: str, option_index: int) -> bool:
    conn = get_db()
    vote_id = uuid.uuid4().hex
    try:
        conn.execute(
            "INSERT INTO poll_votes (id, poll_id, profile_id, option_index) VALUES (?,?,?,?)",
            (vote_id, poll_id, profile_id, option_index),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_poll_user_vote(poll_id: str, profile_id: str) -> int | None:
    conn = get_db()
    row = conn.execute(
        "SELECT option_index FROM poll_votes WHERE poll_id=? AND profile_id=?",
        (poll_id, profile_id),
    ).fetchone()
    return row["option_index"] if row else None


# ---------------------------------------------------------------------------
# User Sessions
# ---------------------------------------------------------------------------

def create_session(user_id: str, token_hash: str, device: str = "", ip_address: str = "") -> str:
    conn = get_db()
    session_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO user_sessions (id, user_id, token_hash, device, ip_address) VALUES (?,?,?,?,?)",
        (session_id, user_id, token_hash, device, ip_address),
    )
    conn.commit()
    return session_id


def get_user_sessions(user_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, user_id, device, ip_address, last_active, created_at FROM user_sessions WHERE user_id=? ORDER BY last_active DESC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_sessions(limit: int = 200) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT us.id, us.user_id, us.device, us.ip_address, us.last_active, us.created_at,
                  u.email, u.display_name
           FROM user_sessions us
           JOIN users u ON u.id = us.user_id
           ORDER BY us.last_active DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def touch_session(session_id: str):
    conn = get_db()
    conn.execute(
        "UPDATE user_sessions SET last_active = datetime('now') WHERE id = ?",
        (session_id,),
    )
    conn.commit()


def revoke_session(session_id: str, user_id: str = None) -> bool:
    conn = get_db()
    if user_id:
        cursor = conn.execute(
            "DELETE FROM user_sessions WHERE id=? AND user_id=?",
            (session_id, user_id),
        )
    else:
        cursor = conn.execute("DELETE FROM user_sessions WHERE id=?", (session_id,))
    conn.commit()
    return cursor.rowcount > 0


def revoke_all_sessions(user_id: str, except_session_id: str = None):
    conn = get_db()
    if except_session_id:
        conn.execute(
            "DELETE FROM user_sessions WHERE user_id=? AND id != ?",
            (user_id, except_session_id),
        )
    else:
        conn.execute("DELETE FROM user_sessions WHERE user_id=?", (user_id,))
    conn.commit()


def get_session_count() -> int:
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as c FROM user_sessions").fetchone()
    return row["c"]


# ---------------------------------------------------------------------------
# User Location
# ---------------------------------------------------------------------------

def save_user_location(user_id: str, latitude: float = None, longitude: float = None,
                       city: str = "", radius_km: int = 100, enabled: bool = True):
    conn = get_db()
    conn.execute(
        """INSERT INTO user_locations (user_id, latitude, longitude, city, radius_km, enabled)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
           latitude=excluded.latitude, longitude=excluded.longitude,
           city=excluded.city, radius_km=excluded.radius_km,
           enabled=excluded.enabled, updated_at=datetime('now')""",
        (user_id, latitude, longitude, city, radius_km, int(enabled)),
    )
    conn.commit()


def get_user_location(user_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM user_locations WHERE user_id=?", (user_id,)
    ).fetchone()
    return dict(row) if row else None


def get_nearby_profiles(latitude: float, longitude: float, radius_km: int,
                        exclude_id: str = "", limit: int = 50) -> list[dict]:
    """Simple distance-based matching using Haversine approximation."""
    conn = get_db()
    # Rough degree-to-km approximation for bounding box
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * max(0.1, abs(math.cos(math.radians(latitude)))))
    rows = conn.execute(
        """SELECT p.*, ul.latitude as user_lat, ul.longitude as user_lon, ul.city as user_city
           FROM profiles p
           JOIN users u ON u.profile_id = p.id
           JOIN user_locations ul ON ul.user_id = u.id
           WHERE ul.enabled = 1
             AND ul.latitude BETWEEN ? AND ?
             AND ul.longitude BETWEEN ? AND ?
             AND p.id != ?
           LIMIT ?""",
        (latitude - lat_delta, latitude + lat_delta,
         longitude - lon_delta, longitude + lon_delta,
         exclude_id, limit),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_location_enabled_count() -> int:
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as c FROM user_locations WHERE enabled=1").fetchone()
    return row["c"]


# ---------------------------------------------------------------------------
# Recovery Codes (2FA backup)
# ---------------------------------------------------------------------------

def save_recovery_codes(user_id: str, code_hashes: list[str]):
    conn = get_db()
    # Clear old codes
    conn.execute("DELETE FROM recovery_codes WHERE user_id=?", (user_id,))
    for ch in code_hashes:
        code_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO recovery_codes (id, user_id, code_hash) VALUES (?,?,?)",
            (code_id, user_id, ch),
        )
    conn.commit()


def use_recovery_code(user_id: str, code_hash: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM recovery_codes WHERE user_id=? AND code_hash=? AND used=0",
        (user_id, code_hash),
    ).fetchone()
    if not row:
        return False
    conn.execute("UPDATE recovery_codes SET used=1 WHERE id=?", (row["id"],))
    conn.commit()
    return True


def get_recovery_code_count(user_id: str) -> int:
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM recovery_codes WHERE user_id=? AND used=0",
        (user_id,),
    ).fetchone()
    return row["c"]


# ---------------------------------------------------------------------------
# Incognito Mode
# ---------------------------------------------------------------------------

def set_incognito_mode(user_id: str, enabled: bool):
    conn = get_db()
    conn.execute(
        "UPDATE users SET incognito_mode=? WHERE id=?",
        (int(enabled), user_id),
    )
    conn.commit()


def is_incognito(user_id: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT incognito_mode FROM users WHERE id=?", (user_id,)
    ).fetchone()
    return bool(row and row["incognito_mode"])


# ---------------------------------------------------------------------------
# Mutual Friends
# ---------------------------------------------------------------------------

def get_mutual_friends(profile_a: str, profile_b: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT p.id, p.name, p.photo
           FROM profile_friends fa
           JOIN profile_friends fb ON fa.friend_id = fb.friend_id
           JOIN profiles p ON p.id = fa.friend_id
           WHERE fa.profile_id=? AND fb.profile_id=?
             AND fa.status='accepted' AND fb.status='accepted'""",
        (profile_a, profile_b),
    ).fetchall()
    return [dict(r) for r in rows]


def get_mutual_friend_count(profile_a: str, profile_b: str) -> int:
    conn = get_db()
    row = conn.execute(
        """SELECT COUNT(*) as c
           FROM profile_friends fa
           JOIN profile_friends fb ON fa.friend_id = fb.friend_id
           WHERE fa.profile_id=? AND fb.profile_id=?
             AND fa.status='accepted' AND fb.status='accepted'""",
        (profile_a, profile_b),
    ).fetchone()
    return row["c"]


# ---------------------------------------------------------------------------
# Message Search
# ---------------------------------------------------------------------------

def search_messages(profile_id: str, query: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    q = f"%{query}%"
    rows = conn.execute(
        """SELECT m.*, p_from.name as from_name, p_to.name as to_name
           FROM messages m
           LEFT JOIN profiles p_from ON p_from.id = m.from_id
           LEFT JOIN profiles p_to ON p_to.id = m.to_id
           WHERE (m.from_id=? OR m.to_id=?) AND m.content LIKE ?
           ORDER BY m.created_at DESC LIMIT ?""",
        (profile_id, profile_id, q, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Account Deletion (GDPR)
# ---------------------------------------------------------------------------

def delete_account(user_id: str) -> bool:
    conn = get_db()
    user = conn.execute("SELECT profile_id FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        return False
    conn.execute("BEGIN")
    try:
        profile_id = user["profile_id"]
        if profile_id:
            tables_with_profile = [
                ("messages", "from_id"), ("messages", "to_id"),
                ("profile_blog_posts", "profile_id"),
                ("profile_comments", "profile_id"), ("profile_comments", "from_id"),
                ("profile_friends", "profile_id"), ("profile_friends", "friend_id"),
                ("activity_feed", "profile_id"), ("status_updates", "profile_id"),
                ("likes", "from_id"), ("photos", "profile_id"),
                ("group_members", "profile_id"), ("group_posts", "profile_id"),
                ("behavioral_events", "profile_id"), ("safety_reports", "reporter_id"),
                ("voice_messages", "from_id"), ("voice_messages", "to_id"),
                ("profile_prompts", "profile_id"), ("super_likes", "from_id"),
                ("super_likes", "to_id"), ("stories", "profile_id"),
                ("story_views", "viewer_id"), ("group_messages", "from_id"),
                ("message_reactions", "profile_id"), ("daily_suggestions", "profile_id"),
                ("compat_games", "profile_a"), ("compat_games", "profile_b"),
                ("music_preferences", "profile_id"), ("blocks", "blocker_id"),
                ("blocks", "blocked_id"),
                ("icebreaker_games", "profile_a"), ("icebreaker_games", "profile_b"),
                ("game_turns", "profile_id"), ("shared_playlists", "profile_a"),
                ("shared_playlists", "profile_b"), ("playlist_songs", "added_by"),
                ("event_photos", "profile_id"), ("profile_badges", "profile_id"),
                ("story_reactions", "profile_id"), ("pinned_messages", "pinned_by"),
                ("passed_profiles", "profile_id"), ("passed_profiles", "passed_id"),
                ("blind_dates", "initiator_id"), ("blind_dates", "target_id"),
                ("date_schedules", "profile_a"), ("date_schedules", "profile_b"),
            ]
            for table, col in tables_with_profile:
                try:
                    conn.execute(f"DELETE FROM {table} WHERE {col}=?", (profile_id,))
                except sqlite3.OperationalError:
                    pass
            conn.execute("DELETE FROM profiles WHERE id=?", (profile_id,))
        user_tables = [
            "notifications", "notification_preferences", "refresh_tokens",
            "email_verifications", "totp_secrets", "push_subscriptions",
            "user_sessions", "user_locations", "recovery_codes",
            "premium_subscriptions", "questionnaire_progress",
            "safety_checkins",
        ]
        for table in user_tables:
            try:
                conn.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
            except sqlite3.OperationalError:
                pass
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return True


# ---------------------------------------------------------------------------
# Data Export (GDPR)
# ---------------------------------------------------------------------------

def export_user_data(user_id: str) -> dict:
    """Export all user data for GDPR compliance."""
    conn = get_db()
    user = conn.execute("SELECT id, email, display_name, created_at FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        return {}
    data = {"user": dict(user)}
    profile_id = conn.execute("SELECT profile_id FROM users WHERE id=?", (user_id,)).fetchone()
    pid = profile_id["profile_id"] if profile_id else None
    if pid:
        profile = conn.execute("SELECT * FROM profiles WHERE id=?", (pid,)).fetchone()
        if profile:
            data["profile"] = {k: v for k, v in dict(profile).items() if k != "embedding"}
        data["messages_sent"] = [dict(r) for r in conn.execute(
            "SELECT id, to_id, content, created_at FROM messages WHERE from_id=? ORDER BY created_at", (pid,)
        ).fetchall()]
        data["messages_received"] = [dict(r) for r in conn.execute(
            "SELECT id, from_id, content, created_at FROM messages WHERE to_id=? ORDER BY created_at", (pid,)
        ).fetchall()]
        data["friends"] = [dict(r) for r in conn.execute(
            "SELECT friend_id, status, created_at FROM profile_friends WHERE profile_id=?", (pid,)
        ).fetchall()]
        data["likes_given"] = [dict(r) for r in conn.execute(
            "SELECT target_type, target_id, reaction, created_at FROM likes WHERE from_id=?", (pid,)
        ).fetchall()]
        data["blog_posts"] = [dict(r) for r in conn.execute(
            "SELECT id, title, content, created_at FROM profile_blog_posts WHERE profile_id=?", (pid,)
        ).fetchall()]
        data["stories"] = [dict(r) for r in conn.execute(
            "SELECT id, content_type, content, created_at FROM stories WHERE profile_id=?", (pid,)
        ).fetchall()]
        data["prompts"] = [dict(r) for r in conn.execute(
            "SELECT prompt, answer FROM profile_prompts WHERE profile_id=?", (pid,)
        ).fetchall()]
    data["notifications"] = [dict(r) for r in conn.execute(
        "SELECT type, title, body, created_at FROM notifications WHERE user_id=? ORDER BY created_at", (user_id,)
    ).fetchall()]
    location = conn.execute("SELECT * FROM user_locations WHERE user_id=?", (user_id,)).fetchone()
    if location:
        data["location_settings"] = dict(location)
    return data


# ---------------------------------------------------------------------------
# Match Expiry
# ---------------------------------------------------------------------------

def get_expiring_matches(profile_id: str, expiry_days: int = 7) -> list[dict]:
    """Get matches that haven't been messaged within expiry_days."""
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM (
               SELECT l.target_id as match_id, l.created_at as matched_at,
                      p.name, p.photo,
                      (SELECT COUNT(*) FROM messages
                       WHERE (from_id=l.from_id AND to_id=l.target_id)
                          OR (from_id=l.target_id AND to_id=l.from_id)) as message_count,
                      ROUND(julianday('now') - julianday(l.created_at)) as days_since_match
               FROM likes l
               JOIN profiles p ON p.id = l.target_id
               WHERE l.from_id = ? AND l.target_type = 'profile'
                 AND l.created_at >= datetime('now', ? || ' days')
           ) WHERE message_count = 0
           ORDER BY matched_at ASC""",
        (profile_id, f"-{expiry_days}"),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Icebreaker Games
# ---------------------------------------------------------------------------

def create_icebreaker_game(profile_a: str, profile_b: str, game_type: str) -> dict:
    conn = get_db()
    game_id = uuid.uuid4().hex
    conn.execute("""
        INSERT INTO icebreaker_games (id, profile_a, profile_b, game_type, current_turn)
        VALUES (?, ?, ?, ?, ?)
    """, (game_id, profile_a, profile_b, game_type, profile_a))
    conn.commit()
    return {"id": game_id, "game_type": game_type, "status": "active", "current_turn": profile_a}


def get_icebreaker_game(game_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM icebreaker_games WHERE id=?", (game_id,)).fetchone()
    if not row:
        return None
    game = dict(row)
    turns = conn.execute(
        "SELECT * FROM game_turns WHERE game_id=? ORDER BY turn_number", (game_id,)
    ).fetchall()
    game["turns"] = [dict(t) for t in turns]
    return game


def submit_game_turn(game_id: str, profile_id: str, content: str) -> dict | None:
    conn = get_db()
    game = conn.execute("SELECT * FROM icebreaker_games WHERE id=?", (game_id,)).fetchone()
    if not game or game["status"] != "active" or game["current_turn"] != profile_id:
        return None
    turn_id = uuid.uuid4().hex
    turn_num = game["turn_count"] + 1
    next_turn = game["profile_b"] if profile_id == game["profile_a"] else game["profile_a"]
    conn.execute(
        "INSERT INTO game_turns (id, game_id, profile_id, content, turn_number) VALUES (?,?,?,?,?)",
        (turn_id, game_id, profile_id, content, turn_num),
    )
    new_status = "completed" if turn_num >= 20 and game["game_type"] == "20_questions" else "active"
    conn.execute(
        "UPDATE icebreaker_games SET current_turn=?, turn_count=?, status=? WHERE id=?",
        (next_turn, turn_num, new_status, game_id),
    )
    conn.commit()
    return {"turn_number": turn_num, "content": content, "next_turn": next_turn, "status": new_status}


def get_games_for_pair(profile_a: str, profile_b: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM icebreaker_games
        WHERE (profile_a=? AND profile_b=?) OR (profile_a=? AND profile_b=?)
        ORDER BY created_at DESC
    """, (profile_a, profile_b, profile_b, profile_a)).fetchall()
    return [dict(r) for r in rows]


def get_total_games_count() -> int:
    conn = get_db()
    return conn.execute("SELECT COUNT(*) FROM icebreaker_games").fetchone()[0]


# ---------------------------------------------------------------------------
# Date Scheduling
# ---------------------------------------------------------------------------

def create_date_schedule(profile_a: str, profile_b: str, scheduled_by: str,
                         date_date: str, date_time: str = None,
                         venue: str = None, notes: str = None) -> dict:
    conn = get_db()
    ds_id = uuid.uuid4().hex
    conn.execute("""
        INSERT INTO date_schedules (id, profile_a, profile_b, scheduled_by, date_date, date_time, venue, notes)
        VALUES (?,?,?,?,?,?,?,?)
    """, (ds_id, profile_a, profile_b, scheduled_by, date_date, date_time, venue, notes))
    conn.commit()
    return {"id": ds_id, "status": "proposed"}


def get_date_schedules(profile_a: str, profile_b: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM date_schedules
        WHERE (profile_a=? AND profile_b=?) OR (profile_a=? AND profile_b=?)
        ORDER BY date_date DESC
    """, (profile_a, profile_b, profile_b, profile_a)).fetchall()
    return [dict(r) for r in rows]


def get_date_schedule(ds_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM date_schedules WHERE id=?", (ds_id,)).fetchone()
    return dict(row) if row else None


def update_date_schedule_status(ds_id: str, status: str) -> bool:
    conn = get_db()
    cursor = conn.execute("UPDATE date_schedules SET status=? WHERE id=?", (status, ds_id))
    conn.commit()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Blind Dates
# ---------------------------------------------------------------------------

def create_blind_date(initiator_id: str, target_id: str, reveal_hours: int = 48) -> dict:
    conn = get_db()
    bd_id = uuid.uuid4().hex
    conn.execute("""
        INSERT OR IGNORE INTO blind_dates (id, initiator_id, target_id, reveal_at)
        VALUES (?, ?, ?, datetime('now', '+' || ? || ' hours'))
    """, (bd_id, initiator_id, target_id, str(reveal_hours)))
    conn.commit()
    return {"id": bd_id, "status": "active"}


def get_active_blind_dates(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT bd.*
        FROM blind_dates bd
        WHERE (bd.initiator_id=? OR bd.target_id=?) AND bd.status='active'
        ORDER BY bd.created_at DESC
    """, (profile_id, profile_id)).fetchall()
    return [dict(r) for r in rows]


def reveal_blind_dates():
    """Reveal blind dates past their reveal time."""
    conn = get_db()
    conn.execute(
        "UPDATE blind_dates SET revealed=1 WHERE reveal_at <= datetime('now') AND revealed=0"
    )
    conn.commit()


def get_blind_date_count() -> int:
    conn = get_db()
    return conn.execute("SELECT COUNT(*) FROM blind_dates WHERE status='active'").fetchone()[0]


# ---------------------------------------------------------------------------
# Second Look (Passed Profiles)
# ---------------------------------------------------------------------------

def pass_profile(profile_id: str, passed_id: str):
    conn = get_db()
    pp_id = uuid.uuid4().hex
    conn.execute(
        "INSERT OR IGNORE INTO passed_profiles (id, profile_id, passed_id) VALUES (?,?,?)",
        (pp_id, profile_id, passed_id),
    )
    conn.commit()


def get_passed_profiles(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT pp.passed_id, p.name, p.age, p.photo, pp.created_at as passed_at
        FROM passed_profiles pp
        JOIN profiles p ON p.id = pp.passed_id
        WHERE pp.profile_id = ?
        ORDER BY pp.created_at DESC
    """, (profile_id,)).fetchall()
    return [dict(r) for r in rows]


def reconsider_profile(profile_id: str, passed_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM passed_profiles WHERE profile_id=? AND passed_id=?",
        (profile_id, passed_id),
    )
    conn.commit()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Threaded Replies
# ---------------------------------------------------------------------------

def save_thread_reply(message_id: str, reply_to_id: str):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO threaded_replies (message_id, reply_to_id) VALUES (?,?)",
        (message_id, reply_to_id),
    )
    try:
        conn.execute("UPDATE messages SET reply_to=? WHERE id=?", (reply_to_id, message_id))
    except sqlite3.OperationalError:
        pass
    conn.commit()


def get_reply_context(message_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("""
        SELECT tr.reply_to_id, m.content as reply_to_content, m.from_id as reply_to_from,
               p.name as reply_to_name
        FROM threaded_replies tr
        JOIN messages m ON m.id = tr.reply_to_id
        JOIN profiles p ON p.id = m.from_id
        WHERE tr.message_id = ?
    """, (message_id,)).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Shared Playlists
# ---------------------------------------------------------------------------

def create_shared_playlist(profile_a: str, profile_b: str, name: str = "Our Playlist") -> dict:
    conn = get_db()
    pl_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO shared_playlists (id, profile_a, profile_b, name) VALUES (?,?,?,?)",
        (pl_id, profile_a, profile_b, name),
    )
    conn.commit()
    return {"id": pl_id, "name": name}


def get_shared_playlists(profile_a: str, profile_b: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM shared_playlists
        WHERE (profile_a=? AND profile_b=?) OR (profile_a=? AND profile_b=?)
        ORDER BY created_at DESC
    """, (profile_a, profile_b, profile_b, profile_a)).fetchall()
    return [dict(r) for r in rows]


def add_playlist_song(playlist_id: str, added_by: str, title: str, artist: str) -> dict:
    conn = get_db()
    song_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO playlist_songs (id, playlist_id, added_by, title, artist) VALUES (?,?,?,?,?)",
        (song_id, playlist_id, added_by, title, artist),
    )
    conn.commit()
    return {"id": song_id, "title": title, "artist": artist}


def get_playlist_songs(playlist_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT ps.*, p.name as added_by_name
        FROM playlist_songs ps JOIN profiles p ON p.id=ps.added_by
        WHERE ps.playlist_id=? ORDER BY ps.created_at
    """, (playlist_id,)).fetchall()
    return [dict(r) for r in rows]


def delete_playlist_song(song_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM playlist_songs WHERE id=? AND added_by=?", (song_id, profile_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def get_total_playlists_count() -> int:
    conn = get_db()
    return conn.execute("SELECT COUNT(*) FROM shared_playlists").fetchone()[0]


# ---------------------------------------------------------------------------
# Event Photos
# ---------------------------------------------------------------------------

def add_event_photo(event_id: str, profile_id: str, filename: str, caption: str = None) -> dict:
    conn = get_db()
    photo_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO event_photos (id, event_id, profile_id, filename, caption) VALUES (?,?,?,?,?)",
        (photo_id, event_id, profile_id, filename, caption),
    )
    conn.commit()
    return {"id": photo_id, "filename": filename}


def get_event_photos(event_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT ep.*, p.name as uploaded_by FROM event_photos ep
        JOIN profiles p ON p.id = ep.profile_id
        WHERE ep.event_id=? ORDER BY ep.created_at
    """, (event_id,)).fetchall()
    return [dict(r) for r in rows]


def delete_event_photo(photo_id: str, profile_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM event_photos WHERE id=? AND profile_id=?", (photo_id, profile_id)
    )
    conn.commit()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Profile Badges
# ---------------------------------------------------------------------------

BADGE_TYPES = {
    "verified": "Verified",
    "early_adopter": "Early Adopter",
    "conversation_starter": "Conversation Starter",
    "frequent_matcher": "Frequent Matcher",
    "event_host": "Event Host",
}


def award_badge(profile_id: str, badge_type: str) -> bool:
    if badge_type not in BADGE_TYPES:
        return False
    conn = get_db()
    badge_id = uuid.uuid4().hex
    try:
        conn.execute(
            "INSERT INTO profile_badges (id, profile_id, badge_type) VALUES (?,?,?)",
            (badge_id, profile_id, badge_type),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_badges(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT badge_type, awarded_at FROM profile_badges WHERE profile_id=?", (profile_id,)
    ).fetchall()
    return [{"type": r["badge_type"], "label": BADGE_TYPES.get(r["badge_type"], r["badge_type"]),
             "awarded_at": r["awarded_at"]} for r in rows]


def check_and_award_badges(profile_id: str):
    """Auto-award badges based on activity."""
    conn = get_db()
    msg_count = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE from_id=?", (profile_id,)
    ).fetchone()[0]
    if msg_count >= 50:
        award_badge(profile_id, "conversation_starter")
    match_count = conn.execute(
        "SELECT COUNT(*) FROM likes WHERE from_id=? AND target_type='profile'", (profile_id,)
    ).fetchone()[0]
    if match_count >= 10:
        award_badge(profile_id, "frequent_matcher")
    event_count = conn.execute(
        "SELECT COUNT(*) FROM events WHERE creator_id=?", (profile_id,)
    ).fetchone()[0]
    if event_count >= 1:
        award_badge(profile_id, "event_host")


# ---------------------------------------------------------------------------
# Story Reactions
# ---------------------------------------------------------------------------

def react_to_story(story_id: str, profile_id: str, reaction: str) -> bool:
    conn = get_db()
    sr_id = uuid.uuid4().hex
    try:
        conn.execute(
            "INSERT OR REPLACE INTO story_reactions (id, story_id, profile_id, reaction) VALUES (?,?,?,?)",
            (sr_id, story_id, profile_id, reaction),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_story_reactions(story_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT sr.reaction, sr.profile_id, p.name
        FROM story_reactions sr JOIN profiles p ON p.id = sr.profile_id
        WHERE sr.story_id=?
    """, (story_id,)).fetchall()
    return [dict(r) for r in rows]


def get_story_reaction_counts(story_id: str) -> dict:
    conn = get_db()
    rows = conn.execute(
        "SELECT reaction, COUNT(*) as count FROM story_reactions WHERE story_id=? GROUP BY reaction",
        (story_id,),
    ).fetchall()
    return {r["reaction"]: r["count"] for r in rows}


# ---------------------------------------------------------------------------
# Pinned Messages
# ---------------------------------------------------------------------------

def pin_message(message_id: str, pinned_by: str, conversation_key: str) -> bool:
    conn = get_db()
    pin_id = uuid.uuid4().hex
    try:
        conn.execute(
            "INSERT INTO pinned_messages (id, message_id, pinned_by, conversation_key) VALUES (?,?,?,?)",
            (pin_id, message_id, pinned_by, conversation_key),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def unpin_message(message_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute("DELETE FROM pinned_messages WHERE message_id=?", (message_id,))
    conn.commit()
    return cursor.rowcount > 0


def get_pinned_messages(conversation_key: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT pm.*, m.content, m.from_id, p.name as from_name
        FROM pinned_messages pm
        JOIN messages m ON m.id = pm.message_id
        JOIN profiles p ON p.id = m.from_id
        WHERE pm.conversation_key=?
        ORDER BY pm.created_at DESC LIMIT 10
    """, (conversation_key,)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Message Cooldowns
# ---------------------------------------------------------------------------

def check_message_cooldown(from_id: str, to_id: str, max_count: int = 10,
                           window_minutes: int = 5) -> bool:
    """Returns True if within cooldown limit (OK to send), False if rate limited."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM message_cooldowns WHERE from_id=? AND to_id=?",
        (from_id, to_id),
    ).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO message_cooldowns (id, from_id, to_id) VALUES (?,?,?)",
            (uuid.uuid4().hex, from_id, to_id),
        )
        conn.commit()
        return True
    from datetime import datetime as dt, timezone as tz, timedelta as td
    window_start = row["window_start"]
    try:
        ws = dt.fromisoformat(window_start.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        ws = dt.now(tz.utc) - td(hours=1)
    now = dt.now(tz.utc)
    if (now - ws).total_seconds() > window_minutes * 60:
        conn.execute(
            "UPDATE message_cooldowns SET message_count=1, window_start=? WHERE from_id=? AND to_id=?",
            (now.isoformat(), from_id, to_id),
        )
        conn.commit()
        return True
    if row["message_count"] >= max_count:
        return False
    conn.execute(
        "UPDATE message_cooldowns SET message_count=message_count+1 WHERE from_id=? AND to_id=?",
        (from_id, to_id),
    )
    conn.commit()
    return True


# ---------------------------------------------------------------------------
# Undo Blocks
# ---------------------------------------------------------------------------

def create_undo_block(blocker_id: str, blocked_id: str, grace_minutes: int = 5) -> str:
    conn = get_db()
    ub_id = uuid.uuid4().hex
    conn.execute("""
        INSERT INTO undo_blocks (id, blocker_id, blocked_id, expires_at)
        VALUES (?, ?, ?, datetime('now', '+' || ? || ' minutes'))
    """, (ub_id, blocker_id, blocked_id, str(grace_minutes)))
    conn.commit()
    return ub_id


def undo_block(blocker_id: str, blocked_id: str) -> bool:
    """Undo a block if within grace period."""
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM undo_blocks WHERE blocker_id=? AND blocked_id=? AND expires_at > datetime('now')",
        (blocker_id, blocked_id),
    ).fetchone()
    if not row:
        return False
    conn.execute("DELETE FROM undo_blocks WHERE id=?", (row["id"],))
    conn.execute("DELETE FROM blocks WHERE blocker_id=? AND blocked_id=?", (blocker_id, blocked_id))
    conn.commit()
    return True


def cleanup_expired_undo_blocks():
    conn = get_db()
    conn.execute("DELETE FROM undo_blocks WHERE expires_at <= datetime('now')")
    conn.commit()


# ---------------------------------------------------------------------------
# Safety Check-ins
# ---------------------------------------------------------------------------

def create_safety_checkin(user_id: str, partner_name: str, emergency_contact: str,
                          emergency_email: str, check_in_minutes: int = 60,
                          date_schedule_id: str = None) -> dict:
    conn = get_db()
    sc_id = uuid.uuid4().hex
    conn.execute("""
        INSERT INTO safety_checkins (id, user_id, date_schedule_id, partner_name,
                                     emergency_contact, emergency_email, check_in_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now', '+' || ? || ' minutes'))
    """, (sc_id, user_id, date_schedule_id, partner_name, emergency_contact,
          emergency_email, str(check_in_minutes)))
    conn.commit()
    return {"id": sc_id, "status": "pending"}


def respond_safety_checkin(checkin_id: str, user_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "UPDATE safety_checkins SET status='safe' WHERE id=? AND user_id=? AND status='pending'",
        (checkin_id, user_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def get_overdue_checkins() -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM safety_checkins
        WHERE status='pending' AND check_in_at <= datetime('now')
    """).fetchall()
    return [dict(r) for r in rows]


def get_user_checkins(user_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM safety_checkins WHERE user_id=? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_total_checkins_count() -> int:
    conn = get_db()
    return conn.execute("SELECT COUNT(*) FROM safety_checkins").fetchone()[0]


# ---------------------------------------------------------------------------
# Dealbreaker Warnings
# ---------------------------------------------------------------------------

def get_shared_dealbreakers(profile_id: str, target_id: str) -> list[dict]:
    """Get shared dealbreaker values between two profiles."""
    conn = get_db()
    p1 = conn.execute("SELECT dealbreakers FROM profiles WHERE id=?", (profile_id,)).fetchone()
    p2 = conn.execute("SELECT dealbreakers FROM profiles WHERE id=?", (target_id,)).fetchone()
    if not p1 or not p2:
        return []
    try:
        d1 = json.loads(p1["dealbreakers"]) if p1["dealbreakers"] else []
        d2 = json.loads(p2["dealbreakers"]) if p2["dealbreakers"] else []
    except (json.JSONDecodeError, TypeError):
        return []
    warnings = []
    if isinstance(d1, list) and isinstance(d2, list):
        for item in set(d1) & set(d2):
            warnings.append({"topic": item, "type": "shared_dealbreaker"})
    return warnings


# ---------------------------------------------------------------------------
# Profile Completeness
# ---------------------------------------------------------------------------

def get_profile_completeness(profile_id: str, user_id: str) -> dict:
    conn = get_db()
    profile = conn.execute("SELECT * FROM profiles WHERE id=?", (profile_id,)).fetchone()
    if not profile:
        return {"score": 0, "tips": []}
    score = 0
    tips = []
    if profile["photo"]:
        score += 20
    else:
        tips.append({"action": "Add a profile photo", "points": 20})
    try:
        about = profile["about_me"]
    except (IndexError, KeyError):
        about = None
    if about:
        score += 15
    else:
        tips.append({"action": "Write an About Me", "points": 15})
    prompt_count = conn.execute(
        "SELECT COUNT(*) FROM profile_prompts WHERE profile_id=?", (profile_id,)
    ).fetchone()[0]
    if prompt_count > 0:
        score += 15
    else:
        tips.append({"action": "Answer profile prompts", "points": 15})
    if profile["big_five"] and profile["big_five"] != "{}":
        score += 25
    else:
        tips.append({"action": "Complete the questionnaire", "points": 25})
    try:
        interests = profile["interests"]
    except (IndexError, KeyError):
        interests = None
    if interests:
        score += 10
    else:
        tips.append({"action": "Add your interests", "points": 10})
    verified = conn.execute(
        "SELECT status FROM selfie_verifications WHERE profile_id=?", (profile_id,)
    ).fetchone()
    if verified and verified["status"] == "approved":
        score += 15
    else:
        tips.append({"action": "Get verified", "points": 15})
    return {"score": min(score, 100), "tips": tips}


# ---------------------------------------------------------------------------
# Rate Limit Logging
# ---------------------------------------------------------------------------

def log_rate_limit_hit(endpoint: str, ip_address: str = None,
                       user_id: str = None, blocked: bool = False):
    conn = get_db()
    conn.execute(
        "INSERT INTO rate_limit_log (id, endpoint, ip_address, user_id, blocked) VALUES (?,?,?,?,?)",
        (uuid.uuid4().hex, endpoint, ip_address, user_id, 1 if blocked else 0),
    )
    conn.commit()


def get_rate_limit_stats() -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT endpoint,
               COUNT(*) as total_hits,
               SUM(CASE WHEN blocked=1 THEN 1 ELSE 0 END) as blocked_count,
               COUNT(DISTINCT ip_address) as unique_ips
        FROM rate_limit_log
        WHERE created_at >= datetime('now', '-24 hours')
        GROUP BY endpoint
        ORDER BY total_hits DESC
    """).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Database Vacuum
# ---------------------------------------------------------------------------

def run_vacuum() -> dict:
    import os as _os
    conn = get_db()
    db_size_before = _os.path.getsize(str(DB_PATH))
    conn.execute("VACUUM")
    db_size_after = _os.path.getsize(str(DB_PATH))
    conn.execute(
        "INSERT INTO vacuum_log (db_size_bytes) VALUES (?)",
        (db_size_after,),
    )
    conn.commit()
    return {"size_before": db_size_before, "size_after": db_size_after,
            "freed": db_size_before - db_size_after}


def get_last_vacuum() -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM vacuum_log ORDER BY ran_at DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def get_webhook_delivery_count() -> int:
    conn = get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM webhooks WHERE enabled=1").fetchone()[0]
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Availability Status
# ---------------------------------------------------------------------------

def set_availability(profile_id: str, status: str, custom_text: str = None, available_until: str = None):
    conn = get_db()
    conn.execute("""
        INSERT INTO availability_status (profile_id, status, custom_text, available_until, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(profile_id) DO UPDATE SET
            status=excluded.status, custom_text=excluded.custom_text,
            available_until=excluded.available_until, updated_at=datetime('now')
    """, (profile_id, status, custom_text, available_until))
    conn.commit()


def get_availability(profile_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM availability_status WHERE profile_id=?", (profile_id,)).fetchone()
    return dict(row) if row else None


def get_available_profiles(status: str = None) -> list[dict]:
    conn = get_db()
    if status:
        rows = conn.execute(
            "SELECT * FROM availability_status WHERE status=? ORDER BY updated_at DESC",
            (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM availability_status ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Conversation Starters
# ---------------------------------------------------------------------------

def generate_starters(from_id: str, to_id: str, from_profile: dict, to_profile: dict) -> list[dict]:
    """Generate personalized conversation starters based on shared traits."""
    import json as _json
    starters = []
    conn = get_db()

    # Shared music
    from_music = conn.execute(
        "SELECT song_title, artist FROM music_preferences WHERE profile_id=?", (from_id,)
    ).fetchall()
    to_music = conn.execute(
        "SELECT song_title, artist FROM music_preferences WHERE profile_id=?", (to_id,)
    ).fetchall()
    from_artists = {r["artist"].lower() for r in from_music}
    to_artists = {r["artist"].lower() for r in to_music}
    shared_artists = from_artists & to_artists
    if shared_artists:
        artist = next(iter(shared_artists)).title()
        starters.append({
            "type": "music",
            "content": f"You both listen to {artist}! What's your favorite song by them?"
        })

    # Shared interests
    from_interests = (from_profile.get("interests") or "").lower().split(",")
    to_interests = (to_profile.get("interests") or "").lower().split(",")
    from_set = {i.strip() for i in from_interests if i.strip()}
    to_set = {i.strip() for i in to_interests if i.strip()}
    shared = from_set & to_set
    if shared:
        interest = next(iter(shared)).title()
        starters.append({
            "type": "interest",
            "content": f"You're both into {interest}! How did you get started with that?"
        })

    # Communication style match
    from_comm = from_profile.get("communication_style")
    to_comm = to_profile.get("communication_style")
    if from_comm and to_comm:
        try:
            fc = _json.loads(from_comm) if isinstance(from_comm, str) else from_comm
            tc = _json.loads(to_comm) if isinstance(to_comm, str) else to_comm
            if fc.get("love_language") == tc.get("love_language"):
                ll = fc.get("love_language", "").replace("_", " ").title()
                starters.append({
                    "type": "compatibility",
                    "content": f"You both value {ll} — what does that look like in your ideal relationship?"
                })
        except (ValueError, TypeError, AttributeError):
            pass

    # Prompts-based
    from_prompts = conn.execute(
        "SELECT prompt, answer FROM profile_prompts WHERE profile_id=? LIMIT 3", (from_id,)
    ).fetchall()
    to_prompts = conn.execute(
        "SELECT prompt, answer FROM profile_prompts WHERE profile_id=? LIMIT 3", (to_id,)
    ).fetchall()
    if to_prompts:
        p = to_prompts[0]
        starters.append({
            "type": "prompt",
            "content": f"I loved your answer to \"{p['prompt']}\" — tell me more!"
        })

    # Generic fallbacks
    if len(starters) < 2:
        defaults = [
            {"type": "general", "content": "What's the best thing that happened to you this week?"},
            {"type": "general", "content": "If you could travel anywhere tomorrow, where would you go?"},
            {"type": "general", "content": "What's something you're passionate about that most people don't know?"},
        ]
        for d in defaults:
            if len(starters) >= 3:
                break
            starters.append(d)

    # Save generated starters
    for s in starters[:3]:
        conn.execute(
            "INSERT INTO conversation_starters (id, from_id, to_id, starter_type, content) VALUES (?,?,?,?,?)",
            (uuid.uuid4().hex, from_id, to_id, s["type"], s["content"])
        )
    conn.commit()
    return starters[:3]


def get_starters(from_id: str, to_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM conversation_starters WHERE from_id=? AND to_id=? ORDER BY created_at DESC LIMIT 3",
        (from_id, to_id)
    ).fetchall()
    return [dict(r) for r in rows]


def mark_starter_used(starter_id: str):
    conn = get_db()
    conn.execute("UPDATE conversation_starters SET used=1 WHERE id=?", (starter_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Date Feedback
# ---------------------------------------------------------------------------

def submit_date_feedback(date_schedule_id: str, profile_id: str, partner_id: str,
                         felt_safe: bool, had_fun: bool, accurate_match: bool,
                         would_meet_again: bool = None, notes: str = None) -> str:
    conn = get_db()
    fid = uuid.uuid4().hex
    conn.execute("""
        INSERT INTO date_feedback (id, date_schedule_id, profile_id, partner_id,
            felt_safe, had_fun, accurate_match, would_meet_again, notes)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (fid, date_schedule_id, profile_id, partner_id,
          1 if felt_safe else 0, 1 if had_fun else 0,
          1 if accurate_match else 0,
          1 if would_meet_again else (0 if would_meet_again is not None else None),
          notes))
    conn.commit()
    return fid


def get_date_feedback(date_schedule_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM date_feedback WHERE date_schedule_id=? ORDER BY created_at",
        (date_schedule_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_feedback_stats(profile_id: str) -> dict:
    conn = get_db()
    row = conn.execute("""
        SELECT COUNT(*) as total,
               AVG(felt_safe) as avg_safe,
               AVG(had_fun) as avg_fun,
               AVG(accurate_match) as avg_accurate,
               SUM(CASE WHEN would_meet_again=1 THEN 1 ELSE 0 END) as meet_again_count
        FROM date_feedback WHERE partner_id=?
    """, (profile_id,)).fetchone()
    return dict(row) if row else {"total": 0}


# ---------------------------------------------------------------------------
# Unread Message Counts
# ---------------------------------------------------------------------------

def get_unread_counts(profile_id: str) -> dict:
    """Get total unread messages and per-conversation unread counts."""
    conn = get_db()
    total = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE to_id=? AND read=0",
        (profile_id,)
    ).fetchone()[0]
    per_conv = conn.execute("""
        SELECT from_id, COUNT(*) as unread
        FROM messages WHERE to_id=? AND read=0
        GROUP BY from_id
    """, (profile_id,)).fetchall()
    return {
        "total": total,
        "per_conversation": {r["from_id"]: r["unread"] for r in per_conv}
    }


# ---------------------------------------------------------------------------
# Admin: User Search & Detail
# ---------------------------------------------------------------------------

def search_users(query: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    pattern = f"%{query}%"
    rows = conn.execute("""
        SELECT u.id, u.email, u.display_name, u.profile_id, u.is_admin,
               u.created_at, u.deactivated, u.email_verified,
               u.subscription_tier, u.onboarding_completed,
               p.name as profile_name, p.age, p.gender, p.verified,
               p.profile_views, p.last_active
        FROM users u
        LEFT JOIN profiles p ON u.profile_id = p.id
        WHERE u.email LIKE ? OR u.display_name LIKE ? OR p.name LIKE ? OR u.id = ?
        ORDER BY u.created_at DESC
        LIMIT ?
    """, (pattern, pattern, pattern, query, limit)).fetchall()
    return [dict(r) for r in rows]


def get_user_detail(user_id: str) -> dict | None:
    conn = get_db()
    user = conn.execute("""
        SELECT u.*, p.name as profile_name, p.age, p.gender, p.seeking,
               p.verified, p.profile_views, p.last_active, p.created_at as profile_created,
               p.deactivated as profile_deactivated, p.location, p.headline
        FROM users u
        LEFT JOIN profiles p ON u.profile_id = p.id
        WHERE u.id = ?
    """, (user_id,)).fetchone()
    if not user:
        return None
    d = dict(user)
    d.pop("password_hash", None)
    pid = d.get("profile_id")

    # Message stats
    if pid:
        d["messages_sent"] = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE from_id=?", (pid,)
        ).fetchone()[0]
        d["messages_received"] = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE to_id=?", (pid,)
        ).fetchone()[0]
        d["matches_count"] = conn.execute("""
            SELECT COUNT(*) FROM likes l1
            JOIN likes l2 ON l1.target_id = l2.from_id AND l1.from_id = l2.target_id
            WHERE l1.from_id=? AND l1.target_type='profile' AND l2.target_type='profile'
        """, (pid,)).fetchone()[0]
        d["reports_filed"] = conn.execute(
            "SELECT COUNT(*) FROM safety_reports WHERE reporter_id=?", (pid,)
        ).fetchone()[0]
        d["reports_received"] = conn.execute(
            "SELECT COUNT(*) FROM safety_reports WHERE reported_id=?", (pid,)
        ).fetchone()[0]
        d["blocks_made"] = conn.execute(
            "SELECT COUNT(*) FROM blocks WHERE blocker_id=?", (pid,)
        ).fetchone()[0]
        d["photos_count"] = conn.execute(
            "SELECT COUNT(*) FROM photos WHERE profile_id=?", (pid,)
        ).fetchone()[0]

    # Session count
    d["active_sessions"] = conn.execute(
        "SELECT COUNT(*) FROM user_sessions WHERE user_id=?", (user_id,)
    ).fetchone()[0]

    # Login history (recent sessions)
    sessions = conn.execute(
        "SELECT device, ip_address, last_active, created_at FROM user_sessions WHERE user_id=? ORDER BY last_active DESC LIMIT 10",
        (user_id,)
    ).fetchall()
    d["recent_sessions"] = [dict(s) for s in sessions]

    return d


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------

def create_announcement(title: str, body: str, ann_type: str, created_by: str, expires_at: str = None) -> str:
    conn = get_db()
    aid = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO announcements (id, title, body, type, created_by, expires_at) VALUES (?,?,?,?,?,?)",
        (aid, title, body, ann_type, created_by, expires_at)
    )
    conn.commit()
    return aid


def get_active_announcements() -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM announcements
        WHERE active=1 AND (expires_at IS NULL OR expires_at > datetime('now'))
        ORDER BY created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


def deactivate_announcement(ann_id: str) -> bool:
    conn = get_db()
    conn.execute("UPDATE announcements SET active=0 WHERE id=?", (ann_id,))
    conn.commit()
    return True


def get_total_date_feedback_count() -> int:
    conn = get_db()
    return conn.execute("SELECT COUNT(*) FROM date_feedback").fetchone()[0]


# ---------------------------------------------------------------------------
# Dealbreaker Quiz Comparison
# ---------------------------------------------------------------------------

def get_dealbreaker_comparison(profile_id_1: str, profile_id_2: str) -> dict:
    """Compare dealbreaker answers between two profiles."""
    conn = get_db()
    p1 = conn.execute("SELECT dealbreakers FROM profiles WHERE id=?", (profile_id_1,)).fetchone()
    p2 = conn.execute("SELECT dealbreakers FROM profiles WHERE id=?", (profile_id_2,)).fetchone()

    try:
        d1 = json.loads(p1["dealbreakers"]) if p1 and p1["dealbreakers"] else []
        d2 = json.loads(p2["dealbreakers"]) if p2 and p2["dealbreakers"] else []
    except (json.JSONDecodeError, TypeError):
        d1, d2 = [], []

    set1 = set(d1) if isinstance(d1, list) else set()
    set2 = set(d2) if isinstance(d2, list) else set()

    shared = [
        {"question": item, "answer_1": item, "answer_2": item}
        for item in sorted(set1 & set2)
    ]
    conflicts = []  # Both flagged same topic — already captured in shared
    profile_1_only = [
        {"question": item, "answer_1": item, "answer_2": None}
        for item in sorted(set1 - set2)
    ]
    profile_2_only = [
        {"question": item, "answer_1": None, "answer_2": item}
        for item in sorted(set2 - set1)
    ]

    return {
        "shared": shared,
        "conflicts": conflicts,
        "profile_1_only": profile_1_only,
        "profile_2_only": profile_2_only,
    }


# ---------------------------------------------------------------------------
# Paginated Feed & Conversations
# ---------------------------------------------------------------------------

def get_activity_feed_paginated(profile_id: str, offset: int = 0,
                                limit: int = 20) -> list[dict]:
    """Get activity feed with LIMIT/OFFSET pagination."""
    conn = get_db()
    rows = conn.execute(
        """SELECT a.*, p.name, p.photo FROM activity_feed a
           JOIN profiles p ON p.id = a.profile_id
           WHERE a.profile_id IN (
               SELECT friend_id FROM profile_friends
               WHERE profile_id=? AND status='accepted'
           ) OR a.profile_id=?
           ORDER BY a.created_at DESC LIMIT ? OFFSET ?""",
        (profile_id, profile_id, limit, offset)
    ).fetchall()
    return [dict(r) for r in rows]


def get_conversations_paginated(profile_id: str, offset: int = 0,
                                limit: int = 20) -> list[dict]:
    """Get conversations list with LIMIT/OFFSET pagination."""
    conn = get_db()
    rows = conn.execute("""
        SELECT m.content as last_message, m.from_id as last_sender,
               m.created_at as last_time, latest.partner_id,
               (SELECT COUNT(*) FROM messages
                WHERE from_id=latest.partner_id AND to_id=? AND read=0) as unread
        FROM messages m
        INNER JOIN (
            SELECT
                CASE WHEN from_id=? THEN to_id ELSE from_id END as partner_id,
                MAX(created_at) as max_created
            FROM messages WHERE from_id=? OR to_id=?
            GROUP BY partner_id
        ) latest ON (
            ((m.from_id=? AND m.to_id=latest.partner_id) OR (m.from_id=latest.partner_id AND m.to_id=?))
            AND m.created_at = latest.max_created
        )
        ORDER BY m.created_at DESC
        LIMIT ? OFFSET ?
    """, (profile_id, profile_id, profile_id, profile_id,
          profile_id, profile_id, limit, offset)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Compatibility History
# ---------------------------------------------------------------------------

def record_compatibility_snapshot(pid1: str, pid2: str, overall: float,
                                  dimensions_json: str) -> str:
    conn = get_db()
    rec_id = uuid.uuid4().hex
    conn.execute(
        """INSERT INTO compatibility_history
           (id, profile_id_1, profile_id_2, overall_score, dimension_scores)
           VALUES (?, ?, ?, ?, ?)""",
        (rec_id, pid1, pid2, overall, dimensions_json),
    )
    conn.commit()
    return rec_id


def get_compatibility_history(pid1: str, pid2: str,
                               limit: int = 10) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM compatibility_history
           WHERE (profile_id_1=? AND profile_id_2=?)
              OR (profile_id_1=? AND profile_id_2=?)
           ORDER BY recorded_at DESC LIMIT ?""",
        (pid1, pid2, pid2, pid1, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Endorsements
# ---------------------------------------------------------------------------

def add_endorsement(endorser_id: str, endorsed_id: str, trait: str) -> str:
    conn = get_db()
    eid = uuid.uuid4().hex
    conn.execute(
        """INSERT OR IGNORE INTO endorsements (id, endorser_id, endorsed_id, trait)
           VALUES (?, ?, ?, ?)""",
        (eid, endorser_id, endorsed_id, trait),
    )
    conn.commit()
    return eid


def get_endorsements(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT trait, COUNT(*) as count
           FROM endorsements WHERE endorsed_id=?
           GROUP BY trait ORDER BY count DESC""",
        (profile_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_endorsement_count(profile_id: str) -> int:
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM endorsements WHERE endorsed_id=?",
        (profile_id,),
    ).fetchone()
    return row["cnt"] if row else 0


# ---------------------------------------------------------------------------
# Group Post Reactions
# ---------------------------------------------------------------------------

def add_group_post_reaction(post_id: str, profile_id: str, emoji: str) -> str:
    conn = get_db()
    rid = uuid.uuid4().hex
    conn.execute(
        """INSERT OR IGNORE INTO group_post_reactions (id, post_id, profile_id, emoji)
           VALUES (?, ?, ?, ?)""",
        (rid, post_id, profile_id, emoji),
    )
    conn.commit()
    return rid


def remove_group_post_reaction(post_id: str, profile_id: str, emoji: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM group_post_reactions WHERE post_id=? AND profile_id=? AND emoji=?",
        (post_id, profile_id, emoji),
    )
    conn.commit()
    return cursor.rowcount > 0


def get_group_post_reactions(post_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT emoji, profile_id, created_at FROM group_post_reactions WHERE post_id=?",
        (post_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Event Messages
# ---------------------------------------------------------------------------

def send_event_message(event_id: str, sender_id: str, content: str) -> str:
    conn = get_db()
    msg_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO event_messages (id, event_id, sender_id, content) VALUES (?, ?, ?, ?)",
        (msg_id, event_id, sender_id, content),
    )
    conn.commit()
    return msg_id


def get_event_messages(event_id: str, limit: int = 50,
                        offset: int = 0) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT em.*, p.name as sender_name, p.photo as sender_photo
           FROM event_messages em
           JOIN profiles p ON p.id = em.sender_id
           WHERE em.event_id=?
           ORDER BY em.created_at ASC LIMIT ? OFFSET ?""",
        (event_id, limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Read Receipts Toggle
# ---------------------------------------------------------------------------

def set_read_receipts_enabled(profile_id: str, enabled: bool) -> None:
    conn = get_db()
    val = 1 if enabled else 0
    conn.execute(
        """INSERT INTO notification_preferences (user_id, read_receipts_enabled)
           VALUES (?, ?)
           ON CONFLICT(user_id) DO UPDATE SET read_receipts_enabled=excluded.read_receipts_enabled""",
        (profile_id, val),
    )
    conn.commit()


def get_read_receipts_enabled(profile_id: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT read_receipts_enabled FROM notification_preferences WHERE user_id=?",
        (profile_id,),
    ).fetchone()
    if not row:
        return True
    val = row["read_receipts_enabled"]
    return bool(val) if val is not None else True


# ---------------------------------------------------------------------------
# Slow Reveal
# ---------------------------------------------------------------------------

def get_reveal_stage(viewer_id: str, target_id: str) -> int:
    conn = get_db()
    row = conn.execute(
        "SELECT stage FROM profile_reveal_stages WHERE viewer_id=? AND target_id=?",
        (viewer_id, target_id),
    ).fetchone()
    return row["stage"] if row else 0


def advance_reveal_stage(viewer_id: str, target_id: str) -> int:
    conn = get_db()
    current = get_reveal_stage(viewer_id, target_id)
    if current >= 3:
        return 3
    new_stage = current + 1
    rid = uuid.uuid4().hex
    conn.execute(
        """INSERT INTO profile_reveal_stages (id, viewer_id, target_id, stage)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(viewer_id, target_id) DO UPDATE SET stage=excluded.stage,
           unlocked_at=datetime('now')""",
        (rid, viewer_id, target_id, new_stage),
    )
    conn.commit()
    return new_stage


def get_revealed_profile(target_id: str, stage: int) -> dict:
    profile = get_profile(target_id)
    if not profile:
        return {}
    # Stage 0: name, age, bio only
    base = {"id": profile["id"], "name": profile["name"], "age": profile.get("age")}
    bio = profile.get("about_me") or profile.get("headline") or ""
    base["bio"] = bio
    if stage < 1:
        return base
    # Stage 1: + interests, prompts
    base["interests"] = profile.get("interests")
    base["open_ended"] = profile.get("open_ended", {})
    prompts = get_profile_prompts(target_id)
    base["prompts"] = prompts
    if stage < 2:
        return base
    # Stage 2: + photos
    base["photo"] = profile.get("photo")
    photos = get_photos(target_id)
    base["photos"] = photos
    if stage < 3:
        return base
    # Stage 3: full profile
    return profile


# ---------------------------------------------------------------------------
# Shared Interests
# ---------------------------------------------------------------------------

def get_shared_interests(pid1: str, pid2: str) -> dict:
    conn = get_db()
    p1 = conn.execute("SELECT interests FROM profiles WHERE id=?", (pid1,)).fetchone()
    p2 = conn.execute("SELECT interests FROM profiles WHERE id=?", (pid2,)).fetchone()
    if not p1 or not p2:
        return {"shared": [], "unique_1": [], "unique_2": []}
    try:
        i1_raw = p1["interests"] or ""
        i2_raw = p2["interests"] or ""
        # Interests may be JSON array or comma-separated string
        try:
            i1 = set(json.loads(i1_raw)) if i1_raw.startswith("[") else set(
                s.strip() for s in i1_raw.split(",") if s.strip())
        except (json.JSONDecodeError, TypeError):
            i1 = set(s.strip() for s in i1_raw.split(",") if s.strip())
        try:
            i2 = set(json.loads(i2_raw)) if i2_raw.startswith("[") else set(
                s.strip() for s in i2_raw.split(",") if s.strip())
        except (json.JSONDecodeError, TypeError):
            i2 = set(s.strip() for s in i2_raw.split(",") if s.strip())
    except Exception:
        return {"shared": [], "unique_1": [], "unique_2": []}
    return {
        "shared": sorted(i1 & i2),
        "unique_1": sorted(i1 - i2),
        "unique_2": sorted(i2 - i1),
    }


# ---------------------------------------------------------------------------
# Notification Digest
# ---------------------------------------------------------------------------

def get_notification_digest(profile_id: str, since_hours: int = 24) -> dict:
    conn = get_db()
    rows = conn.execute(
        """SELECT type, COUNT(*) as count FROM notifications
           WHERE user_id=? AND read=0
             AND created_at >= datetime('now', '-' || ? || ' hours')
           GROUP BY type""",
        (profile_id, since_hours),
    ).fetchall()
    summary = {r["type"]: r["count"] for r in rows}
    total = sum(summary.values())
    return {"total_unread": total, "by_type": summary, "since_hours": since_hours}


# ---------------------------------------------------------------------------
# Flagged Content
# ---------------------------------------------------------------------------

def flag_content(content_type: str, content_id: str, reporter_id: str, reason: str) -> str:
    conn = get_db()
    flag_id = uuid.uuid4().hex
    conn.execute(
        """INSERT INTO flagged_content (id, content_type, content_id, reporter_id, reason)
           VALUES (?,?,?,?,?)""",
        (flag_id, content_type, content_id, reporter_id, reason),
    )
    conn.commit()
    return flag_id


def get_flagged_content(status: str = "pending", limit: int = 50, offset: int = 0) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM flagged_content WHERE status=?
           ORDER BY created_at DESC LIMIT ? OFFSET ?""",
        (status, limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]


def review_flagged_content(flag_id: str, admin_id: str, new_status: str) -> bool:
    conn = get_db()
    cur = conn.execute(
        """UPDATE flagged_content SET status=?, reviewed_by=?, reviewed_at=datetime('now')
           WHERE id=?""",
        (new_status, admin_id, flag_id),
    )
    conn.commit()
    return cur.rowcount > 0


def get_flagged_content_count(status: str = "pending") -> int:
    conn = get_db()
    return conn.execute(
        "SELECT COUNT(*) as c FROM flagged_content WHERE status=?", (status,)
    ).fetchone()["c"]


# ---------------------------------------------------------------------------
# Bulk Admin Operations
# ---------------------------------------------------------------------------

def bulk_deactivate_profiles(profile_ids: list[str]) -> int:
    if not profile_ids:
        return 0
    conn = get_db()
    placeholders = ",".join("?" for _ in profile_ids)
    cur = conn.execute(
        f"UPDATE profiles SET deactivated=1 WHERE id IN ({placeholders})",
        profile_ids,
    )
    conn.commit()
    return cur.rowcount


def bulk_delete_profiles(profile_ids: list[str]) -> int:
    if not profile_ids:
        return 0
    conn = get_db()
    placeholders = ",".join("?" for _ in profile_ids)
    try:
        conn.execute("BEGIN")
        conn.execute(
            f"DELETE FROM profiles WHERE id IN ({placeholders})", profile_ids
        )
        conn.execute(
            f"DELETE FROM users WHERE profile_id IN ({placeholders})", profile_ids
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return len(profile_ids)


def bulk_verify_profiles(profile_ids: list[str]) -> int:
    if not profile_ids:
        return 0
    conn = get_db()
    placeholders = ",".join("?" for _ in profile_ids)
    cur = conn.execute(
        f"UPDATE selfie_verifications SET status='approved' WHERE profile_id IN ({placeholders})",
        profile_ids,
    )
    # Also mark profiles as verified
    conn.execute(
        f"UPDATE profiles SET verified=1 WHERE id IN ({placeholders})",
        profile_ids,
    )
    conn.commit()
    return cur.rowcount


# ---------------------------------------------------------------------------
# Export Functions
# ---------------------------------------------------------------------------

def export_users_csv() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT u.id, u.email, u.display_name,
                  p.age, p.gender, p.location,
                  u.created_at, COALESCE(p.deactivated, 0) as deactivated,
                  COALESCE(p.verified, 0) as verified,
                  COALESCE(u.subscription_tier, 'free') as subscription_tier
           FROM users u
           LEFT JOIN profiles p ON p.id = u.profile_id
           ORDER BY u.created_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


def export_safety_reports_csv() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT id, reporter_id, reported_id, report_type as reason,
                  'reported' as status, created_at
           FROM safety_reports ORDER BY created_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


def export_analytics_csv(days: int = 30) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT date(created_at) as day, event_type, COUNT(*) as count
           FROM analytics_events
           WHERE created_at >= datetime('now', '-' || ? || ' days')
           GROUP BY day, event_type
           ORDER BY day DESC, event_type""",
        (days,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Dashboard Chart Data
# ---------------------------------------------------------------------------

def get_daily_signups(days: int = 30) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT date(created_at) as day, COUNT(*) as count
           FROM users
           WHERE created_at >= datetime('now', '-' || ? || ' days')
           GROUP BY day ORDER BY day""",
        (days,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_daily_messages(days: int = 30) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT date(created_at) as day, COUNT(*) as count
           FROM messages
           WHERE created_at >= datetime('now', '-' || ? || ' days')
           GROUP BY day ORDER BY day""",
        (days,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_daily_matches(days: int = 30) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT date(l1.created_at) as day, COUNT(*) as count
           FROM likes l1
           JOIN likes l2 ON l1.from_id = l2.target_id
               AND l1.target_id = l2.from_id
               AND l1.target_type = 'profile'
               AND l2.target_type = 'profile'
           WHERE l1.from_id < l1.target_id
             AND l1.created_at >= datetime('now', '-' || ? || ' days')
           GROUP BY day ORDER BY day""",
        (days,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_engagement_over_time(days: int = 30) -> dict:
    return {
        "signups": get_daily_signups(days),
        "messages": get_daily_messages(days),
        "matches": get_daily_matches(days),
    }


# ---------------------------------------------------------------------------
# Report Reasons & Escalation
# ---------------------------------------------------------------------------

def create_safety_report_v2(reporter_id: str, reported_id: str, report_type: str,
                            reason_category: str, notes: str = None) -> str:
    """Create report with structured reason category."""
    conn = get_db()
    report_id = uuid.uuid4().hex
    conn.execute("""
        INSERT INTO safety_reports (id, reporter_id, reported_id, report_type, notes, status, reason_category)
        VALUES (?, ?, ?, ?, ?, 'open', ?)
    """, (report_id, reporter_id, reported_id, report_type, notes, reason_category))
    # Store detailed reason
    conn.execute("""
        INSERT INTO report_reasons (id, report_id, reason_category, reason_detail)
        VALUES (?, ?, ?, ?)
    """, (uuid.uuid4().hex, report_id, reason_category, notes))
    # Auto-escalate: if user has 3+ open reports, flag for priority review
    count = conn.execute(
        "SELECT COUNT(*) FROM safety_reports WHERE reported_id = ? AND status = 'open'",
        (reported_id,)
    ).fetchone()[0]
    if count >= 3:
        conn.execute(
            "UPDATE safety_reports SET status = 'escalated' WHERE reported_id = ? AND status = 'open'",
            (reported_id,)
        )
    conn.commit()
    return report_id


def get_report_counts_for_user(profile_id: str) -> dict:
    conn = get_db()
    total = conn.execute(
        "SELECT COUNT(*) FROM safety_reports WHERE reported_id = ?", (profile_id,)
    ).fetchone()[0]
    open_count = conn.execute(
        "SELECT COUNT(*) FROM safety_reports WHERE reported_id = ? AND status IN ('open','escalated')",
        (profile_id,)
    ).fetchone()[0]
    return {"total": total, "open": open_count}


def review_safety_report(report_id: str, admin_id: str, resolution: str, status: str = "resolved") -> bool:
    conn = get_db()
    from datetime import datetime, timezone
    cur = conn.execute("""
        UPDATE safety_reports SET status = ?, resolution = ?, reviewed_by = ?,
        reviewed_at = ? WHERE id = ?
    """, (status, resolution, admin_id, datetime.now(timezone.utc).isoformat(), report_id))
    conn.commit()
    return cur.rowcount > 0


def get_safety_reports_queue(status: str = None, limit: int = 50, offset: int = 0) -> list[dict]:
    conn = get_db()
    if status:
        rows = conn.execute("""
            SELECT sr.*, p1.name as reporter_name, p2.name as reported_name
            FROM safety_reports sr
            LEFT JOIN profiles p1 ON p1.id = sr.reporter_id
            LEFT JOIN profiles p2 ON p2.id = sr.reported_id
            WHERE sr.status = ?
            ORDER BY CASE sr.status WHEN 'escalated' THEN 0 WHEN 'open' THEN 1 ELSE 2 END,
                     sr.created_at DESC
            LIMIT ? OFFSET ?
        """, (status, limit, offset)).fetchall()
    else:
        rows = conn.execute("""
            SELECT sr.*, p1.name as reporter_name, p2.name as reported_name
            FROM safety_reports sr
            LEFT JOIN profiles p1 ON p1.id = sr.reporter_id
            LEFT JOIN profiles p2 ON p2.id = sr.reported_id
            ORDER BY CASE sr.status WHEN 'escalated' THEN 0 WHEN 'open' THEN 1 ELSE 2 END,
                     sr.created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Suspensions
# ---------------------------------------------------------------------------

def suspend_user(user_id: str, reason: str, suspended_by: str,
                 suspension_type: str = "temporary", duration_days: int = None) -> str:
    conn = get_db()
    from datetime import datetime, timedelta, timezone
    suspension_id = uuid.uuid4().hex
    expires_at = None
    if suspension_type == "temporary" and duration_days:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=duration_days)).isoformat()
    conn.execute("""
        INSERT INTO suspensions (id, user_id, reason, suspended_by, suspension_type, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (suspension_id, user_id, reason, suspended_by, suspension_type, expires_at))
    conn.execute("UPDATE users SET suspended = 1 WHERE id = ?", (user_id,))
    conn.commit()
    return suspension_id


def unsuspend_user(user_id: str) -> bool:
    conn = get_db()
    conn.execute("UPDATE users SET suspended = 0 WHERE id = ?", (user_id,))
    conn.execute("""
        UPDATE suspensions SET appeal_result = 'overturned', appeal_reviewed = 1
        WHERE user_id = ? AND appeal_reviewed = 0
    """, (user_id,))
    conn.commit()
    return True


def get_user_suspensions(user_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM suspensions WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def submit_appeal(suspension_id: str, appeal_text: str) -> bool:
    conn = get_db()
    cur = conn.execute(
        "UPDATE suspensions SET appealed = 1, appeal_text = ? WHERE id = ? AND appealed = 0",
        (appeal_text, suspension_id)
    )
    conn.commit()
    return cur.rowcount > 0


def review_appeal(suspension_id: str, result: str) -> bool:
    """result: 'upheld' or 'overturned'"""
    conn = get_db()
    cur = conn.execute(
        "UPDATE suspensions SET appeal_reviewed = 1, appeal_result = ? WHERE id = ?",
        (result, suspension_id)
    )
    if result == "overturned":
        row = conn.execute("SELECT user_id FROM suspensions WHERE id = ?", (suspension_id,)).fetchone()
        if row:
            conn.execute("UPDATE users SET suspended = 0 WHERE id = ?", (row["user_id"],))
    conn.commit()
    return cur.rowcount > 0


def get_pending_appeals() -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT s.*, u.email, u.display_name
        FROM suspensions s
        JOIN users u ON u.id = s.user_id
        WHERE s.appealed = 1 AND s.appeal_reviewed = 0
        ORDER BY s.created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


def check_suspension_expired() -> int:
    """Unsuspend users whose temporary suspension expired. Returns count."""
    conn = get_db()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    rows = conn.execute(
        "SELECT DISTINCT user_id FROM suspensions WHERE suspension_type = 'temporary' AND expires_at <= ? AND appeal_result IS NULL",
        (now,)
    ).fetchall()
    expired_users = [r["user_id"] for r in rows]
    if expired_users:
        placeholders = ",".join("?" * len(expired_users))
        conn.execute(f"UPDATE users SET suspended = 0 WHERE id IN ({placeholders})", expired_users)
        conn.commit()
    return len(expired_users)


# ---------------------------------------------------------------------------
# Photo Hashes
# ---------------------------------------------------------------------------

def save_photo_hash(profile_id: str, photo_filename: str, phash: str) -> str:
    conn = get_db()
    hash_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO photo_hashes (id, profile_id, photo_filename, phash) VALUES (?, ?, ?, ?)",
        (hash_id, profile_id, photo_filename, phash)
    )
    conn.commit()
    return hash_id


def find_similar_photos(phash: str, max_distance: int = 5) -> list[dict]:
    """Find photos with similar perceptual hash. Returns matches within hamming distance."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM photo_hashes").fetchall()
    results = []
    for r in rows:
        dist = _hamming_distance(phash, r["phash"])
        if dist <= max_distance:
            results.append({**dict(r), "distance": dist})
    return sorted(results, key=lambda x: x["distance"])


def _hamming_distance(h1: str, h2: str) -> int:
    """Compute hamming distance between two hex hash strings."""
    if len(h1) != len(h2):
        return 999
    return bin(int(h1, 16) ^ int(h2, 16)).count('1')


# ---------------------------------------------------------------------------
# Conversation Quality Signals
# ---------------------------------------------------------------------------

def update_response_stats(profile_id: str):
    """Recalculate response rate and avg reply time for a profile."""
    conn = get_db()
    # Get all conversations where this user received messages
    received = conn.execute("""
        SELECT m.from_id, m.created_at, m.to_id
        FROM messages m WHERE m.to_id = ?
        ORDER BY m.created_at
    """, (profile_id,)).fetchall()

    if not received:
        return

    total_received_convos = set()
    replied_convos = set()
    reply_times = []

    for msg in received:
        conv_key = msg["from_id"]
        total_received_convos.add(conv_key)
        # Check if user replied
        reply = conn.execute("""
            SELECT created_at FROM messages
            WHERE from_id = ? AND to_id = ? AND created_at > ?
            ORDER BY created_at LIMIT 1
        """, (profile_id, msg["from_id"], msg["created_at"])).fetchone()
        if reply:
            replied_convos.add(conv_key)
            from datetime import datetime
            try:
                t1 = datetime.fromisoformat(msg["created_at"].replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(reply["created_at"].replace("Z", "+00:00"))
                diff_minutes = (t2 - t1).total_seconds() / 60
                if diff_minutes < 10080:  # ignore gaps > 7 days
                    reply_times.append(diff_minutes)
            except (ValueError, TypeError):
                pass

    rate = len(replied_convos) / max(len(total_received_convos), 1)
    avg_minutes = sum(reply_times) / max(len(reply_times), 1) if reply_times else None

    conn.execute(
        "UPDATE profiles SET response_rate = ?, avg_reply_minutes = ? WHERE id = ?",
        (round(rate, 2), round(avg_minutes, 1) if avg_minutes else None, profile_id)
    )
    conn.commit()


def get_response_stats(profile_id: str) -> dict:
    conn = get_db()
    row = conn.execute(
        "SELECT response_rate, avg_reply_minutes, last_message_at FROM profiles WHERE id = ?",
        (profile_id,)
    ).fetchone()
    if not row:
        return {}
    return {
        "response_rate": row["response_rate"],
        "avg_reply_minutes": row["avg_reply_minutes"],
        "last_message_at": row["last_message_at"],
    }


def update_last_message_time(profile_id: str):
    conn = get_db()
    from datetime import datetime, timezone
    conn.execute(
        "UPDATE profiles SET last_message_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), profile_id)
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Saved Searches
# ---------------------------------------------------------------------------

def save_search(profile_id: str, name: str, filters: dict) -> str:
    conn = get_db()
    search_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO saved_searches (id, profile_id, name, filters) VALUES (?, ?, ?, ?)",
        (search_id, profile_id, name, json.dumps(filters))
    )
    conn.commit()
    return search_id


def get_saved_searches(profile_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM saved_searches WHERE profile_id = ? ORDER BY created_at DESC",
        (profile_id,)
    ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["filters"] = json.loads(d["filters"]) if d["filters"] else {}
        results.append(d)
    return results


def delete_saved_search(search_id: str, profile_id: str) -> bool:
    conn = get_db()
    cur = conn.execute(
        "DELETE FROM saved_searches WHERE id = ? AND profile_id = ?",
        (search_id, profile_id)
    )
    conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Recently Active / New Users
# ---------------------------------------------------------------------------

def get_recently_active_profiles(hours: int = 24, limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT p.id, p.name, p.age, p.gender, p.photo, p.verified, p.last_active,
               p.response_rate, p.avg_reply_minutes, p.created_at,
               p.headline, p.profile_theme
        FROM profiles p
        WHERE p.deactivated = 0
          AND p.last_active >= datetime('now', '-' || ? || ' hours')
        ORDER BY p.last_active DESC
        LIMIT ?
    """, (hours, limit)).fetchall()
    return [dict(r) for r in rows]


def get_new_profiles(days: int = 7, limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute("""
        SELECT p.id, p.name, p.age, p.gender, p.photo, p.verified,
               p.headline, p.profile_theme, p.created_at
        FROM profiles p
        WHERE p.deactivated = 0
          AND p.created_at >= datetime('now', '-' || ? || ' days')
        ORDER BY p.created_at DESC
        LIMIT ?
    """, (days, limit)).fetchall()
    return [dict(r) for r in rows]


def get_ghost_matches(profile_id: str, days_silent: int = 7) -> list[dict]:
    """Find mutual matches where neither has messaged in X days."""
    conn = get_db()
    rows = conn.execute("""
        SELECT l1.target_id as match_id, p.name, p.photo,
               MAX(m.created_at) as last_msg
        FROM likes l1
        JOIN likes l2 ON l1.from_id = l2.target_id AND l1.target_id = l2.from_id
            AND l1.target_type = 'profile' AND l2.target_type = 'profile'
        JOIN profiles p ON p.id = l1.target_id
        LEFT JOIN messages m ON (
            (m.from_id = ? AND m.to_id = l1.target_id) OR
            (m.from_id = l1.target_id AND m.to_id = ?)
        )
        WHERE l1.from_id = ?
          AND p.deactivated = 0
        GROUP BY l1.target_id
        HAVING last_msg IS NULL OR last_msg < datetime('now', '-' || ? || ' days')
    """, (profile_id, profile_id, profile_id, days_silent)).fetchall()
    return [dict(r) for r in rows]
