"""Tests for Celery configuration."""

# Celery does not publish type stubs.
# pyright: reportUnknownMemberType=false

from unittest.mock import Mock

import pytest

from aggregator import celery_app


def test_load_environment_reads_repository_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    load_dotenv = Mock()
    monkeypatch.setattr(celery_app, "load_dotenv", load_dotenv)

    celery_app.load_environment()

    load_dotenv.assert_called_once_with(dotenv_path=celery_app.DOTENV_PATH)


def test_worker_includes_background_tasks() -> None:
    assert "aggregator.background_tasks" in celery_app.celery_app.conf.include
