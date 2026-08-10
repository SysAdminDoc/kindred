"""Migrate a Kindred SQLite database into an empty PostgreSQL database.

The application keeps SQLite as its development backend. This module provides
an explicit, repeatable migration bridge for production cutover without making
the request path depend on a PostgreSQL driver or server.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from app.config import DB_PATH


class MigrationError(RuntimeError):
    """Raised when a migration cannot proceed without risking data loss."""


@dataclass(frozen=True)
class ColumnSnapshot:
    name: str
    sqlite_type: str
    not_null: bool
    default: str | None
    primary_key_position: int
    identity: bool


@dataclass(frozen=True)
class ForeignKeySnapshot:
    constraint_id: int
    columns: tuple[str, ...]
    referenced_table: str
    referenced_columns: tuple[str, ...]
    on_update: str
    on_delete: str


@dataclass(frozen=True)
class IndexSnapshot:
    name: str
    columns: tuple[str, ...]
    unique: bool


@dataclass(frozen=True)
class TableSnapshot:
    name: str
    columns: tuple[ColumnSnapshot, ...]
    primary_key: tuple[str, ...]
    foreign_keys: tuple[ForeignKeySnapshot, ...]
    indexes: tuple[IndexSnapshot, ...]
    row_count: int
    source_sql: str


@dataclass(frozen=True)
class DatabaseSnapshot:
    sqlite_path: Path
    schema_version: int
    tables: tuple[TableSnapshot, ...]

    @property
    def total_rows(self) -> int:
        return sum(table.row_count for table in self.tables)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sqlite_path": str(self.sqlite_path),
            "schema_version": self.schema_version,
            "table_count": len(self.tables),
            "total_rows": self.total_rows,
            "tables": [
                {"name": table.name, "rows": table.row_count,
                 "columns": len(table.columns)}
                for table in self.tables
            ],
        }


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _sqlite_pragma(conn: sqlite3.Connection, pragma: str, table: str) -> list[tuple]:
    safe_table = table.replace('"', '""')
    return conn.execute(f'PRAGMA {pragma}({_quote_identifier(safe_table)})').fetchall()


def _postgres_type(sqlite_type: str) -> str:
    normalized = (sqlite_type or "TEXT").upper()
    if "INT" in normalized:
        return "BIGINT"
    if any(token in normalized for token in ("CHAR", "CLOB", "TEXT")):
        return "TEXT"
    if "BLOB" in normalized:
        return "BYTEA"
    if any(token in normalized for token in ("REAL", "FLOA", "DOUB")):
        return "DOUBLE PRECISION"
    if "BOOL" in normalized:
        return "BOOLEAN"
    if any(token in normalized for token in ("DECIMAL", "NUMERIC")):
        return "NUMERIC"
    if normalized in {"DATE", "DATETIME", "TIMESTAMP"}:
        return "TIMESTAMP"
    return "TEXT"


def _postgres_default(default: str | None) -> str | None:
    if default is None:
        return None
    value = default.strip()
    unwrapped = value
    while unwrapped.startswith("(") and unwrapped.endswith(")"):
        unwrapped = unwrapped[1:-1].strip()
    lowered = unwrapped.lower()
    if lowered in {"current_timestamp", "current_timestamp()"}:
        return "CURRENT_TIMESTAMP"
    if re.fullmatch(r"datetime\(\s*'now'\s*\)", lowered):
        return "CURRENT_TIMESTAMP"
    return value


def _foreign_keys(
    conn: sqlite3.Connection,
    table: str,
    primary_key: tuple[str, ...],
    primary_keys: dict[str, tuple[str, ...]],
) -> tuple[ForeignKeySnapshot, ...]:
    rows = _sqlite_pragma(conn, "foreign_key_list", table)
    grouped: dict[int, list[tuple]] = {}
    for row in rows:
        grouped.setdefault(int(row[0]), []).append(row)

    result: list[ForeignKeySnapshot] = []
    for constraint_id, group in sorted(grouped.items()):
        group.sort(key=lambda row: int(row[1]))
        referenced_columns = tuple(row[4] or "" for row in group)
        if any(not column for column in referenced_columns):
            referenced_columns = primary_keys.get(str(group[0][2]), primary_key)
        if len(referenced_columns) != len(group):
            raise MigrationError(
                f"Cannot resolve foreign-key columns for {table} constraint {constraint_id}"
            )
        result.append(ForeignKeySnapshot(
            constraint_id=constraint_id,
            columns=tuple(row[3] for row in group),
            referenced_table=str(group[0][2]),
            referenced_columns=referenced_columns,
            on_update=str(group[0][5] or "NO ACTION"),
            on_delete=str(group[0][6] or "NO ACTION"),
        ))
    return tuple(result)


def _indexes(conn: sqlite3.Connection, table: str) -> tuple[IndexSnapshot, ...]:
    result: list[IndexSnapshot] = []
    for row in _sqlite_pragma(conn, "index_list", table):
        # seq, name, unique, origin, partial were added across SQLite versions.
        index_name = str(row[1])
        unique = bool(row[2])
        origin = str(row[3]) if len(row) > 3 else "c"
        partial = bool(row[4]) if len(row) > 4 else False
        if partial:
            raise MigrationError(f"Partial index is not supported: {table}.{index_name}")
        if origin == "pk":
            continue
        columns = []
        for info in _sqlite_pragma(conn, "index_info", index_name):
            if int(info[1]) < 0:
                raise MigrationError(f"Expression index is not supported: {table}.{index_name}")
            columns.append(str(info[2]))
        if not columns:
            raise MigrationError(f"Index has no migratable columns: {table}.{index_name}")
        if index_name.startswith("sqlite_autoindex_"):
            index_name = f"kindred_uq_{table}_{len(result)}"
        result.append(IndexSnapshot(index_name, tuple(columns), unique))
    return tuple(result)


def inspect_sqlite(sqlite_path: str | Path) -> DatabaseSnapshot:
    """Read the SQLite schema and row counts without modifying the source."""
    path = Path(sqlite_path).expanduser().resolve()
    if not path.is_file():
        raise MigrationError(f"SQLite database does not exist: {path}")

    conn = sqlite3.connect(str(path))
    try:
        objects = conn.execute("""
            SELECT name, type, sql
            FROM sqlite_master
            WHERE name NOT LIKE 'sqlite_%'
              AND type IN ('table', 'index', 'view', 'trigger')
            ORDER BY type, name
        """).fetchall()
        unsupported = [
            f"{kind}:{name}" for name, kind, _ in objects
            if kind in {"view", "trigger"}
        ]
        if unsupported:
            raise MigrationError(
                "Unsupported SQLite objects would be lost: " + ", ".join(unsupported)
            )

        table_rows = [row for row in objects if row[1] == "table"]
        primary_keys = {}
        for table_name, _, _ in table_rows:
            column_rows = _sqlite_pragma(conn, "table_info", table_name)
            primary_keys[str(table_name)] = tuple(
                str(row[1]) for row in sorted(column_rows, key=lambda item: int(item[5]))
                if int(row[5]) > 0
            )
        tables = []
        for table_name, _, source_sql in table_rows:
            source_sql = source_sql or ""
            if re.search(r"\bCHECK\s*\(", source_sql, re.IGNORECASE):
                raise MigrationError(
                    f"CHECK constraint requires manual review before migrating: {table_name}"
                )
            column_rows = _sqlite_pragma(conn, "table_info", table_name)
            primary_key = primary_keys[str(table_name)]
            columns = tuple(ColumnSnapshot(
                name=str(row[1]),
                sqlite_type=str(row[2] or "TEXT"),
                not_null=bool(row[3]),
                default=row[4],
                primary_key_position=int(row[5]),
                identity=(
                    int(row[5]) == 1
                    and "AUTOINCREMENT" in source_sql.upper()
                    and str(row[2]).upper() == "INTEGER"
                ),
            ) for row in column_rows)
            tables.append(TableSnapshot(
                name=str(table_name),
                columns=columns,
                primary_key=primary_key,
                foreign_keys=_foreign_keys(conn, str(table_name), primary_key, primary_keys),
                indexes=_indexes(conn, str(table_name)),
                row_count=int(conn.execute(
                    f"SELECT COUNT(*) FROM {_quote_identifier(str(table_name))}"
                ).fetchone()[0]),
                source_sql=source_sql,
            ))

        schema_version = 0
        if any(table.name == "schema_versions" for table in tables):
            row = conn.execute("SELECT MAX(version) FROM schema_versions").fetchone()
            schema_version = int(row[0] or 0)
        return DatabaseSnapshot(path, schema_version, tuple(tables))
    finally:
        conn.close()


def _render_create_table(table: TableSnapshot) -> str:
    definitions = []
    single_primary_key = len(table.primary_key) == 1
    for column in table.columns:
        column_type = _postgres_type(column.sqlite_type)
        if column.identity:
            column_type += " GENERATED BY DEFAULT AS IDENTITY"
        parts = [_quote_identifier(column.name), column_type]
        if column.not_null or column.primary_key_position > 0:
            parts.append("NOT NULL")
        if single_primary_key and column.primary_key_position > 0:
            parts.append("PRIMARY KEY")
        default = _postgres_default(column.default)
        if default is not None:
            parts.extend(("DEFAULT", default))
        definitions.append(" ".join(parts))
    if len(table.primary_key) > 1:
        definitions.append(
            "PRIMARY KEY (" + ", ".join(_quote_identifier(c) for c in table.primary_key) + ")"
        )
    return (
        f"CREATE TABLE IF NOT EXISTS {_quote_identifier(table.name)} (\n    "
        + ",\n    ".join(definitions)
        + "\n)"
    )


def render_postgres_schema(snapshot: DatabaseSnapshot) -> list[str]:
    """Render the table portion of the target schema for review or dry runs."""
    return [_render_create_table(table) for table in snapshot.tables]


def _render_foreign_key(table: TableSnapshot, foreign_key: ForeignKeySnapshot) -> str:
    name = f"fk_{table.name}_{foreign_key.constraint_id}"
    clause = (
        f"ALTER TABLE {_quote_identifier(table.name)} ADD CONSTRAINT {_quote_identifier(name)} "
        "FOREIGN KEY ("
        + ", ".join(_quote_identifier(c) for c in foreign_key.columns)
        + f") REFERENCES {_quote_identifier(foreign_key.referenced_table)} ("
        + ", ".join(_quote_identifier(c) for c in foreign_key.referenced_columns)
        + ")"
    )
    if foreign_key.on_delete != "NO ACTION":
        clause += f" ON DELETE {foreign_key.on_delete}"
    if foreign_key.on_update != "NO ACTION":
        clause += f" ON UPDATE {foreign_key.on_update}"
    return clause


def _render_index(table: TableSnapshot, index: IndexSnapshot) -> str:
    unique = "UNIQUE " if index.unique else ""
    columns = ", ".join(_quote_identifier(column) for column in index.columns)
    return (
        f"CREATE {unique}INDEX IF NOT EXISTS {_quote_identifier(index.name)} "
        f"ON {_quote_identifier(table.name)} ({columns})"
    )


def _load_psycopg():
    try:
        import psycopg
    except ImportError as exc:
        raise MigrationError(
            "PostgreSQL migration requires psycopg; install requirements.txt first"
        ) from exc
    return psycopg


def _target_tables(cursor) -> list[str]:
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public' AND table_type='BASE TABLE'
        ORDER BY table_name
    """)
    return [str(row[0]) for row in cursor.fetchall()]


def _sync_identity_sequences(cursor, snapshot: DatabaseSnapshot) -> None:
    for table in snapshot.tables:
        for column in table.columns:
            if not column.identity:
                continue
            table_sql = _quote_identifier(table.name)
            column_sql = _quote_identifier(column.name)
            cursor.execute(f"SELECT MAX({column_sql}) FROM {table_sql}")
            maximum = cursor.fetchone()[0]
            sequence_name = f"public.{table.name}"
            if maximum is None:
                cursor.execute(
                    "SELECT setval(pg_get_serial_sequence(%s, %s), 1, false)",
                    (sequence_name, column.name),
                )
            else:
                cursor.execute(
                    "SELECT setval(pg_get_serial_sequence(%s, %s), %s, true)",
                    (sequence_name, column.name, int(maximum)),
                )


def migrate_sqlite_to_postgres(
    sqlite_path: str | Path,
    postgres_dsn: str,
    *,
    batch_size: int = 500,
    verify: bool = True,
    connect: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Copy a SQLite database into an empty PostgreSQL database.

    The target must be empty. Existing target data is never dropped or
    overwritten. The optional ``connect`` hook is intended for tests.
    """
    if not postgres_dsn.strip():
        raise MigrationError("A PostgreSQL DSN is required")
    if batch_size < 1:
        raise MigrationError("batch_size must be positive")

    snapshot = inspect_sqlite(sqlite_path)
    psycopg = _load_psycopg()
    connection = (connect or psycopg.connect)(postgres_dsn)
    source = sqlite3.connect(str(snapshot.sqlite_path))
    try:
        with connection.cursor() as cursor:
            existing = _target_tables(cursor)
            if existing:
                raise MigrationError(
                    "Target PostgreSQL database is not empty: " + ", ".join(existing[:10])
                )

            for statement in render_postgres_schema(snapshot):
                cursor.execute(statement)

            for table in snapshot.tables:
                columns = [column.name for column in table.columns]
                column_sql = ", ".join(_quote_identifier(column) for column in columns)
                placeholders = ", ".join("%s" for _ in columns)
                insert_sql = (
                    f"INSERT INTO {_quote_identifier(table.name)} ({column_sql}) "
                    f"VALUES ({placeholders})"
                )
                rows = source.execute(
                    f"SELECT * FROM {_quote_identifier(table.name)}"
                )
                while True:
                    batch = rows.fetchmany(batch_size)
                    if not batch:
                        break
                    cursor.executemany(insert_sql, batch)

            for table in snapshot.tables:
                for foreign_key in table.foreign_keys:
                    cursor.execute(_render_foreign_key(table, foreign_key))
                for index in table.indexes:
                    cursor.execute(_render_index(table, index))
            _sync_identity_sequences(cursor, snapshot)
        if verify:
            with connection.cursor() as cursor:
                mismatches = []
                for table in snapshot.tables:
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {_quote_identifier(table.name)}"
                    )
                    actual = int(cursor.fetchone()[0])
                    if actual != table.row_count:
                        mismatches.append({
                            "table": table.name,
                            "expected": table.row_count,
                            "actual": actual,
                        })
                if mismatches:
                    raise MigrationError(
                        "PostgreSQL verification failed: " + json.dumps(mismatches)
                    )
        connection.commit()
        return {
            "sqlite_path": str(snapshot.sqlite_path),
            "schema_version": snapshot.schema_version,
            "table_count": len(snapshot.tables),
            "rows_migrated": snapshot.total_rows,
            "verified": verify,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        source.close()
        connection.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate a Kindred SQLite database into an empty PostgreSQL database."
    )
    parser.add_argument(
        "--sqlite", default=str(DB_PATH), help="SQLite source path (default: configured DB_PATH)"
    )
    parser.add_argument(
        "--postgres-dsn", default=os.getenv("KINDRED_POSTGRES_DSN", ""),
        help="PostgreSQL DSN (or KINDRED_POSTGRES_DSN)",
    )
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--no-verify", action="store_true", help="Skip target row-count verification")
    parser.add_argument("--dry-run", action="store_true", help="Inspect and report without connecting")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        snapshot = inspect_sqlite(args.sqlite)
        if args.dry_run:
            report = {"mode": "dry-run", **snapshot.to_dict()}
        else:
            report = migrate_sqlite_to_postgres(
                args.sqlite,
                args.postgres_dsn,
                batch_size=args.batch_size,
                verify=not args.no_verify,
            )
    except MigrationError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"Migration failed: {exc}")
        return 2

    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
