import tempfile
import unittest
from pathlib import Path

from starlette.requests import Request

from app.object_storage import (
    InvalidObjectKey,
    InvalidRange,
    ObjectNotFound,
    ObjectStorage,
    ObjectStorageConfigurationError,
    ObjectStorageUnavailable,
    parse_range_header,
)
from app.object_storage_migration import migrate_local_media


class FakeBody:
    def __init__(self, content: bytes):
        self.content = content
        self.closed = False

    def read(self):
        return self.content

    def close(self):
        self.closed = True


class MissingObject(Exception):
    response = {
        "Error": {"Code": "NoSuchKey"},
        "ResponseMetadata": {"HTTPStatusCode": 404},
    }


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.bucket_checks = 0

    def head_bucket(self, **kwargs):
        self.bucket_checks += 1
        return {}

    def put_object(self, *, Bucket, Key, Body, ContentType):
        self.objects[Key] = (bytes(Body), ContentType)
        return {"ETag": '"fake"'}

    def head_object(self, *, Bucket, Key):
        if Key not in self.objects:
            raise MissingObject(Key)
        content, content_type = self.objects[Key]
        return {
            "ContentLength": len(content),
            "ContentType": content_type,
            "ETag": '"fake"',
        }

    def get_object(self, *, Bucket, Key, Range=None):
        if Key not in self.objects:
            raise MissingObject(Key)
        content, content_type = self.objects[Key]
        if Range:
            start, end = (int(part) for part in Range.removeprefix("bytes=").split("-"))
            body = content[start:end + 1]
            content_range = f"bytes {start}-{end}/{len(content)}"
        else:
            body = content
            content_range = None
        result = {
            "Body": FakeBody(body),
            "ContentLength": len(body),
            "ContentType": content_type,
            "ETag": '"fake"',
        }
        if content_range:
            result["ContentRange"] = content_range
        return result

    def delete_object(self, *, Bucket, Key):
        self.objects.pop(Key, None)
        return {}


class UnavailableS3:
    def head_bucket(self, **kwargs):
        raise RuntimeError("offline")


class ObjectStorageTests(unittest.TestCase):
    def test_local_backend_round_trip_and_atomic_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = ObjectStorage(upload_dir=directory)
            storage.initialize()
            self.assertEqual(storage.put_bytes("nested/photo.jpg", b"first", "image/jpeg"), "nested/photo.jpg")
            self.assertEqual(storage.get_object("nested/photo.jpg").content, b"first")
            storage.put_bytes("nested/photo.jpg", b"second", "image/jpeg")
            self.assertEqual(storage.get_object("nested/photo.jpg").content, b"second")
            self.assertEqual(storage.get_metadata("nested/photo.jpg").size, 6)
            self.assertEqual(storage.url("nested/photo.jpg"), "/uploads/nested/photo.jpg")
            storage.delete("nested/photo.jpg")
            with self.assertRaises(ObjectNotFound):
                storage.get_object("nested/photo.jpg")

    def test_remote_backend_keeps_logical_keys_and_supports_ranges(self):
        with tempfile.TemporaryDirectory() as directory:
            client = FakeS3()
            storage = ObjectStorage(
                upload_dir=directory,
                endpoint="http://minio:9000",
                bucket="kindred",
                access_key="access",
                secret_key="secret",
                prefix="media",
                required=True,
                client=client,
            )
            self.assertEqual(storage.initialize(), "s3")
            storage.put_bytes("clip.mp4", b"0123456789", "video/mp4")
            self.assertIn("media/clip.mp4", client.objects)
            self.assertEqual(storage.get_object("clip.mp4").content, b"0123456789")
            ranged = storage.get_object("clip.mp4", (2, 5), total_size=10)
            self.assertEqual(ranged.content, b"2345")
            self.assertEqual(ranged.total_size, 10)
            self.assertEqual(storage.url("clip.mp4"), "/uploads/clip.mp4")
            request = Request({
                "type": "http",
                "method": "GET",
                "path": "/uploads/clip.mp4",
                "headers": [(b"range", b"bytes=2-5")],
                "query_string": b"",
                "server": ("testserver", 80),
                "client": ("testclient", 123),
                "scheme": "http",
            })
            response = storage.media_response(request, "clip.mp4")
            self.assertEqual(response.status_code, 206)
            self.assertEqual(response.body, b"2345")
            self.assertEqual(response.headers["content-range"], "bytes 2-5/10")

    def test_remote_backend_reads_legacy_local_files(self):
        with tempfile.TemporaryDirectory() as directory:
            legacy_path = Path(directory) / "legacy.jpg"
            legacy_path.write_bytes(b"legacy")
            storage = ObjectStorage(
                upload_dir=directory,
                endpoint="http://minio:9000",
                bucket="kindred",
                client=FakeS3(),
            )
            storage.initialize()
            self.assertEqual(storage.get_object("legacy.jpg").content, b"legacy")

    def test_required_remote_configuration_fails_without_bucket(self):
        storage = ObjectStorage(required=True)
        with self.assertRaises(ObjectStorageConfigurationError):
            storage.initialize()

    def test_optional_remote_outage_does_not_fall_back_to_local_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = ObjectStorage(
                upload_dir=directory,
                endpoint="http://minio:9000",
                bucket="kindred",
                client=UnavailableS3(),
            )
            self.assertEqual(storage.initialize(), "s3")
            self.assertFalse(storage.health()["healthy"])
            with self.assertRaises(ObjectStorageUnavailable):
                storage.put_bytes("photo.jpg", b"photo")
            self.assertFalse((Path(directory) / "photo.jpg").exists())

    def test_keys_and_ranges_reject_unsafe_values(self):
        with self.assertRaises(InvalidObjectKey):
            ObjectStorage().put_bytes("../outside.jpg", b"bad")
        self.assertEqual(parse_range_header("bytes=-4", 10), (6, 9))
        with self.assertRaises(InvalidRange):
            parse_range_header("bytes=1-2,4-5", 10)

    def test_local_media_migration_is_repeatable_and_supports_dry_run(self):
        with tempfile.TemporaryDirectory() as directory:
            upload_dir = Path(directory)
            (upload_dir / "photo.jpg").write_bytes(b"photo")
            (upload_dir / ".temporary-upload").write_bytes(b"skip")
            client = FakeS3()
            storage = ObjectStorage(
                upload_dir=upload_dir,
                endpoint="http://minio:9000",
                bucket="kindred",
                prefix="media",
                client=client,
            )
            dry_run = migrate_local_media(
                storage=storage, upload_dir=upload_dir, dry_run=True
            )
            self.assertEqual(dry_run["copied"], 1)
            self.assertNotIn("media/photo.jpg", client.objects)
            result = migrate_local_media(storage=storage, upload_dir=upload_dir)
            self.assertEqual(result["copied"], 1)
            self.assertIn("media/photo.jpg", client.objects)


if __name__ == "__main__":
    unittest.main()
