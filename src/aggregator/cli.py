"""Command-line interface"""
# Peewee's model query methods are intentionally dynamically typed.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
from datetime import date, timedelta

from aggregator.email_sync import sync_messages
from aggregator.template_assignment import assign_email_templates

from .database import database_connection
from .email_pull import pull_messages
from .models import Email, Template


def pull_test(label: str | None = None, from_date: date | None = None):
    label = label or "Transactions"
    from_date = from_date or date.today() - timedelta(days=1)
    return pull_messages(label, from_date)

def sync_test(label: str | None = None, from_date: date | None = None):
    label = label or "Transactions"
    from_date = from_date or date.today() - timedelta(days=1)
    return sync_messages(label, from_date)

def get_last_email() -> Email | None:
    """Return the most recently received email stored in the database."""
    with database_connection():
        return Email.select().order_by(Email.received_at.desc()).first()

def mine_test():
    with database_connection():
        assignment_result = assign_email_templates()
        print(assignment_result)
        templates = Template.select()
        for template in templates:
            print(template.text)
            print(f"Count: {len(template.emails)}")  # pyright: ignore[reportUnknownArgumentType, reportAttributeAccessIssue]
            print("\n----\n")

def main() -> int:
    return 0
