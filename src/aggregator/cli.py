"""Command-line interface"""
from datetime import date, timedelta

from .email_pull import pull_messages


def pull_test(label: str | None = None, from_date: date | None = None):
    label = label or "Transactions"
    from_date = from_date or date.today() - timedelta(days=1)
    return pull_messages(label, from_date)

def main() -> int:
    return 0
