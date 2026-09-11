"""Celery configuration for long-running aggregator operations."""

# Celery does not publish type stubs.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from __future__ import annotations

import os
from pathlib import Path

from celery import Celery
from dotenv import load_dotenv

DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def load_environment() -> None:
    """Load local configuration before Celery resolves its broker settings."""
    load_dotenv(dotenv_path=DOTENV_PATH)


load_environment()
REDIS_URL = os.environ.get("AGGREGATOR_REDIS_URL", "redis://127.0.0.1:16379/0")

celery_app = Celery(
    "aggregator",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["aggregator.background_tasks"],
)
celery_app.conf.update(
    task_default_queue="aggregator-actions",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=35 * 60,
    task_soft_time_limit=30 * 60,
    result_expires=7 * 24 * 60 * 60,
    broker_transport_options={"visibility_timeout": 60 * 60},
)


def worker_main() -> None:
    """Run the dedicated, single-concurrency action worker."""
    celery_app.worker_main(
        ["worker", "--loglevel=INFO", "--concurrency=1", "--queues=aggregator-actions"]
    )
