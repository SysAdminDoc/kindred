import tempfile
import unittest
from pathlib import Path

from app import database
from app.explanations import explain_match_decision
from app.main import app, get_matches, match_explanation, suspension_explanation


class RightToExplanationTests(unittest.TestCase):
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

        database.save_profile({
            "id": "viewer",
            "name": "Viewer",
            "age": 30,
            "gender": "woman",
            "seeking": "man",
        })
        database.save_profile({
            "id": "target",
            "name": "Target",
            "age": 31,
            "gender": "man",
            "seeking": "woman",
        })
        database.save_profile({
            "id": "mismatch",
            "name": "Mismatch",
            "age": 31,
            "gender": "woman",
            "seeking": "woman",
        })
        self.user_id = database.create_user("viewer@example.com", "hash", "Viewer")
        database.link_profile_to_user(self.user_id, "viewer")
        self.admin_id = database.create_user("admin@example.com", "hash", "Admin", True)

    def tearDown(self):
        conn = getattr(database._local, "conn", None)
        if conn is not None:
            conn.close()
        database._local.conn = None
        database.DB_PATH = self.old_db_path
        database.UPLOAD_DIR = self.old_upload_dir
        self.temp.cleanup()

    def test_match_explanation_reports_score_and_private_weight_application(self):
        result = match_explanation("target", database.get_user_by_id(self.user_id))

        self.assertEqual(result["decision"], "shown")
        self.assertEqual(result["algorithmic_outcome"], "match_shown")
        self.assertEqual(result["score"]["total"], 45.0)
        self.assertEqual(result["score"]["weights"]["personality"], 0.2)
        self.assertIn("eligible_for_matching", {
            reason["code"] for reason in result["reasons"]
        })

    def test_match_explanation_reports_safety_and_preference_hiding(self):
        database.block_profile("viewer", "target")
        blocked = match_explanation("target", database.get_user_by_id(self.user_id))
        self.assertEqual(blocked["decision"], "hidden")
        self.assertEqual(blocked["reasons"][0]["code"], "safety_block")
        self.assertEqual(get_matches("viewer")["matches"], [])

        database.unblock_profile("viewer", "target")
        mismatch = match_explanation("mismatch", database.get_user_by_id(self.user_id))
        self.assertEqual(mismatch["decision"], "hidden")
        self.assertEqual(mismatch["reasons"][0]["code"], "viewer_preference_mismatch")

    def test_match_explanation_honors_report_cooling_off(self):
        database.create_report_cooling_off("viewer", "target", days=7)

        result = match_explanation("target", database.get_user_by_id(self.user_id))

        self.assertEqual(result["decision"], "hidden")
        self.assertEqual(result["reasons"][0]["code"], "report_cooling_off")

    def test_suspension_explanation_contains_reason_and_appeal_state(self):
        suspension_id = database.suspend_user(
            self.user_id,
            "Repeated targeted harassment",
            self.admin_id,
            suspension_type="temporary",
            duration_days=7,
        )

        result = suspension_explanation(database.get_user_by_id(self.user_id))

        self.assertEqual(result["decision"], "suspended")
        self.assertEqual(result["reasons"][0]["code"], "active_suspension")
        self.assertEqual(result["suspensions"][0]["reason"], "Repeated targeted harassment")
        self.assertNotIn("suspended_by", result["suspensions"][0])

        database.submit_appeal(suspension_id, "I would like this reviewed.")
        pending = suspension_explanation(database.get_user_by_id(self.user_id))
        self.assertEqual(pending["suspensions"][0]["appeal_status"], "pending")

        database.unsuspend_user(self.user_id)
        active = suspension_explanation(database.get_user_by_id(self.user_id))
        self.assertEqual(active["decision"], "active")

    def test_explanation_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        self.assertIn("/api/explanations/match/{target_id}", paths)
        self.assertIn("/api/right-to-explanation/match/{target_id}", paths)
        self.assertIn("/api/explanations/suspension", paths)
        self.assertIn("/api/right-to-explanation/suspension", paths)

    def test_missing_target_is_a_hidden_decision_without_score(self):
        result = explain_match_decision(
            database.get_profile("viewer"),
            None,
            evaluated_at="2026-08-03T00:00:00+00:00",
        )

        self.assertEqual(result["decision"], "hidden")
        self.assertIsNone(result["score"])
        self.assertEqual(result["evaluated_at"], "2026-08-03T00:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
