"""Create the immutable Gmail message snapshots table."""

from peewee import CharField, DateTimeField, Model, TextField


def up(migrator: object, db: object) -> None:
    """Create the table used by ``aggregator.email_sync.Email``."""

    class Email(Model):
        message_id = CharField(unique=True)
        history_id = CharField(null=True)
        received_at = DateTimeField()
        sender = TextField()
        subject = TextField(null=True)
        body_text = TextField(null=True)
        body_html = TextField(null=True)
        headers = TextField()
        authentication_status = TextField(null=True)

        class Meta:
            database = db
            table_name = "emails"

    db.create_tables([Email])


def down(migrator: object, db: object) -> None:
    """Remove the Gmail message snapshots table."""
    migrator.migrate(migrator.drop_table("emails"))
