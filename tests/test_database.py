from __future__ import annotations

from aggregator.database import (
    DATABASE_PATH,
    close_database,
    connect_database,
    database,
    database_connection,
)


def _use_in_memory_database() -> None:
    close_database()
    database.init(":memory:")  # pyright: ignore[reportUnknownMemberType]


def _restore_default_database() -> None:
    close_database()
    database.init(str(DATABASE_PATH))  # pyright: ignore[reportUnknownMemberType]


def test_database_uses_the_project_root_sqlite_file() -> None:
    assert database.database == str(DATABASE_PATH)


def test_connect_and_close_database_manage_the_shared_connection() -> None:
    _use_in_memory_database()
    try:
        assert database.is_closed()

        connect_database()
        assert not database.is_closed()

        close_database()
        assert database.is_closed()
    finally:
        _restore_default_database()


def test_database_connection_opens_and_closes_a_new_connection() -> None:
    _use_in_memory_database()
    try:
        with database_connection() as connection:
            assert connection is database
            assert not database.is_closed()

        assert database.is_closed()
    finally:
        _restore_default_database()


def test_database_connection_preserves_an_existing_connection() -> None:
    _use_in_memory_database()
    try:
        connect_database()

        with database_connection() as connection:
            assert connection is database
            assert not database.is_closed()

        assert not database.is_closed()
    finally:
        _restore_default_database()
