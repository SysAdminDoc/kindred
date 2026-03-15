"""
Kindred v1.6.0 - FastAPI Backend (User Server)
Compatibility-first dating + social platform.
"""

import hashlib
import json as json_stdlib
import math
import secrets
import shutil
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from passlib.hash import bcrypt
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import (
    JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS,
    CORS_ORIGINS, RATE_LIMIT_DEFAULT, RATE_LIMIT_AUTH,
    PHOTO_REVEAL_THRESHOLD, MAX_UPLOAD_MB,
    BCRYPT_ROUNDS, REFRESH_TOKEN_DAYS,
    VAPID_PUBLIC_KEY, CONTENT_FILTER_ENABLED,
    PREMIUM_ENABLED, DAILY_SUGGESTION_COUNT,
    LOCATION_MATCH_RADIUS_KM, STORY_EXPIRY_HOURS,
    MATCH_EXPIRY_DAYS, DEFAULT_LOCALE,
)
from app.logging_config import setup_logging, get_logger
from app.content_filter import check_content, filter_message
from app.database import (
    init_db, save_profile, get_profile, get_all_profiles,
    update_profile_field, send_message, get_conversation, get_conversations_for,
    get_conversation_count, get_last_message_sender,
    mark_messages_read, use_invite,
    create_date_plan, update_date_plan, get_date_plans, get_date_plans_between,
    log_behavioral_event, get_behavioral_profile,
    create_safety_report,
    create_blog_post, get_blog_posts, delete_blog_post,
    create_profile_comment, get_profile_comments, delete_profile_comment,
    send_friend_request, respond_friend_request, get_friends, get_friend_requests,
    remove_friend, are_friends, increment_profile_views,
    create_user, get_user_by_email, get_user_by_id, link_profile_to_user,
    create_notification, get_notifications, get_unread_notification_count,
    mark_notifications_read, mark_notification_read,
    toggle_like, get_likes, get_like_count, has_liked,
    create_status_update, get_status_updates, get_friend_status_feed,
    delete_status_update, update_last_seen, get_online_friends,
    add_photo, get_photos, delete_photo, set_primary_photo,
    search_profiles,
    log_activity, get_activity_feed, get_explore_profiles, get_recent_profiles,
    create_group, get_group, get_all_groups, get_my_groups,
    join_group, leave_group, is_group_member, get_group_members,
    create_group_post, get_group_posts, delete_group_post,
    create_event, get_event, get_all_events, rsvp_event,
    get_event_rsvps, get_my_events,
    get_or_create_game, answer_game, get_game_history, get_game_score,
    submit_selfie_verification, get_verification_status,
    save_video_intro, get_video_intro, delete_video_intro,
    add_music_pref, get_music_prefs, delete_music_pref, compute_music_compatibility,
    block_profile, unblock_profile, is_blocked_either, get_blocked_profiles,
    create_password_reset, use_password_reset,
    get_notification_prefs, update_notification_prefs, should_notify,
    get_conversation_paginated, mark_messages_read_with_timestamp,
    deactivate_profile, reactivate_profile,
    add_group_moderator, remove_group_moderator, is_group_moderator,
    create_refresh_token, get_refresh_token, revoke_refresh_token, revoke_all_user_tokens,
    create_email_verification, verify_email_token,
    submit_photo_for_moderation,
    save_questionnaire_progress, get_questionnaire_progress, delete_questionnaire_progress,
    add_message_reaction, remove_message_reaction, get_message_reactions,
    save_daily_suggestions, get_daily_suggestions, mark_suggestion_seen,
    get_profile_viewers, get_who_liked_me,
    save_totp_secret, get_totp_secret, verify_totp_setup, delete_totp_secret,
    save_push_subscription, get_push_subscriptions, delete_push_subscription,
    send_group_message, get_group_messages,
    log_content_filter,
    get_subscription, update_subscription, is_premium,
    log_analytics_event, mark_onboarding_completed, has_completed_onboarding,
    save_voice_message, get_voice_messages,
    save_profile_prompt, get_profile_prompts, delete_profile_prompt, update_profile_prompt,
    create_super_like, has_super_liked, get_super_likes_for, get_super_like_count,
    create_story, get_stories_feed, get_story, view_story, delete_story,
    cleanup_expired_stories,
    create_group_poll, get_group_polls, vote_poll, get_poll_user_vote,
    create_session, get_user_sessions, touch_session, revoke_session, revoke_all_sessions,
    save_user_location, get_user_location, get_nearby_profiles,
    save_recovery_codes, use_recovery_code, get_recovery_code_count,
    set_incognito_mode, is_incognito,
    get_mutual_friends, get_mutual_friend_count,
    search_messages,
    delete_account, export_user_data,
    get_expiring_matches,
    UPLOAD_DIR,
)
from app.questions import (
    BIG_FIVE_ITEMS, VALUES_QUESTIONS, ATTACHMENT_ITEMS,
    LOVE_LANGUAGES, DEALBREAKERS, OPEN_ENDED_PROMPTS,
    SCENARIO_QUESTIONS, TRADEOFF_QUESTIONS, BEHAVIORAL_QUESTIONS,
    SELF_DISCLOSURE, COMMUNICATION_QUESTIONS, FINANCIAL_QUESTIONS,
    ENERGY_QUESTIONS,
    score_big_five, classify_attachment, build_profile_text,
)
from app.engine import (
    generate_embedding, find_matches, compute_compatibility,
    generate_narrative, generate_icebreakers, generate_coaching_tips,
    DEFAULT_WEIGHTS,
)

logger = setup_logging()
log = get_logger("api")

app = FastAPI(title="Kindred", version="1.6.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Too many requests. Please slow down."})


# File upload magic byte validation
MAGIC_BYTES = {
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".png": [b"\x89PNG"],
    ".webp": [b"RIFF"],
    ".gif": [b"GIF87a", b"GIF89a"],
    ".mp4": [b"\x00\x00\x00\x18ftyp", b"\x00\x00\x00\x1cftyp", b"\x00\x00\x00\x20ftyp", b"\x00\x00\x00"],
    ".webm": [b"\x1a\x45\xdf\xa3"],
    ".mov": [b"\x00\x00\x00\x14ftyp", b"\x00\x00\x00\x08wide", b"\x00\x00\x00"],
}


def validate_file_magic(content: bytes, ext: str) -> bool:
    patterns = MAGIC_BYTES.get(ext, [])
    if not patterns:
        return True
    return any(content[:len(p)] == p for p in patterns)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, profile_id: str, ws: WebSocket):
        await ws.accept()
        self.active[profile_id].append(ws)

    def disconnect(self, profile_id: str, ws: WebSocket):
        if profile_id in self.active:
            self.active[profile_id] = [w for w in self.active[profile_id] if w is not ws]
            if not self.active[profile_id]:
                del self.active[profile_id]

    async def send_to(self, profile_id: str, data: dict):
        import json as _json
        for ws in self.active.get(profile_id, []):
            try:
                await ws.send_text(_json.dumps(data))
            except Exception:
                pass

    def is_online(self, profile_id: str) -> bool:
        return bool(self.active.get(profile_id))


ws_manager = ConnectionManager()

security = HTTPBearer(auto_error=False)


def create_token(user_id: str, is_admin: bool = False) -> str:
    payload = {
        "sub": user_id,
        "admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict | None:
    """Returns user dict or None if no/invalid token. Non-blocking."""
    if not creds:
        return None
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = get_user_by_id(payload["sub"])
        return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def require_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Returns user dict or raises 401."""
    if not creds:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = get_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

STATIC_DIR = Path(__file__).parent.parent / "static"

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class AuthRegister(BaseModel):
    email: str
    password: str
    display_name: str = ""

class AuthLogin(BaseModel):
    email: str
    password: str

class ProfileSubmission(BaseModel):
    name: str
    age: int
    gender: str
    seeking: str
    big_five_answers: dict[str, int] = {}
    attachment_answers: dict[str, int] = {}
    values: dict[str, str | int] = {}
    love_language: str = ""
    dealbreakers: list[str] = []
    open_ended: dict[str, str] = {}
    scenario_answers: dict[str, int] = {}
    tradeoffs: dict[str, str] = {}
    behavioral_answers: dict[str, str] = {}
    self_disclosure: dict[str, str] = {}
    communication_style: dict[str, str] = {}
    financial_values: dict[str, str] = {}
    dating_energy: str = ""
    dating_pace: str = ""
    relationship_intent: str = ""
    weight_prefs: dict[str, float] = {}
    invite_code: str = ""

class MessageSend(BaseModel):
    from_id: str
    to_id: str
    content: str

class WeightUpdate(BaseModel):
    weights: dict[str, float]

class PrivacyUpdate(BaseModel):
    privacy: dict[str, str]

class DatePlanCreate(BaseModel):
    profile_a: str
    profile_b: str
    proposed_by: str
    suggestion: str
    proposed_time: str | None = None

class DatePlanUpdate(BaseModel):
    status: str

class BehavioralEvent(BaseModel):
    profile_id: str
    event_type: str
    target_id: str | None = None
    duration_ms: int | None = None

class SafetyReport(BaseModel):
    reporter_id: str
    reported_id: str
    report_type: str
    notes: str | None = None

class ProfilePageUpdate(BaseModel):
    location: str | None = None
    headline: str | None = None
    about_me: str | None = None
    who_id_like_to_meet: str | None = None
    interests: str | None = None
    heroes: str | None = None
    mood: str | None = None
    music_embeds: list[str] | None = None
    video_embeds: list[str] | None = None
    profile_song: str | None = None
    profile_theme: str | None = None

class BlogPostCreate(BaseModel):
    title: str
    content: str

class ProfileCommentCreate(BaseModel):
    from_id: str
    content: str

class FriendAction(BaseModel):
    accept: bool

class LikeToggle(BaseModel):
    from_id: str
    target_type: str
    target_id: str
    reaction: str = "like"

class StatusCreate(BaseModel):
    profile_id: str
    content: str
    mood: str = ""

class NotifPrefsUpdate(BaseModel):
    messages: int = 1
    friend_requests: int = 1
    likes: int = 1
    comments: int = 1
    group_posts: int = 1
    events: int = 1

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class ProfilePromptCreate(BaseModel):
    prompt: str
    answer: str
    sort_order: int = 0

class StoryCreate(BaseModel):
    content_type: str = "text"
    content: str
    background: str = "#6c7086"

class PollCreate(BaseModel):
    question: str
    options: list[str]

class PollVote(BaseModel):
    option_index: int

class LocationUpdate(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    city: str = ""
    radius_km: int = 100
    enabled: bool = True

class IncognitoUpdate(BaseModel):
    enabled: bool

class AccountDeleteConfirm(BaseModel):
    confirmation: str

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    init_db()
    from app.i18n import init_i18n
    init_i18n()
    from app.backup import start_backup_scheduler
    start_backup_scheduler()
    cleanup_expired_stories()

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/api/auth/register")
@limiter.limit(RATE_LIMIT_AUTH)
def register(request: Request, body: AuthRegister):
    if not body.email or "@" not in body.email:
        raise HTTPException(status_code=400, detail="Valid email required")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    pw_hash = bcrypt.using(rounds=BCRYPT_ROUNDS).hash(body.password)
    user_id = create_user(body.email, pw_hash, body.display_name)
    token = create_token(user_id)
    refresh = _create_refresh_token_for_user(user_id)
    log.info("User registered: %s", body.email)
    log_analytics_event("signup", user_id)
    return {
        "token": token,
        "refresh_token": refresh,
        "user_id": user_id,
        "display_name": body.display_name or body.email.split("@")[0],
    }


@app.post("/api/auth/login")
@limiter.limit(RATE_LIMIT_AUTH)
def login(request: Request, body: AuthLogin):
    user = get_user_by_email(body.email)
    if not user or not bcrypt.verify(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("deactivated"):
        raise HTTPException(status_code=403, detail="Account deactivated")
    token = create_token(user["id"], bool(user["is_admin"]))
    refresh = _create_refresh_token_for_user(user["id"])
    log.info("User logged in: %s", body.email)
    log_analytics_event("login", user["id"])
    return {
        "token": token,
        "refresh_token": refresh,
        "user_id": user["id"],
        "profile_id": user["profile_id"],
        "display_name": user["display_name"],
        "is_admin": bool(user["is_admin"]),
    }


@app.get("/api/auth/me")
def get_me(user: dict = Depends(require_user)):
    return {
        "user_id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "profile_id": user["profile_id"],
        "is_admin": bool(user["is_admin"]),
    }


@app.post("/api/auth/password-reset")
@limiter.limit(RATE_LIMIT_AUTH)
def request_password_reset(request: Request, body: PasswordResetRequest):
    user = get_user_by_email(body.email)
    if user:
        token = create_password_reset(user["id"])
        # In production, send email. For dev, return token directly.
        return {"message": "If that email exists, a reset link has been sent", "dev_token": token}
    return {"message": "If that email exists, a reset link has been sent"}


@app.post("/api/auth/password-reset/confirm")
@limiter.limit(RATE_LIMIT_AUTH)
def confirm_password_reset(request: Request, body: PasswordResetConfirm):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    pw_hash = bcrypt.using(rounds=BCRYPT_ROUNDS).hash(body.new_password)
    if not use_password_reset(body.token, pw_hash):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    return {"message": "Password reset successful"}


@app.post("/api/auth/change-password")
def change_password(body: PasswordChange, user: dict = Depends(require_user)):
    if not bcrypt.verify(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    from app.database import get_db
    conn = get_db()
    conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                 (bcrypt.using(rounds=BCRYPT_ROUNDS).hash(body.new_password), user["id"]))
    conn.commit()
    return {"message": "Password changed successfully"}


# ---------------------------------------------------------------------------
# Refresh Tokens
# ---------------------------------------------------------------------------

def _create_refresh_token_for_user(user_id: str) -> str:
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires = (datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)).isoformat()
    create_refresh_token(user_id, token_hash, expires)
    return raw


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@app.post("/api/auth/refresh")
@limiter.limit(RATE_LIMIT_AUTH)
def refresh_access_token(request: Request, body: RefreshTokenRequest):
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    stored = get_refresh_token(token_hash)
    if not stored:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    # Rotate: revoke old, issue new
    revoke_refresh_token(token_hash)
    user = get_user_by_id(stored["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    token = create_token(user["id"], bool(user["is_admin"]))
    new_refresh = _create_refresh_token_for_user(user["id"])
    return {"token": token, "refresh_token": new_refresh}


@app.post("/api/auth/logout")
def logout(body: RefreshTokenRequest, user: dict = Depends(require_user)):
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    revoke_refresh_token(token_hash)
    return {"message": "Logged out"}


@app.post("/api/auth/logout-all")
def logout_all(user: dict = Depends(require_user)):
    revoke_all_user_tokens(user["id"])
    return {"message": "All sessions revoked"}


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

@app.get("/api/auth/verify-email/{token}")
def verify_email(token: str):
    result = verify_email_token(token)
    if not result:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    log.info("Email verified for user: %s", result["user_id"])
    return {"message": "Email verified successfully"}


# ---------------------------------------------------------------------------
# Questionnaire Progress
# ---------------------------------------------------------------------------

class QuestionnaireProgressUpdate(BaseModel):
    progress_data: dict
    current_index: int


@app.get("/api/questionnaire/progress")
def get_progress(user: dict = Depends(require_user)):
    progress = get_questionnaire_progress(user["id"])
    if not progress:
        return {"progress": None}
    import json as _json
    return {
        "progress_data": _json.loads(progress["progress_data"]) if isinstance(progress["progress_data"], str) else progress["progress_data"],
        "current_index": progress["current_index"],
    }


@app.put("/api/questionnaire/progress")
def save_progress(body: QuestionnaireProgressUpdate, user: dict = Depends(require_user)):
    import json as _json
    save_questionnaire_progress(
        user["id"],
        _json.dumps(body.progress_data),
        body.current_index,
    )
    return {"message": "Progress saved"}


@app.delete("/api/questionnaire/progress")
def clear_progress(user: dict = Depends(require_user)):
    delete_questionnaire_progress(user["id"])
    return {"message": "Progress cleared"}


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@app.get("/api/notifications")
def list_notifications(user: dict = Depends(require_user)):
    notifs = get_notifications(user["id"])
    unread = get_unread_notification_count(user["id"])
    return {"notifications": notifs, "unread": unread}


@app.post("/api/notifications/read")
def read_all_notifications(user: dict = Depends(require_user)):
    mark_notifications_read(user["id"])
    return {"message": "All notifications marked read"}


@app.post("/api/notifications/{notification_id}/read")
def read_notification(notification_id: str, user: dict = Depends(require_user)):
    mark_notification_read(notification_id)
    return {"message": "Notification marked read"}


@app.get("/api/notifications/preferences")
def get_notif_prefs(user: dict = Depends(require_user)):
    return get_notification_prefs(user["id"])


@app.put("/api/notifications/preferences")
def update_notif_prefs(body: NotifPrefsUpdate, user: dict = Depends(require_user)):
    update_notification_prefs(user["id"], body.model_dump())
    return {"message": "Notification preferences updated"}

# ---------------------------------------------------------------------------
# Questionnaire
# ---------------------------------------------------------------------------

@app.get("/api/questionnaire")
def get_questionnaire():
    return {
        "big_five": [{"id": i[0], "text": i[1], "trait": i[2]} for i in BIG_FIVE_ITEMS],
        "scenarios": [
            {"id": s["id"], "text": s["text"],
             "options": [o["label"] for o in s["options"]]}
            for s in SCENARIO_QUESTIONS
        ],
        "behavioral": BEHAVIORAL_QUESTIONS,
        "tradeoffs": TRADEOFF_QUESTIONS,
        "self_disclosure": SELF_DISCLOSURE,
        "values": VALUES_QUESTIONS,
        "attachment": [{"id": i[0], "text": i[1]} for i in ATTACHMENT_ITEMS],
        "love_languages": LOVE_LANGUAGES,
        "dealbreakers": DEALBREAKERS,
        "open_ended": OPEN_ENDED_PROMPTS,
        "communication": COMMUNICATION_QUESTIONS,
        "financial": FINANCIAL_QUESTIONS,
        "energy": ENERGY_QUESTIONS,
        "default_weights": DEFAULT_WEIGHTS,
    }

# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

@app.post("/api/profile")
def create_profile(submission: ProfileSubmission,
                   user: dict | None = Depends(get_current_user)):
    big_five = score_big_five(
        submission.big_five_answers,
        submission.scenario_answers or None,
        submission.behavioral_answers or None,
    )
    attachment = classify_attachment(
        submission.attachment_answers,
        submission.scenario_answers or None,
    )

    profile_data = {
        "name": submission.name,
        "age": submission.age,
        "gender": submission.gender,
        "seeking": submission.seeking,
        "big_five": big_five,
        "attachment": attachment,
        "values": submission.values,
        "tradeoffs": submission.tradeoffs,
        "self_disclosure": submission.self_disclosure,
        "love_language": submission.love_language,
        "dealbreakers": submission.dealbreakers,
        "open_ended": submission.open_ended,
        "scenario_answers": submission.scenario_answers,
        "behavioral_answers": submission.behavioral_answers,
        "communication_style": submission.communication_style,
        "financial_values": submission.financial_values,
        "dating_energy": submission.dating_energy or None,
        "dating_pace": submission.dating_pace or None,
        "relationship_intent": submission.relationship_intent or None,
        "weight_prefs": submission.weight_prefs,
        "invite_code": submission.invite_code or None,
    }

    profile_text = build_profile_text(profile_data)
    embedding = generate_embedding(profile_text)
    profile_data["embedding"] = embedding.tobytes()

    profile_id = save_profile(profile_data)

    if submission.invite_code:
        use_invite(submission.invite_code, profile_id)

    # Link profile to authenticated user and clear questionnaire progress
    if user:
        link_profile_to_user(user["id"], profile_id)
        delete_questionnaire_progress(user["id"])

    return {
        "id": profile_id,
        "big_five": big_five,
        "attachment": attachment,
        "message": "Profile created successfully",
    }


@app.get("/api/profile/{profile_id}")
def read_profile(profile_id: str):
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    result = {k: v for k, v in profile.items() if k != "embedding"}
    return result


@app.get("/api/profiles")
def list_profiles():
    profiles = get_all_profiles()
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "age": p["age"],
            "gender": p["gender"],
            "seeking": p["seeking"],
            "photo": p.get("photo"),
            "verified": p.get("verified", 0),
            "dating_energy": p.get("dating_energy"),
            "relationship_intent": p.get("relationship_intent"),
            "created_at": p["created_at"],
        }
        for p in profiles
    ]

# ---------------------------------------------------------------------------
# Photo Upload
# ---------------------------------------------------------------------------

@app.post("/api/profile/{profile_id}/photo")
async def upload_photo(profile_id: str, file: UploadFile = File(...),
                       user: dict = Depends(require_user)):
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    if user.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Can only upload your own photo")

    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(status_code=400, detail="Only JPG, PNG, WEBP allowed")

    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large (max {MAX_UPLOAD_MB}MB)")
    if not validate_file_magic(content, ext):
        raise HTTPException(status_code=400, detail="File content doesn't match extension")

    # Generate thumbnail
    filename = f"{profile_id}{ext}"
    filepath = UPLOAD_DIR / filename
    with open(filepath, "wb") as f:
        f.write(content)

    _generate_thumbnail(filepath, profile_id)
    update_profile_field(profile_id, "photo", filename)
    submit_photo_for_moderation(profile_id, filename)
    return {"photo": filename}


def _generate_thumbnail(filepath: Path, profile_id: str, size: tuple = (200, 200)):
    try:
        from PIL import Image
        img = Image.open(filepath)
        img.thumbnail(size, Image.LANCZOS)
        thumb_path = UPLOAD_DIR / f"thumb_{profile_id}{filepath.suffix}"
        img.save(str(thumb_path), quality=85)
    except Exception:
        pass  # Thumbnail generation is best-effort

# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

@app.get("/api/matches/{profile_id}")
def get_matches(profile_id: str, top_n: int = 20):
    target = get_profile(profile_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    all_profiles = get_all_profiles()
    if len(all_profiles) < 2:
        return {"matches": [], "message": "Need at least 2 profiles to match"}

    custom_weights = target.get("weight_prefs") or None
    matches = find_matches(profile_id, all_profiles, top_n, custom_weights)

    for m in matches:
        if m["compatibility"]["total"] < PHOTO_REVEAL_THRESHOLD:
            m["photo"] = None
            m["photo_locked"] = True
        else:
            m["photo_locked"] = False

    return {"matches": matches, "profile_id": profile_id}


@app.get("/api/compatibility/{id_a}/{id_b}")
def compare_profiles(id_a: str, id_b: str):
    profile_a = get_profile(id_a)
    profile_b = get_profile(id_b)
    if profile_a is None or profile_b is None:
        raise HTTPException(status_code=404, detail="One or both profiles not found")

    result = compute_compatibility(profile_a, profile_b)
    result["profiles"] = {
        "a": {"id": id_a, "name": profile_a["name"]},
        "b": {"id": id_b, "name": profile_b["name"]},
    }

    result["narrative"] = generate_narrative(profile_a, profile_b, result)
    result["icebreakers"] = generate_icebreakers(profile_a, profile_b, result)
    result["coaching_tips"] = generate_coaching_tips(profile_a, profile_b, result)

    # Conversation stats for date suggestion
    msg_count = get_conversation_count(id_a, id_b)
    result["message_count"] = msg_count
    result["suggest_date"] = msg_count >= 8

    # Date plans between these two
    result["date_plans"] = get_date_plans_between(id_a, id_b)

    threshold_met = result["total"] >= PHOTO_REVEAL_THRESHOLD
    result["photo_a"] = profile_a.get("photo") if threshold_met else None
    result["photo_b"] = profile_b.get("photo") if threshold_met else None
    result["photo_threshold"] = PHOTO_REVEAL_THRESHOLD

    return result

# ---------------------------------------------------------------------------
# User Weights & Privacy
# ---------------------------------------------------------------------------

@app.put("/api/profile/{profile_id}/weights")
def update_weights(profile_id: str, body: WeightUpdate, user: dict = Depends(require_user)):
    if user.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Can only update your own weights")
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    update_profile_field(profile_id, "weight_prefs", body.weights)
    return {"message": "Weights updated", "weights": body.weights}


@app.put("/api/profile/{profile_id}/privacy")
def update_privacy(profile_id: str, body: PrivacyUpdate, user: dict = Depends(require_user)):
    if user.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Can only update your own privacy")
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    update_profile_field(profile_id, "privacy", body.privacy)
    return {"message": "Privacy settings updated"}

# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------

@app.post("/api/messages")
async def send_msg(msg: MessageSend, user: dict = Depends(require_user)):
    if not msg.content.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if is_blocked_either(msg.from_id, msg.to_id):
        raise HTTPException(status_code=403, detail="Cannot message this user")
    content_text = msg.content.strip()
    # Content filter
    filtered_text, was_filtered = filter_message(content_text)
    if was_filtered:
        log_content_filter("message", None, msg.from_id, content_text, "profanity", "profanity", "censored")
        content_text = filtered_text
    spam_check = check_content(content_text)
    if not spam_check["clean"] and spam_check.get("type") == "spam":
        log_content_filter("message", None, msg.from_id, content_text, spam_check["reason"], "spam", "blocked")
        raise HTTPException(status_code=400, detail="Message flagged as spam")
    msg_id = send_message(msg.from_id, msg.to_id, content_text)
    # Notify recipient
    sender = get_profile(msg.from_id)
    sender_name = sender["name"] if sender else "Someone"
    from app.database import get_db
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE profile_id=?", (msg.to_id,)).fetchone()
    conn.close()
    if row:
        create_notification(
            row["id"], "message",
            f"New message from {sender_name}",
            content_text[:100],
            f"/messages/{msg.from_id}"
        )
    # Real-time push via WebSocket
    await ws_manager.send_to(msg.to_id, {
        "type": "message",
        "from": msg.from_id,
        "from_name": sender_name,
        "content": content_text,
        "id": msg_id,
    })
    log_analytics_event("message_sent", msg.from_id)
    return {"id": msg_id, "status": "sent"}


@app.get("/api/messages/{profile_id}")
def get_inbox(profile_id: str, user: dict = Depends(require_user)):
    convos = get_conversations_for(profile_id)
    for c in convos:
        partner = get_profile(c["partner_id"])
        c["partner_name"] = partner["name"] if partner else "Unknown"
        c["your_turn"] = c.get("last_sender") != profile_id
    return {"conversations": convos}


@app.get("/api/messages/{id_a}/{id_b}")
def get_msgs(id_a: str, id_b: str, limit: int = 50, before: str = "",
             user: dict = Depends(require_user)):
    if before:
        messages = get_conversation_paginated(id_a, id_b, limit, before)
    else:
        messages = get_conversation_paginated(id_a, id_b, limit)
    read_count = mark_messages_read_with_timestamp(id_a, id_b)
    msg_count = get_conversation_count(id_a, id_b)
    last_sender = get_last_message_sender(id_a, id_b)
    return {
        "messages": messages,
        "message_count": msg_count,
        "your_turn": last_sender != id_a if last_sender else False,
        "suggest_date": msg_count >= 8,
        "has_more": len(messages) == limit,
        "read_count": read_count,
    }


@app.post("/api/messages/photo")
async def send_photo_message(from_id: str, to_id: str,
                              file: UploadFile = File(...),
                              user: dict = Depends(require_user)):
    if not from_id or not to_id:
        raise HTTPException(status_code=400, detail="from_id and to_id required")
    if is_blocked_either(from_id, to_id):
        raise HTTPException(status_code=403, detail="Cannot message this user")
    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        raise HTTPException(status_code=400, detail="Only image files allowed")
    content = await file.read()
    if not validate_file_magic(content, ext):
        raise HTTPException(status_code=400, detail="File content doesn't match extension")
    import uuid as _uuid
    filename = f"msg_{_uuid.uuid4().hex[:8]}{ext}"
    filepath = UPLOAD_DIR / filename
    with open(filepath, "wb") as f:
        f.write(content)
    msg_id = send_message(from_id, to_id, "[Photo]", photo=filename)
    # Notify
    sender = get_profile(from_id)
    sender_name = sender["name"] if sender else "Someone"
    from app.database import get_db
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE profile_id=?", (to_id,)).fetchone()
    conn.close()
    if row:
        create_notification(
            row["id"], "message",
            f"Photo from {sender_name}", "Sent you a photo",
            f"/messages/{from_id}"
        )
    return {"id": msg_id, "photo": filename}

# ---------------------------------------------------------------------------
# Date Plans
# ---------------------------------------------------------------------------

@app.post("/api/date-plans")
def create_plan(plan: DatePlanCreate):
    plan_id = create_date_plan(
        plan.profile_a, plan.profile_b, plan.proposed_by,
        plan.suggestion, plan.proposed_time
    )
    return {"id": plan_id, "status": "proposed"}


@app.put("/api/date-plans/{plan_id}")
def update_plan(plan_id: str, body: DatePlanUpdate):
    if body.status not in ("accepted", "declined", "completed"):
        raise HTTPException(status_code=400, detail="Invalid status")
    if not update_date_plan(plan_id, body.status):
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"id": plan_id, "status": body.status}


@app.get("/api/date-plans/{profile_id}")
def get_plans(profile_id: str):
    plans = get_date_plans(profile_id)
    # Enrich with names
    for p in plans:
        pa = get_profile(p["profile_a"])
        pb = get_profile(p["profile_b"])
        p["name_a"] = pa["name"] if pa else "Unknown"
        p["name_b"] = pb["name"] if pb else "Unknown"
    return {"plans": plans}

# ---------------------------------------------------------------------------
# Behavioral Events
# ---------------------------------------------------------------------------

@app.post("/api/behavioral")
def log_event(event: BehavioralEvent):
    log_behavioral_event(
        event.profile_id, event.event_type,
        event.target_id, event.duration_ms
    )
    return {"status": "logged"}


@app.get("/api/behavioral/{profile_id}")
def get_behavior(profile_id: str):
    return get_behavioral_profile(profile_id)

# ---------------------------------------------------------------------------
# Safety Reports
# ---------------------------------------------------------------------------

@app.post("/api/safety/report")
def report_safety(report: SafetyReport):
    report_id = create_safety_report(
        report.reporter_id, report.reported_id,
        report.report_type, report.notes
    )
    return {"id": report_id, "message": "Report submitted"}


# ---------------------------------------------------------------------------
# Profile Export (radar chart data)
# ---------------------------------------------------------------------------

@app.get("/api/profile/{profile_id}/export")
def export_profile(profile_id: str):
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "name": profile["name"],
        "age": profile["age"],
        "big_five": profile["big_five"],
        "attachment": profile["attachment"],
        "love_language": profile["love_language"],
        "values": profile["values"],
        "communication_style": profile.get("communication_style", {}),
        "financial_values": profile.get("financial_values", {}),
    }

# ---------------------------------------------------------------------------
# Profile Page
# ---------------------------------------------------------------------------

@app.get("/api/profile/{profile_id}/page")
def get_profile_page(profile_id: str, viewer: str = ""):
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    increment_profile_views(profile_id)
    friends = get_friends(profile_id)
    comments = get_profile_comments(profile_id)
    blog_posts = get_blog_posts(profile_id)
    # Enrich comment authors
    for c in comments:
        author = get_profile(c["from_id"])
        c["from_name"] = author["name"] if author else "Unknown"
        c["from_photo"] = author.get("photo") if author else None
    is_friend = are_friends(viewer, profile_id) if viewer else False
    pending = False
    if viewer and not is_friend:
        reqs = get_friend_requests(profile_id)
        pending = any(r["from_id"] == viewer for r in reqs)
    return {
        "id": profile["id"],
        "name": profile["name"],
        "age": profile["age"],
        "gender": profile["gender"],
        "photo": profile.get("photo"),
        "verified": profile.get("verified", 0),
        "location": profile.get("location"),
        "headline": profile.get("headline"),
        "about_me": profile.get("about_me"),
        "who_id_like_to_meet": profile.get("who_id_like_to_meet"),
        "interests": profile.get("interests"),
        "heroes": profile.get("heroes"),
        "mood": profile.get("mood"),
        "music_embeds": profile.get("music_embeds", []),
        "video_embeds": profile.get("video_embeds", []),
        "profile_song": profile.get("profile_song"),
        "profile_views": profile.get("profile_views", 0),
        "love_language": profile.get("love_language"),
        "big_five": profile.get("big_five", {}),
        "attachment": profile.get("attachment"),
        "dating_energy": profile.get("dating_energy"),
        "relationship_intent": profile.get("relationship_intent"),
        "profile_theme": profile.get("profile_theme"),
        "created_at": profile["created_at"],
        "friends": friends,
        "friend_count": len(friends),
        "is_friend": is_friend,
        "friend_pending": pending,
        "comments": comments,
        "blog_posts": blog_posts,
    }


@app.put("/api/profile/{profile_id}/page")
def update_profile_page(profile_id: str, body: ProfilePageUpdate):
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    import json as _json
    for field in ("location", "headline", "about_me", "who_id_like_to_meet",
                  "interests", "heroes", "mood", "profile_song", "profile_theme"):
        val = getattr(body, field)
        if val is not None:
            update_profile_field(profile_id, field, val)
    if body.music_embeds is not None:
        update_profile_field(profile_id, "music_embeds", _json.dumps(body.music_embeds))
    if body.video_embeds is not None:
        update_profile_field(profile_id, "video_embeds", _json.dumps(body.video_embeds))
    return {"message": "Profile page updated"}


# Blog
@app.post("/api/profile/{profile_id}/blog")
def create_blog(profile_id: str, post: BlogPostCreate):
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not post.title.strip() or not post.content.strip():
        raise HTTPException(status_code=400, detail="Title and content required")
    post_id = create_blog_post(profile_id, post.title.strip(), post.content.strip())
    return {"id": post_id, "message": "Blog post created"}


@app.get("/api/profile/{profile_id}/blog")
def list_blog(profile_id: str):
    return {"posts": get_blog_posts(profile_id)}


@app.delete("/api/blog/{post_id}")
def del_blog(post_id: str, profile_id: str = ""):
    if not profile_id:
        raise HTTPException(status_code=400, detail="profile_id required")
    if not delete_blog_post(post_id, profile_id):
        raise HTTPException(status_code=404, detail="Post not found")
    return {"message": "Deleted"}


# Comments
@app.post("/api/profile/{profile_id}/comments")
def add_comment(profile_id: str, comment: ProfileCommentCreate):
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not comment.content.strip():
        raise HTTPException(status_code=400, detail="Content required")
    cid = create_profile_comment(profile_id, comment.from_id, comment.content.strip())
    return {"id": cid, "message": "Comment posted"}


@app.get("/api/profile/{profile_id}/comments")
def list_comments(profile_id: str):
    comments = get_profile_comments(profile_id)
    for c in comments:
        author = get_profile(c["from_id"])
        c["from_name"] = author["name"] if author else "Unknown"
        c["from_photo"] = author.get("photo") if author else None
    return {"comments": comments}


@app.delete("/api/comment/{comment_id}")
def del_comment(comment_id: str, profile_id: str = ""):
    if not profile_id:
        raise HTTPException(status_code=400, detail="profile_id required")
    if not delete_profile_comment(comment_id, profile_id):
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"message": "Deleted"}


# Friends
@app.post("/api/profile/{profile_id}/friend/{friend_id}")
def add_friend(profile_id: str, friend_id: str):
    if profile_id == friend_id:
        raise HTTPException(status_code=400, detail="Cannot friend yourself")
    if are_friends(profile_id, friend_id):
        raise HTTPException(status_code=400, detail="Already friends")
    req_id = send_friend_request(profile_id, friend_id)
    # Notify
    sender = get_profile(profile_id)
    from app.database import get_db
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE profile_id=?", (friend_id,)).fetchone()
    conn.close()
    if row and sender:
        create_notification(
            row["id"], "friend_request",
            f"{sender['name']} sent you a friend request",
            "", f"/profile/{profile_id}"
        )
    return {"id": req_id, "message": "Friend request sent"}


@app.put("/api/profile/{profile_id}/friend/{friend_id}")
def handle_friend_request(profile_id: str, friend_id: str, body: FriendAction):
    respond_friend_request(profile_id, friend_id, body.accept)
    return {"message": "Accepted" if body.accept else "Declined"}


@app.delete("/api/profile/{profile_id}/friend/{friend_id}")
def unfriend(profile_id: str, friend_id: str):
    remove_friend(profile_id, friend_id)
    return {"message": "Friend removed"}


@app.get("/api/profile/{profile_id}/friends")
def list_friends(profile_id: str):
    return {"friends": get_friends(profile_id)}


@app.get("/api/profile/{profile_id}/friend-requests")
def list_friend_requests(profile_id: str):
    return {"requests": get_friend_requests(profile_id)}


# ---------------------------------------------------------------------------
# Likes / Reactions
# ---------------------------------------------------------------------------

@app.post("/api/likes")
def like_toggle(body: LikeToggle):
    if body.target_type not in ("profile", "blog_post", "comment", "status"):
        raise HTTPException(status_code=400, detail="Invalid target type")
    liked = toggle_like(body.from_id, body.target_type, body.target_id, body.reaction)
    count = get_like_count(body.target_type, body.target_id)
    # Notify on like (not unlike)
    if liked and body.target_type == "profile":
        from app.database import get_db
        sender = get_profile(body.from_id)
        conn = get_db()
        row = conn.execute("SELECT id FROM users WHERE profile_id=?", (body.target_id,)).fetchone()
        conn.close()
        if row and sender:
            create_notification(row["id"], "like", f"{sender['name']} liked your profile", "", f"/profile/{body.from_id}")
    return {"liked": liked, "count": count}


@app.get("/api/likes/{target_type}/{target_id}")
def get_target_likes(target_type: str, target_id: str, viewer: str = ""):
    likes = get_likes(target_type, target_id)
    viewer_liked = has_liked(viewer, target_type, target_id) if viewer else False
    return {"likes": likes, "count": len(likes), "viewer_liked": viewer_liked}

# ---------------------------------------------------------------------------
# Status Updates
# ---------------------------------------------------------------------------

@app.post("/api/status")
def post_status(body: StatusCreate):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Status cannot be empty")
    sid = create_status_update(body.profile_id, body.content.strip(), body.mood)
    return {"id": sid, "message": "Status posted"}


@app.get("/api/status/{profile_id}")
def list_statuses(profile_id: str):
    return {"statuses": get_status_updates(profile_id)}


@app.delete("/api/status/{status_id}")
def remove_status(status_id: str, profile_id: str = ""):
    if not profile_id:
        raise HTTPException(status_code=400, detail="profile_id required")
    if not delete_status_update(status_id, profile_id):
        raise HTTPException(status_code=404, detail="Status not found")
    return {"message": "Deleted"}


@app.get("/api/feed/status")
def status_feed(profile_id: str):
    return {"feed": get_friend_status_feed(profile_id)}

# ---------------------------------------------------------------------------
# Online Status / Heartbeat
# ---------------------------------------------------------------------------

@app.post("/api/heartbeat/{profile_id}")
def heartbeat(profile_id: str):
    update_last_seen(profile_id)
    return {"status": "ok"}


@app.get("/api/online/{profile_id}")
def online_friends(profile_id: str):
    return {"online": get_online_friends(profile_id)}

# ---------------------------------------------------------------------------
# Photo Gallery
# ---------------------------------------------------------------------------

@app.post("/api/profile/{profile_id}/photos")
async def upload_gallery_photo(profile_id: str, file: UploadFile = File(...),
                                caption: str = "", is_primary: bool = False,
                                user: dict = Depends(require_user)):
    if user.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Can only upload your own photos")
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(status_code=400, detail="Only JPG, PNG, WEBP allowed")
    content = await file.read()
    if not validate_file_magic(content, ext):
        raise HTTPException(status_code=400, detail="File content doesn't match extension")
    import uuid as _uuid
    filename = f"{profile_id}_{_uuid.uuid4().hex[:6]}{ext}"
    filepath = UPLOAD_DIR / filename
    with open(filepath, "wb") as f:
        f.write(content)
    _generate_thumbnail(filepath, f"{profile_id}_{_uuid.uuid4().hex[:4]}")
    photo_id = add_photo(profile_id, filename, caption, is_primary)
    if is_primary:
        update_profile_field(profile_id, "photo", filename)
    submit_photo_for_moderation(profile_id, filename)
    return {"id": photo_id, "filename": filename}


@app.get("/api/profile/{profile_id}/photos")
def list_photos(profile_id: str):
    return {"photos": get_photos(profile_id)}


@app.delete("/api/photo/{photo_id}")
def remove_photo(photo_id: str, profile_id: str = ""):
    if not profile_id:
        raise HTTPException(status_code=400, detail="profile_id required")
    if not delete_photo(photo_id, profile_id):
        raise HTTPException(status_code=404, detail="Photo not found")
    return {"message": "Photo deleted"}


@app.put("/api/photo/{photo_id}/primary")
def make_primary(photo_id: str, profile_id: str = ""):
    if not profile_id:
        raise HTTPException(status_code=400, detail="profile_id required")
    if not set_primary_photo(photo_id, profile_id):
        raise HTTPException(status_code=404, detail="Photo not found")
    return {"message": "Primary photo updated"}


# ---------------------------------------------------------------------------
# Search / Discover
# ---------------------------------------------------------------------------

@app.get("/api/search")
def search(query: str = "", gender: str = "", seeking: str = "",
           age_min: int = 0, age_max: int = 999, location: str = ""):
    results = search_profiles(query, gender, seeking, age_min, age_max, location)
    return {"results": [
        {
            "id": p["id"], "name": p["name"], "age": p["age"],
            "gender": p["gender"], "seeking": p["seeking"],
            "photo": p.get("photo"), "headline": p.get("headline"),
            "location": p.get("location"),
            "dating_energy": p.get("dating_energy"),
            "relationship_intent": p.get("relationship_intent"),
        }
        for p in results
    ]}


# ---------------------------------------------------------------------------
# Activity Feed / Explore
# ---------------------------------------------------------------------------

@app.get("/api/activity/{profile_id}")
def activity_feed(profile_id: str):
    return {"activity": get_activity_feed(profile_id)}


@app.get("/api/explore")
def explore():
    return {
        "featured": [
            {"id": p["id"], "name": p["name"], "age": p["age"],
             "photo": p.get("photo"), "headline": p.get("headline"),
             "location": p.get("location"), "profile_views": p.get("profile_views", 0),
             "dating_energy": p.get("dating_energy"),
             "relationship_intent": p.get("relationship_intent")}
            for p in get_explore_profiles(12)
        ],
        "recent": [
            {"id": p["id"], "name": p["name"], "age": p["age"],
             "photo": p.get("photo"), "headline": p.get("headline"),
             "created_at": p["created_at"]}
            for p in get_recent_profiles(10)
        ],
    }


# ---------------------------------------------------------------------------
# Groups / Communities
# ---------------------------------------------------------------------------

class GroupCreate(BaseModel):
    name: str
    description: str = ""
    privacy: str = "public"

class GroupPostCreate(BaseModel):
    content: str


@app.post("/api/groups")
def create_group_endpoint(body: GroupCreate, user: dict = Depends(require_user)):
    if not user.get("profile_id"):
        raise HTTPException(status_code=400, detail="Profile required to create groups")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Group name required")
    gid = create_group(body.name.strip(), body.description.strip(), user["profile_id"], body.privacy)
    log_activity(user["profile_id"], "created_group", "group", gid, body.name.strip())
    return {"id": gid, "message": "Group created"}


@app.get("/api/groups")
def list_groups():
    return {"groups": get_all_groups()}


@app.get("/api/groups/mine")
def my_groups(user: dict = Depends(require_user)):
    if not user.get("profile_id"):
        return {"groups": []}
    return {"groups": get_my_groups(user["profile_id"])}


@app.get("/api/groups/{group_id}")
def read_group(group_id: str, viewer: str = ""):
    group = get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    members = get_group_members(group_id)
    posts = get_group_posts(group_id)
    is_member = is_group_member(group_id, viewer) if viewer else False
    return {**group, "members": members, "member_count": len(members),
            "posts": posts, "is_member": is_member}


@app.post("/api/groups/{group_id}/join")
def join_group_endpoint(group_id: str, user: dict = Depends(require_user)):
    if not user.get("profile_id"):
        raise HTTPException(status_code=400, detail="Profile required")
    join_group(group_id, user["profile_id"])
    log_activity(user["profile_id"], "joined_group", "group", group_id)
    return {"message": "Joined group"}


@app.post("/api/groups/{group_id}/leave")
def leave_group_endpoint(group_id: str, user: dict = Depends(require_user)):
    if not user.get("profile_id"):
        raise HTTPException(status_code=400, detail="Profile required")
    leave_group(group_id, user["profile_id"])
    return {"message": "Left group"}


@app.post("/api/groups/{group_id}/posts")
def post_to_group(group_id: str, body: GroupPostCreate, user: dict = Depends(require_user)):
    if not user.get("profile_id"):
        raise HTTPException(status_code=400, detail="Profile required")
    if not is_group_member(group_id, user["profile_id"]):
        raise HTTPException(status_code=403, detail="Must be a member to post")
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Content required")
    pid = create_group_post(group_id, user["profile_id"], body.content.strip())
    return {"id": pid, "message": "Post created"}


@app.delete("/api/groups/{group_id}/posts/{post_id}")
def delete_group_post_endpoint(group_id: str, post_id: str,
                                user: dict = Depends(require_user)):
    if not user.get("profile_id"):
        raise HTTPException(status_code=400, detail="Profile required")
    if not delete_group_post(post_id, user["profile_id"]):
        raise HTTPException(status_code=404, detail="Post not found")
    return {"message": "Post deleted"}


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class EventCreate(BaseModel):
    title: str
    description: str = ""
    location: str = ""
    event_date: str = ""
    event_time: str = ""
    group_id: str = ""
    max_attendees: int = 0

class EventRSVP(BaseModel):
    status: str = "going"


@app.post("/api/events")
def create_event_endpoint(body: EventCreate, user: dict = Depends(require_user)):
    if not user.get("profile_id"):
        raise HTTPException(status_code=400, detail="Profile required")
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Event title required")
    eid = create_event(
        body.title.strip(), body.description.strip(), user["profile_id"],
        body.location.strip(), body.event_date, body.event_time,
        body.group_id, body.max_attendees
    )
    log_activity(user["profile_id"], "created_event", "event", eid, body.title.strip())
    return {"id": eid, "message": "Event created"}


@app.get("/api/events")
def list_events():
    return {"events": get_all_events()}


@app.get("/api/events/mine")
def my_events(user: dict = Depends(require_user)):
    if not user.get("profile_id"):
        return {"events": []}
    return {"events": get_my_events(user["profile_id"])}


@app.get("/api/events/{event_id}")
def read_event(event_id: str):
    event = get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    rsvps = get_event_rsvps(event_id)
    return {**event, "rsvps": rsvps, "attendee_count": len([r for r in rsvps if r["status"] == "going"])}


@app.post("/api/events/{event_id}/rsvp")
def rsvp_event_endpoint(event_id: str, body: EventRSVP,
                         user: dict = Depends(require_user)):
    if not user.get("profile_id"):
        raise HTTPException(status_code=400, detail="Profile required")
    if body.status not in ("going", "interested", "not_going"):
        raise HTTPException(status_code=400, detail="Invalid RSVP status")
    rsvp_event(event_id, user["profile_id"], body.status)
    return {"message": f"RSVP: {body.status}"}


# ---------------------------------------------------------------------------
# Compatibility Games
# ---------------------------------------------------------------------------

class GameAnswer(BaseModel):
    answer: str


@app.get("/api/games/{profile_a}/{profile_b}")
def get_game(profile_a: str, profile_b: str):
    game = get_or_create_game(profile_a, profile_b)
    if not game:
        score = get_game_score(profile_a, profile_b)
        return {"complete": True, "score": score, "game": None}
    # Don't reveal the other person's answer
    result = {**game}
    if result.get("answer_a") and result.get("answer_b"):
        pass  # Both answered, show both
    elif profile_a == game["profile_a"]:
        result.pop("answer_b", None)
    else:
        result.pop("answer_a", None)
    return {"complete": False, "game": result, "score": get_game_score(profile_a, profile_b)}


@app.post("/api/games/{game_id}/answer/{profile_id}")
def submit_game_answer(game_id: str, profile_id: str, body: GameAnswer):
    result = answer_game(game_id, profile_id, body.answer)
    if not result:
        raise HTTPException(status_code=404, detail="Game not found or not a participant")
    return {"game": result, "message": "Answer submitted"}


@app.get("/api/games/{profile_a}/{profile_b}/history")
def game_history(profile_a: str, profile_b: str):
    history = get_game_history(profile_a, profile_b)
    score = get_game_score(profile_a, profile_b)
    return {"history": history, "score": score}


# ---------------------------------------------------------------------------
# Selfie Verification
# ---------------------------------------------------------------------------

@app.post("/api/verify/selfie/{profile_id}")
async def upload_selfie(profile_id: str, file: UploadFile = File(...),
                        user: dict = Depends(require_user)):
    if user.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Can only verify your own profile")
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(status_code=400, detail="Invalid image format")
    content = await file.read()
    if not validate_file_magic(content, ext):
        raise HTTPException(status_code=400, detail="File content doesn't match extension")
    filename = f"verify_{profile_id}_{uuid.uuid4().hex[:6]}{ext}"
    filepath = UPLOAD_DIR / filename
    with open(filepath, "wb") as f:
        f.write(content)
    vid = submit_selfie_verification(profile_id, filename)
    return {"id": vid, "status": "pending", "message": "Selfie submitted for verification"}


@app.get("/api/verify/status/{profile_id}")
def verification_status(profile_id: str):
    status = get_verification_status(profile_id)
    if not status:
        return {"status": "none"}
    return {"status": status["status"], "submitted_at": status["created_at"]}


# ---------------------------------------------------------------------------
# Video Intros
# ---------------------------------------------------------------------------

@app.post("/api/video-intro/{profile_id}")
async def upload_video_intro(profile_id: str, file: UploadFile = File(...),
                              user: dict = Depends(require_user)):
    if user.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Can only upload your own video intro")
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    ext = Path(file.filename).suffix.lower() if file.filename else ".mp4"
    if ext not in (".mp4", ".webm", ".mov"):
        raise HTTPException(status_code=400, detail="Supported formats: mp4, webm, mov")
    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Video too large (max {MAX_UPLOAD_MB}MB)")
    if not validate_file_magic(content, ext):
        raise HTTPException(status_code=400, detail="File content doesn't match extension")
    filename = f"intro_{profile_id}_{uuid.uuid4().hex[:6]}{ext}"
    filepath = UPLOAD_DIR / filename
    with open(filepath, "wb") as f:
        f.write(content)
    vid = save_video_intro(profile_id, filename)
    return {"id": vid, "filename": filename}


@app.get("/api/video-intro/{profile_id}")
def get_intro(profile_id: str):
    intro = get_video_intro(profile_id)
    if not intro:
        return {"intro": None}
    return {"intro": intro}


@app.delete("/api/video-intro/{profile_id}")
def remove_intro(profile_id: str):
    if not delete_video_intro(profile_id):
        raise HTTPException(status_code=404, detail="No video intro found")
    return {"message": "Video intro deleted"}


# ---------------------------------------------------------------------------
# Music Preferences
# ---------------------------------------------------------------------------

class MusicPrefCreate(BaseModel):
    song_title: str
    artist: str
    genre: str = ""
    spotify_url: str = ""


@app.post("/api/music/{profile_id}")
def add_music(profile_id: str, body: MusicPrefCreate):
    mid = add_music_pref(profile_id, body.song_title, body.artist, body.genre, body.spotify_url)
    return {"id": mid, "message": "Music added"}


@app.get("/api/music/{profile_id}")
def list_music(profile_id: str):
    return {"music": get_music_prefs(profile_id)}


@app.delete("/api/music/{pref_id}/{profile_id}")
def remove_music(pref_id: str, profile_id: str):
    if not delete_music_pref(pref_id, profile_id):
        raise HTTPException(status_code=404, detail="Music preference not found")
    return {"message": "Removed"}


@app.get("/api/music-compat/{profile_a}/{profile_b}")
def music_compatibility(profile_a: str, profile_b: str):
    return compute_music_compatibility(profile_a, profile_b)


# ---------------------------------------------------------------------------
# Blocking
# ---------------------------------------------------------------------------

@app.post("/api/block/{profile_id}/{blocked_id}")
def block_user(profile_id: str, blocked_id: str, user: dict = Depends(require_user)):
    if user.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Can only block from your own profile")
    if profile_id == blocked_id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
    block_profile(profile_id, blocked_id)
    return {"message": "User blocked"}


@app.delete("/api/block/{profile_id}/{blocked_id}")
def unblock_user(profile_id: str, blocked_id: str, user: dict = Depends(require_user)):
    if user.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Can only unblock from your own profile")
    unblock_profile(profile_id, blocked_id)
    return {"message": "User unblocked"}


@app.get("/api/blocks/{profile_id}")
def list_blocks(profile_id: str, user: dict = Depends(require_user)):
    if user.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Can only view your own blocks")
    return {"blocks": get_blocked_profiles(profile_id)}


# ---------------------------------------------------------------------------
# Profile Deactivation
# ---------------------------------------------------------------------------

@app.post("/api/profile/{profile_id}/deactivate")
def deactivate(profile_id: str, user: dict = Depends(require_user)):
    if user.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Can only deactivate your own profile")
    deactivate_profile(profile_id)
    return {"message": "Profile deactivated"}


@app.post("/api/profile/{profile_id}/reactivate")
def reactivate(profile_id: str, user: dict = Depends(require_user)):
    if user.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Can only reactivate your own profile")
    reactivate_profile(profile_id)
    return {"message": "Profile reactivated"}


# ---------------------------------------------------------------------------
# Group Moderation
# ---------------------------------------------------------------------------

@app.post("/api/groups/{group_id}/moderators/{target_id}")
def add_mod(group_id: str, target_id: str, user: dict = Depends(require_user)):
    group = get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group["creator_id"] != user.get("profile_id"):
        raise HTTPException(status_code=403, detail="Only group creator can add moderators")
    add_group_moderator(group_id, target_id)
    return {"message": "Moderator added"}


@app.delete("/api/groups/{group_id}/moderators/{target_id}")
def remove_mod(group_id: str, target_id: str, user: dict = Depends(require_user)):
    group = get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group["creator_id"] != user.get("profile_id"):
        raise HTTPException(status_code=403, detail="Only group creator can remove moderators")
    remove_group_moderator(group_id, target_id)
    return {"message": "Moderator removed"}


@app.delete("/api/groups/{group_id}/members/{target_id}")
def kick_member(group_id: str, target_id: str, user: dict = Depends(require_user)):
    if not is_group_moderator(group_id, user.get("profile_id")):
        raise HTTPException(status_code=403, detail="Must be group creator or moderator")
    leave_group(group_id, target_id)
    return {"message": "Member removed from group"}


# ---------------------------------------------------------------------------
# Message Reactions
# ---------------------------------------------------------------------------

class ReactionCreate(BaseModel):
    reaction: str


@app.post("/api/messages/{message_id}/reactions")
def react_to_message(message_id: str, body: ReactionCreate,
                     user: dict = Depends(require_user)):
    if body.reaction not in ("❤️", "👍", "😂", "😮", "😢"):
        raise HTTPException(status_code=400, detail="Invalid reaction")
    rid = add_message_reaction(message_id, user.get("profile_id", ""), body.reaction)
    return {"id": rid, "reaction": body.reaction}


@app.delete("/api/messages/{message_id}/reactions/{reaction}")
def unreact_to_message(message_id: str, reaction: str,
                       user: dict = Depends(require_user)):
    remove_message_reaction(message_id, user.get("profile_id", ""), reaction)
    return {"message": "Reaction removed"}


@app.get("/api/messages/{message_id}/reactions")
def list_reactions(message_id: str):
    return {"reactions": get_message_reactions(message_id)}


# ---------------------------------------------------------------------------
# Daily Suggestions (Top Picks)
# ---------------------------------------------------------------------------

@app.get("/api/suggestions/daily")
def daily_suggestions(user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id:
        return {"suggestions": []}
    existing = get_daily_suggestions(profile_id)
    if existing:
        return {"suggestions": existing}
    # Generate fresh suggestions
    target = get_profile(profile_id)
    if not target:
        return {"suggestions": []}
    all_profiles = get_all_profiles()
    if len(all_profiles) < 2:
        return {"suggestions": []}
    custom_weights = target.get("weight_prefs") or None
    matches = find_matches(profile_id, all_profiles, DAILY_SUGGESTION_COUNT, custom_weights)
    suggestions = [{"suggested_id": m["id"], "score": m["compatibility"]["total"]} for m in matches]
    save_daily_suggestions(profile_id, suggestions)
    log_analytics_event("daily_suggestions_generated", profile_id)
    return {"suggestions": get_daily_suggestions(profile_id)}


@app.post("/api/suggestions/{suggestion_id}/seen")
def mark_seen(suggestion_id: str, user: dict = Depends(require_user)):
    mark_suggestion_seen(suggestion_id)
    return {"message": "Marked as seen"}


# ---------------------------------------------------------------------------
# Who Viewed Me
# ---------------------------------------------------------------------------

@app.get("/api/profile/{profile_id}/viewers")
def profile_viewers(profile_id: str, user: dict = Depends(require_user)):
    if user.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Can only view your own viewers")
    viewers = get_profile_viewers(profile_id)
    return {"viewers": viewers}


# ---------------------------------------------------------------------------
# Who Liked You
# ---------------------------------------------------------------------------

@app.get("/api/profile/{profile_id}/liked-by")
def who_liked_me(profile_id: str, user: dict = Depends(require_user)):
    if user.get("profile_id") != profile_id:
        raise HTTPException(status_code=403, detail="Can only view your own likes")
    likers = get_who_liked_me(profile_id)
    # Premium gate: if not premium, only return count and blurred data
    if PREMIUM_ENABLED and not is_premium(user["id"]):
        return {
            "likers": [{"id": l["id"], "name": "???", "photo": None, "blurred": True} for l in likers],
            "count": len(likers),
            "premium_required": True,
        }
    return {"likers": likers, "count": len(likers), "premium_required": False}


# ---------------------------------------------------------------------------
# 2FA (TOTP)
# ---------------------------------------------------------------------------

@app.post("/api/auth/2fa/setup")
def setup_2fa(user: dict = Depends(require_user)):
    import base64
    secret = base64.b32encode(secrets.token_bytes(20)).decode("utf-8").rstrip("=")
    save_totp_secret(user["id"], secret)
    # OTP Auth URI for authenticator apps
    email = user.get("email", "user")
    otp_uri = f"otpauth://totp/Kindred:{email}?secret={secret}&issuer=Kindred&digits=6&period=30"
    return {"secret": secret, "otp_uri": otp_uri}


@app.post("/api/auth/2fa/verify")
def verify_2fa_setup(body: dict, user: dict = Depends(require_user)):
    code = body.get("code", "")
    totp = get_totp_secret(user["id"])
    if not totp:
        raise HTTPException(status_code=400, detail="2FA not set up")
    # TOTP verification
    import hmac, struct, time, base64, hashlib as _hashlib
    secret_bytes = base64.b32decode(totp["secret"] + "=" * (-len(totp["secret"]) % 8))
    counter = int(time.time()) // 30
    valid = False
    for offset in (-1, 0, 1):  # Allow 30s window
        c = struct.pack(">Q", counter + offset)
        h = hmac.new(secret_bytes, c, _hashlib.sha1).digest()
        o = h[-1] & 0x0F
        otp = str((struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % 1000000).zfill(6)
        if hmac.compare_digest(otp, code):
            valid = True
            break
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid code")
    verify_totp_setup(user["id"])
    return {"message": "2FA enabled successfully"}


@app.get("/api/auth/2fa/status")
def get_2fa_status(user: dict = Depends(require_user)):
    totp = get_totp_secret(user["id"])
    return {"enabled": bool(totp and totp.get("verified"))}


@app.delete("/api/auth/2fa")
def disable_2fa(user: dict = Depends(require_user)):
    delete_totp_secret(user["id"])
    return {"message": "2FA disabled"}


# ---------------------------------------------------------------------------
# Web Push Notifications
# ---------------------------------------------------------------------------

@app.get("/api/push/vapid-key")
def get_vapid_key():
    return {"publicKey": VAPID_PUBLIC_KEY}


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict


@app.post("/api/push/subscribe")
def subscribe_push(body: PushSubscription, user: dict = Depends(require_user)):
    sub_id = save_push_subscription(
        user["id"], body.endpoint,
        body.keys.get("p256dh", ""), body.keys.get("auth", "")
    )
    return {"id": sub_id, "message": "Subscribed to push notifications"}


@app.delete("/api/push/subscribe")
def unsubscribe_push(body: PushSubscription, user: dict = Depends(require_user)):
    delete_push_subscription(body.endpoint)
    return {"message": "Unsubscribed from push notifications"}


# ---------------------------------------------------------------------------
# Group Chat
# ---------------------------------------------------------------------------

class GroupMessageCreate(BaseModel):
    content: str


@app.post("/api/groups/{group_id}/messages")
def post_group_message(group_id: str, body: GroupMessageCreate,
                       user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id or not is_group_member(group_id, profile_id):
        raise HTTPException(status_code=403, detail="Must be a group member")
    content, was_filtered = filter_message(body.content.strip())
    if was_filtered:
        log_content_filter("group_message", None, profile_id, body.content.strip(), "profanity", "profanity", "censored")
    spam = check_content(content)
    if not spam["clean"] and spam.get("type") == "spam":
        raise HTTPException(status_code=400, detail="Message flagged as spam")
    msg_id = send_group_message(group_id, profile_id, content)
    return {"id": msg_id, "content": content}


@app.get("/api/groups/{group_id}/messages")
def list_group_messages(group_id: str, limit: int = 100, before: str = "",
                        user: dict = Depends(require_user)):
    msgs = get_group_messages(group_id, limit, before or None)
    return {"messages": msgs, "has_more": len(msgs) == limit}


# ---------------------------------------------------------------------------
# Premium Subscription
# ---------------------------------------------------------------------------

@app.get("/api/subscription")
def get_sub(user: dict = Depends(require_user)):
    sub = get_subscription(user["id"])
    return sub


@app.post("/api/subscription/upgrade")
def upgrade_sub(body: dict, user: dict = Depends(require_user)):
    tier = body.get("tier", "premium")
    if tier not in ("premium", "plus"):
        raise HTTPException(status_code=400, detail="Invalid tier")
    # In production, this would integrate with a payment provider
    update_subscription(user["id"], tier)
    log_analytics_event("subscription_upgrade", user["id"], {"tier": tier})
    return {"message": f"Upgraded to {tier}", "tier": tier}


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

@app.post("/api/onboarding/complete")
def complete_onboarding(user: dict = Depends(require_user)):
    mark_onboarding_completed(user["id"])
    return {"message": "Onboarding completed"}


@app.get("/api/onboarding/status")
def onboarding_status(user: dict = Depends(require_user)):
    return {"completed": has_completed_onboarding(user["id"])}


# ---------------------------------------------------------------------------
# WebSocket Real-time
# ---------------------------------------------------------------------------

@app.websocket("/ws/{profile_id}")
async def websocket_endpoint(websocket: WebSocket, profile_id: str):
    await ws_manager.connect(profile_id, websocket)
    update_last_seen(profile_id)
    try:
        while True:
            import json as _json
            data = await websocket.receive_text()
            msg = _json.loads(data)
            msg_type = msg.get("type", "")

            if msg_type == "message":
                to_id = msg.get("to")
                content = msg.get("content", "").strip()
                if to_id and content:
                    content, _ = filter_message(content)
                    spam = check_content(content)
                    if not spam["clean"] and spam.get("type") == "spam":
                        continue
                    msg_id = send_message(profile_id, to_id, content)
                    # Send to recipient in real-time
                    sender = get_profile(profile_id)
                    await ws_manager.send_to(to_id, {
                        "type": "message",
                        "from": profile_id,
                        "from_name": sender["name"] if sender else "Unknown",
                        "content": content,
                        "id": msg_id,
                    })
                    # Also send back to sender for confirmation
                    await ws_manager.send_to(profile_id, {
                        "type": "message_sent",
                        "to": to_id,
                        "content": content,
                        "id": msg_id,
                    })

            elif msg_type == "typing":
                to_id = msg.get("to")
                if to_id:
                    await ws_manager.send_to(to_id, {
                        "type": "typing",
                        "from": profile_id,
                    })

            elif msg_type == "group_message":
                group_id = msg.get("group_id")
                content = msg.get("content", "").strip()
                if group_id and content and is_group_member(group_id, profile_id):
                    content, _ = filter_message(content)
                    gm_id = send_group_message(group_id, profile_id, content)
                    sender = get_profile(profile_id)
                    members = get_group_members(group_id)
                    for member in members:
                        if member["profile_id"] != profile_id:
                            await ws_manager.send_to(member["profile_id"], {
                                "type": "group_message",
                                "group_id": group_id,
                                "from": profile_id,
                                "from_name": sender["name"] if sender else "Unknown",
                                "content": content,
                                "id": gm_id,
                            })

            elif msg_type == "reaction":
                message_id = msg.get("message_id")
                reaction = msg.get("reaction")
                to_id = msg.get("to")
                if message_id and reaction:
                    add_message_reaction(message_id, profile_id, reaction)
                    if to_id:
                        await ws_manager.send_to(to_id, {
                            "type": "reaction",
                            "message_id": message_id,
                            "from": profile_id,
                            "reaction": reaction,
                        })

            elif msg_type == "heartbeat":
                update_last_seen(profile_id)

    except WebSocketDisconnect:
        ws_manager.disconnect(profile_id, websocket)


@app.get("/api/ws-online")
def ws_online_users():
    return {"online": list(ws_manager.active.keys())}


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    import sys
    import os
    from app.config import DB_PATH
    db_size_mb = round(DB_PATH.stat().st_size / (1024 * 1024), 2) if DB_PATH.exists() else 0
    return {
        "status": "healthy",
        "version": "1.6.0",
        "python": sys.version,
        "database_size_mb": db_size_mb,
        "active_websockets": sum(len(v) for v in ws_manager.active.values()),
        "pid": os.getpid(),
    }


# ---------------------------------------------------------------------------
# Voice Messages
# ---------------------------------------------------------------------------

@app.post("/api/voice-message/{to_id}")
async def upload_voice_message(to_id: str, file: UploadFile = File(...),
                               user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="No profile linked")
    if is_blocked_either(profile_id, to_id):
        raise HTTPException(status_code=403, detail="Blocked")
    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
    fname = f"voice_{uuid.uuid4().hex[:12]}.webm"
    (UPLOAD_DIR / fname).write_bytes(content)
    msg_id = save_voice_message(profile_id, to_id, fname, duration_ms=0)
    # Also send as a regular message linking to the voice file
    send_message(profile_id, to_id, f"[voice:{fname}]")
    await ws_manager.send_to(to_id, {
        "type": "voice_message", "from": profile_id, "filename": fname, "id": msg_id,
    })
    log_analytics_event("voice_message_sent", profile_id)
    return {"id": msg_id, "filename": fname}


@app.get("/api/voice-messages/{partner_id}")
def list_voice_messages(partner_id: str, user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="No profile linked")
    return {"voice_messages": get_voice_messages(profile_id, partner_id)}


# ---------------------------------------------------------------------------
# Profile Prompts
# ---------------------------------------------------------------------------

@app.post("/api/profile-prompts")
def create_prompt(body: ProfilePromptCreate, user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="No profile linked")
    existing = get_profile_prompts(profile_id)
    if len(existing) >= 3:
        raise HTTPException(status_code=400, detail="Maximum 3 prompts allowed")
    pid = save_profile_prompt(profile_id, body.prompt, body.answer, body.sort_order)
    return {"id": pid}


@app.get("/api/profile-prompts/{profile_id}")
def list_prompts(profile_id: str):
    return {"prompts": get_profile_prompts(profile_id)}


@app.delete("/api/profile-prompts/{prompt_id}")
def remove_prompt(prompt_id: str, user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id or not delete_profile_prompt(prompt_id, profile_id):
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"message": "Prompt deleted"}


@app.put("/api/profile-prompts/{prompt_id}")
def edit_prompt(prompt_id: str, body: ProfilePromptCreate, user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id or not update_profile_prompt(prompt_id, profile_id, body.answer):
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"message": "Prompt updated"}


# ---------------------------------------------------------------------------
# Super Like
# ---------------------------------------------------------------------------

@app.post("/api/super-like/{target_id}")
def super_like(target_id: str, user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="No profile linked")
    if is_blocked_either(profile_id, target_id):
        raise HTTPException(status_code=403, detail="Blocked")
    if has_super_liked(profile_id, target_id):
        raise HTTPException(status_code=400, detail="Already super liked")
    sl_id = create_super_like(profile_id, target_id)
    sender = get_profile(profile_id)
    target_user = get_user_by_id(target_id)
    if not target_user:
        from app.database import get_db
        conn = get_db()
        row = conn.execute("SELECT u.id FROM users u WHERE u.profile_id=?", (target_id,)).fetchone()
        if row:
            create_notification(row["id"], "super_like",
                f"{sender['name'] if sender else 'Someone'} super liked you!",
                link=f"/profile/{profile_id}")
    log_analytics_event("super_like", profile_id)
    return {"id": sl_id, "message": "Super liked!"}


@app.get("/api/super-likes/received")
def received_super_likes(user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="No profile linked")
    return {"super_likes": get_super_likes_for(profile_id), "count": get_super_like_count(profile_id)}


@app.get("/api/super-liked/{target_id}")
def check_super_liked(target_id: str, user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    return {"super_liked": has_super_liked(profile_id, target_id) if profile_id else False}


# ---------------------------------------------------------------------------
# Match Expiry
# ---------------------------------------------------------------------------

@app.get("/api/matches/expiring")
def expiring_matches(user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="No profile linked")
    return {"matches": get_expiring_matches(profile_id, MATCH_EXPIRY_DAYS)}


# ---------------------------------------------------------------------------
# Stories / Moments
# ---------------------------------------------------------------------------

@app.post("/api/stories")
async def post_story(user: dict = Depends(require_user),
                     content_type: str = "text", content: str = "",
                     background: str = "#6c7086", file: UploadFile = None):
    profile_id = user.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="No profile linked")
    photo = None
    if file:
        file_content = await file.read()
        if len(file_content) > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")
        fname = f"story_{uuid.uuid4().hex[:12]}{Path(file.filename).suffix}"
        (UPLOAD_DIR / fname).write_bytes(file_content)
        photo = fname
        content_type = "photo"
    if not content and not photo:
        raise HTTPException(status_code=400, detail="Content required")
    story_id = create_story(profile_id, content_type, content or "", background, photo, STORY_EXPIRY_HOURS)
    log_analytics_event("story_posted", profile_id)
    return {"id": story_id}


@app.post("/api/stories/text")
def post_text_story(body: StoryCreate, user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="No profile linked")
    story_id = create_story(profile_id, body.content_type, body.content, body.background, None, STORY_EXPIRY_HOURS)
    log_analytics_event("story_posted", profile_id)
    return {"id": story_id}


@app.get("/api/stories/feed")
def stories_feed(user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="No profile linked")
    return {"stories": get_stories_feed(profile_id)}


@app.get("/api/stories/{story_id}")
def read_story(story_id: str, user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    story = get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if profile_id and profile_id != story["profile_id"]:
        view_story(story_id, profile_id)
    return story


@app.delete("/api/stories/{story_id}")
def remove_story(story_id: str, user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id or not delete_story(story_id, profile_id):
        raise HTTPException(status_code=404, detail="Story not found")
    return {"message": "Story deleted"}


# ---------------------------------------------------------------------------
# Group Polls
# ---------------------------------------------------------------------------

@app.post("/api/groups/{group_id}/polls")
def create_poll(group_id: str, body: PollCreate, user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id or not is_group_member(group_id, profile_id):
        raise HTTPException(status_code=403, detail="Not a group member")
    if len(body.options) < 2 or len(body.options) > 10:
        raise HTTPException(status_code=400, detail="2-10 options required")
    poll_id = create_group_poll(group_id, profile_id, body.question, body.options)
    return {"id": poll_id}


@app.get("/api/groups/{group_id}/polls")
def list_polls(group_id: str, user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    polls = get_group_polls(group_id)
    for p in polls:
        p["my_vote"] = get_poll_user_vote(p["id"], profile_id) if profile_id else None
    return {"polls": polls}


@app.post("/api/polls/{poll_id}/vote")
def submit_vote(poll_id: str, body: PollVote, user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="No profile linked")
    if not vote_poll(poll_id, profile_id, body.option_index):
        raise HTTPException(status_code=400, detail="Already voted")
    return {"message": "Vote recorded"}


# ---------------------------------------------------------------------------
# Incognito Mode
# ---------------------------------------------------------------------------

@app.post("/api/settings/incognito")
def toggle_incognito(body: IncognitoUpdate, user: dict = Depends(require_user)):
    set_incognito_mode(user["id"], body.enabled)
    return {"incognito": body.enabled}


@app.get("/api/settings/incognito")
def get_incognito(user: dict = Depends(require_user)):
    return {"incognito": is_incognito(user["id"])}


# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------

@app.get("/api/sessions")
def list_sessions(user: dict = Depends(require_user)):
    return {"sessions": get_user_sessions(user["id"])}


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str, user: dict = Depends(require_user)):
    if not revoke_session(session_id, user["id"]):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session revoked"}


@app.post("/api/sessions/revoke-all")
def revoke_other_sessions(user: dict = Depends(require_user)):
    revoke_all_sessions(user["id"])
    return {"message": "All other sessions revoked"}


# ---------------------------------------------------------------------------
# Account Deletion (GDPR)
# ---------------------------------------------------------------------------

@app.delete("/api/account")
def delete_user_account(body: AccountDeleteConfirm, user: dict = Depends(require_user)):
    if body.confirmation != "DELETE":
        raise HTTPException(status_code=400, detail="Type DELETE to confirm")
    if not delete_account(user["id"]):
        raise HTTPException(status_code=500, detail="Failed to delete account")
    log_analytics_event("account_deleted", user.get("profile_id"))
    return {"message": "Account deleted"}


# ---------------------------------------------------------------------------
# Data Export (GDPR)
# ---------------------------------------------------------------------------

@app.get("/api/account/export")
def export_data(user: dict = Depends(require_user)):
    data = export_user_data(user["id"])
    if not data:
        raise HTTPException(status_code=404, detail="No data found")
    return data


# ---------------------------------------------------------------------------
# 2FA Recovery Codes
# ---------------------------------------------------------------------------

@app.post("/api/2fa/recovery-codes")
def generate_recovery_codes(user: dict = Depends(require_user)):
    totp = get_totp_secret(user["id"])
    if not totp or not totp.get("verified"):
        raise HTTPException(status_code=400, detail="2FA not enabled")
    codes = [secrets.token_hex(4).upper() for _ in range(10)]
    code_hashes = [hashlib.sha256(c.encode()).hexdigest() for c in codes]
    save_recovery_codes(user["id"], code_hashes)
    return {"codes": codes, "warning": "Save these codes. They cannot be shown again."}


@app.get("/api/2fa/recovery-codes/count")
def recovery_code_count(user: dict = Depends(require_user)):
    return {"remaining": get_recovery_code_count(user["id"])}


@app.post("/api/2fa/recover")
def use_2fa_recovery(code: str, user: dict = Depends(require_user)):
    code_hash = hashlib.sha256(code.strip().upper().encode()).hexdigest()
    if not use_recovery_code(user["id"], code_hash):
        raise HTTPException(status_code=400, detail="Invalid or used recovery code")
    return {"message": "Recovery code accepted", "remaining": get_recovery_code_count(user["id"])}


# ---------------------------------------------------------------------------
# Mutual Friends
# ---------------------------------------------------------------------------

@app.get("/api/mutual-friends/{profile_id}")
def mutual_friends(profile_id: str, user: dict = Depends(require_user)):
    my_profile = user.get("profile_id")
    if not my_profile:
        return {"mutual_friends": [], "count": 0}
    friends = get_mutual_friends(my_profile, profile_id)
    return {"mutual_friends": friends, "count": len(friends)}


# ---------------------------------------------------------------------------
# Message Search
# ---------------------------------------------------------------------------

@app.get("/api/messages/search")
def msg_search(q: str = "", user: dict = Depends(require_user)):
    profile_id = user.get("profile_id")
    if not profile_id or not q.strip():
        return {"results": []}
    return {"results": search_messages(profile_id, q.strip())}


# ---------------------------------------------------------------------------
# Location Matching
# ---------------------------------------------------------------------------

@app.post("/api/settings/location")
def update_location(body: LocationUpdate, user: dict = Depends(require_user)):
    save_user_location(user["id"], body.latitude, body.longitude,
                       body.city, body.radius_km, body.enabled)
    return {"message": "Location updated"}


@app.get("/api/settings/location")
def get_location(user: dict = Depends(require_user)):
    loc = get_user_location(user["id"])
    return loc or {"latitude": None, "longitude": None, "city": "", "radius_km": 100, "enabled": False}


@app.get("/api/nearby")
def nearby_profiles(user: dict = Depends(require_user)):
    loc = get_user_location(user["id"])
    if not loc or not loc.get("enabled") or not loc.get("latitude"):
        return {"profiles": [], "message": "Location not enabled"}
    profile_id = user.get("profile_id", "")
    profiles = get_nearby_profiles(
        loc["latitude"], loc["longitude"],
        loc.get("radius_km", LOCATION_MATCH_RADIUS_KM),
        exclude_id=profile_id,
    )
    return {"profiles": [{
        "id": p["id"], "name": p["name"], "age": p["age"],
        "photo": p.get("photo"), "location": p.get("location"),
    } for p in profiles]}


# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------

@app.get("/api/i18n/locales")
def list_locales():
    from app.i18n import get_available_locales
    return {"locales": get_available_locales(), "default": DEFAULT_LOCALE}


@app.get("/api/i18n/translations/{locale}")
def get_translations(locale: str):
    from app.i18n import get_translations as _get_translations
    return {"locale": locale, "translations": _get_translations(locale)}


# ---------------------------------------------------------------------------
# Static Files
# ---------------------------------------------------------------------------

UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse(str(STATIC_DIR / "index.html"))
