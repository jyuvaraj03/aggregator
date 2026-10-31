"""Persist the selected account card colour."""

from peewee import SQL, Check, IntegerField


def up(migrator: object, _: object) -> None:
    """Give existing and new accounts the Ocean theme by default."""
    migrator.migrate(
        migrator.add_column(
            "accounts",
            "color",
            IntegerField(
                default=0, constraints=[SQL("DEFAULT 0"), Check("color BETWEEN 0 AND 19")]
            ),
        )
    )


def down(migrator: object, _: object) -> None:
    """Remove account card colours."""
    migrator.migrate(migrator.drop_column("accounts", "color"))
