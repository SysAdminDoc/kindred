import tempfile
import unittest
from pathlib import Path

from app import database


class WeightLearningPersistenceTests(unittest.TestCase):
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

        for profile_id in ("rater", "partner"):
            database.save_profile({
                "id": profile_id,
                "name": profile_id,
                "age": 30,
                "gender": "x",
                "seeking": "x",
            })
        self.schedule_id = database.create_date_schedule(
            "rater", "partner", "rater", "2026-08-03"
        )["id"]

    def tearDown(self):
        conn = getattr(database._local, "conn", None)
        if conn is not None:
            conn.close()
        database._local.conn = None
        database.DB_PATH = self.old_db_path
        database.UPLOAD_DIR = self.old_upload_dir
        self.temp.cleanup()

    def test_learning_event_updates_profile_and_is_idempotent(self):
        previous = {}
        updated = {"personality": 0.3, "values": 0.2}
        breakdown = {"personality": 70, "values": 50}

        self.assertTrue(database.save_weight_learning(
            "rater", "partner", self.schedule_id, 0.75,
            breakdown, previous, updated,
        ))
        self.assertFalse(database.save_weight_learning(
            "rater", "partner", self.schedule_id, 0.25,
            breakdown, updated, previous,
        ))

        profile = database.get_profile("rater")
        self.assertEqual(profile["learned_weight_prefs"], updated)
        events = database.get_weight_learning_events("rater")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["outcome"], 0.75)
        self.assertEqual(events[0]["breakdown"], breakdown)

    def test_embedding_update_and_moderation_submission_are_idempotent(self):
        self.assertTrue(database.update_profile_embedding("rater", b"embedding"))
        self.assertEqual(database.get_profile("rater")["embedding"], b"embedding")

        first = database.submit_photo_for_moderation("rater", "rater.jpg")
        second = database.submit_photo_for_moderation("rater", "rater.jpg")
        self.assertEqual(first, second)
        self.assertEqual(len(database.get_pending_photo_moderations()), 1)


if __name__ == "__main__":
    unittest.main()
