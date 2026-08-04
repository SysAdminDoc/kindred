import unittest
from unittest.mock import patch

from app.job_queue import JobQueue, job_queue
from app.tasks import generate_profile_embedding, queue_photo_moderation, transcribe_voice_message


class JobQueueTests(unittest.TestCase):
    def test_local_mode_keeps_inline_backend(self):
        self.assertEqual(job_queue.backend_name, "inline")
        self.assertTrue(job_queue.health()["healthy"])

    def test_required_mode_without_redis_fails_closed(self):
        queue = JobQueue(enabled=True, required=True)
        with self.assertRaisesRegex(RuntimeError, "KINDRED_QUEUE_REQUIRED"):
            queue.initialize()

    def test_actors_have_separate_retryable_queues(self):
        self.assertEqual(generate_profile_embedding.queue_name, "kindred-embeddings")
        self.assertEqual(queue_photo_moderation.queue_name, "kindred-moderation")
        self.assertEqual(transcribe_voice_message.queue_name, "kindred-transcription")
        self.assertEqual(generate_profile_embedding.options["max_retries"], 3)
        self.assertEqual(queue_photo_moderation.options["max_retries"], 3)
        self.assertEqual(transcribe_voice_message.options["max_retries"], 3)

    def test_embedding_actor_is_idempotent_when_profile_is_already_ready(self):
        with patch("app.tasks.init_db"), patch("app.tasks.get_profile", return_value={"embedding": b"ready"}), \
             patch("app.tasks.generate_embedding") as generate:
            self.assertEqual(generate_profile_embedding.fn("profile-1"), "embedding-already-present")
            generate.assert_not_called()

    def test_photo_actor_submits_manual_review_record(self):
        with patch("app.tasks.init_db"), patch(
            "app.tasks.submit_photo_for_moderation", return_value="moderation-1"
        ) as submit:
            result = queue_photo_moderation.fn("profile-1", "profile.jpg")
        self.assertEqual(result, "moderation-1")
        submit.assert_called_once_with("profile-1", "profile.jpg")


if __name__ == "__main__":
    unittest.main()
