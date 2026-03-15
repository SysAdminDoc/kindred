"""
Kindred v1.7.0 - Configuration
Loads settings from environment variables or .env file.
"""

import os
import secrets
from pathlib import Path

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

# --- JWT ---
JWT_SECRET = os.getenv("KINDRED_JWT_SECRET", secrets.token_urlsafe(48))
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("KINDRED_JWT_EXPIRE_HOURS", "72"))

# --- Admin ---
ADMIN_EMAIL = os.getenv("KINDRED_ADMIN_EMAIL", "admin@kindred.local")
ADMIN_PASSWORD = os.getenv("KINDRED_ADMIN_PASSWORD", "admin")

# --- Server ---
HOST = os.getenv("KINDRED_HOST", "127.0.0.1")
USER_PORT = int(os.getenv("KINDRED_USER_PORT", "8000"))
ADMIN_PORT = int(os.getenv("KINDRED_ADMIN_PORT", "8001"))
CORS_ORIGINS = os.getenv("KINDRED_CORS_ORIGINS", "*").split(",")

# --- Database ---
DB_PATH = Path(os.getenv("KINDRED_DB_PATH", str(Path(__file__).parent.parent / "kindred.db")))

# --- Uploads ---
UPLOAD_DIR = Path(os.getenv("KINDRED_UPLOAD_DIR", str(Path(__file__).parent.parent / "uploads")))
MAX_UPLOAD_MB = int(os.getenv("KINDRED_MAX_UPLOAD_MB", "30"))

# --- Rate Limiting ---
RATE_LIMIT_DEFAULT = os.getenv("KINDRED_RATE_LIMIT", "60/minute")
RATE_LIMIT_AUTH = os.getenv("KINDRED_RATE_LIMIT_AUTH", "10/minute")

# --- Photo reveal ---
PHOTO_REVEAL_THRESHOLD = float(os.getenv("KINDRED_PHOTO_REVEAL_THRESHOLD", "60.0"))

# --- Logging ---
LOG_LEVEL = os.getenv("KINDRED_LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("KINDRED_LOG_FORMAT", "json")  # "json" or "text"

# --- Email (stub - configure for production) ---
SMTP_HOST = os.getenv("KINDRED_SMTP_HOST", "")
SMTP_PORT = int(os.getenv("KINDRED_SMTP_PORT", "587"))
SMTP_USER = os.getenv("KINDRED_SMTP_USER", "")
SMTP_PASSWORD = os.getenv("KINDRED_SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("KINDRED_SMTP_FROM", "noreply@kindred.app")

# --- Security ---
BCRYPT_ROUNDS = int(os.getenv("KINDRED_BCRYPT_ROUNDS", "12"))
REFRESH_TOKEN_DAYS = int(os.getenv("KINDRED_REFRESH_TOKEN_DAYS", "30"))

# --- Background tasks ---
EMBEDDING_WORKERS = int(os.getenv("KINDRED_EMBEDDING_WORKERS", "2"))

# --- Web Push (VAPID) ---
VAPID_PUBLIC_KEY = os.getenv("KINDRED_VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("KINDRED_VAPID_PRIVATE_KEY", "")
VAPID_CONTACT = os.getenv("KINDRED_VAPID_CONTACT", "mailto:admin@kindred.app")

# --- Content Filtering ---
CONTENT_FILTER_ENABLED = os.getenv("KINDRED_CONTENT_FILTER", "true").lower() == "true"

# --- Premium ---
PREMIUM_ENABLED = os.getenv("KINDRED_PREMIUM_ENABLED", "false").lower() == "true"

# --- Daily Suggestions ---
DAILY_SUGGESTION_COUNT = int(os.getenv("KINDRED_DAILY_SUGGESTIONS", "5"))

# --- Location Matching ---
LOCATION_MATCH_RADIUS_KM = int(os.getenv("KINDRED_LOCATION_RADIUS_KM", "100"))

# --- Stories ---
STORY_EXPIRY_HOURS = int(os.getenv("KINDRED_STORY_EXPIRY_HOURS", "24"))

# --- Match Expiry ---
MATCH_EXPIRY_DAYS = int(os.getenv("KINDRED_MATCH_EXPIRY_DAYS", "7"))

# --- Backups ---
BACKUP_DIR = Path(os.getenv("KINDRED_BACKUP_DIR", str(Path(__file__).parent.parent / "backups")))
BACKUP_KEEP_COUNT = int(os.getenv("KINDRED_BACKUP_KEEP_COUNT", "7"))
BACKUP_INTERVAL_HOURS = int(os.getenv("KINDRED_BACKUP_INTERVAL_HOURS", "24"))

# --- i18n ---
DEFAULT_LOCALE = os.getenv("KINDRED_DEFAULT_LOCALE", "en")

# --- Blind Date ---
BLIND_DATE_HOURS = int(os.getenv("KINDRED_BLIND_DATE_HOURS", "48"))

# --- Message Cooldown ---
MESSAGE_COOLDOWN_MINUTES = int(os.getenv("KINDRED_MESSAGE_COOLDOWN_MINUTES", "5"))
MESSAGE_COOLDOWN_COUNT = int(os.getenv("KINDRED_MESSAGE_COOLDOWN_COUNT", "10"))

# --- Undo Block Grace Period ---
UNDO_BLOCK_MINUTES = int(os.getenv("KINDRED_UNDO_BLOCK_MINUTES", "5"))

# --- Safety Check-in ---
SAFETY_CHECKIN_DEFAULT_MINUTES = int(os.getenv("KINDRED_SAFETY_CHECKIN_MINUTES", "60"))

# --- Database Vacuum ---
VACUUM_INTERVAL_HOURS = int(os.getenv("KINDRED_VACUUM_INTERVAL_HOURS", "168"))

# --- Webhooks ---
WEBHOOKS_ENABLED = os.getenv("KINDRED_WEBHOOKS_ENABLED", "false").lower() == "true"

# --- Theme ---
DEFAULT_THEME = os.getenv("KINDRED_DEFAULT_THEME", "mocha")  # "mocha" or "latte"

# --- Schema version (for migration tracking) ---
SCHEMA_VERSION = 6
