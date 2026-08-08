import json
from pathlib import Path

import pytest

from scripts.snapshot_quality_evidence import (
    DEFAULT_SNAPSHOT,
    EvidenceSnapshotError,
    build_snapshot,
    validate_snapshot,
)


def test_committed_quality_evidence_snapshot_is_valid():
    result = validate_snapshot()

    assert result["ok"] is True
    assert result["release_quality_status"] == "not_passed"
    assert result["evaluation_set_count"] == 3


def test_build_snapshot_contains_only_sanitized_summaries(tmp_path: Path):
    project = tmp_path / "project"
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

    snapshot = build_snapshot(project)
    serialized = json.dumps(snapshot, ensure_ascii=False)

    assert set(snapshot["reports"]) == {"verification", "quality_gate"}
    assert "steps" not in serialized
    assert "query" not in serialized
    assert "error" not in serialized
    assert "F:\\" not in serialized


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
        card.read_text(encoding="utf-8").replace(
            "`verification.passed=false`", ""
        ),
        encoding="utf-8",
    )

    with pytest.raises(EvidenceSnapshotError, match="系统卡缺少"):
        validate_snapshot(project)
