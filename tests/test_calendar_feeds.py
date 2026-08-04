import tempfile
import unittest
from pathlib import Path

from app import database
from app.calendar_feed import render_calendar


class CalendarFeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        old_conn = getattr(database._local, "conn", None)
        if old_conn is not None:
            old_conn.close()
        database._local.conn = None
        database.DB_PATH = Path(self.temp.name) / "kindred.db"
        database.init_db()

        for profile_id in ("alice", "bob", "outsider"):
            database.save_profile({
                "id": profile_id,
                "name": profile_id.title(),
                "age": 30,
                "gender": "x",
                "seeking": "x",
            })
        database.toggle_like("alice", "profile", "bob")
        database.toggle_like("bob", "profile", "alice")
        self.schedule = database.create_date_schedule(
            "alice", "bob", "alice", "2026-09-01", "18:30",
            "Coffee, & Co.", "Bring a question\nand an open mind",
        )

    def tearDown(self):
        conn = getattr(database._local, "conn", None)
        if conn is not None:
            conn.close()
        database._local.conn = None
        database.DB_PATH = self.old_db_path
        self.temp.cleanup()

    def test_feed_token_is_hashed_and_calendar_round_trips(self):
        feed = database.create_calendar_feed("alice", "bob", "alice")
        stored_hash = database.get_db().execute(
            "SELECT token_hash FROM calendar_feeds WHERE id=?", (feed["id"],)
        ).fetchone()["token_hash"]
        self.assertNotEqual(stored_hash, feed["token"])
        self.assertEqual(
            database.get_calendar_feed_by_token(feed["token"])["profile_a"],
            "alice",
        )

        calendar = render_calendar([{
            **database.get_date_schedule(self.schedule["id"]),
            "status": "accepted",
        }])
        self.assertIn("BEGIN:VCALENDAR\r\n", calendar)
        self.assertIn("UID:" + self.schedule["id"] + "@kindred", calendar)
        self.assertIn("DTSTART:20260901T183000", calendar)
        self.assertIn("LOCATION:Coffee\\, & Co.", calendar)
        self.assertIn("DESCRIPTION:Bring a question\\nand an open mind", calendar)
        self.assertIn("STATUS:CONFIRMED", calendar)

        self.assertTrue(database.revoke_calendar_feed("bob", "alice"))
        self.assertIsNone(database.get_calendar_feed_by_token(feed["token"]))

    def test_shared_feed_route_requires_match_and_revocation_stops_access(self):
        from app import main

        class RequestStub:
            @staticmethod
            def url_for(name, **values):
                return f"https://kindred.test/api/calendar/{values['token']}.ics"

        response = main.create_shared_calendar_feed_endpoint(
            "bob", RequestStub(), {"profile_id": "alice"}
        )
        self.assertIn("/api/calendar/", response["url"])
        token = response["url"].rsplit("/", 1)[-1].removesuffix(".ics")
        ics_response = main.calendar_feed_ics(token)
        self.assertEqual(ics_response.status_code, 200)
        self.assertIn("Kindred Date", ics_response.body.decode("utf-8"))

        with self.assertRaises(main.HTTPException) as denied:
            main._require_calendar_pair("outsider", {"profile_id": "alice"})
        self.assertEqual(denied.exception.status_code, 403)

        database.toggle_like("bob", "profile", "alice")
        with self.assertRaises(main.HTTPException) as expired:
            main.calendar_feed_ics(token)
        self.assertEqual(expired.exception.status_code, 404)

    def test_one_off_export_is_limited_to_date_participants(self):
        from app import main

        with self.assertRaises(main.HTTPException) as denied:
            main.export_date_ics(self.schedule["id"], {"profile_id": "outsider"})
        self.assertEqual(denied.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
