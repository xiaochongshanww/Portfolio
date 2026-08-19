from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def _configure_cli_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def build_planned_record(
    *,
    trial_id: str,
    participant_id: str,
    delivery: str,
    environment_owner: str,
    source_register_version: str,
    tasks: list[str],
) -> dict[str, object]:
    values = {
        "trial_id": trial_id.strip(),
        "participant_id": participant_id.strip(),
        "delivery": delivery.strip(),
        "environment_owner": environment_owner.strip(),
        "source_register_version": source_register_version.strip(),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ValueError("以下字段不能为空：" + ", ".join(missing))
    normalized_tasks = [task.strip() for task in tasks if task.strip()]
    if len(normalized_tasks) < 3:
        raise ValueError("至少需要 3 个固定任务；这只是计划记录，不代表任务已执行")

    return {
        "schema_version": 1,
        "status": "planned",
        **values,
        "started_at": None,
        "ended_at": None,
        "data_cleanup_date": None,
        "preflight": {
            "participant_acknowledged": False,
            "source_scope_confirmed": False,
            "no_unrelated_data": False,
            "key_log_owner_defined": False,
            "disclaimer_shown": False,
        },
        "fixed_tasks": [
            {
                "task_id": f"T-{index:03d}",
                "question": question,
                "found_basis": False,
                "references": [],
                "human_review_required": True,
                "defect_ids": [],
            }
            for index, question in enumerate(normalized_tasks, start=1)
        ],
        "defects": [],
        "conclusion": None,
        "created_at": datetime.now(UTC).isoformat(),
    }


def main() -> int:
    _configure_cli_streams()
    parser = argparse.ArgumentParser(description="生成待执行的封闭试用计划记录（不会生成完成证据）")
    parser.add_argument("--output", type=Path, required=True, help="输出 JSON 文件")
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--participant-id", required=True, help="不得填写真实姓名")
    parser.add_argument("--delivery", required=True, help="受控宿主机或运行包等交付方式")
    parser.add_argument("--environment-owner", required=True)
    parser.add_argument("--source-register-version", required=True)
    parser.add_argument("--task", action="append", required=True, help="固定任务；至少重复 3 次")
    args = parser.parse_args()
    try:
        record = build_planned_record(
            trial_id=args.trial_id,
            participant_id=args.participant_id,
            delivery=args.delivery,
            environment_owner=args.environment_owner,
            source_register_version=args.source_register_version,
            tasks=args.task,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            raise ValueError(f"输出文件已存在：{args.output}")
        args.output.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError) as exc:
        print(f"trial_record_create_error: {exc}")
        return 1
    print(
        json.dumps(
            {"ok": True, "status": "planned", "record": str(args.output.resolve())},
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
