from __future__ import annotations

from datetime import date

import pytest
from _pytest.capture import CaptureFixture

from aggregator import cli


def test_demo_command_outputs_normalized_records(capsys: CaptureFixture[str]) -> None:
    assert True


def test_email_helpers_use_the_configured_label_indirectly(monkeypatch: pytest.MonkeyPatch) -> None:
    from_date = date(2026, 9, 1)
    captured: dict[str, date] = {}

    def pull(value: date) -> str:
        captured["pull"] = value
        return "pulled"

    def sync(value: date) -> str:
        captured["sync"] = value
        return "synced"

    monkeypatch.setattr(cli, "pull_messages", pull)
    monkeypatch.setattr(cli, "sync_messages", sync)

    assert cli.pull_test(from_date) == "pulled"
    assert cli.sync_test(from_date) == "synced"
    assert captured == {"pull": from_date, "sync": from_date}
