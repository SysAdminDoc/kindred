from io import BytesIO
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from app.selfie_liveness import SelfieLivenessAnalyzer


def image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (48, 48), (90, 120, 160)).save(output, format="JPEG")
    return output.getvalue()


def landmarks(ear: float, yaw: float) -> list[SimpleNamespace]:
    points = [SimpleNamespace(x=0.5, y=0.5) for _ in range(455)]
    points[33] = SimpleNamespace(x=0.3, y=0.4)
    points[133] = SimpleNamespace(x=0.5, y=0.4)
    vertical_offset = ear * 0.1
    points[160] = SimpleNamespace(x=0.35, y=0.4 - vertical_offset)
    points[144] = SimpleNamespace(x=0.35, y=0.4 + vertical_offset)
    points[158] = SimpleNamespace(x=0.45, y=0.4 - vertical_offset)
    points[153] = SimpleNamespace(x=0.45, y=0.4 + vertical_offset)
    points[362] = SimpleNamespace(x=0.6, y=0.4)
    points[263] = SimpleNamespace(x=0.8, y=0.4)
    points[385] = SimpleNamespace(x=0.65, y=0.4 - vertical_offset)
    points[380] = SimpleNamespace(x=0.65, y=0.4 + vertical_offset)
    points[387] = SimpleNamespace(x=0.75, y=0.4 - vertical_offset)
    points[373] = SimpleNamespace(x=0.75, y=0.4 + vertical_offset)
    points[1] = SimpleNamespace(x=0.55 + yaw * 0.5, y=0.55)
    return points


class FakeLandmarker:
    def __init__(self, sequence: list[list[SimpleNamespace]]) -> None:
        self.sequence = sequence
        self.index = 0

    def detect_for_video(self, image, timestamp_ms):
        del image, timestamp_ms
        result = SimpleNamespace(face_landmarks=[self.sequence[self.index]])
        self.index += 1
        return result

    def close(self):
        return None


class SelfieLivenessTests(unittest.TestCase):
    def analyzer_for(self, sequence):
        temp = tempfile.TemporaryDirectory()
        model = Path(temp.name) / "model.task"
        model.write_bytes(b"test-model")
        landmarker = FakeLandmarker(sequence)
        analyzer = SelfieLivenessAnalyzer(
            model,
            min_frames=8,
            max_frames=12,
            min_duration_ms=900,
            landmarker_factory=lambda path: landmarker,
        )
        analyzer.initialize()
        self.addCleanup(analyzer.close)
        self.addCleanup(temp.cleanup)
        return analyzer

    def test_blink_and_head_turn_pass_with_aggregate_evidence(self):
        sequence = [
            landmarks(0.30, 0.00),
            landmarks(0.30, 0.00),
            landmarks(0.15, 0.00),
            landmarks(0.30, 0.00),
            landmarks(0.30, 0.05),
            landmarks(0.30, 0.15),
            landmarks(0.30, 0.18),
            landmarks(0.30, 0.18),
        ]
        result = self.analyzer_for(sequence).analyze([image_bytes()] * 8)
        self.assertTrue(result.passed)
        self.assertTrue(result.blink_detected)
        self.assertTrue(result.head_turn_detected)
        self.assertEqual(result.face_frames, 8)
        self.assertEqual(result.evidence["duration_ms"], 1050)

    def test_missing_blink_does_not_pass(self):
        sequence = [landmarks(0.30, value) for value in (0.0, 0.0, 0.05, 0.15, 0.18, 0.18, 0.18, 0.18)]
        result = self.analyzer_for(sequence).analyze([image_bytes()] * 8)
        self.assertFalse(result.passed)
        self.assertEqual(result.reason, "blink_not_detected")

    def test_missing_sequence_is_rejected_before_model_use(self):
        analyzer = SelfieLivenessAnalyzer("missing.task", min_frames=8)
        result = analyzer.analyze([image_bytes()] * 7)
        self.assertEqual(result.reason, "insufficient_frames")
        self.assertFalse(result.passed)


if __name__ == "__main__":
    unittest.main()
