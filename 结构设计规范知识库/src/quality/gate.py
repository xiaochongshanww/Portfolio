from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.evaluation.runner import DEFAULT_EVAL_PATH, STRUCTURED_EVAL_PATH
from src.evaluation.answer_runner import ANSWER_EVAL_PATH
from src.pipeline.paths import ACTIVE_DB_PATH, AUDIT_DIR, DATA_DIR, MANIFEST_PATH


REGULAR_REPORT_PATH = AUDIT_DIR / "reports" / "evaluation_latest.json"
STRUCTURED_REPORT_PATH = AUDIT_DIR / "reports" / "evaluation_structured_latest.json"
ANSWER_REPORT_PATH = AUDIT_DIR / "reports" / "evaluation_answer_latest.json"
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
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    historical_failures = [job for job in jobs if job.get("status") == "failed"]
    latest_by_type: dict[str, dict[str, Any]] = {}
    for job in jobs:
        job_type = str(job.get("type") or "unknown")
        timestamp = _parse_time(job.get("finished_at") or job.get("started_at") or job.get("created_at"))
        current = latest_by_type.get(job_type)
        current_time = _parse_time(
            (current or {}).get("finished_at")
            or (current or {}).get("started_at")
            or (current or {}).get("created_at")
        )
        if current is None or (timestamp and (current_time is None or timestamp > current_time)):
            latest_by_type[job_type] = job
    unresolved = [
        job
        for job in latest_by_type.values()
        if job.get("status") == "failed"
    ]
    stale = []
    for job in jobs:
        if job.get("status") not in {"queued", "running"}:
            continue
        started = _parse_time(
            job.get("progress_at")
            or job.get("started_at")
            or job.get("created_at")
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


def evaluate_quality_gate(
    *,
    manifest_path: Path = MANIFEST_PATH,
    regular_report_path: Path = REGULAR_REPORT_PATH,
    structured_report_path: Path = STRUCTURED_REPORT_PATH,
    answer_report_path: Path = ANSWER_REPORT_PATH,
    regular_eval_path: Path = DEFAULT_EVAL_PATH,
    structured_eval_path: Path = STRUCTURED_EVAL_PATH,
    answer_eval_path: Path = ANSWER_EVAL_PATH,
    active_db_path: Path = ACTIVE_DB_PATH,
    jobs: list[dict[str, Any]] | None = None,
    runtime_collection_count: int | None = None,
    now: datetime | None = None,
    max_report_age: timedelta = DEFAULT_REPORT_MAX_AGE,
    job_stale_after: timedelta = timedelta(hours=2),
) -> dict[str, Any]:
    gate_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
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
    regular = _read_json(regular_report_path)
    structured = _read_json(structured_report_path)
    answer = _read_json(answer_report_path)
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

    check("manifest", bool(active_manifest), "活动版本 manifest 可读取" if active_manifest else "缺少活动版本 manifest")
    check(
        "knowledge_base",
        int(active_manifest.get("document_count", 0)) > 0 and int(active_manifest.get("chunk_count", 0)) > 0,
        f"知识库包含 {active_manifest.get('document_count', 0)} 份文档、{active_manifest.get('chunk_count', 0)} 个 chunk",
    )
    missing_required = int(active_manifest.get("artifact_status", {}).get("missing_required_count", 0))
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

    def report_is_fresh(report: dict[str, Any], evaluation_path: Path) -> tuple[bool, datetime | None]:
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
    }


def render_quality_gate_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 自动质量门禁报告",
        "",
        f"- 结论：{'通过' if result.get('passed') else '未通过'}",
        f"- 生成时间：{result.get('generated_at', '-')}",
        f"- 数据版本：`{result.get('data_version_hash') or '-'}`",
        "",
        "## 检查项",
        "",
        "| 检查 | 状态 | 说明 |",
        "| --- | --- | --- |",
    ]
    for item in result.get("checks", []):
        lines.append(
            f"| `{item.get('name')}` | {item.get('status')} | {item.get('message', '')} |"
        )
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
