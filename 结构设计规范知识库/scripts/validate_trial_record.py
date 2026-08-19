from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"planned", "running", "completed", "paused"}
DECISIONS = {"continue", "adjust", "pause"}
DEFECT_CATEGORIES = {"content", "parsing", "retrieval", "citation", "ui", "permission"}
SEVERITIES = {"low", "medium", "high", "critical"}
REQUIRED_PREFLIGHT = {
    "participant_acknowledged",
    "source_scope_confirmed",
    "no_unrelated_data",
    "key_log_owner_defined",
    "disclaimer_shown",
}
SECRET_FIELD_NAMES = {
    "api_key",
    "apikey",
    "access_token",
    "authorization",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
}
SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{20,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{16,}"),
)


class TrialRecordError(ValueError):
    def __init__(self, issues: list[str] | str):
        self.issues = [issues] if isinstance(issues, str) else list(issues)
        super().__init__("；".join(self.issues))


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TrialRecordError(f"试用记录不存在：{path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrialRecordError(f"试用记录无法读取或不是有效 UTF-8 JSON：{path}") from exc
    if not isinstance(value, dict):
        raise TrialRecordError("试用记录根节点必须是对象")
    return value


def _required_string(value: Any, label: str, issues: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{label}必须是非空字符串")
        return ""
    return value.strip()


def _string_list(value: Any, label: str, issues: list[str], *, required: bool) -> list[str]:
    if not isinstance(value, list):
        if required:
            issues.append(f"{label}必须是字符串数组")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            issues.append(f"{label}[{index}]必须是非空字符串")
        else:
            result.append(item.strip())
    if required and not result:
        issues.append(f"{label}不能为空")
    return result


def _iso_datetime(value: Any, label: str, issues: list[str], *, required: bool) -> str:
    if value in (None, ""):
        if required:
            issues.append(f"{label}必须填写 ISO 8601 时间")
        return ""
    if not isinstance(value, str):
        issues.append(f"{label}必须是 ISO 8601 时间字符串")
        return ""
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        issues.append(f"{label}不是有效 ISO 8601 时间：{value}")
    return value


def _iso_date(value: Any, label: str, issues: list[str], *, required: bool) -> str:
    if value in (None, ""):
        if required:
            issues.append(f"{label}必须填写 ISO 8601 日期")
        return ""
    if not isinstance(value, str):
        issues.append(f"{label}必须是 ISO 8601 日期字符串")
        return ""
    try:
        date.fromisoformat(value)
    except ValueError:
        issues.append(f"{label}不是有效 ISO 8601 日期：{value}")
    return value


def _validate_no_secrets(value: Any, path: str, issues: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_name = str(key).strip().lower().replace("-", "_")
            if key_name in SECRET_FIELD_NAMES:
                issues.append(f"{path}.{key}禁止保存密钥、令牌或凭据")
            _validate_no_secrets(item, f"{path}.{key}", issues)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_no_secrets(item, f"{path}[{index}]", issues)
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS):
            issues.append(f"{path}疑似包含访问令牌，必须删除后再保存")


def _validate_task(task: Any, index: int, issues: list[str], *, completed: bool) -> None:
    label = f"fixed_tasks[{index}]"
    if not isinstance(task, dict):
        issues.append(f"{label}必须是对象")
        return
    _required_string(task.get("task_id"), f"{label}.task_id", issues)
    _required_string(task.get("question"), f"{label}.question", issues)
    if not isinstance(task.get("found_basis"), bool):
        issues.append(f"{label}.found_basis必须是布尔值")
    _string_list(task.get("references"), f"{label}.references", issues, required=completed)
    if not isinstance(task.get("human_review_required"), bool):
        issues.append(f"{label}.human_review_required必须是布尔值")
    _string_list(task.get("defect_ids", []), f"{label}.defect_ids", issues, required=False)


def _validate_defect(defect: Any, index: int, issues: list[str]) -> None:
    label = f"defects[{index}]"
    if not isinstance(defect, dict):
        issues.append(f"{label}必须是对象")
        return
    _required_string(defect.get("defect_id"), f"{label}.defect_id", issues)
    category = _required_string(defect.get("category"), f"{label}.category", issues)
    if category and category not in DEFECT_CATEGORIES:
        issues.append(f"{label}.category不受支持：{category}")
    severity = _required_string(defect.get("severity"), f"{label}.severity", issues)
    if severity and severity not in SEVERITIES:
        issues.append(f"{label}.severity不受支持：{severity}")
    _required_string(defect.get("reproduction"), f"{label}.reproduction", issues)
    _required_string(defect.get("resolution"), f"{label}.resolution", issues)


def _validate_conclusion(record: dict[str, Any], status: str, issues: list[str]) -> None:
    conclusion = record.get("conclusion")
    if not isinstance(conclusion, dict):
        issues.append("completed/paused 试用必须包含 conclusion 对象")
        return
    decision = _required_string(conclusion.get("decision"), "conclusion.decision", issues)
    if decision and decision not in DECISIONS:
        issues.append(f"conclusion.decision不受支持：{decision}")
    if status == "paused" and decision != "pause":
        issues.append("paused 试用的 conclusion.decision 必须是 pause")
    _string_list(conclusion.get("evidence"), "conclusion.evidence", issues, required=True)
    _string_list(
        conclusion.get("unresolved_risks"), "conclusion.unresolved_risks", issues, required=False
    )
    if not isinstance(conclusion.get("data_deleted"), bool):
        issues.append("conclusion.data_deleted必须是布尔值")
    if conclusion.get("data_deleted") is True:
        _iso_date(record.get("data_cleanup_date"), "data_cleanup_date", issues, required=True)
    elif not conclusion.get("unresolved_risks"):
        issues.append("未删除试用数据时必须记录 unresolved_risks")
    _required_string(conclusion.get("next_owner"), "conclusion.next_owner", issues)
    _iso_date(conclusion.get("next_date"), "conclusion.next_date", issues, required=True)


def validate_trial_record(path: Path) -> dict[str, Any]:
    record = _load_json(path.resolve())
    issues: list[str] = []
    _validate_no_secrets(record, "$", issues)
    if record.get("schema_version") != 1:
        issues.append("schema_version必须是 1")
    status = _required_string(record.get("status"), "status", issues)
    if status and status not in STATUSES:
        issues.append(f"status不受支持：{status}")
    trial_id = _required_string(record.get("trial_id"), "trial_id", issues)
    _required_string(record.get("participant_id"), "participant_id", issues)
    _required_string(record.get("delivery"), "delivery", issues)
    _required_string(record.get("environment_owner"), "environment_owner", issues)
    _required_string(record.get("source_register_version"), "source_register_version", issues)

    is_executed = status in {"running", "completed", "paused"}
    is_closed = status in {"completed", "paused"}
    _iso_datetime(record.get("started_at"), "started_at", issues, required=is_executed)
    _iso_datetime(record.get("ended_at"), "ended_at", issues, required=is_closed)
    _iso_date(record.get("data_cleanup_date"), "data_cleanup_date", issues, required=False)

    preflight = record.get("preflight")
    if not isinstance(preflight, dict):
        issues.append("preflight必须是对象")
        preflight = {}
    missing_preflight = sorted(REQUIRED_PREFLIGHT - set(preflight))
    if missing_preflight:
        issues.append("preflight缺少字段：" + ", ".join(missing_preflight))
    for field in REQUIRED_PREFLIGHT:
        if field in preflight and not isinstance(preflight[field], bool):
            issues.append(f"preflight.{field}必须是布尔值")
    if is_executed and any(preflight.get(field) is not True for field in REQUIRED_PREFLIGHT):
        issues.append("开始试用前必须全部确认前置条件")

    tasks = record.get("fixed_tasks")
    if not isinstance(tasks, list):
        issues.append("fixed_tasks必须是数组")
        tasks = []
    if is_executed and not tasks:
        issues.append("开始试用前至少需要一项固定任务")
    if status == "completed" and len(tasks) < 3:
        issues.append("completed 试用至少需要三项固定任务")
    for index, task in enumerate(tasks):
        _validate_task(task, index, issues, completed=status == "completed")

    defects = record.get("defects")
    if not isinstance(defects, list):
        issues.append("defects必须是数组")
        defects = []
    for index, defect in enumerate(defects):
        _validate_defect(defect, index, issues)
    if is_closed:
        _validate_conclusion(record, status, issues)

    result: dict[str, Any] = {
        "ok": not issues,
        "record_path": str(path.resolve()),
        "trial_id": trial_id,
        "status": status,
        "task_count": len(tasks),
        "defect_count": len(defects),
    }
    if issues:
        result.update({"error": "trial_record_invalid", "issues": issues})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="校验封闭试用记录的结构、前置条件和安全边界")
    parser.add_argument("--record", type=Path, required=True, help="机器可读试用记录 JSON")
    args = parser.parse_args()
    try:
        result = validate_trial_record(args.record)
    except TrialRecordError as exc:
        result = {"ok": False, "error": "trial_record_unreadable", "issues": exc.issues}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
