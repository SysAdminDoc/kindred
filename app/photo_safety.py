"""Upload-time perceptual-hash safety checks.

The local matcher stores hashes only, never a copy of the known-abuse corpus.
The optional PhotoDNA adapter is deliberately a hash webhook: the production
provider-specific request/response contract stays outside the application and
is enabled only after the operator has an approved endpoint and credentials.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from io import BytesIO
from urllib.error import URLError
from urllib.request import Request, urlopen

import numpy as np  # type: ignore[import-untyped]
from PIL import Image

from app.config import (
    PHOTO_DHASH_MAX_DISTANCE,
    PHOTO_HASH_ENABLED,
    PHOTO_HASH_MAX_DISTANCE,
    PHOTO_SAFETY_REQUIRED,
    PHOTODNA_API_KEY,
    PHOTODNA_ENABLED,
    PHOTODNA_HOOK_URL,
    PHOTODNA_TIMEOUT_SECONDS,
)


log = logging.getLogger("kindred.photo_safety")


class PhotoSafetyError(RuntimeError):
    """Base error for safety scanner configuration or required failures."""


class PhotoSafetyConfigurationError(PhotoSafetyError):
    """The enabled safety integration is not configured safely."""


@dataclass(frozen=True)
class PhotoHashes:
    phash: str
    dhash: str


@dataclass(frozen=True)
class ExternalScanResult:
    status: str
    matched: bool = False


@dataclass(frozen=True)
class PhotoSafetyResult:
    hashes: PhotoHashes | None
    local_matches: tuple[dict, ...]
    external: ExternalScanResult
    blocked: bool
    reason: str | None = None


def _dct_basis(size: int) -> np.ndarray:
    coordinates: np.ndarray = np.arange(size, dtype=np.float64)
    frequencies: np.ndarray = np.arange(size, dtype=np.float64)
    basis = np.cos(
        (np.pi / size) * (coordinates[:, None] + 0.5) * frequencies[None, :]
    )
    basis[:, 0] *= 1 / np.sqrt(size)
    basis[:, 1:] *= np.sqrt(2 / size)
    return basis


_DCT_BASIS = _dct_basis(32)
_RESAMPLING = getattr(Image, "Resampling", Image)


def _bits_to_hex(bits) -> str:
    value = 0
    for bit in bits:
        value = (value << 1) | int(bool(bit))
    return f"{value:016x}"


def compute_photo_hashes(content: bytes) -> PhotoHashes:
    """Compute a 64-bit DCT pHash and a 64-bit horizontal-gradient dHash."""

    try:
        with Image.open(BytesIO(content)) as image:
            grayscale = image.convert("L")
            dct_image = grayscale.resize((32, 32), _RESAMPLING.LANCZOS)
            dct_pixels = np.asarray(dct_image, dtype=np.float64)
            coefficients = _DCT_BASIS.T @ dct_pixels @ _DCT_BASIS
            low_frequency = coefficients[:8, :8]
            median = np.median(low_frequency.flatten()[1:])
            phash = _bits_to_hex(low_frequency.flatten() > median)

            dhash_image = grayscale.resize((9, 8), _RESAMPLING.LANCZOS)
            dhash_pixels = np.asarray(dhash_image, dtype=np.int16)
            dhash = _bits_to_hex((dhash_pixels[:, 1:] > dhash_pixels[:, :-1]).flatten())
    except Exception as exc:
        raise PhotoSafetyError("Unable to compute perceptual image hashes") from exc
    return PhotoHashes(phash=phash, dhash=dhash)


class PhotoDNAHashHook:
    """Call an operator-provided hash endpoint when the feature is enabled."""

    def __init__(
        self,
        *,
        enabled: bool = PHOTODNA_ENABLED,
        url: str = PHOTODNA_HOOK_URL,
        api_key: str = PHOTODNA_API_KEY,
        timeout_seconds: float = PHOTODNA_TIMEOUT_SECONDS,
    ):
        self.enabled = enabled
        self.url = url.strip()
        self.api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds

    def initialize(self) -> None:
        if self.enabled and not self.url:
            raise PhotoSafetyConfigurationError(
                "KINDRED_PHOTODNA_HOOK_URL is required when PhotoDNA is enabled"
            )

    def health(self) -> dict:
        return {
            "enabled": self.enabled,
            "configured": bool(self.url),
        }

    def scan(self, hashes: PhotoHashes) -> ExternalScanResult:
        if not self.enabled:
            return ExternalScanResult(status="disabled")
        payload = json.dumps({"phash": hashes.phash, "dhash": hashes.dhash}).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Ocp-Apim-Subscription-Key"] = self.api_key
        request = Request(self.url, data=payload, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (AttributeError, OSError, TypeError, URLError, ValueError, TimeoutError) as exc:
            log.warning("PhotoDNA hash hook unavailable: %s", exc)
            return ExternalScanResult(status="unavailable")
        matched = bool(
            result.get("match") or result.get("matched") or result.get("blocked")
        )
        return ExternalScanResult(status="matched" if matched else "clear", matched=matched)


class PhotoSafetyScanner:
    def __init__(
        self,
        *,
        hash_enabled: bool = PHOTO_HASH_ENABLED,
        safety_required: bool = PHOTO_SAFETY_REQUIRED,
        phash_max_distance: int = PHOTO_HASH_MAX_DISTANCE,
        dhash_max_distance: int = PHOTO_DHASH_MAX_DISTANCE,
        external_hook: PhotoDNAHashHook | None = None,
    ):
        self.hash_enabled = hash_enabled
        self.safety_required = safety_required
        self.phash_max_distance = phash_max_distance
        self.dhash_max_distance = dhash_max_distance
        self.external_hook = external_hook or PhotoDNAHashHook()
        self._initialized = False

    def initialize(self) -> str:
        self.external_hook.initialize()
        self._initialized = True
        return "enabled" if self.hash_enabled or self.external_hook.enabled else "disabled"

    def health(self) -> dict:
        return {
            "hash_enabled": self.hash_enabled,
            "required": self.safety_required,
            "phash_max_distance": self.phash_max_distance,
            "dhash_max_distance": self.dhash_max_distance,
            "photodna": self.external_hook.health(),
        }

    def scan(
        self,
        content: bytes,
        *,
        profile_id: str,
        filename: str,
    ) -> PhotoSafetyResult:
        if not self._initialized:
            self.initialize()
        if not self.hash_enabled and not self.external_hook.enabled:
            return PhotoSafetyResult(
                hashes=None,
                local_matches=(),
                external=ExternalScanResult(status="disabled"),
                blocked=False,
            )

        hashes = compute_photo_hashes(content)
        local_matches: tuple[dict, ...] = ()
        if self.hash_enabled:
            from app.database import find_known_abuse_photo_matches

            local_matches = tuple(
                find_known_abuse_photo_matches(
                    hashes.phash,
                    hashes.dhash,
                    self.phash_max_distance,
                    self.dhash_max_distance,
                )
            )
        external = self.external_hook.scan(hashes)
        reason: str | None = None
        if local_matches:
            reason = "local_known_abuse_match"
        elif external.matched:
            reason = "photodna_match"
        elif external.status == "unavailable" and self.safety_required:
            reason = "photodna_unavailable"
        blocked = reason is not None
        if blocked:
            from app.database import record_photo_safety_event

            record_photo_safety_event(
                profile_id,
                filename,
                hashes.phash,
                hashes.dhash,
                len(local_matches),
                external.status,
                reason or "blocked",
            )
        return PhotoSafetyResult(
            hashes=hashes,
            local_matches=local_matches,
            external=external,
            blocked=blocked,
            reason=reason,
        )


photo_safety = PhotoSafetyScanner()
