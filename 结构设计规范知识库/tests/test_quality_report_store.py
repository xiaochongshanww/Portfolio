import json
from pathlib import Path

import pytest
from src.quality import report_store
from src.quality.report_store import (
    QUALITY_RUN_LATEST_POINTER_NAME,
    QualityReportStoreError,
    atomic_write_text,
    finalize_quality_run,
    load_quality_run_manifest,
    load_quality_run_pointer,
    quality_report_store_lock,
    quality_run_artifact_path,
    read_json_object,
    resolve_latest_quality_artifact,
    resolve_latest_quality_artifacts,
    write_quality_report,
)

RUN_ID = "a" * 32


def _write_complete_run(
    reports_dir: Path,
    run_id: str = RUN_ID,
    *,
    passed: bool = False,
) -> None:
    for report_kind in ("regular", "structured", "answer", "gate", "verification"):
        payload = {"kind": report_kind, "verification_run_id": run_id}
        if report_kind == "verification":
            payload["passed"] = passed
        write_quality_report(
            reports_dir,
            report_kind,
            payload,
            f"# {report_kind}\n",
            verification_run_id=run_id,
        )


def test_run_scoped_report_does_not_publish_compatibility_files(tmp_path: Path):
    reports_dir = tmp_path / "reports"

    json_path, markdown_path = write_quality_report(
        reports_dir,
        "regular",
        {"ok": True},
        "# report\n",
        verification_run_id=RUN_ID,
    )

    assert json_path == reports_dir / "runs" / RUN_ID / "evaluation.json"
    assert markdown_path == reports_dir / "runs" / RUN_ID / "evaluation.md"
    assert not (reports_dir / "evaluation_latest.json").exists()
    assert not (reports_dir / QUALITY_RUN_LATEST_POINTER_NAME).exists()


def test_finalize_publishes_complete_run_and_compatibility_files(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    _write_complete_run(reports_dir)

    pointer = finalize_quality_run(
        reports_dir,
        RUN_ID,
        passed=False,
        completed_at="2026-08-09T00:00:00+00:00",
    )

    assert pointer["verification_run_id"] == RUN_ID
    assert pointer["passed"] is False
    assert load_quality_run_pointer(reports_dir) == pointer
    assert resolve_latest_quality_artifact(reports_dir, "regular_json") == (
        reports_dir / "runs" / RUN_ID / "evaluation.json"
    )
    assert read_json_object(reports_dir / "evaluation_latest.json")["kind"] == "regular"
    manifest = read_json_object(reports_dir / "runs" / RUN_ID / "manifest.json")
    assert set(manifest["artifacts"]) == set(report_store.REQUIRED_ARTIFACT_KEYS)


def test_finalize_rejects_incomplete_run_without_changing_pointer(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    pointer_path = reports_dir / QUALITY_RUN_LATEST_POINTER_NAME
    pointer_path.parent.mkdir(parents=True)
    pointer_path.write_text("existing pointer", encoding="utf-8")
    write_quality_report(
        reports_dir,
        "regular",
        {"ok": False, "verification_run_id": RUN_ID},
        "# report\n",
        verification_run_id=RUN_ID,
    )

    with pytest.raises(QualityReportStoreError, match="缺少产物"):
        finalize_quality_run(reports_dir, RUN_ID, passed=False)

    assert pointer_path.read_text(encoding="utf-8") == "existing pointer"


def test_atomic_write_failure_preserves_existing_target_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    target = tmp_path / "report.json"
    target.write_text("old", encoding="utf-8")

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError(f"injected replace failure: {source} -> {destination}")

    monkeypatch.setattr(report_store.os, "replace", fail_replace)

    with pytest.raises(OSError, match="injected"):
        atomic_write_text(target, "new")

    assert target.read_text(encoding="utf-8") == "old"
    assert list(tmp_path.glob(".*.tmp")) == []


def test_pointer_rejects_traversal_and_artifact_tampering(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    _write_complete_run(reports_dir, passed=True)
    finalize_quality_run(reports_dir, RUN_ID, passed=True)
    pointer_path = reports_dir / QUALITY_RUN_LATEST_POINTER_NAME
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    pointer["artifacts"]["verification_json"] = "../verification.json"
    pointer_path.write_text(json.dumps(pointer), encoding="utf-8")

    with pytest.raises(QualityReportStoreError, match="相对路径无效"):
        load_quality_run_pointer(reports_dir)

    finalize_quality_run(reports_dir, RUN_ID, passed=True)
    quality_run_artifact_path(reports_dir, RUN_ID, "answer_json").write_text(
        json.dumps({"tampered": True}),
        encoding="utf-8",
    )
    with pytest.raises(QualityReportStoreError, match="完整性校验失败"):
        load_quality_run_pointer(reports_dir)


def test_latest_resolution_falls_back_only_when_pointer_is_absent(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    legacy = reports_dir / "quality_gate_latest.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("{}", encoding="utf-8")

    assert resolve_latest_quality_artifact(reports_dir, "gate_json") == legacy

    (reports_dir / QUALITY_RUN_LATEST_POINTER_NAME).write_text("not-json", encoding="utf-8")
    with pytest.raises(QualityReportStoreError, match="无法读取"):
        resolve_latest_quality_artifact(reports_dir, "gate_json")


def test_json_reader_rejects_non_object_payload(tmp_path: Path):
    path = tmp_path / "report.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(QualityReportStoreError, match="必须是 JSON 对象"):
        read_json_object(path)


def test_finalized_run_is_immutable_but_unchanged_publish_can_retry(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    _write_complete_run(reports_dir)
    first = finalize_quality_run(
        reports_dir,
        RUN_ID,
        passed=False,
        completed_at="2026-08-09T00:00:00+00:00",
    )

    with pytest.raises(QualityReportStoreError, match="不可修改"):
        write_quality_report(
            reports_dir,
            "regular",
            {"verification_run_id": RUN_ID},
            "changed",
            verification_run_id=RUN_ID,
        )

    assert (
        finalize_quality_run(
            reports_dir,
            RUN_ID,
            passed=False,
            completed_at="2026-08-09T00:00:00+00:00",
        )
        == first
    )


def test_finalize_rejects_report_from_another_run(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    _write_complete_run(reports_dir)
    quality_run_artifact_path(reports_dir, RUN_ID, "regular_json").write_text(
        json.dumps({"verification_run_id": "b" * 32}),
        encoding="utf-8",
    )

    with pytest.raises(QualityReportStoreError, match="运行身份不一致"):
        finalize_quality_run(reports_dir, RUN_ID, passed=False)


def test_manifest_loader_rejects_verification_conclusion_mismatch(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    _write_complete_run(reports_dir, passed=False)
    finalize_quality_run(reports_dir, RUN_ID, passed=False)
    manifest_path = reports_dir / "runs" / RUN_ID / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["passed"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(QualityReportStoreError, match="结论.*不一致"):
        load_quality_run_manifest(reports_dir, RUN_ID)


def test_publish_failure_keeps_previous_pointer_and_can_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    reports_dir = tmp_path / "reports"
    previous_run_id = "b" * 32
    _write_complete_run(reports_dir, previous_run_id)
    finalize_quality_run(
        reports_dir,
        previous_run_id,
        passed=False,
        completed_at="2026-08-08T00:00:00+00:00",
    )
    previous_pointer = (reports_dir / QUALITY_RUN_LATEST_POINTER_NAME).read_bytes()

    _write_complete_run(reports_dir, RUN_ID)
    real_atomic_write_bytes = report_store.atomic_write_bytes

    def fail_compatibility_write(path: Path, content: bytes) -> None:
        if path.name == "quality_gate_latest.md":
            raise OSError("injected compatibility publish failure")
        real_atomic_write_bytes(path, content)

    monkeypatch.setattr(report_store, "atomic_write_bytes", fail_compatibility_write)
    with pytest.raises(OSError, match="injected"):
        finalize_quality_run(
            reports_dir,
            RUN_ID,
            passed=False,
            completed_at="2026-08-09T00:00:00+00:00",
        )
    assert (reports_dir / QUALITY_RUN_LATEST_POINTER_NAME).read_bytes() == previous_pointer

    monkeypatch.setattr(report_store, "atomic_write_bytes", real_atomic_write_bytes)
    pointer = finalize_quality_run(
        reports_dir,
        RUN_ID,
        passed=False,
        completed_at="2026-08-09T00:00:00+00:00",
    )
    assert pointer["verification_run_id"] == RUN_ID


def test_batch_resolution_validates_latest_pointer_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    reports_dir = tmp_path / "reports"
    _write_complete_run(reports_dir)
    finalize_quality_run(reports_dir, RUN_ID, passed=False)
    real_load = report_store.load_quality_run_pointer
    calls = 0

    def counted_load(path: Path):
        nonlocal calls
        calls += 1
        return real_load(path)

    monkeypatch.setattr(report_store, "load_quality_run_pointer", counted_load)

    resolved = resolve_latest_quality_artifacts(
        reports_dir,
        ("regular_json", "structured_json", "answer_json"),
    )

    assert calls == 1
    assert set(resolved) == {"regular_json", "structured_json", "answer_json"}


def test_store_lock_times_out_instead_of_overlapping_writer(tmp_path: Path):
    reports_dir = tmp_path / "reports"

    with quality_report_store_lock(reports_dir):
        with pytest.raises(QualityReportStoreError, match="存储锁超时"):
            with quality_report_store_lock(reports_dir, timeout_seconds=0.01):
                pytest.fail("第二个写入者不应取得同一存储锁")
