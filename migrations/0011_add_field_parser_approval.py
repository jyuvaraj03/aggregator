"""Store explicit approval for template field parsers."""

from peewee import SQL, BooleanField


def up(migrator: object, _: object) -> None:
    """Require existing and future parser sets to be reviewed explicitly."""
    migrator.migrate(
        migrator.add_column(
            "templates",
            "field_parsers_approved",
            BooleanField(default=False, constraints=[SQL("DEFAULT 0")]),
        )
    )


def down(migrator: object, _: object) -> None:
    """Remove parser approval state."""
    migrator.migrate(migrator.drop_column("templates", "field_parsers_approved"))
