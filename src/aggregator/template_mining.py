"""Extract reusable templates from persisted email bodies with Drain3."""

# Drain3 and Peewee's model query methods are intentionally dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

from .database import database, database_connection
from .models import Email, Template

MINIMUM_CLUSTER_SIZE = 3


@dataclass(frozen=True, slots=True)
class TemplateMiningResult:
    """Counts produced while mining one supplied batch of emails."""

    processed: int
    skipped: int
    templates_created: int


def mine_templates(emails: Iterable[Email]) -> TemplateMiningResult:
    """Mine Drain3 templates for emails in the iterable's supplied order.

    The miner is deliberately in-memory: this is a batch operation, rather than
    a persistent or incremental Drain3 state machine. Empty readable bodies are
    left without a template.
    """
    with database_connection():
        miner, cluster_ids_by_email_id, empty_email_ids = _mine_emails(emails)
        with database.atomic():
            templates_by_cluster_id = _store_templates(miner)
            _tag_emails(cluster_ids_by_email_id, empty_email_ids, templates_by_cluster_id)

    return TemplateMiningResult(
        processed=len(cluster_ids_by_email_id),
        skipped=len(empty_email_ids),
        templates_created=len(templates_by_cluster_id),
    )


def _mine_emails(emails: Iterable[Email]) -> tuple[TemplateMiner, dict[int, int], list[int]]:
    miner = TemplateMiner(config=TemplateMinerConfig())
    cluster_ids_by_email_id: dict[int, int] = {}
    empty_email_ids: list[int] = []

    for email in emails:
        readable_body = email.readable_body()
        if not readable_body:
            empty_email_ids.append(email.id)
            continue
        result = miner.add_log_message(readable_body)
        cluster_ids_by_email_id[email.id] = int(result["cluster_id"])

    return miner, cluster_ids_by_email_id, empty_email_ids


def _store_templates(miner: TemplateMiner) -> dict[int, Template]:
    return {
        cluster.cluster_id: Template.get_or_create(text=cluster.get_template())[0]
        for cluster in miner.drain.clusters
        if cluster.size >= MINIMUM_CLUSTER_SIZE
    }


def _tag_emails(
    cluster_ids_by_email_id: Mapping[int, int],
    empty_email_ids: Iterable[int],
    templates_by_cluster_id: Mapping[int, Template],
) -> None:
    for email_id, cluster_id in cluster_ids_by_email_id.items():
        if cluster_id not in templates_by_cluster_id:
            continue
        query = Email.update(template=templates_by_cluster_id[cluster_id]).where(
            Email.id == email_id
        )
        query.execute()
    if empty_ids := list(empty_email_ids):
        Email.update(template=None).where(Email.id.in_(empty_ids)).execute()
