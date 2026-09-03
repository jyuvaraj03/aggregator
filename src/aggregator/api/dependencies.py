"""FastAPI dependencies shared by database-backed routes."""

from __future__ import annotations

from collections.abc import Generator

from peewee import SqliteDatabase

from ..database import database_connection


def database_dependency() -> Generator[SqliteDatabase]:
    """Keep a database connection open while a route reads and serializes models."""
    with database_connection() as connection:
        yield connection
