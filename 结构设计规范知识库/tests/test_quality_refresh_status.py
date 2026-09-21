from __future__ import annotations

from typing import Any

import pytest
from src.app.api import admin

RUN_ID = "a" * 32


def _event() -> dict[str, Any]:
    return {
        "event_id": "event-1",
        "created_at": "2026-08-31T00:00:00Z",
        "evaluation_set_id": "regular",
        "revision_id": "regular-r1",
        "content_hash": "evaluation-hash",
        "status": "pending",
    }


def _report(**overrides: Any) -> dict[str, Any]:
    report: dict[str, Any] = {
        "evaluation_set_id": "regular",
        "evaluation_set_revision_id": "regular-r1",
        "evaluation_set_hash": "evaluation-hash",
        "data_version_hash": "data-current",
        "verification_run_id": RUN_ID,
    }
    report.update(overrides)
    return report


def _configure(
    monkeypatch: pytest.MonkeyPatch,
    report: dict[str, Any] | None,
    *,
    active_data_version_hash: str = "data-current",
) -> None:
    monkeypatch.setattr(admin, "list_quality_refresh_events", lambda limit=500: [_event()])
    monkeypatch.setattr(
        admin,
        "_read_latest_quality_reports",
        lambda keys: (
            {key: report if key == "regular_json" else None for key in keys},
            {},
        ),
    )
    monkeypatch.setattr(
        admin,
        "read_active_manifest",
        lambda: {"data_version_hash": active_data_version_hash},
    )


def test_quality_refresh_requires_current_data_version(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure(monkeypatch, _report(data_version_hash="data-old"))

    result = admin._quality_refresh_status()

    assert result["pending_count"] == 1
    assert result["items"][0]["status"] == "pending"


@pytest.mark.parametrize(
    "overrides",
    [
        {"evaluation_set_id": "structured"},
        {"evaluation_set_revision_id": "regular-r2"},
        {"evaluation_set_hash": "other-hash"},
        {"verification_run_id": "invalid"},
    ],
)
def test_quality_refresh_requires_complete_report_identity(
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, Any],
) -> None:
    _configure(monkeypatch, _report(**overrides))

    result = admin._quality_refresh_status()

    assert result["pending_count"] == 1
    assert result["items"][0]["status"] == "pending"


def test_quality_refresh_is_completed_for_matching_complete_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(monkeypatch, _report())

    result = admin._quality_refresh_status()

    assert result["pending_count"] == 0
    assert result["items"][0]["status"] == "completed"
