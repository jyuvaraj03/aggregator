"""Track durable parser generation and human review sessions."""

from peewee import CharField, ForeignKeyField, IntegerField, Model, TextField


def up(_: object, db: object) -> None:
    class Template(Model):
        class Meta:
            database = db
            table_name = "templates"

    class ParserGenerationSession(Model):
        template = ForeignKeyField(Template, on_delete="CASCADE")
        thread_id = CharField(unique=True)
        status = CharField()
        current_round = IntegerField(default=1)
        active_job_id = CharField(null=True)
        published_fingerprint = CharField(null=True)
        template_text = TextField()
        examples_json = TextField()

        class Meta:
            database = db
            table_name = "parser_generation_sessions"

    db.create_tables([ParserGenerationSession])


def down(migrator: object, _: object) -> None:
    migrator.migrate(migrator.drop_table("parser_generation_sessions"))
