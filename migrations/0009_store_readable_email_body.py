"""Store only the normalized readable body for imported emails."""

from peewee import CharField, TextField


def up(migrator: object, db: object) -> None:
    """Replace legacy Gmail metadata and body variants with one readable body."""
    migrator.migrate(
        migrator.add_column("emails", "body", TextField(default="")),
        migrator.drop_column("emails", "history_id"),
        migrator.drop_column("emails", "body_text"),
        migrator.drop_column("emails", "body_html"),
        migrator.drop_column("emails", "headers"),
        migrator.drop_column("emails", "authentication_status"),
    )


def down(migrator: object, db: object) -> None:
    """Restore empty legacy storage columns without reconstructing discarded data."""
    migrator.migrate(
        migrator.add_column("emails", "history_id", CharField(null=True)),
        migrator.add_column("emails", "body_text", TextField(null=True)),
        migrator.add_column("emails", "body_html", TextField(null=True)),
        migrator.add_column("emails", "headers", TextField(default="{}")),
        migrator.add_column("emails", "authentication_status", TextField(null=True)),
        migrator.drop_column("emails", "body"),
    )
