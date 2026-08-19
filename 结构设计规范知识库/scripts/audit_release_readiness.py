from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from scripts.validate_runtime_manifest import RuntimeManifestError, validate_runtime_manifest
    from scripts.validate_source_register import SourceRegisterError, validate_source_register
    from scripts.validate_trial_record import TrialRecordError, validate_trial_record
except ModuleNotFoundError:  # Direct ``python scripts/audit_release_readiness.py`` entry.
    from validate_runtime_manifest import RuntimeManifestError, validate_runtime_manifest
    from validate_source_register import SourceRegisterError, validate_source_register
    from validate_trial_record import TrialRecordError, validate_trial_record

DEFAULT_SNAPSHOT = PROJECT_ROOT / "docs" / "quality" / "质量证据状态.json"
DEFAULT_ROADMAP = PROJECT_ROOT / "docs" / "architecture" / "持续迭代路线图.md"
DEFAULT_DECISIONS = PROJECT_ROOT / "docs" / "architecture" / "技术与产品待决策事项.md"
DEFAULT_RERANK_COMPARISON_REPORT = (
    PROJECT_ROOT / "data" / "audit" / "reports" / "rerank_comparison_latest.json"
)
DEFAULT_RERANK_ANSWER_REPORT = (
    PROJECT_ROOT / "data" / "audit" / "reports" / "rerank_answer_latest.json"
)
AUDIT_PROFILES = {"external", "internal-research"}


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
    items: list[str] | None = None,
) -> dict[str, Any]:
    result = {
        "id": check_id,
        "name": name,
        "ok": ok,
        "blocking": blocking,
        "status": status,
        "detail": detail,
    }
    if items is not None:
        result["items"] = list(items)
    return result


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


def _quality_check(
    snapshot_path: Path,
    *,
    runtime_data_version_hash: str | None = None,
) -> dict[str, Any]:
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
    report_payloads: list[tuple[str, dict[str, Any]]] = []
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
            continue
        try:
            report_payload = _load_json(report_path, f"质量报告 {name}")
        except ReadinessAuditError as exc:
            missing.append(str(exc))
            continue
        report_payloads.append((name, report_payload))

    if runtime_data_version_hash:
        for name, report_payload in report_payloads:
            report_version = str(report_payload.get("data_version_hash") or "")
            if report_version != runtime_data_version_hash:
                missing.append(
                    f"{name}: data_version_hash={report_version or 'missing'}，"
                    f"当前运行版本={runtime_data_version_hash}"
                )

    verification_run_ids = {
        str(payload.get("verification_run_id") or "")
        for _, payload in report_payloads
        if payload.get("verification_run_id")
    }
    if len(verification_run_ids) > 1:
        missing.append("质量报告来自多个 verification_run_id")
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


def _source_check(profile: str) -> dict[str, Any]:
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
            items=exc.issues,
        )
    if profile == "internal-research":
        blockers = result.get("internal_research_blockers") or []
        if result.get("internal_research_eligible") is not True:
            return _check(
                "source_internal_research",
                "来源内部研究资格",
                ok=False,
                blocking=True,
                status="blocked",
                detail=f"{len(blockers)} 项内部研究来源阻断",
                items=blockers,
            )
        return _check(
            "source_internal_research",
            "来源内部研究资格",
            ok=True,
            blocking=True,
            status="eligible",
            detail="所有活动来源均登记为允许内部研究或封闭验证",
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
            items=blockers,
        )
    return _check(
        "source_release",
        "来源发布资格",
        ok=True,
        blocking=True,
        status="eligible",
        detail="所有来源通过对外资格校验",
    )


def _trial_check(trial_record: Path | None, profile: str) -> dict[str, Any]:
    if profile == "internal-research":
        return _check(
            "closed_trial",
            "封闭试用证据",
            ok=True,
            blocking=False,
            status="not_required",
            detail="内部研究模式不代表真实用户试用，不要求试用记录",
        )
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


def _runtime_manifest_check() -> dict[str, Any]:
    try:
        result = validate_runtime_manifest()
    except RuntimeManifestError as exc:
        return _check(
            "runtime_manifest",
            "运行 manifest 一致性",
            ok=False,
            blocking=True,
            status="invalid",
            detail=f"运行 manifest 无法校验（{len(exc.issues)} 项）",
        )
    if not result.get("ok"):
        issues = result.get("issues") or []
        return _check(
            "runtime_manifest",
            "运行 manifest 一致性",
            ok=False,
            blocking=True,
            status="inconsistent",
            detail="；".join(str(issue) for issue in issues),
        )
    check = _check(
        "runtime_manifest",
        "运行 manifest 一致性",
        ok=True,
        blocking=True,
        status="consistent",
        detail="活动指针、文档数量和 chunk 数量一致",
    )
    check["data_version_hash"] = result.get("data_version_hash")
    return check


def _rerank_check(
    roadmap_status: str,
    *,
    comparison_path: Path,
    answer_path: Path,
    runtime_data_version_hash: str | None,
) -> dict[str, Any]:
    if roadmap_status != "已完成":
        return _check(
            "rerank_quality",
            "精排质量证据",
            ok=False,
            blocking=False,
            status=roadmap_status or "missing",
            detail="真实供应商对照和回答盲测未完成；精排默认关闭，不阻断基线发布",
        )

    issues: list[str] = []
    reports: dict[str, dict[str, Any]] = {}
    for label, path in (
        ("精排对照", comparison_path.resolve()),
        ("回答盲测", answer_path.resolve()),
    ):
        if not path.is_file():
            issues.append(f"{label}报告不存在")
            continue
        try:
            reports[label] = _load_json(path, label)
        except ReadinessAuditError:
            issues.append(f"{label}报告不是有效 JSON")

    comparison = reports.get("精排对照", {})
    if comparison:
        if comparison.get("ok") is not True:
            issues.append("精排对照报告未通过")
        if comparison.get("comparison_complete") is not True:
            issues.append("精排对照报告不完整")
        case_count = comparison.get("case_count")
        if isinstance(case_count, bool) or not isinstance(case_count, int) or case_count < 100:
            issues.append("精排对照用例数少于 100")
        fallback_count = comparison.get("fallback_case_count")
        if fallback_count != 0:
            issues.append("精排对照存在降级用例")
        if str(comparison.get("provider") or "") in {"", "none"}:
            issues.append("精排对照没有有效供应商")
        if (
            runtime_data_version_hash
            and comparison.get("data_version_hash") != runtime_data_version_hash
        ):
            issues.append("精排对照未绑定当前运行数据版本")

    answer = reports.get("回答盲测", {})
    if answer:
        if answer.get("ok") is not True:
            issues.append("回答盲测报告未通过")
        if answer.get("rerank_enabled") is not True:
            issues.append("回答盲测未声明启用精排")
        case_count = answer.get("case_count")
        if isinstance(case_count, bool) or not isinstance(case_count, int) or case_count < 24:
            issues.append("回答盲测用例数少于当前 24 条盲测集")
        pass_rate = answer.get("pass_rate")
        if (
            not isinstance(pass_rate, (int, float))
            or isinstance(pass_rate, bool)
            or pass_rate < 0.9
        ):
            issues.append("回答盲测通过率低于 90%")
        if (
            runtime_data_version_hash
            and answer.get("data_version_hash") != runtime_data_version_hash
        ):
            issues.append("回答盲测未绑定当前运行数据版本")

    if issues:
        return _check(
            "rerank_quality",
            "精排质量证据",
            ok=False,
            blocking=False,
            status="invalid",
            detail="；".join(issues),
        )
    return _check(
        "rerank_quality",
        "精排质量证据",
        ok=True,
        blocking=False,
        status="verified",
        detail="真实 100 条精排对照和启用精排的回答盲测均通过证据校验",
    )


def _remediation_for_check(check: dict[str, Any]) -> dict[str, Any] | None:
    """Return role-based next steps without changing the readiness decision."""
    if check.get("ok"):
        return None
    check_id = check.get("id")
    if check_id == "quality_evidence":
        return {
            "owner": "质量运营负责人",
            "actions": [
                "按当前活动数据版本重新生成完整质量证据，不能用旧报告或跨运行报告拼接通过结论。",
                "先修复报告哈希、运行身份或数据版本不一致，再重新执行发布审计。",
            ],
            "verification": [
                "质量快照的 release_quality_status 为 passed",
                "三类报告与当前活动 manifest 的 data_version_hash 一致",
            ],
        }
    if check_id == "source_release":
        return {
            "owner": "来源治理负责人",
            "actions": [
                "按 items 逐条补齐来源取得日期、凭证索引、权利复核和原始文件仓库存储处置。",
                "只有逐来源证据真实完成后，才更新来源登记台账；不要直接修改审计结果或路线图状态。",
            ],
            "verification": [
                "python scripts/validate_source_register.py --require-release-eligible",
                "默认 external profile 的 source_release 检查通过",
            ],
        }
    if check_id == "source_internal_research":
        return {
            "owner": "来源治理负责人",
            "actions": [
                "核对活动来源的 allowed_uses、来源范围和派生资产限制，确保内部研究声明与实际用途一致。",
                "禁止把 C 级、test_fixture 或未声明内部用途的来源通过临时字段改成可用。",
            ],
            "verification": [
                "python scripts/validate_source_register.py",
                "python scripts/audit_release_readiness.py --profile internal-research",
            ],
        }
    if check_id == "runtime_manifest":
        return {
            "owner": "知识库运维负责人",
            "actions": [
                "先定位活动指针、manifest、文档数量或 chunk 数量的差异，禁止手工修改活动指针伪造一致性。",
                "在维护窗口修复或重新发布完整运行知识包，再执行同一组运行校验。",
            ],
            "verification": [
                "python scripts/validate_runtime_manifest.py",
                "重新运行发布就绪审计并确认 runtime_manifest 为 consistent",
            ],
        }
    if check_id == "closed_trial":
        return {
            "owner": "试用负责人",
            "actions": [
                "按封闭试用方案执行受控真实试用，记录参与者范围、任务、错误、成本、隐私处理和停止/继续结论。",
                "试用记录完成前，不得把计划记录或模板文件当作真实试用证据。",
            ],
            "verification": [
                "python scripts/validate_trial_record.py <completed-trial-record.json>",
                "审计中的 closed_trial 状态为 completed 且结论为 continue",
            ],
        }
    if check_id == "delivery_decision":
        return {
            "owner": "产品与工程负责人",
            "actions": [
                "复核 D-001 内容分发授权边界和 D-002 交付形态，形成明确的产品与治理决策。",
                "在决策生效前继续保持宿主机运行、内部研究和封闭验证边界，不承诺安装器、公共 Web 服务或对外知识包。",
            ],
            "verification": [
                "更新 docs/architecture/技术与产品待决策事项.md 并形成对应 ADR 或发布记录",
                "路线图中的 I-010 状态与实际决策证据一致",
            ],
        }
    if check_id == "rerank_quality":
        return {
            "owner": "检索质量负责人",
            "actions": [
                "在真实证据形成前保持 RERANK_ENABLED=false，不把 HTTP 429、降级或模拟结果当作质量结论。",
                "具备受控供应商额度后，使用完整精排质量入口生成当前数据版本的 100 条对照和启用精排回答盲测。",
            ],
            "verification": [
                "python scripts/run_rerank_quality_evidence.py --help",
                "两份精排证据报告完整、无降级且通过发布审计校验",
            ],
        }
    return None


def audit_release_readiness(
    *,
    profile: str = "external",
    snapshot_path: Path = DEFAULT_SNAPSHOT,
    roadmap_path: Path = DEFAULT_ROADMAP,
    decisions_path: Path = DEFAULT_DECISIONS,
    trial_record: Path | None = None,
    rerank_comparison_report: Path = DEFAULT_RERANK_COMPARISON_REPORT,
    rerank_answer_report: Path = DEFAULT_RERANK_ANSWER_REPORT,
) -> dict[str, Any]:
    if profile not in AUDIT_PROFILES:
        raise ReadinessAuditError(f"不支持的审计 profile：{profile}")
    rows = _roadmap_rows(roadmap_path.resolve())
    decisions = _decision_rows(decisions_path.resolve())
    runtime_check = _runtime_manifest_check()
    runtime_data_version_hash = (
        str(runtime_check.get("data_version_hash") or "") if runtime_check.get("ok") else None
    )
    checks = [
        _quality_check(
            snapshot_path.resolve(),
            runtime_data_version_hash=runtime_data_version_hash,
        ),
        _source_check(profile),
        runtime_check,
        _trial_check(trial_record, profile),
    ]

    delivery_row = rows.get("I-010", {})
    d001 = decisions.get("D-001", {})
    d002 = decisions.get("D-002", {})
    delivery_ok = profile == "internal-research" or delivery_row.get("status") == "已完成"
    checks.append(
        _check(
            "delivery_decision",
            "交付形态与授权边界",
            ok=delivery_ok,
            blocking=profile != "internal-research",
            status=(
                "internal_only"
                if profile == "internal-research"
                else delivery_row.get("status", "missing")
            ),
            detail=(
                "仅允许项目成员范围内的内部研究，不代表对外交付承诺"
                if profile == "internal-research"
                else "I-010 已完成"
                if delivery_ok
                else "I-010 仍受 D-001/D-002 约束，不能作出对外交付承诺"
            ),
        )
    )

    rerank_row = rows.get("I-034", {})
    checks.append(
        _rerank_check(
            rerank_row.get("status", "missing"),
            comparison_path=rerank_comparison_report,
            answer_path=rerank_answer_report,
            runtime_data_version_hash=runtime_data_version_hash,
        )
    )

    for check in checks:
        remediation = _remediation_for_check(check)
        if remediation is not None:
            check["remediation"] = remediation

    blockers = [item["detail"] for item in checks if not item["ok"] and item["blocking"]]
    warnings = [item["detail"] for item in checks if not item["ok"] and not item["blocking"]]
    ready = not blockers
    return {
        "ok": True,
        "profile": profile,
        "ready": ready,
        "external_release_ready": profile == "external" and ready,
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
    internal_profile = result.get("profile") == "internal-research"
    title = "内部研究就绪审计" if internal_profile else "发布就绪审计"
    ready_label = "内部研究可用" if internal_profile else "可发布"
    blocked_label = "内部研究阻断" if internal_profile else "阻断"
    lines = [
        f"# {title}",
        "",
        f"- 总体结果：{ready_label if result.get('ready') else blocked_label}",
        f"- 审计范围：`{result.get('profile', 'external')}`",
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
    source_checks = [
        item
        for item in result.get("checks", [])
        if item.get("id") in {"source_release", "source_internal_research"} and item.get("items")
    ]
    if source_checks:
        lines.extend(["", "## 来源资格明细", ""])
        for item in source_checks:
            lines.extend(f"- {issue}" for issue in item["items"])
    remediation_checks = [item for item in result.get("checks", []) if item.get("remediation")]
    if remediation_checks:
        lines.extend(["", "## 整改行动", ""])
        for item in remediation_checks:
            remediation = item["remediation"]
            lines.extend(
                [
                    f"### {item.get('name', '')} (`{item.get('id', '')}`)",
                    f"- 责任角色：{remediation.get('owner', '')}",
                ]
            )
            lines.extend(f"- {action}" for action in remediation.get("actions", []))
            lines.append("- 验证：" + "；".join(remediation.get("verification", [])))
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
    parser = argparse.ArgumentParser(
        description="审计当前项目是否具备对外发布条件；也支持内部研究 profile"
    )
    parser.add_argument(
        "--profile",
        choices=sorted(AUDIT_PROFILES),
        default="external",
        help="审计范围：external 对外发布；internal-research 仅内部研究",
    )
    parser.add_argument("--trial-record", type=Path, help="已完成的封闭试用记录 JSON")
    parser.add_argument(
        "--rerank-comparison-report",
        type=Path,
        default=DEFAULT_RERANK_COMPARISON_REPORT,
        help="真实精排对照报告 JSON",
    )
    parser.add_argument(
        "--rerank-answer-report",
        type=Path,
        default=DEFAULT_RERANK_ANSWER_REPORT,
        help="启用精排的回答盲测报告 JSON",
    )
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    try:
        result = audit_release_readiness(
            profile=args.profile,
            trial_record=args.trial_record,
            rerank_comparison_report=args.rerank_comparison_report,
            rerank_answer_report=args.rerank_answer_report,
        )
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
