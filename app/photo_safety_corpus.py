"""Import a JSON hashed-image corpus into Kindred's local safety database."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from app.database import add_known_abuse_photo_hash, init_db


HASH_RE = re.compile(r"^[0-9a-fA-F]{16}$")


def load_records(path: Path, default_source: str) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("records", [])
    if not isinstance(payload, list):
        raise ValueError("Corpus JSON must be a list or an object with a records list")
    records: list[dict[str, str]] = []
    for index, record in enumerate(payload, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"Corpus record {index} is not an object")
        phash = str(record.get("phash", "")).lower()
        dhash = str(record.get("dhash", "")).lower()
        source = str(record.get("source", default_source)).strip()
        external_ref = str(record.get("external_ref", "")).strip()
        if not HASH_RE.fullmatch(phash) or not HASH_RE.fullmatch(dhash):
            raise ValueError(f"Corpus record {index} must contain two 16-digit hex hashes")
        if not source:
            raise ValueError(f"Corpus record {index} has no source")
        records.append({
            "phash": phash,
            "dhash": dhash,
            "source": source,
            "external_ref": external_ref,
        })
    return records


def import_records(records: list[dict[str, str]], dry_run: bool = False) -> int:
    if dry_run:
        return len(records)
    init_db()
    for record in records:
        add_known_abuse_photo_hash(
            record["phash"],
            record["dhash"],
            record["source"],
            record["external_ref"],
        )
    return len(records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import a hashed abuse-image corpus")
    parser.add_argument("input", type=Path, help="JSON file containing phash/dhash records")
    parser.add_argument("--source", default="operator", help="Source label for records without one")
    parser.add_argument("--dry-run", action="store_true", help="Validate and count without writing")
    args = parser.parse_args(argv)
    try:
        records = load_records(args.input, args.source)
        count = import_records(records, args.dry_run)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({"imported": count, "dry_run": int(args.dry_run)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
