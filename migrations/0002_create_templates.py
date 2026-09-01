"""Store mined email templates and their email associations."""

from peewee import ForeignKeyField, Model, TextField


def up(migrator: object, db: object) -> None:
    """Create templates and add the optional template link to emails."""

    class Template(Model):
        text = TextField()

        class Meta:
            database = db
            table_name = "templates"

    db.create_tables([Template])
    migrator.migrate(
        migrator.add_column(
            "emails",
            "template_id",
            ForeignKeyField(Template, field=Template.id, null=True, on_delete="SET NULL"),
        )
    )


def down(migrator: object, db: object) -> None:
    """Remove template associations and extracted templates."""
    migrator.migrate(migrator.drop_column("emails", "template_id"))
    migrator.migrate(migrator.drop_table("templates"))
