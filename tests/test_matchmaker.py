import asyncio
import tempfile
import unittest
from pathlib import Path

from app import database
from app import main


class MatchmakerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        old_conn = getattr(database._local, "conn", None)
        if old_conn is not None:
            old_conn.close()
        database._local.conn = None
        database.DB_PATH = Path(self.temp.name) / "kindred.db"
        database.init_db()

        for profile_id in ("alice", "bob", "candidate"):
            database.save_profile({
                "id": profile_id,
                "name": profile_id.title(),
                "age": 30,
                "gender": "x",
                "seeking": "x",
                "headline": f"{profile_id} headline",
            })
            user_id = database.create_user(f"{profile_id}@example.test", "hash")
            database.link_profile_to_user(user_id, profile_id)
        database.send_friend_request("alice", "bob")
        self.assertTrue(database.respond_friend_request("bob", "alice", True))

    def tearDown(self):
        conn = getattr(database._local, "conn", None)
        if conn is not None:
            conn.close()
        database._local.conn = None
        database.DB_PATH = self.old_db_path
        self.temp.cleanup()

    def test_friend_can_propose_and_recipient_accepts_as_a_like(self):
        proposal = asyncio.run(main.create_matchmaker_proposal_endpoint(
            main.MatchmakerProposalCreate(
                friend_id="bob", suggested_id="candidate", note="You both love hiking."
            ),
            {"profile_id": "alice"},
        ))
        self.assertEqual(proposal["status"], "pending")
        self.assertEqual(proposal["suggested_name"], "Candidate")
        self.assertEqual(
            database.get_notifications(database.get_user_by_profile_id("bob")["id"])[0]["type"],
            "matchmaker_proposal",
        )

        received = main.list_matchmaker_proposals({"profile_id": "bob"})
        self.assertEqual(len(received["received"]), 1)
        self.assertEqual(received["received"][0]["proposer_name"], "Alice")

        response = asyncio.run(main.respond_to_matchmaker_proposal(
            proposal["id"],
            main.MatchmakerProposalAction(accept=True),
            {"profile_id": "bob"},
        ))
        self.assertFalse(response["matched"])
        self.assertTrue(database.has_liked("bob", "profile", "candidate"))
        self.assertEqual(response["proposal"]["status"], "accepted")

    def test_only_accepted_friends_can_propose_and_pending_duplicates_are_rejected(self):
        with self.assertRaises(main.HTTPException) as denied:
            asyncio.run(main.create_matchmaker_proposal_endpoint(
                main.MatchmakerProposalCreate(friend_id="candidate", suggested_id="bob"),
                {"profile_id": "alice"},
            ))
        self.assertEqual(denied.exception.status_code, 403)

        first = asyncio.run(main.create_matchmaker_proposal_endpoint(
            main.MatchmakerProposalCreate(friend_id="bob", suggested_id="candidate"),
            {"profile_id": "alice"},
        ))
        with self.assertRaises(main.HTTPException) as duplicate:
            asyncio.run(main.create_matchmaker_proposal_endpoint(
                main.MatchmakerProposalCreate(friend_id="bob", suggested_id="candidate"),
                {"profile_id": "alice"},
            ))
        self.assertEqual(duplicate.exception.status_code, 409)

        self.assertEqual(
            main.withdraw_matchmaker_proposal_endpoint(first["id"], {"profile_id": "alice"})["message"],
            "Suggestion withdrawn",
        )


if __name__ == "__main__":
    unittest.main()
