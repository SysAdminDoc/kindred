import tempfile
import unittest
from pathlib import Path

from app import database


class ReportCoolingOffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        old_conn = getattr(database._local, "conn", None)
        if old_conn is not None:
            old_conn.close()
        database._local.conn = None
        database.DB_PATH = Path(self.temp.name) / "kindred.db"
        database.init_db()
        for profile_id in ("reporter", "reported", "other"):
            database.save_profile({
                "id": profile_id,
                "name": profile_id.title(),
                "age": 30,
                "gender": "x",
                "seeking": "x",
            })

    def tearDown(self):
        conn = getattr(database._local, "conn", None)
        if conn is not None:
            conn.close()
        database._local.conn = None
        database.DB_PATH = self.old_db_path
        self.temp.cleanup()

    def test_basic_report_creates_pair_exclusion(self):
        report_id = database.create_safety_report(
            "reporter", "reported", "user", "unwanted contact"
        )

        self.assertTrue(report_id)
        self.assertIn("reported", database.get_report_cooling_off_ids("reporter"))
        self.assertTrue(database.is_report_cooling_off("reporter", "reported"))
        self.assertFalse(database.is_report_cooling_off("reported", "reporter"))

    def test_structured_report_renews_existing_exclusion(self):
        database.create_report_cooling_off("reporter", "reported", days=1)
        first = database.get_db().execute(
            "SELECT expires_at FROM report_cooling_off WHERE reporter_id=? AND reported_id=?",
            ("reporter", "reported"),
        ).fetchone()["expires_at"]

        report_id = database.create_safety_report_v2(
            "reporter", "reported", "user", "harassment", "Repeated contact"
        )
        second = database.get_db().execute(
            "SELECT expires_at FROM report_cooling_off WHERE reporter_id=? AND reported_id=?",
            ("reporter", "reported"),
        ).fetchone()["expires_at"]

        self.assertTrue(report_id)
        self.assertGreater(second, first)
        self.assertEqual(
            database.get_db().execute(
                "SELECT COUNT(*) FROM report_cooling_off WHERE reporter_id=? AND reported_id=?",
                ("reporter", "reported"),
            ).fetchone()[0],
            1,
        )

    def test_expired_exclusion_is_not_returned(self):
        database.create_report_cooling_off("reporter", "reported", days=30)
        database.get_db().execute(
            "UPDATE report_cooling_off SET expires_at=datetime('now', '-1 second')"
        )
        database.get_db().commit()

        self.assertFalse(database.is_report_cooling_off("reporter", "reported"))
        self.assertNotIn("reported", database.get_report_cooling_off_ids("reporter"))

    def test_zero_days_is_permanent(self):
        database.create_report_cooling_off("reporter", "reported", days=0)

        self.assertTrue(database.is_report_cooling_off("reporter", "reported"))
        expires_at = database.get_db().execute(
            "SELECT expires_at FROM report_cooling_off WHERE reporter_id=? AND reported_id=?",
            ("reporter", "reported"),
        ).fetchone()["expires_at"]
        self.assertEqual(expires_at, "9999-12-31 23:59:59")


if __name__ == "__main__":
    unittest.main()
