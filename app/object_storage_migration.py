"""Copy legacy local uploads into the configured S3-compatible backend."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.config import UPLOAD_DIR
from app.object_storage import ObjectStorageError, object_storage


def iter_local_media(upload_dir: Path = UPLOAD_DIR):
    if not upload_dir.exists():
        return
    for path in sorted(upload_dir.rglob("*")):
        if path.is_file() and not path.name.startswith("."):
            yield path


def migrate_local_media(
    *,
    storage=object_storage,
    upload_dir: Path = UPLOAD_DIR,
    dry_run: bool = False,
) -> dict[str, int]:
    if not storage.is_remote:
        raise ObjectStorageError(
            "Configure KINDRED_OBJECT_STORAGE_BUCKET before migrating local media"
        )
    storage.initialize()
    copied = 0
    for path in iter_local_media(upload_dir) or ():
        key = path.relative_to(upload_dir).as_posix()
        if not dry_run:
            storage.put_file(key, path)
        copied += 1
    return {"copied": copied, "dry_run": int(dry_run)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy legacy uploads/ files to configured object storage"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the migration count without uploading files",
    )
    args = parser.parse_args(argv)
    try:
        result = migrate_local_media(dry_run=args.dry_run)
    except ObjectStorageError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
