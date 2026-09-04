"""Seed the fixed transaction field catalog."""

FIELD_NAMES = (
    "amount",
    "currency_code",
    "payee",
    "description",
    "transaction_date",
    "account_hint",
    "is_credit",
)


def up(_: object, db: object) -> None:
    """Add each fixed field exactly once."""
    db.execute_sql(
        "INSERT OR IGNORE INTO fields (name) VALUES " + ", ".join("(?)" for _ in FIELD_NAMES),
        FIELD_NAMES,
    )


def down(_: object, db: object) -> None:
    """Remove the fixed field catalog."""
    db.execute_sql(
        "DELETE FROM fields WHERE name IN (" + ", ".join("?" for _ in FIELD_NAMES) + ")",
        FIELD_NAMES,
    )
