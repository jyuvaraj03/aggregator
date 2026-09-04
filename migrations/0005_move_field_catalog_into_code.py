"""Replace the persisted field catalog with fixed field names in parser rows."""

from peewee import CharField, ForeignKeyField, Model, TextField

FIELD_NAMES = (
    "amount",
    "currency_code",
    "payee",
    "description",
    "transaction_date",
    "account_hint",
    "is_credit",
)


def up(migrator: object, db: object) -> None:
    """Discard parser configurations and remove the redundant field catalog."""

    class Template(Model):
        class Meta:
            database = db
            table_name = "templates"

    class FieldParser(Model):
        template = ForeignKeyField(Template, on_delete="CASCADE")
        field_name = CharField()
        rule = CharField()
        parameter_indices = TextField()
        constant_value = TextField(null=True)

        class Meta:
            database = db
            table_name = "field_parsers"
            indexes = ((("template", "field_name"), True),)

    migrator.migrate(migrator.drop_table("field_parsers"))
    db.create_tables([FieldParser])
    migrator.migrate(migrator.drop_table("fields"))


def down(migrator: object, db: object) -> None:
    """Restore empty legacy parser storage and its seeded fixed field catalog."""

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

    migrator.migrate(migrator.drop_table("field_parsers"))
    db.create_tables([Field, FieldParser])
    db.execute_sql(
        "INSERT INTO fields (name) VALUES " + ", ".join("(?)" for _ in FIELD_NAMES),
        FIELD_NAMES,
    )
