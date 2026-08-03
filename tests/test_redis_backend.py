import fnmatch
import unittest
from datetime import datetime, timedelta, timezone

from app.redis_backend import RedisConfigurationError, RedisSessionStore


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.hashes = {}
        self.sets = {}
        self.expirations = {}

    def ping(self):
        return True

    def hset(self, name, key=None, value=None, mapping=None):
        self.hashes.setdefault(name, {})
        if mapping is not None:
            self.hashes[name].update(mapping)
        else:
            self.hashes[name][key] = value
        return 1

    def hgetall(self, name):
        return dict(self.hashes.get(name, {}))

    def expire(self, name, seconds):
        self.expirations[name] = seconds
        return True

    def ttl(self, name):
        return self.expirations.get(name, -1)

    def set(self, name, value, ex=None):
        self.values[name] = value
        if ex is not None:
            self.expirations[name] = ex
        return True

    def get(self, name):
        return self.values.get(name)

    def delete(self, *names):
        removed = 0
        for name in names:
            removed += int(name in self.values or name in self.hashes or name in self.sets)
            self.values.pop(name, None)
            self.hashes.pop(name, None)
            self.sets.pop(name, None)
        return removed

    def sadd(self, name, value):
        self.sets.setdefault(name, set()).add(value)
        return 1

    def smembers(self, name):
        return set(self.sets.get(name, set()))

    def srem(self, name, value):
        values = self.sets.get(name, set())
        if value in values:
            values.remove(value)
            return 1
        return 0

    def exists(self, name):
        return int(name in self.values or name in self.hashes or name in self.sets)

    def scan_iter(self, match=None):
        names = list(self.hashes)
        return (name for name in names if not match or fnmatch.fnmatch(name, match))


class RedisSessionStoreTests(unittest.TestCase):
    def test_refresh_sessions_and_rate_limit_uri_share_redis(self):
        client = FakeRedis()
        store = RedisSessionStore(
            "redis://test",
            required=True,
            prefix="test",
            client_factory=lambda _: client,
        )
        expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        self.assertEqual(store.rate_limit_storage_uri, "redis://test")
        session_id = store.create_session(
            "user-1", "hash-1", expires, device="browser", ip_address="127.0.0.1"
        )
        stored = store.get_refresh_token("hash-1")
        self.assertEqual(stored["id"], session_id)
        self.assertEqual(stored["user_id"], "user-1")
        self.assertEqual(store.list_sessions("user-1")[0]["device"], "browser")
        self.assertTrue(store.revoke_refresh_token("hash-1"))
        self.assertIsNone(store.get_refresh_token("hash-1"))

    def test_required_mode_fails_without_a_url(self):
        store = RedisSessionStore(required=True)

        with self.assertRaises(RedisConfigurationError):
            store.initialize()

    def test_local_mode_uses_sqlite_and_memory_rate_limits(self):
        store = RedisSessionStore()

        self.assertEqual(store.backend_name, "sqlite")
        self.assertEqual(store.rate_limit_storage_uri, "memory://")


if __name__ == "__main__":
    unittest.main()
