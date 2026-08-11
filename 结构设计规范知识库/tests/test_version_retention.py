import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from src.app.admin import workflows
from src.app.admin.models import Job
from src.app.admin.storage import JobStore
from src.app.main import app
from src.pipeline import version_retention
from src.pipeline.active_db import write_active_db
from src.pipeline.version_retention import (
    UnsafeVersionPath,
    VersionRetentionError,
    VersionRetentionPolicy,
    create_cleanup_plan,
    execute_cleanup_plan,
    inventory_versions,
    set_version_pin,
)

NOW = datetime(2026, 8, 8, 8, 0, tzinfo=UTC)


def policy(**overrides: int) -> VersionRetentionPolicy:
    values = {
        "keep_recent_passed": 1,
        "success_max_age_days": 30,
        "failed_max_age_days": 7,
        "minimum_age_hours": 24,
        "high_watermark_bytes": 10_000_000,
        "low_watermark_bytes": 8_000_000,
        "plan_ttl_minutes": 15,
    }
    values.update(overrides)
    return VersionRetentionPolicy(**values)


def age_tree(path: Path, *, days: int = 0, hours: int = 0) -> None:
    timestamp = (NOW - timedelta(days=days, hours=hours)).timestamp()
    children = sorted(path.rglob("*"), key=lambda item: len(item.parts), reverse=True)
    for child in children:
        os.utime(child, (timestamp, timestamp))
    os.utime(path, (timestamp, timestamp))


def make_version(
    versions_dir: Path,
    version_id: str,
    *,
    gate_passed: bool | None = None,
    complete: bool = True,
    days_old: int = 40,
    content_size: int = 32,
) -> Path:
    version = versions_dir / version_id
    (version / "db").mkdir(parents=True)
    (version / "db" / "data.bin").write_bytes(b"x" * content_size)
    if complete:
        (version / "manifest.json").write_text(
            json.dumps({"data_version_hash": version_id}), encoding="utf-8"
        )
    if gate_passed is not None:
        gate = version / "quality" / "candidate_activation_gate.json"
        gate.parent.mkdir(parents=True)
        gate.write_text(json.dumps({"passed": gate_passed}), encoding="utf-8")
    age_tree(version, days=days_old)
    return version


def paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    data = tmp_path / "data"
    versions = data / "db_versions"
    versions.mkdir(parents=True)
    return versions, data / "active_db.json", data / "audit"


def by_id(inventory: dict) -> dict[str, dict]:
    return {item["version_id"]: item for item in inventory["versions"]}


def test_inventory_classifies_and_protects_operational_versions(tmp_path: Path):
    versions, pointer, audit = paths(tmp_path)
    make_version(versions, "active", gate_passed=True, days_old=60)
    make_version(versions, "running", complete=False, days_old=60)
    make_version(versions, "pinned", gate_passed=False, days_old=60)
    make_version(versions, "recent", gate_passed=True, days_old=20)
    make_version(versions, "old-passed", gate_passed=True, days_old=40)
    make_version(versions, "old-failed", gate_passed=False, days_old=10)
    write_active_db(
        {
            "active_db_dir": str(versions / "active" / "db"),
            "manifest": str(versions / "active" / "manifest.json"),
        },
        pointer,
    )
    set_version_pin(
        "pinned", pinned=True, note="保留故障证据", versions_dir=versions, audit_dir=audit
    )
    age_tree(versions / "pinned", days=60)

    result = inventory_versions(
        policy=policy(),
        versions_dir=versions,
        pointer_path=pointer,
        jobs=[{"job_id": "running", "type": "rebuild", "status": "running"}],
        now=NOW,
    )
    items = by_id(result)

    assert all("newest_mtime_ns" not in item for item in items.values())
    assert items["active"]["protection_reasons"] == ["active"]
    assert items["running"]["protection_reasons"] == ["running"]
    assert items["pinned"]["protection_reasons"] == ["pinned"]
    assert "recent_rollback" in items["recent"]["protection_reasons"]
    assert items["old-passed"]["cleanup_reason"] == "expired_successful"
    assert items["old-failed"]["cleanup_reason"] == "expired_failed_or_incomplete"
    assert result["cleanup_candidate_count"] == 2


def test_disk_pressure_reclaims_to_low_watermark(tmp_path: Path):
    versions, pointer, _audit = paths(tmp_path)
    for index in range(3):
        make_version(
            versions,
            f"failed-{index}",
            gate_passed=False,
            days_old=3 - index,
            content_size=400,
        )

    result = inventory_versions(
        policy=policy(
            keep_recent_passed=0,
            failed_max_age_days=365,
            minimum_age_hours=0,
            high_watermark_bytes=900,
            low_watermark_bytes=500,
        ),
        versions_dir=versions,
        pointer_path=pointer,
        now=NOW,
    )

    assert result["total_bytes"] > 900
    assert result["projected_bytes"] <= 500
    assert result["cleanup_candidate_count"] == 2
    assert {item["cleanup_reason"] for item in result["versions"] if item["cleanup_eligible"]} == {
        "disk_pressure"
    }


def test_plan_execution_deletes_only_planned_unchanged_versions(tmp_path: Path):
    versions, pointer, audit = paths(tmp_path)
    make_version(versions, "expired", gate_passed=False, days_old=10)
    selected_policy = policy(keep_recent_passed=0)
    plan = create_cleanup_plan(
        policy=selected_policy,
        versions_dir=versions,
        pointer_path=pointer,
        audit_dir=audit,
        now=NOW,
    )

    result = execute_cleanup_plan(
        plan["plan_id"],
        policy=selected_policy,
        versions_dir=versions,
        pointer_path=pointer,
        audit_dir=audit,
        now=NOW + timedelta(minutes=1),
    )

    assert result["status"] == "completed"
    assert result["deleted_count"] == 1
    assert not (versions / "expired").exists()
    assert Path(result["report_path"]).is_file()
    events = (audit / "version_retention" / "events.jsonl").read_text(encoding="utf-8")
    assert "version_cleanup_planned" in events
    assert "version_deleted" in events
    assert "version_cleanup_finished" in events
    with pytest.raises(VersionRetentionError, match="状态不可执行"):
        execute_cleanup_plan(
            plan["plan_id"],
            policy=selected_policy,
            versions_dir=versions,
            pointer_path=pointer,
            audit_dir=audit,
            now=NOW + timedelta(minutes=2),
        )


def test_execution_skips_version_that_became_active(tmp_path: Path):
    versions, pointer, audit = paths(tmp_path)
    version = make_version(versions, "candidate", gate_passed=False, days_old=10)
    selected_policy = policy(keep_recent_passed=0)
    plan = create_cleanup_plan(
        policy=selected_policy,
        versions_dir=versions,
        pointer_path=pointer,
        audit_dir=audit,
        now=NOW,
    )
    write_active_db(
        {"active_db_dir": str(version / "db"), "manifest": str(version / "manifest.json")},
        pointer,
    )

    result = execute_cleanup_plan(
        plan["plan_id"],
        policy=selected_policy,
        versions_dir=versions,
        pointer_path=pointer,
        audit_dir=audit,
        now=NOW + timedelta(minutes=1),
    )

    assert result["status"] == "completed_with_skips"
    assert result["skipped"][0]["reason"] == "protected"
    assert result["skipped"][0]["protection_reasons"] == ["active"]
    assert version.exists()


def test_execution_skips_changed_fingerprint(tmp_path: Path):
    versions, pointer, audit = paths(tmp_path)
    version = make_version(versions, "changed", gate_passed=False, days_old=10)
    selected_policy = policy(keep_recent_passed=0)
    plan = create_cleanup_plan(
        policy=selected_policy,
        versions_dir=versions,
        pointer_path=pointer,
        audit_dir=audit,
        now=NOW,
    )
    (version / "new-evidence.json").write_text("{}", encoding="utf-8")
    age_tree(version, days=10)

    result = execute_cleanup_plan(
        plan["plan_id"],
        policy=selected_policy,
        versions_dir=versions,
        pointer_path=pointer,
        audit_dir=audit,
        now=NOW + timedelta(minutes=1),
    )

    assert result["skipped"] == [{"version_id": "changed", "reason": "fingerprint_changed"}]
    assert version.exists()


def test_expired_or_policy_changed_plan_cannot_execute(tmp_path: Path):
    versions, pointer, audit = paths(tmp_path)
    make_version(versions, "expired", gate_passed=False, days_old=10)
    selected_policy = policy(keep_recent_passed=0)
    expired = create_cleanup_plan(
        policy=selected_policy,
        versions_dir=versions,
        pointer_path=pointer,
        audit_dir=audit,
        now=NOW,
    )
    with pytest.raises(VersionRetentionError, match="已过期"):
        execute_cleanup_plan(
            expired["plan_id"],
            policy=selected_policy,
            versions_dir=versions,
            pointer_path=pointer,
            audit_dir=audit,
            now=NOW + timedelta(minutes=16),
        )

    changed = create_cleanup_plan(
        policy=selected_policy,
        versions_dir=versions,
        pointer_path=pointer,
        audit_dir=audit,
        now=NOW,
    )
    with pytest.raises(VersionRetentionError, match="策略已变化"):
        execute_cleanup_plan(
            changed["plan_id"],
            policy=policy(keep_recent_passed=0, failed_max_age_days=8),
            versions_dir=versions,
            pointer_path=pointer,
            audit_dir=audit,
            now=NOW + timedelta(minutes=1),
        )


def test_delete_failure_restores_visible_version(tmp_path: Path, monkeypatch):
    versions, pointer, audit = paths(tmp_path)
    version = make_version(versions, "recoverable", gate_passed=False, days_old=10)
    selected_policy = policy(keep_recent_passed=0)
    plan = create_cleanup_plan(
        policy=selected_policy,
        versions_dir=versions,
        pointer_path=pointer,
        audit_dir=audit,
        now=NOW,
    )
    monkeypatch.setattr(
        version_retention.shutil, "rmtree", lambda _path: (_ for _ in ()).throw(OSError("locked"))
    )

    result = execute_cleanup_plan(
        plan["plan_id"],
        policy=selected_policy,
        versions_dir=versions,
        pointer_path=pointer,
        audit_dir=audit,
        now=NOW + timedelta(minutes=1),
    )

    assert result["status"] == "partial_failed"
    assert result["failed"][0]["error"] == "locked"
    assert version.exists()
    assert not list(versions.glob(".deleting-*"))


def test_pin_and_path_validation_block_arbitrary_targets(tmp_path: Path):
    versions, _pointer, audit = paths(tmp_path)
    make_version(versions, "kept", gate_passed=False, days_old=10)

    result = set_version_pin(
        "kept", pinned=True, note="调查中", versions_dir=versions, audit_dir=audit
    )

    assert result["pinned"] is True
    assert (
        json.loads((versions / "kept" / ".retention.json").read_text(encoding="utf-8"))["note"]
        == "调查中"
    )
    with pytest.raises(UnsafeVersionPath):
        set_version_pin("../outside", pinned=True, versions_dir=versions, audit_dir=audit)


def test_invalid_pin_marker_fails_closed(tmp_path: Path):
    versions, pointer, _audit = paths(tmp_path)
    version = make_version(versions, "damaged-pin", gate_passed=False, days_old=10)
    (version / ".retention.json").write_text("not-json", encoding="utf-8")
    age_tree(version, days=10)

    result = inventory_versions(
        policy=policy(keep_recent_passed=0),
        versions_dir=versions,
        pointer_path=pointer,
        now=NOW,
    )
    item = by_id(result)["damaged-pin"]

    assert item["protected"] is True
    assert item["protection_reasons"] == ["invalid_pin_marker"]
    assert item["cleanup_eligible"] is False


def test_cleanup_workflow_marks_partial_delete_as_failed(tmp_path: Path, monkeypatch):
    store = JobStore(tmp_path / "jobs")
    job = Job(type="cleanup_versions", params={"plan_id": "a" * 16})
    monkeypatch.setattr(
        workflows,
        "execute_cleanup_plan",
        lambda *_args, **_kwargs: {
            "failed_count": 1,
            "deleted_count": 0,
            "skipped_count": 0,
            "report_path": "report.json",
        },
    )

    with pytest.raises(RuntimeError, match="部分失败"):
        workflows.cleanup_versions_workflow(job, store)

    assert any(entry["level"] == "error" for entry in store.logs(job.job_id))


def test_reparse_version_directory_fails_closed(tmp_path: Path, monkeypatch):
    versions, pointer, _audit = paths(tmp_path)
    version = make_version(versions, "linked", gate_passed=False, days_old=10)
    original = version_retention._is_reparse_point
    monkeypatch.setattr(
        version_retention,
        "_is_reparse_point",
        lambda path: path == version or original(path),
    )

    result = inventory_versions(
        policy=policy(keep_recent_passed=0),
        versions_dir=versions,
        pointer_path=pointer,
        now=NOW,
    )
    item = by_id(result)["linked"]

    assert item["state"] == "unsafe"
    assert item["protected"] is True
    assert "unsafe" in item["protection_reasons"]


def test_openapi_exposes_two_stage_version_management_contract():
    paths = app.openapi()["paths"]

    assert set(paths["/admin/versions"]) == {"get"}
    assert set(paths["/admin/versions/{version_id}/retention"]) == {"put"}
    assert set(paths["/admin/versions/cleanup-plans"]) == {"post"}
    assert set(paths["/admin/jobs/cleanup-versions"]) == {"post"}
