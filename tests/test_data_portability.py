import json
import tempfile
import unittest
from pathlib import Path

from app import database
from app.main import app, export_schema_org_data


class DataPortabilityTests(unittest.TestCase):
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
            "id": "portable-profile",
            "name": "Portable Person",
            "age": 34,
            "gender": "nonbinary",
            "seeking": "any",
            "country": "US",
            "relationship_intent": "long_term",
            "dating_energy": "calm",
            "dating_pace": "slow",
            "love_language": "quality_time",
            "photo": "portable.jpg",
        })
        database.update_profile_field(
            "portable-profile", "about_me", "A curious person who loves trail walks."
        )
        database.update_profile_field("portable-profile", "interests", "hiking, music")
        self.user_id = database.create_user(
            "portable@example.com", "hash", "Portable Person"
        )
        database.link_profile_to_user(self.user_id, "portable-profile")

    def tearDown(self):
        conn = getattr(database._local, "conn", None)
        if conn is not None:
            conn.close()
        database._local.conn = None
        database.DB_PATH = self.old_db_path
        database.UPLOAD_DIR = self.old_upload_dir
        self.temp.cleanup()

    def test_kindred_export_is_versioned_and_retains_full_export_shape(self):
        data = database.export_user_data(self.user_id)

        self.assertEqual(data["format"], "kindred")
        self.assertEqual(data["schema_version"], "1.0")
        self.assertTrue(data["exported_at"])
        self.assertEqual(data["user"]["email"], "portable@example.com")
        self.assertEqual(data["profile"]["id"], "portable-profile")
        self.assertNotIn("embedding", data["profile"])

    def test_schema_org_export_uses_person_json_ld_and_custom_properties(self):
        data = database.export_schema_org_person(self.user_id)

        self.assertEqual(data["@context"], "https://schema.org")
        self.assertEqual(data["@type"], "Person")
        self.assertEqual(data["identifier"]["value"], "portable-profile")
        self.assertEqual(data["name"], "Portable Person")
        self.assertEqual(data["email"], "portable@example.com")
        self.assertEqual(data["gender"], "nonbinary")
        self.assertEqual(data["nationality"]["name"], "US")
        self.assertEqual(data["knowsAbout"], ["hiking", "music"])
        properties = {
            item["propertyID"]: item["value"]
            for item in data["additionalProperty"]
        }
        self.assertEqual(properties["kindredAge"], 34)
        self.assertEqual(properties["kindredPhotoKey"], "portable.jpg")

    def test_schema_org_endpoint_returns_downloadable_json_ld(self):
        response = export_schema_org_data(database.get_user_by_id(self.user_id))

        self.assertEqual(response.media_type, "application/ld+json")
        self.assertIn("kindred-person.jsonld", response.headers["content-disposition"])
        payload = json.loads(response.body)
        self.assertEqual(payload["@type"], "Person")
        self.assertIn("/api/account/export/schema-org", {
            route.path for route in app.routes
        })


if __name__ == "__main__":
    unittest.main()
