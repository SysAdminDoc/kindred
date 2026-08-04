import tempfile
import unittest
from pathlib import Path

from app import database
from app.transcription import (
    OpenAICompatibleTranscriber,
    TranscriptionConfigurationError,
    transcribe_and_store,
)


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.payload


class VoiceTranscriptionTests(unittest.TestCase):
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
        for profile_id in ("sender", "recipient"):
            database.save_profile({
                "id": profile_id,
                "name": profile_id,
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
        database.UPLOAD_DIR = self.old_upload_dir
        self.temp.cleanup()

    def test_disabled_adapter_is_explicitly_accessible(self):
        adapter = OpenAICompatibleTranscriber(enabled=False)
        result = adapter.transcribe(
            b"audio", filename="voice.webm", content_type="audio/webm"
        )
        self.assertEqual(result.status, "disabled")
        self.assertFalse(adapter.health()["ready"])

    def test_enabled_adapter_requires_endpoint(self):
        adapter = OpenAICompatibleTranscriber(enabled=True, url="")
        with self.assertRaises(TranscriptionConfigurationError):
            adapter.initialize()

    def test_adapter_posts_openai_compatible_multipart_and_reads_text(self):
        captured = {}

        def opener(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse(b'{"text":"Hello from Kindred"}')

        adapter = OpenAICompatibleTranscriber(
            enabled=True,
            url="https://transcribe.example/v1/audio/transcriptions",
            api_key="secret",
            model="tiny",
            timeout_seconds=9,
            opener=opener,
        )
        result = adapter.transcribe(
            b"OggS\x00audio",
            filename="voice.ogg",
            content_type="audio/ogg",
        )

        self.assertEqual(result.status, "transcribed")
        self.assertEqual(result.text, "Hello from Kindred")
        self.assertEqual(captured["timeout"], 9)
        self.assertEqual(captured["request"].get_header("Authorization"), "Bearer secret")
        body = captured["request"].data
        self.assertIn(b'name="model"', body)
        self.assertIn(b"tiny", body)
        self.assertIn(b'filename="voice.ogg"', body)
        self.assertIn(b"OggS", body)

    def test_voice_rows_persist_transcription_state_and_metadata(self):
        voice_id = database.save_voice_message(
            "sender",
            "recipient",
            "voice.webm",
            duration_ms=1250,
            mime_type="audio/webm",
            transcription_status="queued",
        )
        queued = database.get_voice_message(voice_id)
        self.assertEqual(queued["duration_ms"], 1250)
        self.assertEqual(queued["transcription_status"], "queued")
        self.assertEqual(queued["mime_type"], "audio/webm")

        database.update_voice_transcription(
            voice_id,
            "transcribed",
            transcript="A safe transcript",
            provider="test-provider",
        )
        result = database.get_voice_messages("sender", "recipient")
        self.assertEqual(result[0]["transcript"], "A safe transcript")
        self.assertEqual(result[0]["transcription_provider"], "test-provider")
        self.assertIsNotNone(result[0]["transcribed_at"])

    def test_inline_persistence_keeps_audio_delivery_when_disabled(self):
        voice_id = database.save_voice_message(
            "sender", "recipient", "voice.webm", transcription_status="queued"
        )
        result = transcribe_and_store(
            voice_id,
            b"audio",
            filename="voice.webm",
            content_type="audio/webm",
        )
        self.assertEqual(result.status, "disabled")
        voice = database.get_voice_message(voice_id)
        self.assertEqual(voice["transcription_status"], "disabled")
        self.assertIsNone(voice["transcript"])


if __name__ == "__main__":
    unittest.main()
