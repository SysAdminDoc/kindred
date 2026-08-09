import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app import database, federation, main


class FederationTests(unittest.TestCase):
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
            "id": "local-profile",
            "name": "Local Member",
            "age": 32,
            "gender": "nonbinary",
            "seeking": "any",
            "big_five": {"openness": 99},
            "open_ended": {"private": "do not publish"},
            "embedding": b"private embedding",
            "photo": "profile.jpg",
        })
        database.update_profile_field(
            "local-profile", "about_me", "A public introduction."
        )
        database.update_profile_field("local-profile", "interests", "music, hiking")
        self.patchers = [
            patch.object(federation, "FEDERATION_ENABLED", True),
            patch.object(federation, "FEDERATION_BASE_URL", "https://kindred.example"),
            patch.object(
                federation,
                "FEDERATION_KEY_PATH",
                Path(self.temp.name) / "federation-key.pem",
            ),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        conn = getattr(database._local, "conn", None)
        if conn is not None:
            conn.close()
        database._local.conn = None
        database.DB_PATH = self.old_db_path
        database.UPLOAD_DIR = self.old_upload_dir
        self.temp.cleanup()

    @staticmethod
    def _remote_actor() -> dict:
        private = Ed25519PrivateKey.generate()
        public_pem = private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        actor_id = "https://remote.example/users/remote-profile"
        return {
            "@context": federation.ACTIVITYSTREAMS_CONTEXT,
            "id": actor_id,
            "type": "Person",
            "preferredUsername": "remote-profile",
            "name": "Remote Member",
            "inbox": "https://remote.example/api/federation/inbox",
            "outbox": "https://remote.example/users/remote-profile/outbox",
            "publicKey": {
                "id": actor_id + "#main-key",
                "owner": actor_id,
                "publicKeyPem": public_pem,
            },
        }

    def test_actor_and_webfinger_exclude_private_vault_fields(self):
        actor = federation.build_actor(database.get_profile("local-profile"))

        self.assertEqual(actor["type"], "Person")
        self.assertEqual(actor["id"], "https://kindred.example/users/local-profile")
        self.assertEqual(actor["summary"], "A public introduction.")
        self.assertEqual(actor["attachment"][0]["value"], ["music", "hiking"])
        self.assertNotIn("big_five", actor)
        self.assertNotIn("open_ended", actor)
        self.assertNotIn("embedding", actor)
        self.assertNotIn("email", actor)
        self.assertEqual(
            federation.build_webfinger(database.get_profile("local-profile"))["subject"],
            "acct:local-profile@kindred.example",
        )

    def test_ed25519_signed_request_round_trips_and_detects_tampering(self):
        actor = federation.build_actor(database.get_profile("local-profile"))
        body = json.dumps({"type": "Create", "actor": actor["id"]}).encode("utf-8")
        url = "https://kindred.example/api/federation/inbox"
        headers = federation.build_signed_headers("POST", url, body, actor["id"])

        federation.verify_incoming_signature(
            "POST", url, body, headers, actor, now=datetime.now(timezone.utc)
        )
        with self.assertRaises(federation.SignatureVerificationError):
            federation.verify_incoming_signature(
                "POST", url, body + b"!", headers, actor, now=datetime.now(timezone.utc)
            )

    def test_remote_peer_match_and_outbox_are_account_scoped(self):
        remote = federation._validate_actor(self._remote_actor())
        database.upsert_federated_peer(remote)
        match = database.create_federated_match(
            "local-profile", remote["id"], "https://remote.example/matches/1"
        )
        activity, _ = federation.new_match_activity(
            federation.actor_url("local-profile"), remote["id"]
        )
        outbox = database.record_federation_outbox("local-profile", activity)

        self.assertEqual(match["status"], "pending")
        self.assertEqual(database.get_federated_matches("local-profile")[0]["handle"], "remote-profile")
        self.assertEqual(database.get_federation_outbox("local-profile")[0]["type"], "Create")
        self.assertEqual(outbox["activity_id"], activity["id"])

    def test_public_actor_route_is_opt_in(self):
        actor = main.federation_actor("local-profile")
        self.assertEqual(actor["id"], "https://kindred.example/users/local-profile")
        with patch.object(federation, "FEDERATION_ENABLED", False):
            with self.assertRaises(main.HTTPException) as denied:
                main.federation_actor("local-profile")
        self.assertEqual(denied.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
