from pathlib import Path

# Peewee and its migration helper are dynamically typed.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from peewee import SqliteDatabase
from playhouse.migrations import Runner

from aggregator.database import PROJECT_ROOT
from aggregator.models import TRANSACTION_FIELD_NAMES


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
    runner.up()

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
