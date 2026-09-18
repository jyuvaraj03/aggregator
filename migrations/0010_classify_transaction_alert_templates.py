"""Store whether mined templates represent transaction alerts."""

from peewee import BooleanField


def up(migrator: object, _: object) -> None:
    """Add a nullable classification without backfilling existing templates."""
    migrator.migrate(
        migrator.add_column(
            "templates",
            "is_transaction_alert",
            BooleanField(null=True),
        )
    )


def down(migrator: object, _: object) -> None:
    """Remove the transaction-alert classification."""
    migrator.migrate(migrator.drop_column("templates", "is_transaction_alert"))
