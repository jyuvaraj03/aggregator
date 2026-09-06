"""Create independently managed accounts."""

from peewee import Model, TextField


def up(_: object, db: object) -> None:
    """Create the accounts table."""

    class Account(Model):
        name = TextField(unique=True)

        class Meta:
            database = db
            table_name = "accounts"

    db.create_tables([Account])


def down(migrator: object, _: object) -> None:
    """Remove the accounts table."""
    migrator.migrate(migrator.drop_table("accounts"))
