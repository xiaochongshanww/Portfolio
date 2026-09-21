from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .evidence_context import validate_verification_run_id
from .report_store import (
    QUALITY_RUNS_DIRECTORY,
    QualityReportStoreError,
    load_quality_run_manifest,
    quality_run_artifact_path,
    read_json_object,
)

REPORT_KEYS = ("regular", "structured", "answer")
REPORT_ARTIFACT_KEYS = {
    "regular": "regular_json",
    "structured": "structured_json",
    "answer": "answer_json",
}
REPORT_METRICS = {
    "regular": (
        "top1_source_hit_rate",
        "authority_hit_rate",
        "clause_hit_rate",
        "keyword_hit_rate",
    ),
    "structured": ("structured_table_hit_rate",),
    "answer": ("pass_rate", "refusal_pass_rate"),
}


def _report_path(reports_dir: Path, run_id: str, kind: str) -> Path:
    return quality_run_artifact_path(reports_dir, run_id, REPORT_ARTIFACT_KEYS[kind])


def _load_run_reports(reports_dir: Path, run_id: str) -> dict[str, dict[str, Any]]:
    validate_verification_run_id(run_id)
    load_quality_run_manifest(reports_dir, run_id)
    return {kind: read_json_object(_report_path(reports_dir, run_id, kind)) for kind in REPORT_KEYS}


def _context(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "data_version_hash": sorted(
            {str(item.get("data_version_hash") or "") for item in reports.values()}
        ),
        "runtime_config_hash": sorted(
            {str(item.get("runtime_config_hash") or "") for item in reports.values()}
        ),
        "evaluation_run_id": sorted(
            {str(item.get("verification_run_id") or "") for item in reports.values()}
        ),
    }


def _evaluation_identity(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "evaluation_set_id": report.get("evaluation_set_id"),
        "revision_id": report.get("evaluation_set_revision_id"),
        "content_hash": report.get("evaluation_set_hash"),
        "case_count": report.get("case_count", 0),
    }


def _failure_ids(report: dict[str, Any]) -> set[str]:
    return {
        str(item.get("id"))
        for item in report.get("failures", [])
        if isinstance(item, dict) and item.get("id") is not None
    }


def _metric_delta(baseline: dict[str, Any], candidate: dict[str, Any], key: str) -> dict[str, Any]:
    before = baseline.get(key)
    after = candidate.get(key)
    delta = (
        round(after - before, 10)
        if isinstance(before, (int, float)) and isinstance(after, (int, float))
        else None
    )
    return {"before": before, "after": after, "delta": delta}


def _compare_kind(
    kind: str,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    baseline_identity = _evaluation_identity(baseline)
    candidate_identity = _evaluation_identity(candidate)
    baseline_failures = _failure_ids(baseline)
    candidate_failures = _failure_ids(candidate)
    return {
        "evaluation_set_changed": (
            baseline_identity["revision_id"] != candidate_identity["revision_id"]
            or baseline_identity["content_hash"] != candidate_identity["content_hash"]
        ),
        "baseline": baseline_identity,
        "candidate": candidate_identity,
        "metrics": {key: _metric_delta(baseline, candidate, key) for key in REPORT_METRICS[kind]},
        "failures": {
            "added": sorted(candidate_failures - baseline_failures),
            "removed": sorted(baseline_failures - candidate_failures),
            "unchanged": sorted(baseline_failures & candidate_failures),
        },
    }


def compare_quality_runs(
    reports_dir: Path,
    baseline_run_id: str,
    candidate_run_id: str,
) -> dict[str, Any]:
    baseline_id = validate_verification_run_id(baseline_run_id)
    candidate_id = validate_verification_run_id(candidate_run_id)
    if baseline_id == candidate_id:
        raise QualityReportStoreError("报告比较必须选择两个不同的质量运行")
    baseline = _load_run_reports(reports_dir, baseline_id)
    candidate = _load_run_reports(reports_dir, candidate_id)
    by_kind = {kind: _compare_kind(kind, baseline[kind], candidate[kind]) for kind in REPORT_KEYS}
    baseline_context = _context(baseline)
    candidate_context = _context(candidate)
    evaluation_set_changed = any(item["evaluation_set_changed"] for item in by_kind.values())
    runtime_changed = (
        baseline_context["data_version_hash"] != candidate_context["data_version_hash"]
        or baseline_context["runtime_config_hash"] != candidate_context["runtime_config_hash"]
    )
    return {
        "schema_version": 1,
        "baseline": {"verification_run_id": baseline_id, "context": baseline_context},
        "candidate": {"verification_run_id": candidate_id, "context": candidate_context},
        "evaluation_sets": by_kind,
        "summary": {
            "evaluation_set_changed": evaluation_set_changed,
            "runtime_changed": runtime_changed,
            "interpretation": (
                "评估集和运行上下文均未变化，可优先归因于检索或回答实现变化。"
                if not evaluation_set_changed and not runtime_changed
                else "比较结果同时包含评估集或运行上下文变化，不能把指标差异直接归因于检索实现。"
            ),
        },
    }


def _iter_run_ids(reports_dir: Path) -> Iterable[str]:
    runs_dir = reports_dir / QUALITY_RUNS_DIRECTORY
    if not runs_dir.is_dir():
        return ()
    return sorted(
        (path.name for path in runs_dir.iterdir() if path.is_dir()),
        reverse=True,
    )


def list_complete_quality_runs(reports_dir: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    if limit <= 0:
        raise ValueError("quality runs limit 必须大于 0")
    result: list[dict[str, Any]] = []
    for run_id in _iter_run_ids(reports_dir):
        try:
            validated_id = validate_verification_run_id(run_id)
            manifest = load_quality_run_manifest(reports_dir, validated_id)
            reports = _load_run_reports(reports_dir, validated_id)
        except (ValueError, QualityReportStoreError, OSError):
            continue
        context = _context(reports)
        result.append(
            {
                "verification_run_id": validated_id,
                "completed_at": manifest["completed_at"],
                "passed": bool(manifest["passed"]),
                "data_version_hash": context["data_version_hash"][0]
                if len(context["data_version_hash"]) == 1
                else None,
                "runtime_config_hash": context["runtime_config_hash"][0]
                if len(context["runtime_config_hash"]) == 1
                else None,
                "evaluation_set_revisions": {
                    kind: reports[kind].get("evaluation_set_revision_id") for kind in REPORT_KEYS
                },
            }
        )
        if len(result) >= limit:
            break
    result.sort(key=lambda item: str(item["completed_at"]), reverse=True)
    return result
