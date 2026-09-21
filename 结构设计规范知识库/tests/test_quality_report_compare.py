from __future__ import annotations

from pathlib import Path

from src.quality.report_compare import compare_quality_runs, list_complete_quality_runs
from src.quality.report_store import finalize_quality_run, write_quality_report


def _write_run(
    reports_dir: Path,
    run_id: str,
    *,
    revision_suffix: str,
    data_version_hash: str,
    runtime_config_hash: str,
    failed_regular: bool = False,
) -> None:
    common = {
        "verification_run_id": run_id,
        "data_version_hash": data_version_hash,
        "runtime_config_hash": runtime_config_hash,
    }
    reports = {
        "regular": {
            **common,
            "evaluation_set_id": "regular",
            "evaluation_set_revision_id": f"regular-{revision_suffix}",
            "evaluation_set_hash": f"hash-regular-{revision_suffix}",
            "case_count": 100,
            "top1_source_hit_rate": 0.9 if failed_regular else 1.0,
            "authority_hit_rate": 1.0,
            "clause_hit_rate": 1.0,
            "keyword_hit_rate": 1.0,
            "failures": ([{"id": "case-1"}] if failed_regular else []),
        },
        "structured": {
            **common,
            "evaluation_set_id": "structured",
            "evaluation_set_revision_id": f"structured-{revision_suffix}",
            "evaluation_set_hash": f"hash-structured-{revision_suffix}",
            "case_count": 12,
            "structured_table_hit_rate": 1.0,
            "failures": [],
        },
        "answer": {
            **common,
            "evaluation_set_id": "answer",
            "evaluation_set_revision_id": f"answer-{revision_suffix}",
            "evaluation_set_hash": f"hash-answer-{revision_suffix}",
            "case_count": 24,
            "pass_rate": 1.0,
            "refusal_pass_rate": 1.0,
            "failures": [],
        },
        "gate": {**common, "passed": not failed_regular},
        "verification": {**common, "passed": not failed_regular},
    }
    for kind, payload in reports.items():
        write_quality_report(reports_dir, kind, payload, f"# {kind}\n", verification_run_id=run_id)
    finalize_quality_run(reports_dir, run_id, passed=not failed_regular)


def test_complete_quality_runs_are_listed_and_comparable(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    baseline = "a" * 32
    candidate = "b" * 32
    _write_run(
        reports_dir,
        baseline,
        revision_suffix="one",
        data_version_hash="data-one",
        runtime_config_hash="runtime-one",
    )
    _write_run(
        reports_dir,
        candidate,
        revision_suffix="two",
        data_version_hash="data-two",
        runtime_config_hash="runtime-two",
        failed_regular=True,
    )

    runs = list_complete_quality_runs(reports_dir)
    assert {item["verification_run_id"] for item in runs} == {baseline, candidate}
    comparison = compare_quality_runs(reports_dir, baseline, candidate)
    assert comparison["summary"]["evaluation_set_changed"] is True
    assert comparison["summary"]["runtime_changed"] is True
    assert comparison["evaluation_sets"]["regular"]["failures"]["added"] == ["case-1"]
    assert (
        comparison["evaluation_sets"]["regular"]["metrics"]["top1_source_hit_rate"]["delta"] == -0.1
    )


def test_quality_run_comparison_rejects_same_run(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    run_id = "c" * 32
    _write_run(
        reports_dir,
        run_id,
        revision_suffix="one",
        data_version_hash="data-one",
        runtime_config_hash="runtime-one",
    )
    try:
        compare_quality_runs(reports_dir, run_id, run_id)
    except RuntimeError as exc:
        assert "两个不同" in str(exc)
    else:
        raise AssertionError("same-run comparison should fail")
