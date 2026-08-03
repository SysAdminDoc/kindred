"""Optional Redis-backed sessions and shared rate-limit readiness checks."""

from __future__ import annotations

import json
import logging
import secrets
from collections.abc import Awaitable, Callable, Iterable
from datetime import datetime, timezone
from typing import Any

from app.config import REDIS_KEY_PREFIX, REDIS_REQUIRED, REDIS_URL

logger = logging.getLogger(__name__)


class RedisConfigurationError(RuntimeError):
    """Raised when Redis is required but cannot be used."""


class RedisSessionStore:
    """Store refresh-token sessions in Redis when explicitly configured.

    The store is deliberately lazy so importing the app does not require a
    Redis server during local development. A missing or unavailable optional
    Redis instance falls back to SQLite; required mode fails closed.
    """

    def __init__(
        self,
        redis_url: str = "",
        required: bool = False,
        prefix: str = "kindred",
        client_factory: Callable[[str], Any] | None = None,
    ):
        self.redis_url = redis_url.strip()
        self.required = required
        self.prefix = prefix
        self._client_factory = client_factory
        self._client: Any = None
        self._backend = "uninitialized"

    def initialize(self) -> str:
        """Connect once and return ``redis`` or the development fallback."""
        if self._backend != "uninitialized":
            return self._backend
        if not self.redis_url:
            if self.required:
                raise RedisConfigurationError(
                    "KINDRED_REDIS_REQUIRED is enabled but KINDRED_REDIS_URL is empty"
                )
            self._backend = "sqlite"
            return self._backend

        try:
            if self._client_factory:
                client = self._client_factory(self.redis_url)
            else:
                import redis
                client = redis.Redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
            client.ping()
        except Exception as exc:
            self._client = None
            self._backend = "sqlite"
            if self.required:
                raise RedisConfigurationError(
                    f"Required Redis backend is unavailable: {exc}"
                ) from exc
            logger.warning("Redis unavailable; using SQLite session fallback: %s", exc)
            return self._backend

        self._client = client
        self._backend = "redis"
        return self._backend

    def reset(self) -> None:
        """Reset the lazy connection state (primarily useful for tests)."""
        self._client = None
        self._backend = "uninitialized"

    @property
    def enabled(self) -> bool:
        return self.initialize() == "redis"

    @property
    def backend_name(self) -> str:
        return self.initialize()

    @property
    def rate_limit_storage_uri(self) -> str:
        """Return a slowapi storage URI after validating configured Redis."""
        return self.redis_url if self.enabled else "memory://"

    def health(self) -> dict[str, Any]:
        backend = self.backend_name
        return {
            "configured": bool(self.redis_url),
            "required": self.required,
            "backend": backend,
            "healthy": backend == "redis" or not self.required,
        }

    def _session_key(self, session_id: str) -> str:
        return f"{self.prefix}:session:{session_id}"

    def _token_key(self, token_hash: str) -> str:
        return f"{self.prefix}:session-token:{token_hash}"

    def _user_key(self, user_id: str) -> str:
        return f"{self.prefix}:user-sessions:{user_id}"

    def _websocket_channel(self) -> str:
        return f"{self.prefix}:websocket-events"

    def _websocket_presence_index(self, profile_id: str) -> str:
        return f"{self.prefix}:websocket-presence:{profile_id}"

    def _websocket_presence_key(self, profile_id: str, connection_id: str) -> str:
        return f"{self.prefix}:websocket-presence:{profile_id}:{connection_id}"

    def publish_websocket(self, profile_id: str, data: dict[str, Any]) -> bool:
        """Publish a message for every WebSocket worker to fan out locally."""
        if not self.enabled:
            return False
        event = json.dumps(
            {"profile_id": profile_id, "data": data},
            separators=(",", ":"),
        )
        try:
            self._client.publish(self._websocket_channel(), event)
        except Exception as exc:
            logger.warning("Redis WebSocket publish failed: %s", exc)
            return False
        return True

    def add_websocket_presence(
        self,
        profile_id: str,
        connection_id: str,
        ttl_seconds: int = 90,
    ) -> bool:
        """Register one connection with a short-lived distributed presence key."""
        if not self.enabled:
            return False
        key = self._websocket_presence_key(profile_id, connection_id)
        index = self._websocket_presence_index(profile_id)
        try:
            self._client.set(key, "1", ex=max(1, ttl_seconds))
            self._client.sadd(index, key)
        except Exception as exc:
            logger.warning("Redis WebSocket presence registration failed: %s", exc)
            return False
        return True

    def refresh_websocket_presence(
        self,
        profile_id: str,
        connection_id: str,
        ttl_seconds: int = 90,
    ) -> bool:
        """Extend a live connection's presence lease."""
        if not self.enabled:
            return False
        key = self._websocket_presence_key(profile_id, connection_id)
        try:
            return bool(self._client.expire(key, max(1, ttl_seconds)))
        except Exception as exc:
            logger.warning("Redis WebSocket presence refresh failed: %s", exc)
            return False

    def remove_websocket_presence(self, profile_id: str, connection_id: str) -> bool:
        """Remove a connection and its presence index entry."""
        if not self.enabled:
            return False
        key = self._websocket_presence_key(profile_id, connection_id)
        try:
            self._client.delete(key)
            self._client.srem(self._websocket_presence_index(profile_id), key)
        except Exception as exc:
            logger.warning("Redis WebSocket presence removal failed: %s", exc)
            return False
        return True

    def websocket_online_profiles(self, profile_ids: Iterable[str]) -> set[str]:
        """Return profiles with at least one non-expired distributed connection."""
        if not self.enabled:
            return set()
        online: set[str] = set()
        for profile_id in profile_ids:
            index = self._websocket_presence_index(profile_id)
            try:
                members = self._client.smembers(index)
                for key in members:
                    if self._client.exists(key):
                        online.add(profile_id)
                    else:
                        self._client.srem(index, key)
            except Exception as exc:
                logger.warning("Redis WebSocket presence lookup failed: %s", exc)
                break
        return online

    async def listen_websocket_events(
        self,
        handler: Callable[[str, dict[str, Any]], Awaitable[None]],
        stop_event: Any,
    ) -> None:
        """Listen for WebSocket events until the owning ASGI worker shuts down."""
        if not self.enabled:
            return
        import redis.asyncio as redis_asyncio

        client = redis_asyncio.Redis.from_url(
            self.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        pubsub = client.pubsub()
        try:
            await pubsub.subscribe(self._websocket_channel())
            while not stop_event.is_set():
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if not message or message.get("type") != "message":
                    continue
                try:
                    event = json.loads(message.get("data", "{}"))
                    profile_id = event.get("profile_id")
                    data = event.get("data")
                    if profile_id and isinstance(data, dict):
                        await handler(str(profile_id), data)
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    logger.warning("Ignoring malformed Redis WebSocket event: %s", exc)
        finally:
            try:
                await pubsub.unsubscribe(self._websocket_channel())
            except Exception:
                pass
            try:
                await pubsub.aclose()
            except Exception:
                pass
            try:
                await client.aclose()
            except Exception:
                pass

    def _ttl(self, expires_at: str) -> int:
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            return max(1, int((expiry - datetime.now(timezone.utc)).total_seconds()))
        except (TypeError, ValueError):
            return 86400

    def create_session(
        self,
        user_id: str,
        token_hash: str,
        expires_at: str,
        device: str = "",
        ip_address: str = "",
    ) -> str | None:
        if not self.enabled:
            return None
        session_id = secrets.token_urlsafe(24)
        now = datetime.now(timezone.utc).isoformat()
        ttl = self._ttl(expires_at)
        client = self._client
        client.hset(self._session_key(session_id), mapping={
            "user_id": user_id,
            "token_hash": token_hash,
            "device": device[:200],
            "ip_address": ip_address[:200],
            "expires_at": expires_at,
            "last_active": now,
            "created_at": now,
        })
        client.expire(self._session_key(session_id), ttl)
        client.set(self._token_key(token_hash), session_id, ex=ttl)
        client.sadd(self._user_key(user_id), session_id)
        return session_id

    def get_refresh_token(self, token_hash: str) -> dict | None:
        if not self.enabled:
            return None
        client = self._client
        session_id = client.get(self._token_key(token_hash))
        if not session_id:
            return None
        data = client.hgetall(self._session_key(session_id))
        if not data:
            client.delete(self._token_key(token_hash))
            return None
        data["id"] = session_id
        data["revoked"] = 0
        # The refresh route expects the SQLite-compatible field name.
        data["expires_at"] = self._session_expiry(data, client, session_id)
        return data

    def _session_expiry(self, data: dict, client, session_id: str) -> str:
        expires_at = data.get("expires_at")
        if expires_at:
            return expires_at
        ttl = client.ttl(self._session_key(session_id))
        return str(ttl)

    def touch_session(self, session_id: str) -> bool:
        if not self.enabled:
            return False
        changed = self._client.hset(
            self._session_key(session_id),
            "last_active",
            datetime.now(timezone.utc).isoformat(),
        )
        return bool(changed or self._client.exists(self._session_key(session_id)))

    def revoke_session(self, session_id: str, user_id: str | None = None) -> bool:
        if not self.enabled:
            return False
        client = self._client
        key = self._session_key(session_id)
        data = client.hgetall(key)
        if not data or (user_id and data.get("user_id") != user_id):
            return False
        client.delete(key)
        if data.get("token_hash"):
            client.delete(self._token_key(data["token_hash"]))
        client.srem(self._user_key(data.get("user_id", "")), session_id)
        return True

    def revoke_refresh_token(self, token_hash: str) -> bool:
        if not self.enabled:
            return False
        session_id = self._client.get(self._token_key(token_hash))
        return bool(session_id and self.revoke_session(session_id))

    def revoke_all_sessions(self, user_id: str) -> int:
        if not self.enabled:
            return 0
        client = self._client
        session_ids = list(client.smembers(self._user_key(user_id)))
        removed = sum(1 for session_id in session_ids if self.revoke_session(session_id, user_id))
        client.delete(self._user_key(user_id))
        return removed

    def list_sessions(self, user_id: str) -> list[dict]:
        if not self.enabled:
            return []
        sessions = []
        for session_id in self._client.smembers(self._user_key(user_id)):
            data = self._client.hgetall(self._session_key(session_id))
            if not data:
                self._client.srem(self._user_key(user_id), session_id)
                continue
            sessions.append({
                "id": session_id,
                "user_id": data.get("user_id", user_id),
                "device": data.get("device", ""),
                "ip_address": data.get("ip_address", ""),
                "last_active": data.get("last_active"),
                "created_at": data.get("created_at"),
            })
        sessions.sort(key=lambda item: item.get("last_active") or "", reverse=True)
        return sessions

    def list_all_sessions(self, limit: int = 200) -> list[dict]:
        if not self.enabled:
            return []
        sessions = []
        for key in self._client.scan_iter(match=f"{self.prefix}:session:*"):
            session_id = key.rsplit(":", 1)[-1]
            data = self._client.hgetall(key)
            if data:
                sessions.append({
                    "id": session_id,
                    "user_id": data.get("user_id"),
                    "device": data.get("device", ""),
                    "ip_address": data.get("ip_address", ""),
                    "last_active": data.get("last_active"),
                    "created_at": data.get("created_at"),
                })
        sessions.sort(key=lambda item: item.get("last_active") or "", reverse=True)
        return sessions[:max(1, min(limit, 1000))]


redis_sessions = RedisSessionStore(
    REDIS_URL,
    required=REDIS_REQUIRED,
    prefix=REDIS_KEY_PREFIX,
)
