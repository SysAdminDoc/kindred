import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from app import database
from app.photo_safety import (
    ExternalScanResult,
    PhotoDNAHashHook,
    PhotoSafetyScanner,
    compute_photo_hashes,
)
from app.photo_safety_corpus import load_records


def image_bytes(color=(120, 60, 200)) -> bytes:
    output = BytesIO()
    Image.new("RGB", (40, 30), color).save(output, format="JPEG")
    return output.getvalue()


class PhotoSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        old_conn = getattr(database._local, "conn", None)
        if old_conn is not None:
            old_conn.close()
        database._local.conn = None
        database.DB_PATH = Path(self.temp.name) / "kindred.db"
        database.init_db()
        database.save_profile({
            "id": "profile-1",
            "name": "Profile",
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

    def test_hashes_are_deterministic_and_use_two_algorithms(self):
        first = compute_photo_hashes(image_bytes())
        second = compute_photo_hashes(image_bytes())
        self.assertEqual(first, second)
        self.assertRegex(first.phash, r"^[0-9a-f]{16}$")
        self.assertRegex(first.dhash, r"^[0-9a-f]{16}$")

    def test_local_corpus_match_blocks_and_records_only_hash_metadata(self):
        hashes = compute_photo_hashes(image_bytes())
        database.add_known_abuse_photo_hash(hashes.phash, hashes.dhash, "test-corpus", "ref-1")
        scanner = PhotoSafetyScanner(
            external_hook=PhotoDNAHashHook(enabled=False),
        )
        scanner.initialize()
        result = scanner.scan(
            image_bytes(), profile_id="profile-1", filename="upload.jpg"
        )
        self.assertTrue(result.blocked)
        self.assertEqual(result.reason, "local_known_abuse_match")
        events = database.get_photo_safety_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["photo_filename"], "upload.jpg")

    def test_required_external_outage_blocks(self):
        class UnavailableHook:
            enabled = True

            def initialize(self):
                return None

            def health(self):
                return {"enabled": True, "configured": True}

            def scan(self, hashes):
                return ExternalScanResult(status="unavailable")

        scanner = PhotoSafetyScanner(
            safety_required=True,
            external_hook=UnavailableHook(),
        )
        result = scanner.scan(
            image_bytes(), profile_id="profile-1", filename="upload.jpg"
        )
        self.assertTrue(result.blocked)
        self.assertEqual(result.reason, "photodna_unavailable")

    def test_hash_hook_sends_hashes_and_interprets_match(self):
        hook = PhotoDNAHashHook(enabled=True, url="https://hook.example/scan", api_key="secret")
        response = type("Response", (), {
            "__enter__": lambda self: self,
            "__exit__": lambda self, *args: None,
            "read": lambda self: b'{"matched": true}',
        })()
        with patch("app.photo_safety.urlopen", return_value=response) as open_url:
            result = hook.scan(compute_photo_hashes(image_bytes()))
        self.assertTrue(result.matched)
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("Ocp-apim-subscription-key"), "secret")
        self.assertEqual(json.loads(request.data.decode())["phash"].__len__(), 16)

    def test_corpus_loader_validates_hash_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corpus.json"
            path.write_text(json.dumps({
                "records": [{
                    "phash": "0" * 16,
                    "dhash": "f" * 16,
                    "source": "operator",
                }]
            }), encoding="utf-8")
            records = load_records(path, "fallback")
        self.assertEqual(records[0]["source"], "operator")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps([{"phash": "bad", "dhash": "0" * 16}]), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_records(path, "fallback")


if __name__ == "__main__":
    unittest.main()
