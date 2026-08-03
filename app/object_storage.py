"""Media storage with a local development backend and an S3-compatible backend.

Database rows keep the logical media key (usually the generated filename).  The
storage prefix, when configured, is applied only to the remote object key so
existing API responses and ``/uploads/...`` URLs remain stable.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from app.config import (
    OBJECT_STORAGE_ACCESS_KEY,
    OBJECT_STORAGE_ADDRESSING_STYLE,
    OBJECT_STORAGE_BUCKET,
    OBJECT_STORAGE_ENDPOINT,
    OBJECT_STORAGE_PREFIX,
    OBJECT_STORAGE_PUBLIC_URL,
    OBJECT_STORAGE_REGION,
    OBJECT_STORAGE_REQUIRED,
    OBJECT_STORAGE_SECRET_KEY,
    UPLOAD_DIR,
)


log = logging.getLogger("kindred.object_storage")


class ObjectStorageError(RuntimeError):
    """Base error for media storage failures."""


class ObjectStorageConfigurationError(ObjectStorageError):
    """The configured storage backend cannot be used safely."""


class ObjectStorageUnavailable(ObjectStorageError):
    """The configured remote backend is temporarily unavailable."""


class ObjectNotFound(ObjectStorageError):
    """The requested logical key does not exist."""


class InvalidObjectKey(ObjectStorageError):
    """The key is not safe to use as a media path or object key."""


class InvalidRange(ObjectStorageError):
    """The requested byte range cannot be served."""


@dataclass(frozen=True)
class ObjectMetadata:
    key: str
    content_type: str
    size: int
    etag: str | None = None


@dataclass(frozen=True)
class StoredObject:
    metadata: ObjectMetadata
    content: bytes
    range_start: int = 0
    range_end: int | None = None
    total_size: int | None = None


def _content_type(key: str, explicit: str | None = None) -> str:
    return explicit or mimetypes.guess_type(key)[0] or "application/octet-stream"


def _is_not_found(exc: Exception) -> bool:
    """Recognize the error shapes used by boto3 and lightweight test clients."""

    if isinstance(exc, (FileNotFoundError, ObjectNotFound)):
        return True
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        code = response.get("Error", {}).get("Code")
        if status == 404 or code in {
            "404", "NoSuchKey", "NotFound", "NoSuchObject"
        }:
            return True
    return False


class ObjectStorage:
    """Store media locally by default or remotely in an S3-compatible bucket."""

    def __init__(
        self,
        *,
        upload_dir: Path | str = UPLOAD_DIR,
        endpoint: str = OBJECT_STORAGE_ENDPOINT,
        bucket: str = OBJECT_STORAGE_BUCKET,
        access_key: str = OBJECT_STORAGE_ACCESS_KEY,
        secret_key: str = OBJECT_STORAGE_SECRET_KEY,
        region: str = OBJECT_STORAGE_REGION,
        prefix: str = OBJECT_STORAGE_PREFIX,
        public_url: str = OBJECT_STORAGE_PUBLIC_URL,
        required: bool = OBJECT_STORAGE_REQUIRED,
        addressing_style: str = OBJECT_STORAGE_ADDRESSING_STYLE,
        client=None,
    ):
        self.upload_dir = Path(upload_dir)
        self.endpoint = endpoint.strip()
        self.bucket = bucket.strip()
        self.access_key = access_key.strip()
        self.secret_key = secret_key.strip()
        self.region = region.strip()
        self.prefix = self._normalize_prefix(prefix)
        self.public_url = public_url.strip().rstrip("/")
        self.required = required
        self.addressing_style = addressing_style.strip() or (
            "path" if self.endpoint else "auto"
        )
        self._client = client
        self._configured = bool(
            self.endpoint or self.bucket or self.access_key or self.secret_key
        )
        self.backend_name = "s3" if self._configured or required else "local"
        self._initialized = False
        self._healthy = self.backend_name == "local"
        self._last_error: str | None = None

    @staticmethod
    def _normalize_prefix(prefix: str) -> str:
        value = (prefix or "").strip().replace("\\", "/").strip("/")
        if not value:
            return ""
        parts = value.split("/")
        if any(not part or part in {".", ".."} for part in parts):
            raise ObjectStorageConfigurationError("Invalid object storage prefix")
        return "/".join(parts)

    @property
    def is_local(self) -> bool:
        return self.backend_name == "local"

    @property
    def is_remote(self) -> bool:
        return self.backend_name == "s3"

    @property
    def configured(self) -> bool:
        return self._configured

    def initialize(self) -> str:
        """Validate and initialize the selected backend.

        A missing remote configuration intentionally selects local storage.  A
        partially supplied configuration is never silently downgraded because
        that could put production media back on ephemeral disk.
        """

        if self.is_local:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            self._initialized = True
            self._healthy = True
            self._last_error = None
            return self.backend_name

        if not self.bucket:
            error = "S3-compatible object storage requires KINDRED_OBJECT_STORAGE_BUCKET"
            self._initialized = True
            self._healthy = False
            self._last_error = error
            raise ObjectStorageConfigurationError(error)

        try:
            self._client_or_create().head_bucket(Bucket=self.bucket)
        except Exception as exc:
            self._initialized = True
            self._healthy = False
            self._last_error = str(exc) or exc.__class__.__name__
            if self.required:
                raise ObjectStorageUnavailable(
                    "Configured object storage is unavailable"
                ) from exc
            log.warning("Configured object storage is unavailable: %s", exc)
            return self.backend_name

        self._initialized = True
        self._healthy = True
        self._last_error = None
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        return self.backend_name

    def health(self) -> dict:
        return {
            "backend": self.backend_name,
            "configured": self.configured,
            "required": self.required,
            "healthy": self._healthy,
            "bucket": self.bucket or None,
            "prefix": self.prefix,
        }

    def _client_or_create(self):
        if self._client is not None:
            return self._client
        try:
            import boto3  # type: ignore[import-untyped]
            from botocore.config import Config  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ObjectStorageConfigurationError(
                "boto3 is required when S3-compatible object storage is configured"
            ) from exc

        kwargs = {"service_name": "s3"}
        if self.endpoint:
            kwargs["endpoint_url"] = self.endpoint
        if self.access_key:
            kwargs["aws_access_key_id"] = self.access_key
        if self.secret_key:
            kwargs["aws_secret_access_key"] = self.secret_key
        if self.region:
            kwargs["region_name"] = self.region
        kwargs["config"] = Config(s3={"addressing_style": self.addressing_style})
        self._client = boto3.client(**kwargs)
        return self._client

    def _ensure_ready(self) -> None:
        if not self._initialized:
            self.initialize()
        if not self._healthy:
            raise ObjectStorageUnavailable(
                "Configured object storage is unavailable"
            )

    @staticmethod
    def normalize_key(key: str) -> str:
        value = str(key or "").replace("\\", "/")
        value = value.strip("/")
        if not value or "\x00" in value:
            raise InvalidObjectKey("Media key is empty or contains invalid characters")
        parts = value.split("/")
        if any(not part or part in {".", ".."} for part in parts):
            raise InvalidObjectKey("Media key contains an unsafe path component")
        return "/".join(parts)

    def _remote_key(self, key: str) -> str:
        normalized = self.normalize_key(key)
        return f"{self.prefix}/{normalized}" if self.prefix else normalized

    def _local_path(self, key: str) -> Path:
        normalized = self.normalize_key(key)
        root = self.upload_dir.resolve()
        candidate = (root / Path(*normalized.split("/"))).resolve()
        if candidate != root and root not in candidate.parents:
            raise InvalidObjectKey("Media key escapes the upload directory")
        return candidate

    def put_bytes(self, key: str, content: bytes, content_type: str | None = None) -> str:
        normalized = self.normalize_key(key)
        media_type = _content_type(normalized, content_type)
        if self.is_local:
            path = self._local_path(normalized)
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path: str | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    dir=str(path.parent),
                    prefix=f".{path.name}.",
                    delete=False,
                ) as handle:
                    temporary_path = handle.name
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_path, path)
                temporary_path = None
            finally:
                if temporary_path:
                    Path(temporary_path).unlink(missing_ok=True)
            return normalized

        self._ensure_ready()
        try:
            self._client_or_create().put_object(
                Bucket=self.bucket,
                Key=self._remote_key(normalized),
                Body=content,
                ContentType=media_type,
            )
        except Exception as exc:
            self._healthy = False
            self._last_error = str(exc) or exc.__class__.__name__
            raise ObjectStorageUnavailable("Unable to store media object") from exc
        return normalized

    def put_file(self, key: str, path: Path, content_type: str | None = None) -> str:
        return self.put_bytes(key, path.read_bytes(), content_type)

    def _local_metadata(self, normalized: str) -> ObjectMetadata:
        path = self._local_path(normalized)
        try:
            stat = path.stat()
        except FileNotFoundError as exc:
            raise ObjectNotFound(normalized) from exc
        if not path.is_file():
            raise ObjectNotFound(normalized)
        return ObjectMetadata(
            key=normalized,
            content_type=_content_type(normalized),
            size=stat.st_size,
        )

    def _s3_metadata(self, normalized: str) -> ObjectMetadata:
        self._ensure_ready()
        try:
            result = self._client_or_create().head_object(
                Bucket=self.bucket,
                Key=self._remote_key(normalized),
            )
        except Exception as exc:
            if _is_not_found(exc):
                raise ObjectNotFound(normalized) from exc
            raise ObjectStorageUnavailable("Unable to inspect media object") from exc
        return ObjectMetadata(
            key=normalized,
            content_type=result.get("ContentType") or _content_type(normalized),
            size=int(result.get("ContentLength", 0)),
            etag=result.get("ETag"),
        )

    def get_metadata(self, key: str) -> ObjectMetadata:
        normalized = self.normalize_key(key)
        if self.is_local:
            return self._local_metadata(normalized)
        try:
            return self._s3_metadata(normalized)
        except ObjectNotFound:
            # Keep pre-migration local files readable while new writes are remote.
            return self._local_metadata(normalized)

    @staticmethod
    def _parse_content_range(value: str | None) -> tuple[int, int, int | None] | None:
        if not value:
            return None
        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+|\*)", value)
        if not match:
            return None
        total = None if match.group(3) == "*" else int(match.group(3))
        return int(match.group(1)), int(match.group(2)), total

    def _local_object(
        self,
        normalized: str,
        byte_range: tuple[int, int] | None = None,
        total_size: int | None = None,
    ) -> StoredObject:
        metadata = self._local_metadata(normalized)
        start, end = byte_range or (0, metadata.size - 1)
        with self._local_path(normalized).open("rb") as handle:
            handle.seek(start)
            content = handle.read(max(0, end - start + 1))
        actual_end = start + len(content) - 1 if content else start
        return StoredObject(
            metadata=metadata,
            content=content,
            range_start=start,
            range_end=actual_end,
            total_size=total_size or metadata.size,
        )

    def _s3_object(
        self,
        normalized: str,
        byte_range: tuple[int, int] | None = None,
        total_size: int | None = None,
    ) -> StoredObject:
        self._ensure_ready()
        kwargs = {"Bucket": self.bucket, "Key": self._remote_key(normalized)}
        if byte_range:
            kwargs["Range"] = f"bytes={byte_range[0]}-{byte_range[1]}"
        try:
            result = self._client_or_create().get_object(**kwargs)
            body = result["Body"]
            try:
                content = body.read()
            finally:
                close = getattr(body, "close", None)
                if close:
                    close()
        except Exception as exc:
            if _is_not_found(exc):
                raise ObjectNotFound(normalized) from exc
            raise ObjectStorageUnavailable("Unable to read media object") from exc

        content_range = self._parse_content_range(result.get("ContentRange"))
        if content_range:
            start, end, response_total = content_range
            total = response_total or total_size
        elif byte_range:
            start, end = byte_range
            total = total_size
        else:
            start = 0
            end = max(0, len(content) - 1)
            total = int(result.get("ContentLength", len(content)))
        metadata = ObjectMetadata(
            key=normalized,
            content_type=result.get("ContentType") or _content_type(normalized),
            size=total or int(result.get("ContentLength", len(content))),
            etag=result.get("ETag"),
        )
        return StoredObject(
            metadata=metadata,
            content=content,
            range_start=start,
            range_end=end,
            total_size=total,
        )

    def get_object(
        self,
        key: str,
        byte_range: tuple[int, int] | None = None,
        total_size: int | None = None,
    ) -> StoredObject:
        normalized = self.normalize_key(key)
        if self.is_local:
            return self._local_object(normalized, byte_range, total_size)
        try:
            return self._s3_object(normalized, byte_range, total_size)
        except ObjectNotFound:
            # Keep pre-migration local files readable while new writes are remote.
            return self._local_object(normalized, byte_range, total_size)

    def delete(self, key: str) -> None:
        normalized = self.normalize_key(key)
        if self.is_local:
            self._local_path(normalized).unlink(missing_ok=True)
            return

        self._ensure_ready()
        try:
            self._client_or_create().delete_object(
                Bucket=self.bucket,
                Key=self._remote_key(normalized),
            )
        except Exception as exc:
            if not _is_not_found(exc):
                self._healthy = False
                self._last_error = str(exc) or exc.__class__.__name__
                raise ObjectStorageUnavailable("Unable to delete media object") from exc
        # Remove a legacy local copy too, if one exists.
        self._local_path(normalized).unlink(missing_ok=True)

    def url(self, key: str) -> str:
        normalized = self.normalize_key(key)
        if self.public_url and self.is_remote:
            return f"{self.public_url}/{quote(self._remote_key(normalized), safe='/')}"
        return f"/uploads/{quote(normalized, safe='/')}"

    def media_response(self, request: Request, key: str) -> Response:
        """Build a private media response, including single-range video support."""

        if self.public_url and self.is_remote:
            return RedirectResponse(self.url(key), status_code=307)

        if request.method == "HEAD":
            metadata = self.get_metadata(key)
            return Response(
                status_code=200,
                media_type=metadata.content_type,
                headers=self._response_headers(metadata, metadata.size),
            )

        range_header = request.headers.get("range")
        if range_header:
            metadata = self.get_metadata(key)
            try:
                byte_range = parse_range_header(range_header, metadata.size)
            except InvalidRange:
                return Response(
                    status_code=416,
                    headers={"Content-Range": f"bytes */{metadata.size}"},
                )
            stored = self.get_object(key, byte_range, metadata.size)
            end = stored.range_end if stored.range_end is not None else byte_range[1]
            headers = self._response_headers(
                stored.metadata,
                len(stored.content),
                range_value=f"bytes {byte_range[0]}-{end}/{metadata.size}",
            )
            return Response(
                content=stored.content,
                status_code=206,
                media_type=stored.metadata.content_type,
                headers=headers,
            )

        stored = self.get_object(key)
        return Response(
            content=stored.content,
            status_code=200,
            media_type=stored.metadata.content_type,
            headers=self._response_headers(
                stored.metadata,
                len(stored.content),
            ),
        )

    @staticmethod
    def _response_headers(
        metadata: ObjectMetadata,
        content_length: int,
        *,
        range_value: str | None = None,
    ) -> dict[str, str]:
        headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=300",
            "Content-Length": str(content_length),
            "X-Content-Type-Options": "nosniff",
        }
        if metadata.etag:
            headers["ETag"] = metadata.etag
        if range_value:
            headers["Content-Range"] = range_value
        return headers


def parse_range_header(value: str, total_size: int) -> tuple[int, int]:
    """Parse one RFC 9110 byte range; multi-range responses are not supported."""

    if total_size <= 0 or not value.lower().startswith("bytes="):
        raise InvalidRange("Invalid media range")
    spec = value[6:].strip()
    if not spec or "," in spec:
        raise InvalidRange("Only one media range is supported")
    if spec.count("-") != 1:
        raise InvalidRange("Invalid media range")
    start_text, end_text = (part.strip() for part in spec.split("-", 1))
    try:
        if not start_text:
            suffix_length = int(end_text)
            if suffix_length <= 0:
                raise ValueError
            return max(0, total_size - suffix_length), total_size - 1
        start = int(start_text)
        if start < 0 or start >= total_size:
            raise ValueError
        end = total_size - 1 if not end_text else min(int(end_text), total_size - 1)
        if end < start:
            raise ValueError
        return start, end
    except (TypeError, ValueError) as exc:
        raise InvalidRange("Invalid media range") from exc


object_storage = ObjectStorage()
