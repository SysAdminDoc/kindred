"""
Kindred v2.5.1 - Configuration
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
_jwt_file = Path(__file__).parent.parent / ".jwt_secret"
if os.getenv("KINDRED_JWT_SECRET"):
    JWT_SECRET = os.getenv("KINDRED_JWT_SECRET")
elif _jwt_file.exists():
    JWT_SECRET = _jwt_file.read_text().strip()
else:
    JWT_SECRET = secrets.token_urlsafe(48)
    _jwt_file.write_text(JWT_SECRET)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("KINDRED_JWT_EXPIRE_HOURS", "72"))

# --- Admin ---
ADMIN_EMAIL = os.getenv("KINDRED_ADMIN_EMAIL", "admin@kindred.local")
ADMIN_PASSWORD = os.getenv("KINDRED_ADMIN_PASSWORD", "admin")

# --- Server ---
HOST = os.getenv("KINDRED_HOST", "127.0.0.1")
USER_PORT = int(os.getenv("KINDRED_USER_PORT", "8000"))
ADMIN_PORT = int(os.getenv("KINDRED_ADMIN_PORT", "8001"))
CORS_ORIGINS = os.getenv("KINDRED_CORS_ORIGINS", "http://localhost:8000,http://localhost:8001").split(",")

# --- Database ---
DB_PATH = Path(os.getenv("KINDRED_DB_PATH", str(Path(__file__).parent.parent / "kindred.db")))

# --- Uploads ---
UPLOAD_DIR = Path(os.getenv("KINDRED_UPLOAD_DIR", str(Path(__file__).parent.parent / "uploads")))
MAX_UPLOAD_MB = int(os.getenv("KINDRED_MAX_UPLOAD_MB", "30"))

# --- Object storage ---
# Leave the bucket unset for local development.  Supplying any object-storage
# setting selects the S3-compatible backend; required mode then fails closed
# instead of silently writing new media to local disk.
OBJECT_STORAGE_ENDPOINT = os.getenv("KINDRED_OBJECT_STORAGE_ENDPOINT", "").strip()
OBJECT_STORAGE_BUCKET = os.getenv("KINDRED_OBJECT_STORAGE_BUCKET", "").strip()
OBJECT_STORAGE_ACCESS_KEY = os.getenv("KINDRED_OBJECT_STORAGE_ACCESS_KEY", "").strip()
OBJECT_STORAGE_SECRET_KEY = os.getenv("KINDRED_OBJECT_STORAGE_SECRET_KEY", "").strip()
OBJECT_STORAGE_REGION = os.getenv("KINDRED_OBJECT_STORAGE_REGION", "us-east-1").strip()
OBJECT_STORAGE_PREFIX = os.getenv("KINDRED_OBJECT_STORAGE_PREFIX", "media").strip()
OBJECT_STORAGE_PUBLIC_URL = os.getenv("KINDRED_OBJECT_STORAGE_PUBLIC_URL", "").strip()
OBJECT_STORAGE_REQUIRED = os.getenv(
    "KINDRED_OBJECT_STORAGE_REQUIRED", "false"
).lower() == "true"
OBJECT_STORAGE_ADDRESSING_STYLE = os.getenv(
    "KINDRED_OBJECT_STORAGE_ADDRESSING_STYLE", ""
).strip()

# --- Rate Limiting ---
RATE_LIMIT_DEFAULT = os.getenv("KINDRED_RATE_LIMIT", "60/minute")
RATE_LIMIT_AUTH = os.getenv("KINDRED_RATE_LIMIT_AUTH", "10/minute")
REDIS_URL = os.getenv("KINDRED_REDIS_URL", "").strip()
REDIS_REQUIRED = os.getenv("KINDRED_REDIS_REQUIRED", "false").lower() == "true"
REDIS_KEY_PREFIX = os.getenv("KINDRED_REDIS_KEY_PREFIX", "kindred")

# --- Background jobs ---
QUEUE_ENABLED = os.getenv("KINDRED_QUEUE_ENABLED", "false").lower() == "true"
QUEUE_REQUIRED = os.getenv("KINDRED_QUEUE_REQUIRED", "false").lower() == "true"
QUEUE_NAMESPACE = os.getenv("KINDRED_QUEUE_NAMESPACE", f"{REDIS_KEY_PREFIX}:jobs")
QUEUE_PROCESSES = int(os.getenv("KINDRED_QUEUE_PROCESSES", "2"))
QUEUE_THREADS = int(os.getenv("KINDRED_QUEUE_THREADS", "2"))

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
EMBEDDING_MODEL = os.getenv("KINDRED_EMBEDDING_MODEL", "all-mpnet-base-v2")
EMBEDDING_FALLBACK_MODEL = os.getenv(
    "KINDRED_EMBEDDING_FALLBACK_MODEL", "all-MiniLM-L6-v2"
)

# --- Web Push (VAPID) ---
VAPID_PUBLIC_KEY = os.getenv("KINDRED_VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("KINDRED_VAPID_PRIVATE_KEY", "")
VAPID_CONTACT = os.getenv("KINDRED_VAPID_CONTACT", "mailto:admin@kindred.app")

# --- Photo safety ---
PHOTO_HASH_ENABLED = os.getenv("KINDRED_PHOTO_HASH_ENABLED", "true").lower() == "true"
PHOTO_HASH_MAX_DISTANCE = int(os.getenv("KINDRED_PHOTO_HASH_MAX_DISTANCE", "5"))
PHOTO_DHASH_MAX_DISTANCE = int(os.getenv("KINDRED_PHOTO_DHASH_MAX_DISTANCE", "8"))
PHOTO_SAFETY_REQUIRED = os.getenv(
    "KINDRED_PHOTO_SAFETY_REQUIRED", "false"
).lower() == "true"
PHOTODNA_ENABLED = os.getenv("KINDRED_PHOTODNA_ENABLED", "false").lower() == "true"
PHOTODNA_HOOK_URL = os.getenv("KINDRED_PHOTODNA_HOOK_URL", "").strip()
PHOTODNA_API_KEY = os.getenv("KINDRED_PHOTODNA_API_KEY", "").strip()
PHOTODNA_TIMEOUT_SECONDS = float(os.getenv("KINDRED_PHOTODNA_TIMEOUT_SECONDS", "3"))

# --- Selfie liveness ---
_project_root = Path(__file__).parent.parent
SELFIE_LIVENESS_ENABLED = os.getenv(
    "KINDRED_SELFIE_LIVENESS_ENABLED", "true"
).lower() == "true"
SELFIE_LIVENESS_REQUIRED = os.getenv(
    "KINDRED_SELFIE_LIVENESS_REQUIRED", "true"
).lower() == "true"
SELFIE_LIVENESS_MODEL_PATH = Path(os.getenv(
    "KINDRED_SELFIE_LIVENESS_MODEL_PATH",
    str(_project_root / "models" / "face_landmarker.task"),
))
SELFIE_LIVENESS_EXPECTED_SHA256 = os.getenv(
    "KINDRED_SELFIE_LIVENESS_MODEL_SHA256",
    "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff",
).strip().lower()
SELFIE_LIVENESS_MIN_FRAMES = int(os.getenv("KINDRED_SELFIE_LIVENESS_MIN_FRAMES", "8"))
SELFIE_LIVENESS_MAX_FRAMES = int(os.getenv("KINDRED_SELFIE_LIVENESS_MAX_FRAMES", "24"))
SELFIE_LIVENESS_FRAME_INTERVAL_MS = int(
    os.getenv("KINDRED_SELFIE_LIVENESS_FRAME_INTERVAL_MS", "150")
)
SELFIE_LIVENESS_MIN_DURATION_MS = int(
    os.getenv("KINDRED_SELFIE_LIVENESS_MIN_DURATION_MS", "900")
)
SELFIE_LIVENESS_BLINK_CLOSED_EAR = float(
    os.getenv("KINDRED_SELFIE_LIVENESS_BLINK_CLOSED_EAR", "0.20")
)
SELFIE_LIVENESS_BLINK_OPEN_EAR = float(
    os.getenv("KINDRED_SELFIE_LIVENESS_BLINK_OPEN_EAR", "0.24")
)
SELFIE_LIVENESS_HEAD_TURN_DELTA = float(
    os.getenv("KINDRED_SELFIE_LIVENESS_HEAD_TURN_DELTA", "0.12")
)

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

# --- Harassment detection ---
HARASSMENT_ENABLED = os.getenv("KINDRED_HARASSMENT_ENABLED", "true").lower() == "true"
HARASSMENT_WINDOW_MINUTES = int(os.getenv("KINDRED_HARASSMENT_WINDOW_MINUTES", "10"))
HARASSMENT_WARN_SCORE = int(os.getenv("KINDRED_HARASSMENT_WARN_SCORE", "2"))
HARASSMENT_MUTE_SCORE = int(os.getenv("KINDRED_HARASSMENT_MUTE_SCORE", "4"))
HARASSMENT_MUTE_MINUTES = int(os.getenv("KINDRED_HARASSMENT_MUTE_MINUTES", "60"))

# --- Report cooling-off ---
# A value of zero keeps the reporter/reported pair hidden permanently.
REPORT_COOLING_OFF_DAYS = int(os.getenv("KINDRED_REPORT_COOLING_OFF_DAYS", "30"))

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
SCHEMA_VERSION = 13
