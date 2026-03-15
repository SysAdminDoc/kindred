"""
Kindred v1.6.0 - Admin Server
Separate admin experience on port 8001.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from passlib.hash import bcrypt
from pydantic import BaseModel

import sys
import os

from app.config import (
    JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS,
    ADMIN_EMAIL, ADMIN_PASSWORD, CORS_ORIGINS,
    BCRYPT_ROUNDS, DB_PATH, BACKUP_INTERVAL_HOURS, BACKUP_KEEP_COUNT,
    DEFAULT_LOCALE,
)
from app.database import (
    init_db, get_profile, get_all_profiles, delete_profile,
    get_conversation_count,
    get_all_invites, create_invite,
    save_feedback, get_stats,
    get_date_plans,
    get_behavioral_profile,
    get_all_safety_reports,
    get_blog_posts, get_profile_comments, get_friends,
    create_user, get_user_by_email, get_user_by_id,
    get_all_groups, get_group, get_group_members, delete_group,
    get_all_events, get_event, get_event_rsvps, delete_event,
    get_pending_verifications, review_verification,
    get_pending_photo_moderations, review_photo_moderation,
    get_analytics_summary, get_engagement_metrics,
    get_content_filter_logs,
    get_all_active_stories, delete_story,
    get_all_sessions, revoke_session, revoke_all_sessions,
    get_session_count, get_location_enabled_count,
    get_super_like_count,
    UPLOAD_DIR,
)

admin_app = FastAPI(title="Kindred Admin", version="1.6.0")

admin_app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


def require_admin(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    if not creds:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = get_user_by_id(payload["sub"])
        if not user or not user["is_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

STATIC_DIR = Path(__file__).parent.parent / "static"


class FeedbackSubmit(BaseModel):
    profile_a: str
    profile_b: str
    went_on_date: bool = False
    rating: int | None = None
    safety_rating: int | None = None
    would_meet_again: bool | None = None
    notes: str | None = None


class AdminLogin(BaseModel):
    email: str
    password: str


@admin_app.on_event("startup")
def startup():
    init_db()
    # Create default admin if none exists
    from app.database import get_db
    conn = get_db()
    row = conn.execute("SELECT 1 FROM users WHERE is_admin=1").fetchone()
    conn.close()
    if not row:
        pw_hash = bcrypt.using(rounds=BCRYPT_ROUNDS).hash(ADMIN_PASSWORD)
        create_user(ADMIN_EMAIL, pw_hash, "Admin", is_admin=True)


# ─── Admin Auth ───
@admin_app.post("/api/admin/login")
def admin_login(body: AdminLogin):
    user = get_user_by_email(body.email)
    if not user or not bcrypt.verify(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Not an admin account")
    payload = {
        "sub": user["id"],
        "admin": True,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"token": token, "user_id": user["id"], "display_name": user["display_name"]}


# ─── Dashboard Stats ───
@admin_app.get("/api/admin/stats")
def admin_stats():
    stats = get_stats()
    stats["ai_narratives"] = "Puter.js (client-side)"
    return stats


# ─── Profiles (read + delete) ───
@admin_app.get("/api/profiles")
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


@admin_app.get("/api/profile/{profile_id}")
def read_profile(profile_id: str):
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {k: v for k, v in profile.items() if k != "embedding"}


@admin_app.delete("/api/profile/{profile_id}")
def remove_profile(profile_id: str):
    if not delete_profile(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"message": "Profile deleted"}


# ─── Profile Details (for admin inspection) ───
@admin_app.get("/api/profile/{profile_id}/blog")
def list_blog(profile_id: str):
    return {"posts": get_blog_posts(profile_id)}


@admin_app.get("/api/profile/{profile_id}/comments")
def list_comments(profile_id: str):
    comments = get_profile_comments(profile_id)
    for c in comments:
        author = get_profile(c["from_id"])
        c["from_name"] = author["name"] if author else "Unknown"
        c["from_photo"] = author.get("photo") if author else None
    return {"comments": comments}


@admin_app.get("/api/profile/{profile_id}/friends")
def list_friends(profile_id: str):
    return {"friends": get_friends(profile_id)}


# ─── Behavioral ───
@admin_app.get("/api/behavioral/{profile_id}")
def get_behavior(profile_id: str):
    return get_behavioral_profile(profile_id)


# ─── Date Plans ───
@admin_app.get("/api/date-plans/{profile_id}")
def get_plans(profile_id: str):
    plans = get_date_plans(profile_id)
    for p in plans:
        pa = get_profile(p["profile_a"])
        pb = get_profile(p["profile_b"])
        p["name_a"] = pa["name"] if pa else "Unknown"
        p["name_b"] = pb["name"] if pb else "Unknown"
    return {"plans": plans}


# ─── Safety Reports ───
@admin_app.get("/api/admin/safety-reports")
def list_safety_reports():
    reports = get_all_safety_reports()
    for r in reports:
        reporter = get_profile(r["reporter_id"])
        reported = get_profile(r["reported_id"])
        r["reporter_name"] = reporter["name"] if reporter else "Unknown"
        r["reported_name"] = reported["name"] if reported else "Unknown"
    return {"reports": reports}


# ─── Invites ───
@admin_app.post("/api/invites")
def gen_invite(created_by: str = "admin"):
    code = create_invite(created_by)
    return {"code": code}


@admin_app.get("/api/invites")
def list_invites():
    return {"invites": get_all_invites()}


# ─── Feedback ───
@admin_app.post("/api/feedback")
def submit_feedback(fb: FeedbackSubmit):
    fb_id = save_feedback(
        fb.profile_a, fb.profile_b, fb.went_on_date,
        fb.rating, fb.notes, fb.safety_rating, fb.would_meet_again
    )
    return {"id": fb_id, "message": "Feedback submitted"}


# ─── Groups (admin) ───
@admin_app.get("/api/admin/groups")
def admin_list_groups():
    groups = get_all_groups(limit=200)
    for g in groups:
        g["members"] = get_group_members(g["id"])
    return {"groups": groups}


@admin_app.get("/api/admin/groups/{group_id}")
def admin_view_group(group_id: str):
    g = get_group(group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    g["members"] = get_group_members(group_id)
    creator = get_profile(g["creator_id"])
    g["creator_name"] = creator["name"] if creator else "Unknown"
    return g


@admin_app.delete("/api/admin/groups/{group_id}")
def admin_delete_group(group_id: str):
    if not delete_group(group_id):
        raise HTTPException(status_code=404, detail="Group not found")
    return {"message": "Group deleted"}


# ─── Events (admin) ───
@admin_app.get("/api/admin/events")
def admin_list_events():
    events = get_all_events(limit=200)
    for ev in events:
        ev["rsvps"] = get_event_rsvps(ev["id"])
    return {"events": events}


@admin_app.get("/api/admin/events/{event_id}")
def admin_view_event(event_id: str):
    ev = get_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    ev["rsvps"] = get_event_rsvps(event_id)
    creator = get_profile(ev["creator_id"])
    ev["creator_name"] = creator["name"] if creator else "Unknown"
    return ev


@admin_app.delete("/api/admin/events/{event_id}")
def admin_delete_event(event_id: str):
    if not delete_event(event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted"}


# ─── Selfie Verification (admin review) ───
@admin_app.get("/api/admin/verifications")
def list_verifications():
    return {"verifications": get_pending_verifications()}


@admin_app.post("/api/admin/verifications/{verification_id}/approve")
def approve_verification(verification_id: str):
    if not review_verification(verification_id, approved=True):
        raise HTTPException(status_code=404, detail="Verification not found")
    return {"message": "Verification approved, profile now verified"}


@admin_app.post("/api/admin/verifications/{verification_id}/reject")
def reject_verification(verification_id: str):
    if not review_verification(verification_id, approved=False):
        raise HTTPException(status_code=404, detail="Verification not found")
    return {"message": "Verification rejected"}


# ─── Photo Moderation (admin review) ───
@admin_app.get("/api/admin/photo-moderation")
def list_photo_moderations(admin: dict = Depends(require_admin)):
    return {"photos": get_pending_photo_moderations()}


@admin_app.post("/api/admin/photo-moderation/{mod_id}/approve")
def approve_photo(mod_id: str, admin: dict = Depends(require_admin)):
    if not review_photo_moderation(mod_id, approved=True, reviewer_id=admin["id"]):
        raise HTTPException(status_code=404, detail="Photo moderation entry not found")
    return {"message": "Photo approved"}


@admin_app.post("/api/admin/photo-moderation/{mod_id}/reject")
def reject_photo(mod_id: str, admin: dict = Depends(require_admin)):
    if not review_photo_moderation(mod_id, approved=False, reviewer_id=admin["id"]):
        raise HTTPException(status_code=404, detail="Photo moderation entry not found")
    return {"message": "Photo rejected"}


# ─── Analytics ───
@admin_app.get("/api/admin/analytics")
def admin_analytics(days: int = 30, admin: dict = Depends(require_admin)):
    summary = get_analytics_summary(days)
    engagement = get_engagement_metrics(min(days, 7))
    return {"summary": summary, "engagement": engagement}


# ─── Content Filter Log ───
@admin_app.get("/api/admin/content-filter-log")
def admin_content_filter_log(limit: int = 100, admin: dict = Depends(require_admin)):
    logs = get_content_filter_logs(limit)
    return {"logs": logs}


# ─── Health Check ───
@admin_app.get("/api/health")
def health_check():
    db_size_mb = round(DB_PATH.stat().st_size / (1024 * 1024), 2) if DB_PATH.exists() else 0
    return {
        "status": "healthy",
        "version": "1.6.0",
        "python": sys.version,
        "database_size_mb": db_size_mb,
        "pid": os.getpid(),
    }


# ─── Backups ───
@admin_app.get("/api/admin/backups")
def list_backups(admin: dict = Depends(require_admin)):
    from app.backup import list_backups as _list_backups
    return {
        "backups": _list_backups(),
        "scheduler": {
            "interval_hours": BACKUP_INTERVAL_HOURS,
            "keep_count": BACKUP_KEEP_COUNT,
        },
    }


@admin_app.post("/api/admin/backups")
def create_backup(admin: dict = Depends(require_admin)):
    from app.backup import create_backup as _create_backup
    name = _create_backup()
    return {"filename": name, "message": "Backup created"}


@admin_app.post("/api/admin/backups/restore")
def restore_backup(filename: str, admin: dict = Depends(require_admin)):
    from app.backup import restore_backup as _restore_backup
    if not _restore_backup(filename):
        raise HTTPException(status_code=404, detail="Backup not found")
    return {"message": f"Restored from {filename}"}


# ─── Session Management (admin) ───
@admin_app.get("/api/admin/sessions")
def admin_list_sessions(admin: dict = Depends(require_admin)):
    return {"sessions": get_all_sessions(), "count": get_session_count()}


@admin_app.delete("/api/admin/sessions/{session_id}")
def admin_revoke_session(session_id: str, admin: dict = Depends(require_admin)):
    if not revoke_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session revoked"}


@admin_app.post("/api/admin/sessions/revoke-user/{user_id}")
def admin_revoke_user_sessions(user_id: str, admin: dict = Depends(require_admin)):
    revoke_all_sessions(user_id)
    return {"message": "All sessions revoked for user"}


# ─── Stories Moderation ───
@admin_app.get("/api/admin/stories")
def admin_list_stories(admin: dict = Depends(require_admin)):
    return {"stories": get_all_active_stories()}


@admin_app.delete("/api/admin/stories/{story_id}")
def admin_delete_story(story_id: str, admin: dict = Depends(require_admin)):
    from app.database import get_db
    conn = get_db()
    cursor = conn.execute("DELETE FROM stories WHERE id=?", (story_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"message": "Story removed"}


# ─── i18n Admin ───
@admin_app.get("/api/admin/i18n/locales")
def admin_locales(admin: dict = Depends(require_admin)):
    from app.i18n import get_available_locales
    return {"locales": get_available_locales(), "default": DEFAULT_LOCALE}


# ─── Static Files ───
UPLOAD_DIR.mkdir(exist_ok=True)
admin_app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
admin_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@admin_app.get("/")
def serve_admin():
    return FileResponse(str(STATIC_DIR / "admin.html"))
