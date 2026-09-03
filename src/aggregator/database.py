"""Shared SQLite database configuration and connection lifecycle helpers."""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from peewee import SqliteDatabase

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = Path(
    os.environ.get("AGGREGATOR_DATABASE_PATH", PROJECT_ROOT / "aggregator.sqlite3")
)
database = SqliteDatabase(
    str(DATABASE_PATH),
    pragmas={"journal_mode": "wal", "busy_timeout": 5_000, "foreign_keys": 1},
    timeout=5,
)


def connect_database() -> None:
    """Open the shared database connection, reusing one that is already open."""
    database.connect(reuse_if_open=True)


def close_database() -> None:
    """Close the shared database connection when it is open."""
    if not database.is_closed():
        database.close()


@contextmanager
def database_connection() -> Generator[SqliteDatabase]:
    """Yield the shared database, closing it only if this context opened it."""
    opened_here = database.is_closed()
    if opened_here:
        connect_database()
    try:
        yield database
    finally:
        if opened_here:
            close_database()
