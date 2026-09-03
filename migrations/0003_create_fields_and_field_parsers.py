"""Store globally named fields and template-specific parsing rules."""

from peewee import CharField, ForeignKeyField, Model, TextField


def up(_: object, db: object) -> None:
    """Create fields and their parser configurations."""

    class Template(Model):
        class Meta:
            database = db
            table_name = "templates"

    class Field(Model):
        name = CharField(unique=True)

        class Meta:
            database = db
            table_name = "fields"

    class FieldParser(Model):
        template = ForeignKeyField(Template, on_delete="CASCADE")
        field = ForeignKeyField(Field, on_delete="CASCADE")
        rule = CharField()
        parameter_indices = TextField()
        constant_value = TextField(null=True)

        class Meta:
            database = db
            table_name = "field_parsers"
            indexes = ((("template", "field"), True),)

    db.create_tables([Field, FieldParser])


def down(migrator: object, _: object) -> None:
    """Remove parser configurations and fields."""
    migrator.migrate(migrator.drop_table("field_parsers"))
    migrator.migrate(migrator.drop_table("fields"))
