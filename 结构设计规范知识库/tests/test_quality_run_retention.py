import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from src.quality.report_store import (
    QualityReportStoreError,
    finalize_quality_run,
    write_quality_report,
)
from src.quality.run_retention import (
    QualityRunRetentionError,
    QualityRunRetentionPolicy,
    create_quality_run_cleanup_plan,
    execute_quality_run_cleanup_plan,
    list_quality_runs,
)


def _write_complete_run(
    reports_dir: Path,
    run_id: str,
    completed_at: datetime,
    *,
    passed: bool = False,
) -> None:
    for kind in ("regular", "structured", "answer", "gate", "verification"):
        payload = {"verification_run_id": run_id, "kind": kind}
        if kind == "verification":
            payload["passed"] = passed
        write_quality_report(
            reports_dir,
            kind,
            payload,
            f"# {kind}\n",
            verification_run_id=run_id,
        )
    finalize_quality_run(
        reports_dir,
        run_id,
        passed=passed,
        completed_at=completed_at.isoformat(),
    )


def _write_incomplete_run(reports_dir: Path, run_id: str, modified_at: datetime) -> Path:
    run_dir = reports_dir / "runs" / run_id
    run_dir.mkdir(parents=True)
    report = run_dir / "evaluation.json"
    report.write_text(json.dumps({"verification_run_id": run_id}), encoding="utf-8")
    timestamp = modified_at.timestamp()
    os.utime(report, (timestamp, timestamp))
    os.utime(run_dir, (timestamp, timestamp))
    return run_dir


def _snapshot(path: Path, run_id: str) -> Path:
    path.write_text(
        json.dumps(
            {
                "reports": {
                    "verification": {"path": f"data/audit/reports/runs/{run_id}/verification.json"}
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def _aggressive_policy() -> QualityRunRetentionPolicy:
    return QualityRunRetentionPolicy(
        keep_recent_complete=0,
        complete_max_age_days=0,
        incomplete_max_age_days=0,
        minimum_age_hours=0,
        plan_ttl_minutes=15,
    )


def test_inventory_protects_latest_snapshot_and_recent_complete(tmp_path: Path):
    reports = tmp_path / "reports"
    now = datetime(2026, 8, 9, 12, tzinfo=UTC)
    snapshot_run = "1" * 32
    unprotected_run = "2" * 32
    latest_run = "3" * 32
    _write_complete_run(reports, snapshot_run, now - timedelta(days=100))
    _write_complete_run(reports, unprotected_run, now - timedelta(days=99))
    _write_complete_run(reports, latest_run, now - timedelta(days=98))
    snapshot = _snapshot(tmp_path / "snapshot.json", snapshot_run)

    inventory = list_quality_runs(
        reports,
        snapshot_paths=[snapshot],
        policy=QualityRunRetentionPolicy(
            keep_recent_complete=1,
            complete_max_age_days=90,
            incomplete_max_age_days=7,
            minimum_age_hours=24,
        ),
        now=now,
    )
    rows = {row["run_id"]: row for row in inventory["runs"]}

    assert inventory["eligible_count"] == 1
    assert "snapshot_reference" in rows[snapshot_run]["protection_reasons"]
    assert rows[unprotected_run]["eligible"] is True
    assert {"latest", "recent_complete"} <= set(rows[latest_run]["protection_reasons"])


def test_inventory_classifies_old_incomplete_run_as_candidate(tmp_path: Path):
    reports = tmp_path / "reports"
    now = datetime(2026, 8, 9, 12, tzinfo=UTC)
    run_id = "4" * 32
    _write_incomplete_run(reports, run_id, now - timedelta(days=8))

    inventory = list_quality_runs(reports, policy=QualityRunRetentionPolicy(), now=now)

    assert inventory["incomplete_count"] == 1
    assert inventory["runs"][0]["classification"] == "incomplete"
    assert inventory["runs"][0]["eligible"] is True


def test_inventory_fails_closed_for_corrupt_pointer(tmp_path: Path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "quality_run_latest.json").write_text("not-json", encoding="utf-8")

    with pytest.raises(QualityReportStoreError, match="无法读取"):
        list_quality_runs(reports)


def test_inventory_fails_closed_for_corrupt_snapshot(tmp_path: Path):
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text("not-json", encoding="utf-8")

    with pytest.raises(QualityRunRetentionError, match="快照无法读取"):
        list_quality_runs(tmp_path / "reports", snapshot_paths=[snapshot])


def test_plan_and_execute_delete_only_revalidated_candidates(tmp_path: Path):
    reports = tmp_path / "reports"
    audit = tmp_path / "audit"
    now = datetime(2026, 8, 9, 12, tzinfo=UTC)
    old_run = "5" * 32
    latest_run = "6" * 32
    _write_complete_run(reports, old_run, now - timedelta(days=10))
    _write_complete_run(reports, latest_run, now - timedelta(days=1))
    policy = _aggressive_policy()

    plan = create_quality_run_cleanup_plan(reports, audit, policy=policy, now=now)
    result = execute_quality_run_cleanup_plan(
        reports,
        audit,
        plan["plan_id"],
        snapshot_paths=[],
        confirm=True,
        now=now,
    )

    assert plan["candidate_count"] == 1
    assert result["status"] == "succeeded"
    assert result["deleted_count"] == 1
    assert not (reports / "runs" / old_run).exists()
    assert (reports / "runs" / latest_run).is_dir()
    assert Path(result["execution_path"]).is_file()
    events = (audit / "quality_run_retention" / "events.jsonl").read_text(encoding="utf-8")
    assert "quality_run_cleanup_planned" in events
    assert "quality_run_cleanup_executed" in events


def test_execute_requires_explicit_confirmation(tmp_path: Path):
    plan = create_quality_run_cleanup_plan(
        tmp_path / "reports",
        tmp_path / "audit",
        policy=_aggressive_policy(),
    )

    with pytest.raises(QualityRunRetentionError, match="显式确认"):
        execute_quality_run_cleanup_plan(
            tmp_path / "reports",
            tmp_path / "audit",
            plan["plan_id"],
        )


def test_execute_rejects_plan_path_traversal(tmp_path: Path):
    with pytest.raises(QualityRunRetentionError, match="计划标识无效"):
        execute_quality_run_cleanup_plan(
            tmp_path / "reports",
            tmp_path / "audit",
            "../outside",
            confirm=True,
        )


def test_execute_rejects_candidate_content_drift(tmp_path: Path):
    reports = tmp_path / "reports"
    audit = tmp_path / "audit"
    now = datetime(2026, 8, 9, 12, tzinfo=UTC)
    run_id = "7" * 32
    run_dir = _write_incomplete_run(reports, run_id, now - timedelta(days=8))
    plan = create_quality_run_cleanup_plan(
        reports,
        audit,
        policy=_aggressive_policy(),
        now=now,
    )
    (run_dir / "new.txt").write_text("changed", encoding="utf-8")

    with pytest.raises(QualityRunRetentionError, match="内容已变化"):
        execute_quality_run_cleanup_plan(
            reports,
            audit,
            plan["plan_id"],
            confirm=True,
            now=now,
        )
    assert run_dir.is_dir()


def test_execute_rejects_changed_latest_protection(tmp_path: Path):
    reports = tmp_path / "reports"
    audit = tmp_path / "audit"
    now = datetime(2026, 8, 9, 12, tzinfo=UTC)
    old_run = "8" * 32
    initial_latest = "9" * 32
    new_latest = "a" * 32
    _write_complete_run(reports, old_run, now - timedelta(days=10))
    _write_complete_run(reports, initial_latest, now - timedelta(days=2))
    plan = create_quality_run_cleanup_plan(
        reports,
        audit,
        policy=_aggressive_policy(),
        now=now,
    )
    _write_complete_run(reports, new_latest, now - timedelta(days=1))

    with pytest.raises(QualityRunRetentionError, match="保护集已变化"):
        execute_quality_run_cleanup_plan(
            reports,
            audit,
            plan["plan_id"],
            confirm=True,
            now=now,
        )
    assert (reports / "runs" / old_run).is_dir()


def test_execute_rejects_expired_plan(tmp_path: Path):
    created = datetime(2026, 8, 9, 12, tzinfo=UTC)
    plan = create_quality_run_cleanup_plan(
        tmp_path / "reports",
        tmp_path / "audit",
        policy=_aggressive_policy(),
        now=created,
    )

    with pytest.raises(QualityRunRetentionError, match="已过期"):
        execute_quality_run_cleanup_plan(
            tmp_path / "reports",
            tmp_path / "audit",
            plan["plan_id"],
            confirm=True,
            now=created + timedelta(minutes=16),
        )


def test_failed_recursive_delete_restores_quarantined_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from src.quality import run_retention

    reports = tmp_path / "reports"
    audit = tmp_path / "audit"
    now = datetime(2026, 8, 9, 12, tzinfo=UTC)
    run_id = "b" * 32
    run_dir = _write_incomplete_run(reports, run_id, now - timedelta(days=8))
    plan = create_quality_run_cleanup_plan(
        reports,
        audit,
        policy=_aggressive_policy(),
        now=now,
    )
    monkeypatch.setattr(
        run_retention.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(OSError("injected delete failure")),
    )

    result = execute_quality_run_cleanup_plan(
        reports,
        audit,
        plan["plan_id"],
        confirm=True,
        now=now,
    )

    assert result["status"] == "partial_failed"
    assert result["failed_count"] == 1
    assert run_dir.is_dir()
    assert not list((reports / "runs").glob(".deleting-*"))


def test_invalid_run_directory_is_never_candidate(tmp_path: Path):
    reports = tmp_path / "reports"
    invalid = reports / "runs" / "not-a-run-id"
    invalid.mkdir(parents=True)
    (invalid / "report.txt").write_text("content", encoding="utf-8")

    inventory = list_quality_runs(reports, policy=_aggressive_policy())

    assert inventory["invalid_count"] == 1
    assert inventory["runs"][0]["eligible"] is False
    assert inventory["runs"][0]["protection_reasons"] == ["invalid"]
