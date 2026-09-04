"""Store typed transactions and template extraction outcomes."""

from peewee import BooleanField, CharField, DateField, ForeignKeyField, Model, TextField


def up(migrator: object, db: object) -> None:
    """Create transactions and add extraction state to templates."""

    class Email(Model):
        class Meta:
            database = db
            table_name = "emails"

    class Transaction(Model):
        email = ForeignKeyField(Email, unique=True, on_delete="CASCADE")
        amount = TextField(null=True)
        currency_code = TextField(null=True)
        payee = TextField(null=True)
        description = TextField(null=True)
        transaction_date = DateField(null=True)
        account_hint = TextField(null=True)
        is_credit = BooleanField(null=True)

        class Meta:
            database = db
            table_name = "transactions"

    migrator.migrate(
        migrator.add_column(
            "templates",
            "transaction_extraction_status",
            CharField(default="pending"),
        ),
        migrator.add_column(
            "templates",
            "transaction_extraction_error",
            TextField(null=True),
        ),
    )
    db.create_tables([Transaction])


def down(migrator: object, _: object) -> None:
    """Remove transactions and template extraction state."""
    migrator.migrate(
        migrator.drop_table("transactions"),
        migrator.drop_column("templates", "transaction_extraction_error"),
        migrator.drop_column("templates", "transaction_extraction_status"),
    )
