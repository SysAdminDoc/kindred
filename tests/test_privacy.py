import tempfile
import unittest
from pathlib import Path

from app import database
from app.privacy import (
    get_privacy_audit,
    prune_retention_rows,
    purge_inactive_accounts,
)


class PrivacyRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        self.old_upload_dir = database.UPLOAD_DIR
        old_conn = getattr(database._local, "conn", None)
        if old_conn is not None:
            old_conn.close()
        database._local.conn = None
        database.DB_PATH = Path(self.temp.name) / "kindred.db"
        database.UPLOAD_DIR = Path(self.temp.name) / "uploads"
        database.init_db()

    def tearDown(self):
        conn = getattr(database._local, "conn", None)
        if conn is not None:
            conn.close()
        database._local.conn = None
        database.DB_PATH = self.old_db_path
        database.UPLOAD_DIR = self.old_upload_dir
        self.temp.cleanup()

    def test_every_schema_field_has_a_tag_and_every_table_has_a_policy(self):
        audit = get_privacy_audit()
        self.assertTrue(audit["coverage_complete"])
        self.assertEqual(audit["field_count"], audit["tagged_field_count"])
        self.assertGreater(audit["pii_field_count"], 0)
        self.assertEqual(audit["untagged_fields"], [])
        self.assertEqual(audit["missing_table_policies"], [])

    def test_hard_delete_removes_unlinked_account_records_and_media(self):
        profile_id = database.save_profile({
            "id": "profile-1",
            "name": "Delete Me",
            "age": 30,
            "gender": "x",
            "seeking": "x",
            "photo": "profile-1.jpg",
        })
        user_id = database.create_user("delete@example.com", "hash", "Delete Me")
        database.link_profile_to_user(user_id, profile_id)
        conn = database.get_db()
        conn.execute(
            "UPDATE profiles SET deactivated=1, last_active=? WHERE id=?",
            ("2020-01-01T00:00:00+00:00", profile_id),
        )
        conn.execute(
            "INSERT INTO oauth_accounts "
            "(id,user_id,provider,provider_user_id,email,access_token,refresh_token,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            ("oauth-1", user_id, "test", "subject", "delete@example.com", "access", "refresh", "2020-01-01"),
        )
        conn.execute(
            "INSERT INTO request_logs "
            "(id,request_id,method,path,status_code,duration_ms,user_id,ip_address,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            ("request-1", "req", "GET", "/", 200, 1, user_id, "192.0.2.1", "2020-01-01"),
        )
        conn.execute(
            "INSERT INTO analytics_events (id,event_type,profile_id,metadata,created_at) "
            "VALUES (?,?,?,?,?)",
            ("analytics-1", "view", profile_id, "{}", "2020-01-01"),
        )
        conn.commit()

        deleted_media = []
        result = purge_inactive_accounts(
            months=1,
            media_deleter=deleted_media.append,
        )

        self.assertEqual(result["deleted_accounts"], 1)
        self.assertEqual(deleted_media, ["profile-1.jpg"])
        self.assertIsNone(database.get_user_by_id(user_id))
        self.assertIsNone(database.get_profile(profile_id))
        self.assertIsNone(conn.execute(
            "SELECT 1 FROM oauth_accounts WHERE user_id=?", (user_id,)
        ).fetchone())
        self.assertIsNone(conn.execute(
            "SELECT 1 FROM request_logs WHERE user_id=?", (user_id,)
        ).fetchone())
        self.assertIsNone(conn.execute(
            "SELECT 1 FROM analytics_events WHERE profile_id=?", (profile_id,)
        ).fetchone())

    def test_automatic_retention_prunes_only_explicit_short_lived_rows(self):
        conn = database.get_db()
        conn.execute(
            "INSERT INTO request_logs "
            "(id,request_id,method,path,status_code,duration_ms,user_id,ip_address,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            ("old", "req-old", "GET", "/", 200, 1, None, "192.0.2.2", "2020-01-01"),
        )
        conn.execute(
            "INSERT INTO profiles (id,name) VALUES (?,?)",
            ("kept", "Keep Me"),
        )
        conn.commit()

        deleted = prune_retention_rows()

        self.assertGreaterEqual(deleted, 1)
        self.assertIsNone(conn.execute(
            "SELECT 1 FROM request_logs WHERE id='old'"
        ).fetchone())
        self.assertIsNotNone(conn.execute(
            "SELECT 1 FROM profiles WHERE id='kept'"
        ).fetchone())


if __name__ == "__main__":
    unittest.main()
