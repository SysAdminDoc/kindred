"""
Kindred v2.5.0 - Audit Logging
Tracks admin actions for accountability.
"""

import uuid
from datetime import datetime, timezone

from app.database import get_db


def log_audit(admin_user_id: str, action: str, target_type: str = None,
              target_id: str = None, details: str = None):
    """Log an admin action."""
    conn = get_db()
    conn.execute("""
        INSERT INTO audit_log (id, admin_user_id, action, target_type, target_id, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (uuid.uuid4().hex[:12], admin_user_id, action, target_type, target_id,
          details, datetime.now(timezone.utc).isoformat()))
    conn.commit()


def get_audit_logs(limit: int = 100, offset: int = 0, action_filter: str = None) -> list[dict]:
    """Retrieve audit logs with optional filtering."""
    conn = get_db()
    if action_filter:
        action_filter = action_filter.replace('%', '\\%').replace('_', '\\_')
        rows = conn.execute(
            """SELECT a.*, u.email as admin_email FROM audit_log a
               LEFT JOIN users u ON u.id = a.admin_user_id
               WHERE a.action LIKE ? ESCAPE '\\'
               ORDER BY a.created_at DESC LIMIT ? OFFSET ?""",
            (f"%{action_filter}%", limit, offset)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT a.*, u.email as admin_email FROM audit_log a
               LEFT JOIN users u ON u.id = a.admin_user_id
               ORDER BY a.created_at DESC LIMIT ? OFFSET ?""",
            (limit, offset)
        ).fetchall()
    return [dict(r) for r in rows]


def get_audit_log_count() -> int:
    conn = get_db()
    return conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
