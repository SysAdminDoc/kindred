import tempfile
import unittest
from pathlib import Path

from app import database


class LocalEventDiscoveryTests(unittest.TestCase):
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
            "id": "host",
            "name": "Host",
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

    def test_nearby_events_are_distance_sorted_and_far_events_are_filtered(self):
        near_id = database.create_event(
            "Near meetup", "", "host", event_date="2026-09-01",
            latitude=40.713, longitude=-74.006,
        )
        database.create_event(
            "Far meetup", "", "host", event_date="2026-09-02",
            latitude=41.9, longitude=-87.6,
        )

        nearby = database.get_events_nearby(40.7128, -74.006, radius_km=10)
        self.assertEqual([event["id"] for event in nearby], [near_id])
        self.assertLess(nearby[0]["distance_km"], 1)

    def test_local_events_endpoint_uses_saved_location(self):
        from app import main

        user_id = database.create_user("host@example.com", "hash")
        database.link_profile_to_user(user_id, "host")
        database.save_user_location(user_id, 40.7128, -74.006, "New York", 25, True)
        event_id = database.create_event(
            "Saved-location meetup", "", "host", event_date="2026-09-03",
            latitude=40.72, longitude=-74.01,
        )

        result = main.list_local_events(25, {"id": user_id})
        self.assertTrue(result["location_enabled"])
        self.assertEqual(result["center"]["latitude"], 40.7128)
        self.assertEqual(result["events"][0]["id"], event_id)

    def test_event_coordinates_are_validated_as_a_pair(self):
        from app import main

        with self.assertRaises(main.HTTPException) as missing_pair:
            main.create_event_endpoint(
                main.EventCreate(title="Invalid", latitude=40.0),
                {"profile_id": "host"},
            )
        self.assertEqual(missing_pair.exception.status_code, 400)

        with self.assertRaises(main.HTTPException) as out_of_range:
            main.create_event_endpoint(
                main.EventCreate(title="Invalid", latitude=95.0, longitude=10.0),
                {"profile_id": "host"},
            )
        self.assertEqual(out_of_range.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
