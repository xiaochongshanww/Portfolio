from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from scripts.validate_trial_record import TrialRecordError, validate_trial_record
except ModuleNotFoundError:  # Direct ``python scripts/render_trial_record.py`` entry.
    from validate_trial_record import (  # type: ignore[no-redef]
        TrialRecordError,
        validate_trial_record,
    )


def _load_record(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrialRecordError(f"试用记录无法读取或不是有效 UTF-8 JSON：{path}") from exc
    if not isinstance(value, dict):
        raise TrialRecordError("试用记录根节点必须是对象")
    return value


def _cell(value: Any, fallback: str = "-") -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, list):
        return "、".join(str(item) for item in value) or fallback
    text = str(value or "").strip()
    return text or fallback


def render_markdown(record: dict[str, Any], validation: dict[str, Any]) -> str:
    """Render the validated JSON record without creating a second source of truth."""
    status = _cell(record.get("status"))
    lines = [
        "# 封闭试用记录",
        "",
        f"- 记录状态：`{status}`",
        f"- 机器校验：`{'通过' if validation.get('ok') else '未通过'}`",
        f"- 试用编号：{_cell(record.get('trial_id'))}",
        f"- 参与者编号：{_cell(record.get('participant_id'))}",
        f"- 交付方式：{_cell(record.get('delivery'))}",
        f"- 环境责任人：{_cell(record.get('environment_owner'))}",
        f"- 来源登记版本：{_cell(record.get('source_register_version'))}",
        f"- 开始时间：{_cell(record.get('started_at'))}",
        f"- 结束时间：{_cell(record.get('ended_at'))}",
        f"- 数据清理日期：{_cell(record.get('data_cleanup_date'))}",
        "",
        "## 前置确认",
        "",
        "| 项目 | 状态 |",
        "| --- | --- |",
    ]
    preflight = record.get("preflight")
    if isinstance(preflight, dict):
        labels = {
            "participant_acknowledged": "参与者已知晓范围与停止方式",
            "source_scope_confirmed": "来源范围已确认",
            "no_unrelated_data": "未收集无关数据",
            "key_log_owner_defined": "密钥与日志责任人已明确",
            "disclaimer_shown": "已展示免责声明和原文复核要求",
        }
        for key, label in labels.items():
            lines.append(f"| {label} | {_cell(preflight.get(key))} |")
    else:
        lines.append("| 前置确认 | 未填写 |")

    lines.extend(
        [
            "",
            "## 固定任务",
            "",
            "| 编号 | 问题/任务 | 找到依据 | 依据引用 | 人工复核 | 缺陷编号 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    tasks = record.get("fixed_tasks")
    if isinstance(tasks, list) and tasks:
        for task in tasks:
            if not isinstance(task, dict):
                lines.append("| - | 记录格式错误 | - | - | - | - |")
                continue
            lines.append(
                "| "
                + " | ".join(
                    [
                        _cell(task.get("task_id")),
                        _cell(task.get("question")),
                        _cell(task.get("found_basis")),
                        _cell(task.get("references")),
                        _cell(task.get("human_review_required")),
                        _cell(task.get("defect_ids")),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| - | 尚未填写固定任务 | - | - | - | - |")

    lines.extend(
        [
            "",
            "## 缺陷与反馈",
            "",
            "| 编号 | 分类 | 严重度 | 复现步骤 | 处理结论 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    defects = record.get("defects")
    if isinstance(defects, list) and defects:
        for defect in defects:
            if not isinstance(defect, dict):
                lines.append("| - | 记录格式错误 | - | - | - |")
                continue
            lines.append(
                "| "
                + " | ".join(
                    [
                        _cell(defect.get("defect_id")),
                        _cell(defect.get("category")),
                        _cell(defect.get("severity")),
                        _cell(defect.get("reproduction")),
                        _cell(defect.get("resolution")),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| - | 尚未记录缺陷 | - | - | - |")

    conclusion = record.get("conclusion")
    lines.extend(["", "## 收口结论", ""])
    if isinstance(conclusion, dict):
        lines.extend(
            [
                f"- 决定：{_cell(conclusion.get('decision'))}",
                f"- 主要证据：{_cell(conclusion.get('evidence'))}",
                f"- 未解决风险：{_cell(conclusion.get('unresolved_risks'))}",
                f"- 是否删除试用数据：{_cell(conclusion.get('data_deleted'))}",
                f"- 下一步责任人：{_cell(conclusion.get('next_owner'))}",
                f"- 下一日期：{_cell(conclusion.get('next_date'))}",
            ]
        )
    else:
        lines.append("试用尚未收口；计划记录不构成真实试用完成证据。")

    lines.extend(
        [
            "",
            "> 本页面由机器可读 JSON 记录生成。它不替代参与者反馈、原始页面复核、权利判断或产品决策。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="将已通过结构校验的封闭试用 JSON 渲染为 Markdown")
    parser.add_argument("--record", type=Path, required=True, help="机器可读试用记录 JSON")
    parser.add_argument("--output", type=Path, required=True, help="Markdown 输出文件")
    args = parser.parse_args()
    try:
        record = _load_record(args.record)
        validation = validate_trial_record(args.record)
        if not validation.get("ok"):
            issues = "；".join(str(item) for item in validation.get("issues", []))
            raise TrialRecordError(f"试用记录未通过校验：{issues}")
        if args.output.exists():
            raise TrialRecordError(f"输出文件已存在：{args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_markdown(record, validation), encoding="utf-8")
    except (OSError, TrialRecordError) as exc:
        print(f"trial_record_render_error: {exc}")
        return 1
    print(json.dumps({"ok": True, "output": str(args.output.resolve())}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
