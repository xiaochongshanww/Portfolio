from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = PROJECT_ROOT / "data" / "audit" / "reports" / "readiness_external_latest.json"


class ReadinessGapReportError(ValueError):
    """Raised when the upstream readiness audit is missing or malformed."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.resolve().read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReadinessGapReportError(f"就绪审计报告不存在：{path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadinessGapReportError(f"就绪审计报告无法读取或不是有效 UTF-8 JSON：{path}") from exc
    if not isinstance(value, dict):
        raise ReadinessGapReportError("就绪审计报告根节点必须是对象")
    return value


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReadinessGapReportError(f"就绪审计报告的 {label} 必须是非空字符串")
    return value.strip()


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ReadinessGapReportError(f"就绪审计报告的 {label} 必须是非空字符串数组")
    return [item.strip() for item in value]


def _normalise_item(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ReadinessGapReportError(f"closure.items[{index}] 必须是对象")
    item_id = _required_text(item.get("check_id"), f"closure.items[{index}].check_id")
    name = _required_text(item.get("name"), f"closure.items[{index}].name")
    status = _required_text(item.get("status"), f"closure.items[{index}].status")
    detail = _required_text(item.get("detail"), f"closure.items[{index}].detail")
    if not isinstance(item.get("blocking"), bool):
        raise ReadinessGapReportError(f"closure.items[{index}].blocking 必须是布尔值")
    owner = _required_text(item.get("owner"), f"closure.items[{index}].owner")
    actions = _string_list(item.get("actions"), f"closure.items[{index}].actions")
    verification = _string_list(item.get("verification"), f"closure.items[{index}].verification")
    return {
        "check_id": item_id,
        "name": name,
        "status": status,
        "detail": detail,
        "blocking": item["blocking"],
        "owner": owner,
        "actions": actions,
        "verification": verification,
    }


def load_gap_report_data(path: Path = DEFAULT_AUDIT) -> dict[str, Any]:
    """Validate and reduce an external readiness audit to a safe operator view."""
    audit = _load_json(path)
    if audit.get("profile") != "external":
        raise ReadinessGapReportError("差距报告只接受 profile=external 的就绪审计")
    if not isinstance(audit.get("ready"), bool):
        raise ReadinessGapReportError("就绪审计报告的 ready 必须是布尔值")
    checked_at = _required_text(audit.get("checked_at"), "checked_at")
    closure = audit.get("closure")
    if not isinstance(closure, dict):
        raise ReadinessGapReportError("就绪审计报告缺少 closure 对象")
    items = closure.get("items")
    if not isinstance(items, list):
        raise ReadinessGapReportError("就绪审计报告的 closure.items 必须是数组")
    normalised_items = [_normalise_item(item, index) for index, item in enumerate(items)]
    if not isinstance(closure.get("blocking_count"), int):
        raise ReadinessGapReportError("就绪审计报告的 closure.blocking_count 必须是整数")
    if not isinstance(closure.get("warning_count"), int):
        raise ReadinessGapReportError("就绪审计报告的 closure.warning_count 必须是整数")
    if closure.get("ready") is not audit["ready"]:
        raise ReadinessGapReportError("就绪审计报告的 closure.ready 与顶层 ready 不一致")
    if audit["ready"] and normalised_items:
        raise ReadinessGapReportError("ready=true 的外部审计不应包含未收口项")
    if not audit["ready"] and not normalised_items:
        raise ReadinessGapReportError("ready=false 的外部审计必须列出未收口项")
    return {
        "profile": "external",
        "checked_at": checked_at,
        "ready": audit["ready"],
        "blocking_count": closure["blocking_count"],
        "warning_count": closure["warning_count"],
        "items": normalised_items,
        "audit_path": str(path.resolve()),
    }


def render_markdown(data: dict[str, Any]) -> str:
    ready = data["ready"] is True
    items = data["items"]
    lines = [
        "# 外部资格差距收口报告",
        "",
        f"- 审计 profile：`{data['profile']}`",
        f"- 审计时间：`{data['checked_at']}`",
        f"- 当前结论：`{'已收口' if ready else '未收口'}`",
        f"- 阻断项：`{data['blocking_count']}`",
        f"- 非阻断提醒：`{data['warning_count']}`",
        f"- 上游审计：`{data['audit_path']}`",
        "",
        "> 本报告只整理就绪审计的状态、责任角色、整改动作和验证条件，不包含规范原文、页面截图、授权原件、用户数据或密钥。它不能通过修改文字解除发布阻断。",
        "",
        "## 当前结论",
        "",
    ]
    if ready:
        lines.append("外部资格审计已收口；仍须按发布检查单执行最终发布确认。")
    else:
        lines.append("外部资格审计尚未收口，必须完成下列真实证据或决策后重新运行审计。")
    if items:
        lines.extend(
            [
                "",
                "## 未收口项",
                "",
                "| 检查项 | 是否阻断 | 状态 | 当前说明 |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in items:
            lines.append(
                f"| `{item['check_id']}` {item['name']} | "
                f"{'是' if item['blocking'] else '否'} | `{item['status']}` | {item['detail']} |"
            )
        for item in items:
            lines.extend(
                [
                    "",
                    f"### `{item['check_id']}` {item['name']}",
                    "",
                    f"- 责任角色：{item['owner']}",
                    f"- 当前说明：{item['detail']}",
                    "- 整改动作：",
                ]
            )
            lines.extend(f"  - {action}" for action in item["actions"])
            lines.append("- 验证条件：")
            lines.extend(f"  - {check} " for check in item["verification"])
    lines.extend(
        [
            "",
            "## 操作顺序",
            "",
            "1. 先处理 `source_release`，完成来源取得、权利复核和原始文件存储处置；不得通过改写审计结果代替证据。",
            "2. 再按封闭试用方案执行真实试用，完成 JSON 记录并通过试用记录校验；计划记录不能作为完成证据。",
            "3. 如需启用精排，最后在受控凭据下完成 100 条对照和回答级盲测；在此之前保持 `RERANK_ENABLED=false`。",
            "4. 重新运行 `python scripts/audit_release_readiness.py --profile external`，以新生成的 JSON 作为唯一结论来源。",
            "",
            "## 证据边界",
            "",
            "来源登记台账、受控发布证据包、封闭试用记录和精排报告分别是各自事实源；本报告只是交接视图，不替代它们。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="生成外部资格差距收口报告")
    parser.add_argument("--audit-json", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="要求上游 external 审计已收口，否则以失败退出",
    )
    args = parser.parse_args()
    try:
        data = load_gap_report_data(args.audit_json)
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(data), encoding="utf-8")
    except (OSError, ReadinessGapReportError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1
    if args.require_ready and not data["ready"]:
        print(
            json.dumps(
                {"ok": False, "error": "external_readiness_not_ready", "output": str(output)},
                ensure_ascii=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "ready": data["ready"],
                "open_count": len(data["items"]),
                "output": str(output),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
