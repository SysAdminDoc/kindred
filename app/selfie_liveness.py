"""Sequence-based selfie liveness checks.

The analyzer keeps the camera frames in memory only.  It uses MediaPipe's
local Face Landmarker model to extract facial landmarks, then checks for an
eye-aspect-ratio blink and a measurable head turn across the ordered frames.
No frame is written to disk by this module.
"""

from __future__ import annotations

import hashlib
import math
import threading
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
from PIL import Image, UnidentifiedImageError

try:
    import mediapipe as mp  # type: ignore[import-untyped]
    from mediapipe.tasks.python import vision  # type: ignore[import-untyped]
    from mediapipe.tasks.python.core.base_options import BaseOptions  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - exercised by minimal deployments
    mp = None  # type: ignore[assignment]
    vision = None  # type: ignore[assignment]
    BaseOptions = None  # type: ignore[assignment,misc]


class LivenessError(RuntimeError):
    """Base error for liveness configuration or frame processing failures."""


class LivenessConfigurationError(LivenessError):
    """Raised when the local liveness model cannot be loaded."""


class LivenessAnalysisError(LivenessError):
    """Raised when a frame cannot be decoded or analyzed."""


@dataclass(frozen=True)
class LivenessResult:
    """Privacy-preserving result of a liveness attempt."""

    passed: bool
    score: float
    reason: str
    frames_analyzed: int
    face_frames: int
    blink_detected: bool
    head_turn_detected: bool
    evidence: dict[str, Any]

    @classmethod
    def unavailable(cls, reason: str) -> "LivenessResult":
        return cls(
            passed=False,
            score=0.0,
            reason=reason,
            frames_analyzed=0,
            face_frames=0,
            blink_detected=False,
            head_turn_detected=False,
            evidence={},
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "reason": self.reason,
            "frames_analyzed": self.frames_analyzed,
            "face_frames": self.face_frames,
            "blink_detected": self.blink_detected,
            "head_turn_detected": self.head_turn_detected,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class _FrameObservation:
    eye_aspect_ratio: float
    yaw_proxy: float


LandmarkerFactory = Callable[[str], Any]


def _distance(a: Any, b: Any) -> float:
    return math.hypot(float(a.x) - float(b.x), float(a.y) - float(b.y))


def _eye_aspect_ratio(landmarks: Sequence[Any], indices: tuple[int, int, int, int, int, int]) -> float:
    p0, p1, p2, p3, p4, p5 = (landmarks[index] for index in indices)
    horizontal = _distance(p0, p3)
    if horizontal <= 1e-9:
        return 0.0
    return (_distance(p1, p5) + _distance(p2, p4)) / (2.0 * horizontal)


def _landmark_observation(landmarks: Sequence[Any]) -> _FrameObservation:
    # MediaPipe Face Mesh indices.  The two six-point eye contours provide a
    # normalized blink signal; the nose-to-eye-midpoint ratio provides a
    # camera-independent relative yaw signal.
    if len(landmarks) <= 454:
        raise LivenessAnalysisError("face landmark model returned incomplete landmarks")
    left_ear = _eye_aspect_ratio(landmarks, (33, 160, 158, 133, 153, 144))
    right_ear = _eye_aspect_ratio(landmarks, (362, 385, 387, 263, 373, 380))
    eye_aspect_ratio = (left_ear + right_ear) / 2.0
    eye_mid_x = (float(landmarks[33].x) + float(landmarks[263].x)) / 2.0
    eye_width = _distance(landmarks[33], landmarks[263])
    if eye_width <= 1e-9:
        raise LivenessAnalysisError("face landmark model returned an invalid eye span")
    yaw_proxy = (float(landmarks[1].x) - eye_mid_x) / eye_width
    return _FrameObservation(eye_aspect_ratio, yaw_proxy)


def _default_landmarker_factory(model_path: str) -> Any:
    if mp is None or vision is None or BaseOptions is None:
        raise LivenessConfigurationError("MediaPipe Tasks is not installed")
    options = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )
    return vision.FaceLandmarker.create_from_options(options)


class SelfieLivenessAnalyzer:
    """Run local blink and head-turn checks over an ordered image sequence."""

    def __init__(
        self,
        model_path: Path | str,
        *,
        enabled: bool = True,
        required: bool = True,
        min_frames: int = 8,
        max_frames: int = 24,
        frame_interval_ms: int = 150,
        min_duration_ms: int = 900,
        blink_closed_ear: float = 0.20,
        blink_open_ear: float = 0.24,
        head_turn_delta: float = 0.12,
        expected_sha256: str = "",
        landmarker_factory: LandmarkerFactory = _default_landmarker_factory,
    ) -> None:
        self.model_path = Path(model_path)
        self.enabled = enabled
        self.required = required
        self.min_frames = min_frames
        self.max_frames = max_frames
        self.frame_interval_ms = frame_interval_ms
        self.min_duration_ms = min_duration_ms
        self.blink_closed_ear = blink_closed_ear
        self.blink_open_ear = blink_open_ear
        self.head_turn_delta = head_turn_delta
        self.expected_sha256 = expected_sha256.lower().strip()
        self._landmarker_factory = landmarker_factory
        self._landmarker: Any | None = None
        self._lock = threading.Lock()
        self._last_error = ""
        self._initialized = False

    def _verify_model(self) -> None:
        if not self.model_path.is_file():
            raise LivenessConfigurationError(
                f"Face Landmarker model not found: {self.model_path}"
            )
        if not self.expected_sha256:
            return
        digest = hashlib.sha256()
        with self.model_path.open("rb") as model_file:
            for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest().lower() != self.expected_sha256:
            raise LivenessConfigurationError("Face Landmarker model checksum mismatch")

    def initialize(self) -> str:
        if not self.enabled:
            self._initialized = True
            return "disabled"
        if self._initialized and self._landmarker is not None:
            return "mediapipe"
        try:
            self._verify_model()
            self._landmarker = self._landmarker_factory(str(self.model_path))
            self._initialized = True
            self._last_error = ""
            return "mediapipe"
        except Exception as exc:
            self._initialized = False
            self._landmarker = None
            self._last_error = str(exc)
            if self.required:
                if isinstance(exc, LivenessConfigurationError):
                    raise
                raise LivenessConfigurationError(str(exc)) from exc
            return "unavailable"

    def close(self) -> None:
        with self._lock:
            if self._landmarker is not None:
                self._landmarker.close()
            self._landmarker = None
            self._initialized = False

    def health(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "required": self.required,
            "configured": self.model_path.is_file(),
            "ready": self._initialized and self._landmarker is not None,
            "backend": "mediapipe" if self._landmarker is not None else "unavailable",
            "model_path": str(self.model_path),
            "last_error": self._last_error,
            "min_frames": self.min_frames,
            "max_frames": self.max_frames,
        }

    @staticmethod
    def _decode_frame(content: bytes) -> Any:
        if not content:
            raise LivenessAnalysisError("liveness frame is empty")
        try:
            image = Image.open(BytesIO(content)).convert("RGB")
            image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            array = np.asarray(image, dtype=np.uint8)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise LivenessAnalysisError("liveness frame is not a readable image") from exc
        if mp is None:
            raise LivenessConfigurationError("MediaPipe Tasks is not installed")
        return mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(array))

    def _ensure_ready(self) -> Any:
        if not self.enabled:
            raise LivenessConfigurationError("selfie liveness is disabled")
        if self._landmarker is None:
            self.initialize()
        if self._landmarker is None:
            raise LivenessConfigurationError(self._last_error or "liveness model unavailable")
        return self._landmarker

    @staticmethod
    def _detect_observation(landmarker: Any, image: Any, timestamp_ms: int) -> _FrameObservation | None:
        result = landmarker.detect_for_video(image, timestamp_ms)
        faces = getattr(result, "face_landmarks", None) or []
        if not faces:
            return None
        try:
            return _landmark_observation(faces[0])
        except (IndexError, TypeError, ValueError) as exc:
            raise LivenessAnalysisError("face landmark model returned invalid landmarks") from exc

    @staticmethod
    def _blink_detected(ears: Sequence[float], closed_threshold: float, open_threshold: float) -> bool:
        for index, ear in enumerate(ears):
            if ear > closed_threshold:
                continue
            before = any(value >= open_threshold for value in ears[:index])
            after = any(value >= open_threshold for value in ears[index + 1 :])
            if before and after:
                return True
        return False

    def analyze(
        self,
        frames: Sequence[bytes],
        timestamps_ms: Sequence[int] | None = None,
    ) -> LivenessResult:
        """Analyze frames in order and return aggregate evidence only."""
        frame_count = len(frames)
        if frame_count < self.min_frames:
            return LivenessResult(
                False, 0.0, "insufficient_frames", frame_count, 0, False, False, {}
            )
        if frame_count > self.max_frames:
            return LivenessResult(
                False, 0.0, "too_many_frames", frame_count, 0, False, False, {}
            )
        if timestamps_ms is None:
            timestamps = [index * self.frame_interval_ms for index in range(frame_count)]
        else:
            if len(timestamps_ms) != frame_count:
                raise LivenessAnalysisError("timestamp count does not match frame count")
            timestamps = [int(value) for value in timestamps_ms]
            if any(later <= earlier for earlier, later in zip(timestamps, timestamps[1:])):
                raise LivenessAnalysisError("liveness timestamps must be strictly increasing")
        duration_ms = timestamps[-1] - timestamps[0] if timestamps else 0
        if duration_ms < self.min_duration_ms:
            return LivenessResult(
                False,
                0.0,
                "duration_too_short",
                frame_count,
                0,
                False,
                False,
                {"duration_ms": duration_ms},
            )

        with self._lock:
            landmarker = self._ensure_ready()
            observations: list[_FrameObservation] = []
            for content, timestamp in zip(frames, timestamps):
                image = self._decode_frame(content)
                observation = self._detect_observation(landmarker, image, timestamp)
                if observation is not None:
                    observations.append(observation)

        face_frames = len(observations)
        face_ratio = face_frames / frame_count
        if not observations:
            return LivenessResult(
                False,
                0.0,
                "no_face_detected",
                frame_count,
                0,
                False,
                False,
                {"duration_ms": duration_ms, "face_ratio": 0.0},
            )
        ears = [observation.eye_aspect_ratio for observation in observations]
        yaws = [observation.yaw_proxy for observation in observations]
        blink_detected = self._blink_detected(
            ears, self.blink_closed_ear, self.blink_open_ear
        )
        yaw_delta = max(yaws) - min(yaws)
        head_turn_detected = yaw_delta >= self.head_turn_delta
        stable_face = face_ratio >= 0.75
        score = round(
            min(1.0, face_ratio) * 0.5
            + (0.25 if blink_detected else 0.0)
            + (0.25 if head_turn_detected else 0.0),
            3,
        )
        if not stable_face:
            reason = "face_tracking_unstable"
        elif not blink_detected:
            reason = "blink_not_detected"
        elif not head_turn_detected:
            reason = "head_turn_not_detected"
        else:
            reason = "passed"
        return LivenessResult(
            passed=reason == "passed",
            score=score,
            reason=reason,
            frames_analyzed=frame_count,
            face_frames=face_frames,
            blink_detected=blink_detected,
            head_turn_detected=head_turn_detected,
            evidence={
                "duration_ms": duration_ms,
                "face_ratio": round(face_ratio, 3),
                "ear_min": round(min(ears), 4),
                "ear_max": round(max(ears), 4),
                "yaw_delta": round(yaw_delta, 4),
            },
        )


def build_liveness_analyzer() -> SelfieLivenessAnalyzer:
    """Build the configured process-wide analyzer."""
    from app.config import (
        SELFIE_LIVENESS_BLINK_CLOSED_EAR,
        SELFIE_LIVENESS_BLINK_OPEN_EAR,
        SELFIE_LIVENESS_ENABLED,
        SELFIE_LIVENESS_EXPECTED_SHA256,
        SELFIE_LIVENESS_FRAME_INTERVAL_MS,
        SELFIE_LIVENESS_HEAD_TURN_DELTA,
        SELFIE_LIVENESS_MAX_FRAMES,
        SELFIE_LIVENESS_MIN_DURATION_MS,
        SELFIE_LIVENESS_MIN_FRAMES,
        SELFIE_LIVENESS_MODEL_PATH,
        SELFIE_LIVENESS_REQUIRED,
    )

    return SelfieLivenessAnalyzer(
        SELFIE_LIVENESS_MODEL_PATH,
        enabled=SELFIE_LIVENESS_ENABLED,
        required=SELFIE_LIVENESS_REQUIRED,
        min_frames=SELFIE_LIVENESS_MIN_FRAMES,
        max_frames=SELFIE_LIVENESS_MAX_FRAMES,
        frame_interval_ms=SELFIE_LIVENESS_FRAME_INTERVAL_MS,
        min_duration_ms=SELFIE_LIVENESS_MIN_DURATION_MS,
        blink_closed_ear=SELFIE_LIVENESS_BLINK_CLOSED_EAR,
        blink_open_ear=SELFIE_LIVENESS_BLINK_OPEN_EAR,
        head_turn_delta=SELFIE_LIVENESS_HEAD_TURN_DELTA,
        expected_sha256=SELFIE_LIVENESS_EXPECTED_SHA256,
    )


selfie_liveness = build_liveness_analyzer()
