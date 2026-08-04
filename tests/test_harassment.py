import tempfile
import unittest
from pathlib import Path

from app import database
from app.harassment import analyze_message, decide


class HarassmentDetectorTests(unittest.TestCase):
    def test_threat_is_immediately_mute_level(self):
        signal = analyze_message("I will find you at your house")
        self.assertEqual(signal.score, 4)
        self.assertIn("threat", signal.categories)
        decision = decide(signal, 0, 0, warn_score=2, mute_score=4)
        self.assertEqual(decision.action, "auto_mute")

    def test_sliding_window_escalates_repeated_targeted_abuse(self):
        signal = analyze_message("you are an idiot")
        self.assertEqual(signal.score, 1)
        self.assertEqual(decide(signal, 0, 0).action, "flagged")
        self.assertEqual(decide(signal, 1, 1).action, "warn")
        self.assertEqual(decide(signal, 3, 3).action, "auto_mute")


class HarassmentPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        old_conn = getattr(database._local, "conn", None)
        if old_conn is not None:
            old_conn.close()
        database._local.conn = None
        database.DB_PATH = Path(self.temp.name) / "kindred.db"
        database.init_db()
        for profile_id in ("sender", "recipient"):
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

    def test_window_and_mute_are_persisted(self):
        database.record_harassment_event(
            "sender", "recipient", 1, ("targeted_abuse",), "flagged"
        )
        window = database.get_harassment_window("sender", "recipient", 10)
        self.assertEqual(window, {"score": 1, "count": 1})
        database.create_harassment_mute(
            "recipient", "sender", "targeted_abuse", 4, minutes=60
        )
        self.assertTrue(database.is_profile_muted("recipient", "sender"))
        mutes = database.get_harassment_mutes()
        self.assertEqual(len(mutes), 1)
        self.assertEqual(mutes[0]["owner_name"], "Recipient")
        events = database.get_harassment_events()
        self.assertEqual(events[0]["categories"], ["targeted_abuse"])


if __name__ == "__main__":
    unittest.main()
