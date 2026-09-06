"""Associate templates and transactions with explicitly selected accounts."""

from peewee import AutoField, ForeignKeyField, Model


def up(migrator: object, db: object) -> None:
    """Add nullable account references with their respective deletion policies."""

    class Account(Model):
        id = AutoField()

        class Meta:
            database = db
            table_name = "accounts"

    migrator.migrate(
        migrator.add_column(
            "templates",
            "account_id",
            ForeignKeyField(Account, field=Account.id, null=True, on_delete="SET NULL"),
        ),
        migrator.add_column(
            "transactions",
            "account_id",
            ForeignKeyField(Account, field=Account.id, null=True, on_delete="CASCADE"),
        ),
    )


def down(migrator: object, db: object) -> None:
    """Remove explicit account associations."""
    db.execute_sql('DROP INDEX "transactions_account_id"')
    db.execute_sql('DROP INDEX "templates_account_id"')
    migrator.migrate(
        migrator.drop_column("transactions", "account_id"),
        migrator.drop_column("templates", "account_id"),
    )
