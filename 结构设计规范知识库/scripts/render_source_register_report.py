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
    from scripts.validate_source_register import (
        DEFAULT_ACTIVE_DB_PATH,
        DEFAULT_METADATA_PATH,
        DEFAULT_REGISTER_PATH,
        DEFAULT_SOURCE_ROOT,
        SourceRegisterError,
        validate_source_register,
    )
except ModuleNotFoundError:  # Direct ``python scripts/render_source_register_report.py`` entry.
    from validate_source_register import (  # type: ignore[no-redef]
        DEFAULT_ACTIVE_DB_PATH,
        DEFAULT_METADATA_PATH,
        DEFAULT_REGISTER_PATH,
        DEFAULT_SOURCE_ROOT,
        SourceRegisterError,
        validate_source_register,
    )


def _load_records(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceRegisterError(f"来源登记台账无法读取或不是有效 UTF-8 JSON：{path}") from exc
    records = payload.get("documents") if isinstance(payload, dict) else None
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise SourceRegisterError("来源登记台账 documents 必须是对象数组")
    return records


def _text(value: Any, fallback: str = "-") -> str:
    if isinstance(value, list):
        value = "、".join(str(item) for item in value)
    text = str(value or "").strip()
    return (text or fallback).replace("|", "\\|").replace("\r\n", "<br>").replace("\n", "<br>")


def _permission_summary(permissions: Any) -> str:
    if not isinstance(permissions, dict):
        return "未填写"
    enabled = [str(key) for key, value in permissions.items() if value is True]
    return "、".join(enabled) if enabled else "全部关闭"


def _source_blockers(source_file: str, blockers: list[str]) -> list[str]:
    prefix = f"{source_file}:"
    return [item for item in blockers if item.startswith(prefix)]


def render_markdown(result: dict[str, Any], records: list[dict[str, Any]]) -> str:
    """Render a human handoff view without including source document contents."""
    release_ready = bool(result.get("release_eligible"))
    internal_ready = bool(result.get("internal_research_eligible"))
    lines = [
        "# 来源资格阅读报告",
        "",
        f"- 机器校验：`{'通过' if result.get('ok') else '未通过'}`",
        f"- 对外发布资格：`{'通过' if release_ready else '阻断'}`",
        f"- 内部研究资格：`{'通过' if internal_ready else '阻断'}`",
        f"- 登记来源数：{_text(result.get('source_count'))}",
        f"- 生产来源数：{_text(result.get('production_source_count'))}",
        f"- 测试来源：{_text(result.get('test_only_sources'))}",
        "",
        "> 本报告只展示来源登记字段和待补证状态，不包含规范原文、页面截图、授权原件、联系人信息或密钥；它不是授权证明，也不改变发布门禁结论。",
        "",
        "## 来源总览",
        "",
        "| 来源 | 范围 | 权利等级 | 内部用途 | 复核状态 | 仓库存储 | 当前权限 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    blockers = [str(item) for item in result.get("release_blockers", [])]
    for record in records:
        rights = record.get("rights") if isinstance(record.get("rights"), dict) else {}
        review = record.get("review") if isinstance(record.get("review"), dict) else {}
        lines.append(
            "| "
            + " | ".join(
                [
                    _text(record.get("source_file")),
                    _text(record.get("release_scope")),
                    _text(rights.get("status")),
                    _text(rights.get("allowed_uses")),
                    _text(review.get("status")),
                    _text(record.get("repository_storage")),
                    _permission_summary(record.get("permissions")),
                ]
            )
            + " |"
        )

    lines.extend(["", "## 逐来源补证", ""])
    for record in records:
        source_file = str(record.get("source_file") or "")
        if not source_file:
            continue
        rights = record.get("rights") if isinstance(record.get("rights"), dict) else {}
        acquisition = (
            record.get("acquisition") if isinstance(record.get("acquisition"), dict) else {}
        )
        review = record.get("review") if isinstance(record.get("review"), dict) else {}
        source_issues = _source_blockers(source_file, blockers)
        lines.extend(
            [
                f"### {_text(record.get('standard_code'))} · {_text(record.get('title'))}",
                "",
                f"- 来源文件：`{_text(source_file)}`",
                f"- 来源范围：`{_text(record.get('release_scope'))}`",
                f"- 原始文件 SHA-256：`{_text(record.get('original_sha256'))}`",
                f"- 取得日期：{_text(acquisition.get('date'))}",
                f"- 凭证索引：{_text(acquisition.get('reference_index'))}",
                f"- 权利复核：`{_text(review.get('status'))}`（责任角色：{_text(review.get('owner'))}）",
                f"- 仓库存储：`{_text(record.get('repository_storage'))}`",
                f"- 当前允许用途：{_text(rights.get('allowed_uses'))}",
                f"- 当前开启权限：{_permission_summary(record.get('permissions'))}",
            ]
        )
        if source_issues:
            lines.append("- 当前对外发布阻断：")
            lines.extend(f"  - {issue}" for issue in source_issues)
        else:
            lines.append("- 当前对外发布阻断：无")
        lines.append("")

    lines.extend(
        [
            "## 处理顺序",
            "",
            "1. 为每个 production 来源补齐合法取得日期和受控凭证索引。",
            "2. 由内容治理负责人完成权利复核，并记录复核责任人与日期。",
            "3. 评估原始扫描件的仓库存储处置，保留可追溯哈希但不直接改写审计结果。",
            "4. 重新运行 `python scripts/validate_source_register.py --require-release-eligible`，再运行发布就绪审计。",
            "",
            "> 完成上述动作需要真实权利证据和人工复核；不得通过修改报告、路线图或本阅读版文字来解除阻断。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="将来源登记台账渲染为人工阅读的资格报告")
    parser.add_argument("--register", type=Path, default=DEFAULT_REGISTER_PATH)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--active-db", type=Path, default=DEFAULT_ACTIVE_DB_PATH)
    parser.add_argument("--output", type=Path, required=True, help="Markdown 输出文件")
    args = parser.parse_args()
    try:
        result = validate_source_register(
            args.register,
            args.metadata,
            args.source_root,
            args.active_db,
        )
        records = _load_records(args.register.resolve())
        if args.output.exists():
            raise SourceRegisterError(f"输出文件已存在：{args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_markdown(result, records), encoding="utf-8")
    except (OSError, SourceRegisterError) as exc:
        print(f"source_register_report_error: {exc}")
        return 1
    print(json.dumps({"ok": True, "output": str(args.output.resolve())}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
