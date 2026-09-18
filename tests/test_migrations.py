from pathlib import Path
from typing import cast

import pytest

# Peewee and its migration helper are dynamically typed.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from peewee import IntegrityError, SqliteDatabase
from playhouse.migrations import Runner

from aggregator.database import PROJECT_ROOT
from aggregator.parser_configuration import TRANSACTION_FIELD_NAMES


def test_field_catalog_migration_resets_parsers_and_drops_fields(tmp_path: Path) -> None:
    database = SqliteDatabase(str(tmp_path / "migration.sqlite3"), pragmas={"foreign_keys": 1})
    runner = Runner(database, directory=str(PROJECT_ROOT / "migrations"))
    runner.up("0004_seed_transaction_fields")
    database.execute_sql("INSERT INTO templates (text) VALUES (?)", ("Paid <NUMBER>",))
    amount_id = database.execute_sql(
        "SELECT id FROM fields WHERE name = ?", ("amount",)
    ).fetchone()[0]
    database.execute_sql(
        """INSERT INTO field_parsers
           (template_id, field_id, rule, parameter_indices, constant_value)
           VALUES (?, ?, ?, ?, ?)""",
        (1, amount_id, "extracted", "[0]", None),
    )

    runner.up()

    assert "fields" not in database.get_tables()
    assert database.get_columns("field_parsers")[2].name == "field_name"
    assert database.execute_sql("SELECT COUNT(*) FROM field_parsers").fetchone()[0] == 0


def test_field_catalog_migration_reverse_restores_seeded_legacy_tables(tmp_path: Path) -> None:
    database = SqliteDatabase(str(tmp_path / "migration.sqlite3"), pragmas={"foreign_keys": 1})
    runner = Runner(database, directory=str(PROJECT_ROOT / "migrations"))
    runner.up()

    runner.down("0005_move_field_catalog_into_code")

    assert {"fields", "field_parsers"}.issubset(database.get_tables())
    assert [column.name for column in database.get_columns("field_parsers")] == [
        "id",
        "template_id",
        "field_id",
        "rule",
        "parameter_indices",
        "constant_value",
    ]
    names = {
        row[0] for row in database.execute_sql("SELECT name FROM fields ORDER BY id").fetchall()
    }
    assert names == set(TRANSACTION_FIELD_NAMES)
    assert database.execute_sql("SELECT COUNT(*) FROM field_parsers").fetchone()[0] == 0


def test_transaction_migration_adds_and_removes_transaction_storage(tmp_path: Path) -> None:
    database = SqliteDatabase(str(tmp_path / "migration.sqlite3"), pragmas={"foreign_keys": 1})
    runner = Runner(database, directory=str(PROJECT_ROOT / "migrations"))
    runner.up("0006_create_transactions")

    assert "transactions" in database.get_tables()
    assert {
        "transaction_extraction_status",
        "transaction_extraction_error",
    }.issubset(column.name for column in database.get_columns("templates"))
    assert (
        database.execute_sql("SELECT transaction_extraction_status FROM templates").fetchall() == []
    )

    runner.down()

    assert "transactions" not in database.get_tables()
    template_columns = {column.name for column in database.get_columns("templates")}
    assert "transaction_extraction_status" not in template_columns
    assert "transaction_extraction_error" not in template_columns


def test_account_migration_adds_unique_storage_and_rolls_back(tmp_path: Path) -> None:
    database = SqliteDatabase(str(tmp_path / "migration.sqlite3"), pragmas={"foreign_keys": 1})
    runner = Runner(database, directory=str(PROJECT_ROOT / "migrations"))
    runner.up()

    assert "accounts" in database.get_tables()
    assert [column.name for column in database.get_columns("accounts")] == ["id", "name"]
    database.execute_sql("INSERT INTO accounts (name) VALUES (?)", ("Checking",))
    with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
        database.execute_sql("INSERT INTO accounts (name) VALUES (?)", ("Checking",))
    database.execute_sql("INSERT INTO accounts (name) VALUES (?)", ("checking",))

    runner.down("0007_create_accounts")

    assert "accounts" not in database.get_tables()


def test_account_association_migration_constraints_and_downgrade(tmp_path: Path) -> None:
    database = SqliteDatabase(str(tmp_path / "migration.sqlite3"), pragmas={"foreign_keys": 1})
    runner = Runner(database, directory=str(PROJECT_ROOT / "migrations"))
    runner.up("0007_create_accounts")
    database.execute_sql(
        "INSERT INTO templates (text, transaction_extraction_status) VALUES (?, ?)",
        ("Paid <NUMBER>", "pending"),
    )
    database.execute_sql(
        """INSERT INTO emails
           (message_id, received_at, sender, headers, template_id)
           VALUES (?, ?, ?, ?, ?)""",
        ("message-1", "2026-09-01", "sender@example.com", "{}", 1),
    )
    database.execute_sql("INSERT INTO transactions (email_id) VALUES (?)", (1,))

    runner.up()

    assert database.execute_sql("SELECT account_id FROM templates").fetchone() == (None,)
    assert database.execute_sql("SELECT account_id FROM transactions").fetchone() == (None,)
    template_foreign_keys = cast(
        list[tuple[object, ...]],
        database.execute_sql("PRAGMA foreign_key_list(templates)").fetchall(),
    )
    transaction_foreign_keys = cast(
        list[tuple[object, ...]],
        database.execute_sql("PRAGMA foreign_key_list(transactions)").fetchall(),
    )
    template_fk = next(row for row in template_foreign_keys if row[2] == "accounts")
    transaction_fk = next(row for row in transaction_foreign_keys if row[2] == "accounts")
    assert template_fk[2:7] == ("accounts", "account_id", "id", "NO ACTION", "SET NULL")
    assert transaction_fk[2:7] == ("accounts", "account_id", "id", "NO ACTION", "CASCADE")

    database.execute_sql("INSERT INTO accounts (name) VALUES (?)", ("Checking",))
    database.execute_sql("UPDATE templates SET account_id = 1")
    database.execute_sql("UPDATE transactions SET account_id = 1")
    database.execute_sql("DELETE FROM accounts WHERE id = 1")
    assert database.execute_sql("SELECT account_id FROM templates").fetchone() == (None,)
    assert database.execute_sql("SELECT COUNT(*) FROM transactions").fetchone() == (0,)

    runner.down("0008_associate_accounts")

    assert "account_id" not in {column.name for column in database.get_columns("templates")}
    assert "account_id" not in {column.name for column in database.get_columns("transactions")}
    assert "accounts" in database.get_tables()


def test_readable_email_body_migration_discards_legacy_fields(tmp_path: Path) -> None:
    database = SqliteDatabase(str(tmp_path / "migration.sqlite3"), pragmas={"foreign_keys": 1})
    runner = Runner(database, directory=str(PROJECT_ROOT / "migrations"))
    runner.up("0008_associate_accounts")
    database.execute_sql(
        """INSERT INTO emails
           (message_id, received_at, sender, body_text, body_html, headers)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            "message-1",
            "2026-09-01",
            "sender@example.com",
            "plain body",
            "<p>HTML body</p>",
            "{}",
        ),
    )

    runner.up("0009_store_readable_email_body")

    assert [column.name for column in database.get_columns("emails")] == [
        "id",
        "message_id",
        "received_at",
        "sender",
        "subject",
        "template_id",
        "body",
    ]
    assert database.execute_sql("SELECT body FROM emails").fetchone() == ("",)

    runner.down()

    columns = {column.name for column in database.get_columns("emails")}
    assert "body" not in columns
    assert {
        "history_id",
        "body_text",
        "body_html",
        "headers",
        "authentication_status",
    }.issubset(columns)


def test_template_classification_migration_is_nullable_and_reversible(tmp_path: Path) -> None:
    database = SqliteDatabase(str(tmp_path / "migration.sqlite3"), pragmas={"foreign_keys": 1})
    runner = Runner(database, directory=str(PROJECT_ROOT / "migrations"))
    runner.up("0009_store_readable_email_body")
    database.execute_sql(
        "INSERT INTO templates (text, transaction_extraction_status) VALUES (?, ?)",
        ("Paid <NUMBER>", "pending"),
    )

    runner.up()

    columns = {column.name: column for column in database.get_columns("templates")}
    assert columns["is_transaction_alert"].null is True
    assert database.execute_sql(
        "SELECT is_transaction_alert FROM templates WHERE id = 1"
    ).fetchone() == (None,)
    database.execute_sql(
        "INSERT INTO templates (text, transaction_extraction_status) VALUES (?, ?)",
        ("Received <NUMBER>", "pending"),
    )
    assert database.execute_sql(
        "SELECT is_transaction_alert FROM templates WHERE id = 2"
    ).fetchone() == (None,)

    runner.down()

    assert "is_transaction_alert" not in {
        column.name for column in database.get_columns("templates")
    }
