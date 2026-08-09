from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.paths import AUDIT_DIR  # noqa: E402
from src.quality.run_retention import (  # noqa: E402
    QualityRunRetentionError,
    QualityRunRetentionPolicy,
    create_quality_run_cleanup_plan,
    default_snapshot_paths,
    execute_quality_run_cleanup_plan,
    list_quality_runs,
)


def _non_negative(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是整数") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("不能小于 0")
    return parsed


def _positive_minutes(value: str) -> int:
    parsed = _non_negative(value)
    if not 1 <= parsed <= 1440:
        raise argparse.ArgumentTypeError("必须在 1 到 1440 之间")
    return parsed


def _add_common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=AUDIT_DIR / "reports",
        help="质量报告目录",
    )
    parser.add_argument(
        "--audit-dir",
        type=Path,
        default=AUDIT_DIR,
        help="审计目录",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        action="append",
        default=None,
        help="需要保护引用的脱敏质量快照，可重复指定；默认使用仓库当前及历史快照",
    )


def _add_policy(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--keep-recent-complete", type=_non_negative, default=10)
    parser.add_argument("--complete-max-age-days", type=_non_negative, default=90)
    parser.add_argument("--incomplete-max-age-days", type=_non_negative, default=7)
    parser.add_argument("--minimum-age-hours", type=_non_negative, default=24)
    parser.add_argument("--plan-ttl-minutes", type=_positive_minutes, default=15)


def _policy(args: argparse.Namespace) -> QualityRunRetentionPolicy:
    return QualityRunRetentionPolicy(
        keep_recent_complete=args.keep_recent_complete,
        complete_max_age_days=args.complete_max_age_days,
        incomplete_max_age_days=args.incomplete_max_age_days,
        minimum_age_hours=args.minimum_age_hours,
        plan_ttl_minutes=args.plan_ttl_minutes,
    )


def _snapshots(args: argparse.Namespace) -> list[Path]:
    return args.snapshot if args.snapshot is not None else default_snapshot_paths(PROJECT_ROOT)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="管理质量运行证据的保留与受控清理")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser("list", help="只读列出质量运行、保护原因和候选状态")
    _add_common_paths(inventory)
    _add_policy(inventory)

    plan = subparsers.add_parser("plan", help="生成有时限的持久化清理计划")
    _add_common_paths(plan)
    _add_policy(plan)

    execute = subparsers.add_parser("execute", help="执行已持久化且通过重检的清理计划")
    _add_common_paths(execute)
    execute.add_argument("plan_id", help="32 位小写十六进制计划标识")
    execute.add_argument(
        "--confirm",
        action="store_true",
        help="显式确认执行删除；缺少时拒绝执行",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "list":
            result = list_quality_runs(
                args.reports_dir,
                snapshot_paths=_snapshots(args),
                policy=_policy(args),
            )
        elif args.command == "plan":
            result = create_quality_run_cleanup_plan(
                args.reports_dir,
                args.audit_dir,
                snapshot_paths=_snapshots(args),
                policy=_policy(args),
            )
        else:
            result = execute_quality_run_cleanup_plan(
                args.reports_dir,
                args.audit_dir,
                args.plan_id,
                snapshot_paths=_snapshots(args),
                confirm=args.confirm,
            )
    except (OSError, QualityRunRetentionError) as exc:
        print(
            json.dumps(
                {"ok": False, "error": str(exc)},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    if args.command == "execute" and result.get("status") != "succeeded":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
