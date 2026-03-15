"""
Kindred v1.7.0 - Webhook System
Configurable outbound webhooks for platform events.
"""

import json
import uuid
import threading
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError

from app.database import get_db
from app.logging_config import get_logger

log = get_logger("webhooks")


def create_webhook(name: str, url: str, events: list[str], secret: str = "") -> dict:
    """Register a new webhook endpoint."""
    conn = get_db()
    wh_id = uuid.uuid4().hex[:12]
    conn.execute("""
        INSERT INTO webhooks (id, name, url, events, secret, enabled, created_at)
        VALUES (?, ?, ?, ?, ?, 1, ?)
    """, (wh_id, name, url, json.dumps(events), secret,
          datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return {"id": wh_id, "name": name, "url": url, "events": events}


def get_webhooks() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM webhooks ORDER BY created_at DESC").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["events"] = json.loads(d.get("events", "[]"))
        result.append(d)
    return result


def update_webhook(wh_id: str, **kwargs) -> bool:
    conn = get_db()
    sets = []
    vals = []
    for k, v in kwargs.items():
        if k in ("name", "url", "secret", "enabled"):
            sets.append(f"{k}=?")
            vals.append(v)
        elif k == "events":
            sets.append("events=?")
            vals.append(json.dumps(v))
    if not sets:
        return False
    vals.append(wh_id)
    conn.execute(f"UPDATE webhooks SET {', '.join(sets)} WHERE id=?", vals)
    conn.commit()
    return True


def delete_webhook(wh_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute("DELETE FROM webhooks WHERE id=?", (wh_id,))
    conn.commit()
    return cursor.rowcount > 0


def fire_webhook(event_type: str, payload: dict):
    """Fire webhooks for a given event type (non-blocking)."""
    from app.config import WEBHOOKS_ENABLED
    if not WEBHOOKS_ENABLED:
        return

    conn = get_db()
    hooks = conn.execute(
        "SELECT * FROM webhooks WHERE enabled=1"
    ).fetchall()

    for hook in hooks:
        events = json.loads(hook["events"] or "[]")
        if "*" in events or event_type in events:
            threading.Thread(
                target=_send_webhook,
                args=(hook["url"], hook["secret"], event_type, payload),
                daemon=True,
            ).start()


def _send_webhook(url: str, secret: str, event_type: str, payload: dict):
    """Send a webhook POST request."""
    body = json.dumps({
        "event": event_type,
        "data": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if secret:
        import hashlib
        import hmac
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-Kindred-Signature"] = sig
    try:
        req = Request(url, data=body, headers=headers, method="POST")
        urlopen(req, timeout=10)
    except (URLError, OSError) as e:
        log.warning(f"Webhook delivery failed to {url}: {e}")
