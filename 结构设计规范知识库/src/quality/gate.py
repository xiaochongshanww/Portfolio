from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from src.evaluation.answer_runner import ANSWER_EVAL_PATH
from src.evaluation.runner import DEFAULT_EVAL_PATH, STRUCTURED_EVAL_PATH
from src.pipeline.paths import ACTIVE_DB_PATH, AUDIT_DIR, DATA_DIR, MANIFEST_PATH

from .evidence_context import (
    EVIDENCE_CONTEXT_SCHEMA_VERSION,
    current_evidence_context,
    validate_runtime_config_hash,
    validate_verification_run_id,
)
from .report_store import QualityReportStoreError, resolve_latest_quality_artifacts

DEFAULT_REPORT_MAX_AGE = timedelta(days=7)
MIN_REGULAR_CASES = 100
MIN_STRUCTURED_CASES = 12
MIN_TOP1_SOURCE_HIT_RATE = 0.95
MIN_AUTHORITY_HIT_RATE = 0.95
MIN_STRUCTURED_TABLE_HIT_RATE = 0.95


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _load_jobs(jobs_dir: Path = DATA_DIR / "jobs") -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for path in jobs_dir.glob("*.json"):
        try:
            jobs.append(_read_json(path))
        except (OSError, json.JSONDecodeError):
            continue
    return jobs


def summarize_jobs(
    jobs: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    stale_after: timedelta = timedelta(hours=2),
) -> dict[str, Any]:
    now = (now or datetime.now(UTC)).astimezone(UTC)
    historical_failures = [job for job in jobs if job.get("status") == "failed"]
    latest_by_type: dict[str, dict[str, Any]] = {}
    for job in jobs:
        job_type = str(job.get("type") or "unknown")
        timestamp = _parse_time(
            job.get("finished_at") or job.get("started_at") or job.get("created_at")
        )
        current = latest_by_type.get(job_type)
        current_time = _parse_time(
            (current or {}).get("finished_at")
            or (current or {}).get("started_at")
            or (current or {}).get("created_at")
        )
        if current is None or (timestamp and (current_time is None or timestamp > current_time)):
            latest_by_type[job_type] = job
    unresolved = [job for job in latest_by_type.values() if job.get("status") == "failed"]
    stale = []
    for job in jobs:
        if job.get("status") not in {"queued", "running"}:
            continue
        started = _parse_time(
            job.get("progress_at") or job.get("started_at") or job.get("created_at")
        )
        if started and now - started > stale_after:
            stale.append(job)
    return {
        "historical_failed_count": len(historical_failures),
        "unresolved_failed_count": len(unresolved),
        "stale_active_count": len(stale),
        "unresolved_failures": [
            {"job_id": job.get("job_id"), "type": job.get("type"), "error": job.get("error", "")}
            for job in unresolved
        ],
        "stale_active_jobs": [
            {"job_id": job.get("job_id"), "type": job.get("type"), "status": job.get("status")}
            for job in stale
        ],
    }


def _read_evaluation_report(
    path: Path | None,
    *,
    resolution_error: str | None = None,
) -> tuple[dict[str, Any], str | None]:
    if resolution_error:
        return {}, resolution_error
    if path is None:
        return {}, "missing"
    if not path.is_file():
        return {}, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}, "unreadable"
    if not isinstance(payload, dict):
        return {}, "not_object"
    return payload, None


def evaluate_quality_gate(
    *,
    manifest_path: Path = MANIFEST_PATH,
    regular_report_path: Path | None = None,
    structured_report_path: Path | None = None,
    answer_report_path: Path | None = None,
    regular_eval_path: Path = DEFAULT_EVAL_PATH,
    structured_eval_path: Path = STRUCTURED_EVAL_PATH,
    answer_eval_path: Path = ANSWER_EVAL_PATH,
    active_db_path: Path = ACTIVE_DB_PATH,
    jobs: list[dict[str, Any]] | None = None,
    runtime_collection_count: int | None = None,
    now: datetime | None = None,
    max_report_age: timedelta = DEFAULT_REPORT_MAX_AGE,
    job_stale_after: timedelta = timedelta(hours=2),
    expected_verification_run_id: str | None = None,
    expected_runtime_config_hash: str | None = None,
) -> dict[str, Any]:
    gate_time = (now or datetime.now(UTC)).astimezone(UTC)
    if max_report_age <= timedelta(0):
        raise ValueError("max_report_age 必须大于 0")
    if job_stale_after <= timedelta(0):
        raise ValueError("job_stale_after 必须大于 0")
    manifest = _read_json(manifest_path)
    active_db = _read_json(active_db_path)
    active_manifest_path = Path(str(active_db.get("manifest") or manifest_path))
    if not active_manifest_path.is_absolute():
        active_manifest_path = active_db_path.resolve().parents[1] / active_manifest_path
    active_manifest = _read_json(active_manifest_path) or manifest
    reports_dir = AUDIT_DIR / "reports"
    report_paths = {
        "regular_json": regular_report_path,
        "structured_json": structured_report_path,
        "answer_json": answer_report_path,
    }
    unresolved_keys = [key for key, path in report_paths.items() if path is None]
    resolution_error: str | None = None
    if unresolved_keys:
        try:
            report_paths.update(resolve_latest_quality_artifacts(reports_dir, unresolved_keys))
        except (OSError, QualityReportStoreError, ValueError):
            resolution_error = "latest_pointer_invalid"
    regular, regular_error = _read_evaluation_report(
        report_paths["regular_json"],
        resolution_error=resolution_error if regular_report_path is None else None,
    )
    structured, structured_error = _read_evaluation_report(
        report_paths["structured_json"],
        resolution_error=resolution_error if structured_report_path is None else None,
    )
    answer, answer_error = _read_evaluation_report(
        report_paths["answer_json"],
        resolution_error=resolution_error if answer_report_path is None else None,
    )
    reports = (regular, structured, answer)
    if expected_verification_run_id is not None:
        expected_verification_run_id = validate_verification_run_id(expected_verification_run_id)
    expected_runtime_hash = validate_runtime_config_hash(
        expected_runtime_config_hash or str(current_evidence_context()["runtime_config_hash"])
    )
    job_status = summarize_jobs(
        jobs if jobs is not None else _load_jobs(),
        now=gate_time,
        stale_after=job_stale_after,
    )
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, message: str, **details: Any) -> None:
        checks.append(
            {
                "name": name,
                "status": "passed" if passed else "failed",
                "severity": "info" if passed else "blocking",
                "message": message,
                "details": details,
            }
        )

    report_errors = {
        "regular": regular_error,
        "structured": structured_error,
        "answer": answer_error,
    }
    report_integrity_ok = not any(report_errors.values())
    check(
        "evaluation_report_integrity",
        report_integrity_ok,
        (
            "三类评估报告均可读取且来源指针完整"
            if report_integrity_ok
            else "评估报告缺失、损坏或最新运行指针无效"
        ),
        errors={key: value for key, value in report_errors.items() if value},
    )

    check(
        "manifest",
        bool(active_manifest),
        "活动版本 manifest 可读取" if active_manifest else "缺少活动版本 manifest",
    )
    check(
        "knowledge_base",
        int(active_manifest.get("document_count", 0)) > 0
        and int(active_manifest.get("chunk_count", 0)) > 0,
        f"知识库包含 {active_manifest.get('document_count', 0)} 份文档、{active_manifest.get('chunk_count', 0)} 个 chunk",
    )
    missing_required = int(
        active_manifest.get("artifact_status", {}).get("missing_required_count", 0)
    )
    check("required_artifacts", missing_required == 0, f"缺失必需产物 {missing_required} 项")
    high_risk = int(active_manifest.get("audit_status", {}).get("high_risk_count", 0))
    check("high_risk_audit", high_risk == 0, f"高风险审计项 {high_risk} 项")
    active_version = str(active_db.get("data_version_hash") or "")
    manifest_version = str(active_manifest.get("data_version_hash") or "")
    check(
        "active_db_pointer",
        bool(active_db) and bool(manifest_version) and active_version == manifest_version,
        "活动数据库指针与版本 manifest 一致",
    )
    evidence_schema_ok = all(
        report.get("evidence_context_schema") == EVIDENCE_CONTEXT_SCHEMA_VERSION
        for report in reports
    )
    check(
        "evidence_context_schema",
        evidence_schema_ok,
        (
            f"三类评估报告均使用证据上下文 v{EVIDENCE_CONTEXT_SCHEMA_VERSION}"
            if evidence_schema_ok
            else f"三类评估报告必须使用证据上下文 v{EVIDENCE_CONTEXT_SCHEMA_VERSION}"
        ),
    )

    run_ids = [str(report.get("verification_run_id") or "") for report in reports]
    valid_run_ids: list[str] = []
    for run_id in run_ids:
        try:
            valid_run_ids.append(validate_verification_run_id(run_id))
        except ValueError:
            valid_run_ids.append("")
    common_run_id = valid_run_ids[0] if len(set(valid_run_ids)) == 1 else ""
    run_consistent = bool(common_run_id) and all(valid_run_ids)
    if expected_verification_run_id is not None:
        run_consistent = run_consistent and common_run_id == expected_verification_run_id
    check(
        "evaluation_run_consistency",
        run_consistent,
        (
            "三类评估报告来自同一次完整验证运行"
            if run_consistent
            else "三类评估报告缺少有效运行身份、来自不同运行或不属于当前验证"
        ),
        verification_run_id=common_run_id or None,
    )

    report_runtime_hashes = [str(report.get("runtime_config_hash") or "") for report in reports]
    valid_runtime_hashes: list[str] = []
    for value in report_runtime_hashes:
        try:
            valid_runtime_hashes.append(validate_runtime_config_hash(value))
        except ValueError:
            valid_runtime_hashes.append("")
    runtime_consistent = bool(expected_runtime_hash) and all(
        value == expected_runtime_hash for value in valid_runtime_hashes
    )
    check(
        "runtime_config_consistency",
        runtime_consistent,
        (
            "三类评估报告与当前运行配置及关键实现一致"
            if runtime_consistent
            else "三类评估报告缺少有效运行指纹、指纹不一致或不匹配当前运行配置"
        ),
        runtime_config_hash=expected_runtime_hash,
    )
    expected_collection_count = int(active_manifest.get("chunk_count", 0))
    if runtime_collection_count is not None:
        check(
            "runtime_collection",
            runtime_collection_count == expected_collection_count,
            f"运行集合 {runtime_collection_count} 条，活动版本 {expected_collection_count} 条",
        )

    regular_failures = len(regular.get("failures", []))
    regular_ok = (
        regular.get("ok") is True
        and int(regular.get("case_count", 0)) >= MIN_REGULAR_CASES
        and regular_failures == 0
        and float(regular.get("top1_source_hit_rate", 0)) >= MIN_TOP1_SOURCE_HIT_RATE
        and float(regular.get("authority_hit_rate", 0)) >= MIN_AUTHORITY_HIT_RATE
    )
    check(
        "regular_evaluation",
        regular_ok,
        f"常规评估 {regular.get('case_count', 0)} 项，失败 {regular_failures} 项",
        top1_source_hit_rate=regular.get("top1_source_hit_rate"),
        authority_hit_rate=regular.get("authority_hit_rate"),
    )
    structured_failures = len(structured.get("failures", []))
    structured_ok = (
        structured.get("ok") is True
        and int(structured.get("case_count", 0)) >= MIN_STRUCTURED_CASES
        and structured_failures == 0
        and float(structured.get("structured_table_hit_rate", 0)) >= MIN_STRUCTURED_TABLE_HIT_RATE
    )
    check(
        "structured_evaluation",
        structured_ok,
        f"结构化评估 {structured.get('case_count', 0)} 项，失败 {structured_failures} 项",
        structured_table_hit_rate=structured.get("structured_table_hit_rate"),
    )
    answer_rates = answer.get("check_rates", {})
    answer_ok = (
        answer.get("ok") is True
        and int(answer.get("case_count", 0)) >= 24
        and float(answer.get("pass_rate", 0)) >= 0.90
        and float(answer_rates.get("citations", 0)) == 1.0
        and float(answer_rates.get("citation_grounded", 0)) == 1.0
        and float(answer_rates.get("image_routes", 0)) == 1.0
        and float(answer_rates.get("image_offered", 0)) == 1.0
        and float(answer_rates.get("image_http", 0)) == 1.0
        and float(answer.get("refusal_pass_rate", 0)) == 1.0
    )
    check(
        "answer_evaluation",
        answer_ok,
        f"回答盲测 {answer.get('case_count', 0)} 项，通过率 {float(answer.get('pass_rate', 0)):.1%}",
        citation_grounded_rate=answer_rates.get("citation_grounded"),
        image_http_rate=answer_rates.get("image_http"),
        refusal_pass_rate=answer.get("refusal_pass_rate"),
    )

    data_version = manifest_version

    def report_is_fresh(
        report: dict[str, Any], evaluation_path: Path
    ) -> tuple[bool, datetime | None]:
        generated_at = _parse_time(report.get("generated_at"))
        age = gate_time - generated_at if generated_at else None
        fresh = (
            bool(data_version)
            and report.get("data_version_hash") == data_version
            and report.get("evaluation_set_hash") == _file_hash(evaluation_path)
            and age is not None
            and timedelta(0) <= age <= max_report_age
        )
        return fresh, generated_at

    regular_fresh, regular_generated_at = report_is_fresh(regular, regular_eval_path)
    check(
        "regular_report_freshness",
        regular_fresh,
        "常规评估报告与当前数据及评估集一致，且未超过有效期",
        generated_at=regular_generated_at.isoformat() if regular_generated_at else None,
        max_age_seconds=int(max_report_age.total_seconds()),
    )
    structured_fresh, structured_generated_at = report_is_fresh(structured, structured_eval_path)
    check(
        "structured_report_freshness",
        structured_fresh,
        "结构化评估报告与当前数据及评估集一致，且未超过有效期",
        generated_at=structured_generated_at.isoformat() if structured_generated_at else None,
        max_age_seconds=int(max_report_age.total_seconds()),
    )
    answer_fresh, answer_generated_at = report_is_fresh(answer, answer_eval_path)
    check(
        "answer_report_freshness",
        answer_fresh,
        "回答评估报告与当前数据及盲测集一致，且未超过有效期",
        generated_at=answer_generated_at.isoformat() if answer_generated_at else None,
        max_age_seconds=int(max_report_age.total_seconds()),
    )
    check(
        "unresolved_jobs",
        job_status["unresolved_failed_count"] == 0,
        f"未解决失败任务 {job_status['unresolved_failed_count']} 个",
    )
    check(
        "stale_jobs",
        job_status["stale_active_count"] == 0,
        f"卡住的活动任务 {job_status['stale_active_count']} 个",
    )

    failed_checks = [item["name"] for item in checks if item["status"] == "failed"]
    return {
        "generated_at": gate_time.isoformat(),
        "passed": not failed_checks,
        "failed_checks": failed_checks,
        "checks": checks,
        "jobs": job_status,
        "data_version_hash": data_version,
        "evidence_context_schema": EVIDENCE_CONTEXT_SCHEMA_VERSION,
        "verification_run_id": common_run_id or None,
        "runtime_config_hash": expected_runtime_hash,
    }


def render_quality_gate_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 自动质量门禁报告",
        "",
        f"- 结论：{'通过' if result.get('passed') else '未通过'}",
        f"- 生成时间：{result.get('generated_at', '-')}",
        f"- 数据版本：`{result.get('data_version_hash') or '-'}`",
        f"- 验证运行：`{result.get('verification_run_id') or '-'}`",
        f"- 运行配置指纹：`{result.get('runtime_config_hash') or '-'}`",
        "",
        "## 检查项",
        "",
        "| 检查 | 状态 | 说明 |",
        "| --- | --- | --- |",
    ]
    for item in result.get("checks", []):
        lines.append(f"| `{item.get('name')}` | {item.get('status')} | {item.get('message', '')} |")
    jobs = result.get("jobs", {})
    lines.extend(
        [
            "",
            "## 任务审计",
            "",
            f"- 历史失败：{jobs.get('historical_failed_count', 0)}",
            f"- 未解决失败：{jobs.get('unresolved_failed_count', 0)}",
            f"- 卡住任务：{jobs.get('stale_active_count', 0)}",
            "",
        ]
    )
    return "\n".join(lines)
