from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.validate_source_register import SourceRegisterError, validate_source_register
    from scripts.validate_trial_record import TrialRecordError, validate_trial_record
except ModuleNotFoundError:  # Direct ``python scripts/audit_release_readiness.py`` entry.
    from validate_source_register import SourceRegisterError, validate_source_register
    from validate_trial_record import TrialRecordError, validate_trial_record

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = PROJECT_ROOT / "docs" / "quality" / "质量证据状态.json"
DEFAULT_ROADMAP = PROJECT_ROOT / "docs" / "architecture" / "持续迭代路线图.md"
DEFAULT_DECISIONS = PROJECT_ROOT / "docs" / "architecture" / "技术与产品待决策事项.md"


class ReadinessAuditError(ValueError):
    def __init__(self, issues: list[str] | str):
        self.issues = [issues] if isinstance(issues, str) else list(issues)
        super().__init__("；".join(self.issues))


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReadinessAuditError(f"{label}不存在：{path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadinessAuditError(f"{label}无法读取或不是有效 UTF-8 JSON：{path}") from exc
    if not isinstance(value, dict):
        raise ReadinessAuditError(f"{label}根节点必须是对象：{path}")
    return value


def _check(
    check_id: str,
    name: str,
    *,
    ok: bool,
    blocking: bool,
    status: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "name": name,
        "ok": ok,
        "blocking": blocking,
        "status": status,
        "detail": detail,
    }


def _roadmap_rows(path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ReadinessAuditError(f"持续迭代路线图无法读取：{path}") from exc
    for line in lines:
        if not line.startswith("| I-"):
            continue
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 6:
            continue
        iteration = cells[1]
        if iteration.startswith("I-"):
            rows[iteration] = {
                "title": cells[3],
                "status": cells[4],
                "evidence": cells[5],
            }
    return rows


def _decision_rows(path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ReadinessAuditError(f"技术与产品待决策事项无法读取：{path}") from exc
    for line in lines:
        if not line.startswith("| D-"):
            continue
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 5:
            continue
        decision = cells[1]
        if decision.startswith("D-"):
            rows[decision] = {"name": cells[2], "default": cells[3], "trigger": cells[4]}
    return rows


def _quality_check(snapshot_path: Path) -> dict[str, Any]:
    snapshot = _load_json(snapshot_path, "质量证据状态")
    if snapshot.get("release_quality_status") != "passed":
        return _check(
            "quality_evidence",
            "质量证据",
            ok=False,
            blocking=True,
            status=str(snapshot.get("release_quality_status") or "missing"),
            detail="当前质量快照不是 passed",
        )
    reports = snapshot.get("reports")
    if not isinstance(reports, dict) or not reports:
        return _check(
            "quality_evidence",
            "质量证据",
            ok=False,
            blocking=True,
            status="invalid",
            detail="质量快照缺少 reports",
        )
    missing: list[str] = []
    for name, report in reports.items():
        if not isinstance(report, dict):
            missing.append(f"{name}: 记录不是对象")
            continue
        relative_path = str(report.get("path") or "")
        expected_hash = str(report.get("sha256") or "")
        report_path = (PROJECT_ROOT / relative_path).resolve()
        try:
            inside_project = report_path.is_relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            inside_project = False
        if not inside_project or not report_path.is_file():
            missing.append(f"{name}: 报告不存在")
            continue
        actual_hash = hashlib.sha256(report_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            missing.append(f"{name}: SHA-256 不匹配")
    if missing:
        return _check(
            "quality_evidence",
            "质量证据",
            ok=False,
            blocking=True,
            status="invalid",
            detail="；".join(missing),
        )
    return _check(
        "quality_evidence",
        "质量证据",
        ok=True,
        blocking=True,
        status="passed",
        detail="质量快照通过且引用报告哈希一致",
    )


def _source_check() -> dict[str, Any]:
    try:
        result = validate_source_register()
    except SourceRegisterError as exc:
        return _check(
            "source_release",
            "来源发布资格",
            ok=False,
            blocking=True,
            status="invalid",
            detail=f"来源台账结构无效（{len(exc.issues)} 项）",
        )
    blockers = result.get("release_blockers") or []
    if result.get("release_eligible") is not True:
        return _check(
            "source_release",
            "来源发布资格",
            ok=False,
            blocking=True,
            status="blocked",
            detail=f"{len(blockers)} 项来源资格阻断",
        )
    return _check(
        "source_release",
        "来源发布资格",
        ok=True,
        blocking=True,
        status="eligible",
        detail="所有来源通过对外资格校验",
    )


def _trial_check(trial_record: Path | None) -> dict[str, Any]:
    if trial_record is None:
        return _check(
            "closed_trial",
            "封闭试用证据",
            ok=False,
            blocking=True,
            status="not_provided",
            detail="未提供已完成的试用记录",
        )
    try:
        result = validate_trial_record(trial_record)
    except TrialRecordError as exc:
        return _check(
            "closed_trial",
            "封闭试用证据",
            ok=False,
            blocking=True,
            status="invalid",
            detail=f"试用记录无法读取（{len(exc.issues)} 项）",
        )
    if not result.get("ok") or result.get("status") != "completed":
        return _check(
            "closed_trial",
            "封闭试用证据",
            ok=False,
            blocking=True,
            status=str(result.get("status") or "invalid"),
            detail="试用记录未完成结构校验或状态不是 completed",
        )
    record = _load_json(trial_record.resolve(), "试用记录")
    conclusion = record.get("conclusion")
    decision = conclusion.get("decision") if isinstance(conclusion, dict) else ""
    if decision != "continue":
        return _check(
            "closed_trial",
            "封闭试用证据",
            ok=False,
            blocking=True,
            status="not_ready",
            detail=f"试用结论为 {decision or '未填写'}，不是 continue",
        )
    return _check(
        "closed_trial",
        "封闭试用证据",
        ok=True,
        blocking=True,
        status="completed",
        detail="试用记录完成且结论为 continue",
    )


def audit_release_readiness(
    *,
    snapshot_path: Path = DEFAULT_SNAPSHOT,
    roadmap_path: Path = DEFAULT_ROADMAP,
    decisions_path: Path = DEFAULT_DECISIONS,
    trial_record: Path | None = None,
) -> dict[str, Any]:
    rows = _roadmap_rows(roadmap_path.resolve())
    decisions = _decision_rows(decisions_path.resolve())
    checks = [
        _quality_check(snapshot_path.resolve()),
        _source_check(),
        _trial_check(trial_record),
    ]

    delivery_row = rows.get("I-010", {})
    d001 = decisions.get("D-001", {})
    d002 = decisions.get("D-002", {})
    delivery_ok = delivery_row.get("status") == "已完成"
    checks.append(
        _check(
            "delivery_decision",
            "交付形态与授权边界",
            ok=delivery_ok,
            blocking=True,
            status=delivery_row.get("status", "missing"),
            detail=(
                "I-010 已完成"
                if delivery_ok
                else "I-010 仍受 D-001/D-002 约束，不能作出对外交付承诺"
            ),
        )
    )

    rerank_row = rows.get("I-034", {})
    rerank_verified = rerank_row.get("status") == "已完成"
    checks.append(
        _check(
            "rerank_quality",
            "精排质量证据",
            ok=rerank_verified,
            blocking=False,
            status=rerank_row.get("status", "missing"),
            detail=(
                "真实精排质量已证"
                if rerank_verified
                else "真实供应商对照和回答盲测未完成；精排默认关闭，不阻断基线发布"
            ),
        )
    )

    blockers = [item["detail"] for item in checks if not item["ok"] and item["blocking"]]
    warnings = [item["detail"] for item in checks if not item["ok"] and not item["blocking"]]
    return {
        "ok": True,
        "ready": not blockers,
        "checked_at": datetime.now(UTC).isoformat(),
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "context": {
            "delivery_iteration_status": delivery_row.get("status", "missing"),
            "source_decision_default": d001.get("default", "missing"),
            "delivery_decision_default": d002.get("default", "missing"),
        },
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 发布就绪审计",
        "",
        f"- 总体结果：{'可发布' if result.get('ready') else '阻断'}",
        f"- 检查时间：`{result.get('checked_at', '-')}`",
        "",
        "## 检查项",
        "",
        "| 检查项 | 结果 | 是否阻断 | 状态 | 说明 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in result.get("checks", []):
        lines.append(
            f"| {item.get('name', '')} | "
            f"{'通过' if item.get('ok') else '未通过'} | "
            f"{'是' if item.get('blocking') else '否'} | "
            f"`{item.get('status', '')}` | {item.get('detail', '')} |"
        )
    lines.extend(["", "## 阻断原因", ""])
    blockers = result.get("blockers") or ["无"]
    lines.extend(f"- {item}" for item in blockers)
    warnings = result.get("warnings") or []
    if warnings:
        lines.extend(["", "## 非阻断提醒", ""])
        lines.extend(f"- {item}" for item in warnings)
    return "\n".join(lines) + "\n"


def _configure_cli_streams() -> None:
    """Keep governance CLI diagnostics readable on Windows code pages."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def main() -> int:
    _configure_cli_streams()
    parser = argparse.ArgumentParser(description="审计当前项目是否具备对外发布条件")
    parser.add_argument("--trial-record", type=Path, help="已完成的封闭试用记录 JSON")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    try:
        result = audit_release_readiness(trial_record=args.trial_record)
    except ReadinessAuditError as exc:
        result = {
            "ok": False,
            "ready": False,
            "error": "readiness_audit_invalid",
            "issues": exc.issues,
        }
    serialized = json.dumps(result, ensure_ascii=True, indent=2)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(serialized + "\n", encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown(result), encoding="utf-8")
    print(serialized)
    return 0 if result.get("ok") and result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
