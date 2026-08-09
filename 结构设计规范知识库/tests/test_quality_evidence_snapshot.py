import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import scripts.snapshot_quality_evidence as quality_evidence
from scripts.snapshot_quality_evidence import (
    DEFAULT_HISTORY_DIR,
    DEFAULT_HISTORY_INDEX,
    DEFAULT_SNAPSHOT,
    EvidenceSnapshotError,
    build_history_index,
    build_snapshot,
    validate_history,
    validate_snapshot,
    write_snapshot,
)


def _write_quality_source_fixture(project: Path) -> None:
    reports = {
        Path("data/audit/reports/verification_latest.json"): {
            "generated_at": "2026-08-08T17:36:42+00:00",
            "passed": False,
            "steps": [{"error": "sensitive execution detail"}],
        },
        Path("data/audit/reports/quality_gate_latest.json"): {
            "generated_at": "2026-08-08T17:36:41+00:00",
            "passed": False,
            "failed_checks": ["regular_evaluation"],
            "checks": [{"details": {"query": "sensitive query"}}],
        },
    }
    for relative_path, payload in reports.items():
        target = project / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload), encoding="utf-8")
    for relative_path in (
        Path("data/evaluation/queries.jsonl"),
        Path("data/evaluation/complex_structured_tables.jsonl"),
        Path("data/evaluation/answer_holdout.jsonl"),
    ):
        target = project / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(relative_path.read_bytes())


def _copy_committed_history(project: Path) -> None:
    snapshot_target = project / DEFAULT_SNAPSHOT
    snapshot_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DEFAULT_SNAPSHOT, snapshot_target)
    shutil.copytree(DEFAULT_HISTORY_DIR, project / DEFAULT_HISTORY_DIR)
    shutil.copy2(DEFAULT_HISTORY_INDEX, project / DEFAULT_HISTORY_INDEX)


def test_committed_quality_evidence_snapshot_is_valid():
    result = validate_snapshot()

    assert result["ok"] is True
    assert result["release_quality_status"] == "not_passed"
    assert result["evaluation_set_count"] == 3


def test_committed_quality_evidence_history_is_valid():
    result = validate_history()

    assert result["history_entry_count"] >= 1
    assert result["current_snapshot_archived"] is True


def test_build_snapshot_contains_only_sanitized_summaries(tmp_path: Path):
    project = tmp_path / "project"
    _write_quality_source_fixture(project)

    snapshot = build_snapshot(project)
    serialized = json.dumps(snapshot, ensure_ascii=False)

    assert set(snapshot["reports"]) == {"verification", "quality_gate"}
    assert "steps" not in serialized
    assert "query" not in serialized
    assert "error" not in serialized
    assert "F:\\" not in serialized


def test_snapshot_history_write_is_idempotent_and_deterministic(tmp_path: Path):
    project = tmp_path / "project"
    _write_quality_source_fixture(project)

    write_snapshot(project)
    first_archives = sorted((project / DEFAULT_HISTORY_DIR).glob("*.json"))
    first_index = (project / DEFAULT_HISTORY_INDEX).read_bytes()
    write_snapshot(project)

    assert sorted((project / DEFAULT_HISTORY_DIR).glob("*.json")) == first_archives
    assert (project / DEFAULT_HISTORY_INDEX).read_bytes() == first_index
    assert validate_history(project)["history_entry_count"] == 1

    verification_path = project / "data/audit/reports/verification_latest.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    verification["generated_at"] = "2026-08-09T01:00:00+00:00"
    verification_path.write_text(json.dumps(verification), encoding="utf-8")
    write_snapshot(project)

    index = json.loads((project / DEFAULT_HISTORY_INDEX).read_text(encoding="utf-8"))
    assert len(index["entries"]) == 2
    assert [entry["verification_generated_at"] for entry in index["entries"]] == [
        "2026-08-09T01:00:00+00:00",
        "2026-08-08T17:36:42+00:00",
    ]
    assert index == build_history_index(project)
    archive_text = "\n".join(
        path.read_text(encoding="utf-8") for path in (project / DEFAULT_HISTORY_DIR).glob("*.json")
    )
    assert "sensitive execution detail" not in archive_text
    assert "sensitive query" not in archive_text


def test_snapshot_write_publishes_latest_after_history_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    project = tmp_path / "project"
    _write_quality_source_fixture(project)
    latest = project / DEFAULT_SNAPSHOT
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text("existing latest", encoding="utf-8")
    original_write = quality_evidence._write_json_atomic

    def fail_on_index(path: Path, payload: dict[str, object]) -> None:
        if path == project / DEFAULT_HISTORY_INDEX:
            raise EvidenceSnapshotError("injected index failure")
        original_write(path, payload)

    monkeypatch.setattr(quality_evidence, "_write_json_atomic", fail_on_index)

    with pytest.raises(EvidenceSnapshotError, match="injected index failure"):
        write_snapshot(project)

    assert latest.read_text(encoding="utf-8") == "existing latest"


def test_history_validation_rejects_tampered_archive(tmp_path: Path):
    project = tmp_path / "project"
    _copy_committed_history(project)
    archive = next((project / DEFAULT_HISTORY_DIR).glob("*.json"))
    payload = json.loads(archive.read_text(encoding="utf-8"))
    payload["reports"]["verification"]["generated_at"] = "2026-08-09T00:00:00+00:00"
    archive.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(EvidenceSnapshotError, match="文件名与内容指纹不一致"):
        validate_history(project)


def test_history_validation_rejects_stale_index(tmp_path: Path):
    project = tmp_path / "project"
    _copy_committed_history(project)
    (project / DEFAULT_HISTORY_INDEX).write_text(
        json.dumps({"schema_version": 1, "entries": []}),
        encoding="utf-8",
    )

    with pytest.raises(EvidenceSnapshotError, match="历史索引与归档不一致"):
        validate_history(project)


def test_history_validation_requires_current_snapshot_to_be_archived(
    tmp_path: Path,
):
    project = tmp_path / "project"
    _copy_committed_history(project)
    snapshot = json.loads((project / DEFAULT_SNAPSHOT).read_text(encoding="utf-8"))
    snapshot["reports"]["verification"]["generated_at"] = "2026-08-09T00:00:00+00:00"
    (project / DEFAULT_SNAPSHOT).write_text(
        json.dumps(snapshot, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(EvidenceSnapshotError, match="当前质量证据快照尚未归档"):
        validate_history(project)


def test_snapshot_validation_rejects_evaluation_set_drift(tmp_path: Path):
    project = tmp_path / "project"
    snapshot = json.loads(DEFAULT_SNAPSHOT.read_text(encoding="utf-8"))
    for relative_path in (
        Path("docs/quality/质量证据状态.json"),
        Path("docs/quality/检索增强生成系统卡.md"),
        Path("data/evaluation/queries.jsonl"),
        Path("data/evaluation/complex_structured_tables.jsonl"),
        Path("data/evaluation/answer_holdout.jsonl"),
    ):
        source = Path(relative_path)
        target = project / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative_path.suffix == ".jsonl":
            target.write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )
        else:
            target.write_bytes(source.read_bytes())

    snapshot["evaluation_sets"]["regular"]["case_count"] += 1
    (project / DEFAULT_SNAPSHOT).write_text(
        json.dumps(snapshot, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(EvidenceSnapshotError, match="评估集摘要已漂移"):
        validate_snapshot(project)


def test_snapshot_validation_supports_clean_checkout_without_audit_reports(
    tmp_path: Path,
):
    project = tmp_path / "project"
    for relative_path in (
        Path("docs/quality/质量证据状态.json"),
        Path("docs/quality/检索增强生成系统卡.md"),
        Path("data/evaluation/queries.jsonl"),
        Path("data/evaluation/complex_structured_tables.jsonl"),
        Path("data/evaluation/answer_holdout.jsonl"),
    ):
        source = Path(relative_path)
        target = project / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative_path.suffix == ".jsonl":
            target.write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )
        else:
            target.write_bytes(source.read_bytes())

    result = validate_snapshot(project)

    assert result["ok"] is True
    assert result["verified_source_report_count"] == 0


def test_snapshot_validation_rejects_missing_system_card_marker(tmp_path: Path):
    project = tmp_path / "project"
    for relative_path in (
        Path("docs/quality/质量证据状态.json"),
        Path("docs/quality/检索增强生成系统卡.md"),
        Path("data/evaluation/queries.jsonl"),
        Path("data/evaluation/complex_structured_tables.jsonl"),
        Path("data/evaluation/answer_holdout.jsonl"),
    ):
        source = Path(relative_path)
        target = project / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())

    card = project / "docs/quality/检索增强生成系统卡.md"
    card.write_text(
        card.read_text(encoding="utf-8").replace("`verification.passed=false`", ""),
        encoding="utf-8",
    )

    with pytest.raises(EvidenceSnapshotError, match="系统卡缺少"):
        validate_snapshot(project)


def test_snapshot_cli_is_safe_for_ascii_only_console():
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "ascii"

    completed = subprocess.run(
        [sys.executable, "scripts/snapshot_quality_evidence.py"],
        cwd=Path.cwd(),
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["snapshot"] == "docs/quality/质量证据状态.json"
