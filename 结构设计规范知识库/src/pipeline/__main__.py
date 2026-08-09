import argparse
import sys
from datetime import timedelta
from math import isfinite
from pathlib import Path

from .builder import (
    BuildPreflightError,
    audit,
    build,
    parser_status,
    print_json,
    promote_corrections,
    rebuild,
    review,
    status,
)
from .knowledge_package import (
    KnowledgePackageError,
    export_runtime_package,
    import_runtime_package,
    probe_runtime_package,
    validate_runtime_package,
)
from .paths import DATA_DIR, RAW_DIR
from .runtime_backup import (
    RuntimeBackupError,
    create_runtime_backup,
    restore_runtime_backup,
    validate_runtime_backup,
)


def _configure_cli_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="backslashreplace")


def _quality_age_hours(value: str) -> float:
    try:
        hours = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是数字") from exc
    if not isfinite(hours) or not 0 < hours <= 8760:
        raise argparse.ArgumentTypeError("必须大于 0 且不超过 8760 小时")
    return hours


def main() -> None:
    _configure_cli_streams()
    parser = argparse.ArgumentParser(description="结构设计规范知识库构建工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("build", "rebuild"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument(
            "--source", default=str(RAW_DIR), help="PDF 源目录，默认 data/raw"
        )
        command_parser.add_argument(
            "--dry-run", action="store_true", help="只列出将处理的 PDF，不写入产物"
        )
        command_parser.add_argument(
            "--no-corrections", action="store_true", help="构建时不应用 approved corrections"
        )
        command_parser.add_argument(
            "--parser-backend",
            default="mineru",
            choices=["mineru", "pymupdf"],
            help="PDF 解析后端，默认 mineru",
        )

    subparsers.add_parser("status")
    parser_status_parser = subparsers.add_parser(
        "parser-status", help="探测 PDF 解析器实现、版本与兼容状态"
    )
    parser_status_parser.add_argument(
        "--parser-backend",
        default="mineru",
        choices=["mineru", "pymupdf"],
        help="PDF 解析后端，默认 mineru",
    )
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument(
        "--processed-dir", default="data/processed", help="已生成 processed 目录"
    )
    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("--doc", required=True, help="要校对的文档文件名或 doc id")
    review_parser.add_argument("--pages", default="", help="页码范围，例如 40-45")
    review_parser.add_argument("--source", default=str(RAW_DIR), help="PDF 源目录，默认 data/raw")
    review_parser.add_argument(
        "--processed-dir", default="data/processed", help="已生成 processed 目录"
    )
    promote_parser = subparsers.add_parser("promote-corrections")
    promote_parser.add_argument("--doc", required=True, help="要提升候选修正的文档文件名或 doc id")
    promote_parser.add_argument(
        "--include-pending", action="store_true", help="同时提升 pending 候选；默认只提升 approved"
    )
    export_parser = subparsers.add_parser("package-export", help="导出可直接运行的知识包")
    export_parser.add_argument("--output", required=True, help="输出 ZIP 文件")
    export_parser.add_argument(
        "--include-source-pdfs", action="store_true", help="显式包含原始 PDF；默认排除"
    )
    export_parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的输出文件")
    export_parser.add_argument("--actor", default="", help="执行导出的责任人；默认读取当前系统用户")
    export_parser.add_argument(
        "--quality-max-age-hours",
        type=_quality_age_hours,
        default=168,
        help="评估报告最大有效期，单位小时，默认 168（7 天）",
    )
    export_parser.add_argument(
        "--quality-waiver-actor", default="", help="质量门禁未通过时的豁免责任人"
    )
    export_parser.add_argument(
        "--quality-waiver-reason", default="", help="质量门禁未通过时的豁免原因"
    )
    validate_parser = subparsers.add_parser("package-validate", help="校验知识包格式和文件哈希")
    validate_parser.add_argument("--package", required=True, help="知识包 ZIP 文件")
    probe_parser = subparsers.add_parser(
        "package-probe", help="隔离导入并打开 Chroma 验证运行兼容性"
    )
    probe_parser.add_argument("--package", required=True, help="知识包 ZIP 文件")
    probe_parser.add_argument(
        "--expect-source-platform", default="", help="要求清单中的来源平台，例如 windows"
    )
    probe_parser.add_argument(
        "--require-cross-platform",
        action="store_true",
        help="要求来源与本机平台不同且无非预期兼容警告",
    )
    import_parser = subparsers.add_parser("package-import", help="导入并激活运行知识包")
    import_parser.add_argument("--package", required=True, help="知识包 ZIP 文件")
    import_parser.add_argument(
        "--data-dir", default=str(DATA_DIR), help="目标数据目录，默认使用 DATA_DIR"
    )
    import_parser.add_argument("--replace", action="store_true", help="覆盖同包版本和冲突资产")
    import_parser.add_argument(
        "--no-activate",
        action="store_true",
        help="只安装数据库版本，不更新活动指针或共享资产",
    )
    backup_create_parser = subparsers.add_parser(
        "backup-create", help="在维护窗口创建完整 DATA_DIR 快照"
    )
    backup_create_parser.add_argument(
        "--output", required=True, help="输出 ZIP 文件，必须位于 DATA_DIR 外"
    )
    backup_create_parser.add_argument(
        "--data-dir", default=str(DATA_DIR), help="源数据目录，默认使用 DATA_DIR"
    )
    backup_create_parser.add_argument(
        "--overwrite", action="store_true", help="覆盖已存在的输出文件"
    )
    backup_create_parser.add_argument(
        "--actor", default="", help="执行备份的责任人；默认读取当前系统用户"
    )
    backup_create_parser.add_argument(
        "--maintenance-window",
        action="store_true",
        help="确认 API 已停止且 DATA_DIR 处于维护窗口",
    )
    backup_validate_parser = subparsers.add_parser(
        "backup-validate", help="离线校验完整 DATA_DIR 快照"
    )
    backup_validate_parser.add_argument("--backup", required=True, help="要校验的快照 ZIP 文件")
    backup_restore_parser = subparsers.add_parser(
        "backup-restore", help="事务恢复完整 DATA_DIR 快照"
    )
    backup_restore_parser.add_argument("--backup", required=True, help="要恢复的快照 ZIP 文件")
    backup_restore_parser.add_argument(
        "--data-dir", default=str(DATA_DIR), help="目标数据目录，默认使用 DATA_DIR"
    )
    backup_restore_parser.add_argument(
        "--replace", action="store_true", help="替换非空的目标 DATA_DIR"
    )
    backup_restore_parser.add_argument(
        "--actor", default="", help="执行恢复的责任人；默认读取当前系统用户"
    )
    backup_restore_parser.add_argument(
        "--maintenance-window",
        action="store_true",
        help="确认 API 已停止且目标 DATA_DIR 处于维护窗口",
    )
    args = parser.parse_args()

    try:
        if args.command == "status":
            print_json(status())
        elif args.command == "parser-status":
            print_json(parser_status(args.parser_backend))
        elif args.command == "build":
            print_json(
                build(
                    Path(args.source),
                    dry_run_only=args.dry_run,
                    parser_backend=args.parser_backend,
                    apply_corrections=not args.no_corrections,
                )
            )
        elif args.command == "rebuild":
            print_json(
                rebuild(
                    Path(args.source),
                    dry_run_only=args.dry_run,
                    parser_backend=args.parser_backend,
                    apply_corrections=not args.no_corrections,
                )
            )
        elif args.command == "audit":
            print_json(audit(Path(args.processed_dir)))
        elif args.command == "review":
            print_json(review(args.doc, args.pages, Path(args.source), Path(args.processed_dir)))
        elif args.command == "promote-corrections":
            print_json(promote_corrections(args.doc, include_pending=args.include_pending))
        elif args.command == "package-export":
            print_json(
                export_runtime_package(
                    Path(args.output),
                    include_source_pdfs=args.include_source_pdfs,
                    overwrite=args.overwrite,
                    quality_max_age=timedelta(hours=args.quality_max_age_hours),
                    quality_waiver_actor=args.quality_waiver_actor,
                    quality_waiver_reason=args.quality_waiver_reason,
                    export_actor=args.actor,
                )
            )
        elif args.command == "package-validate":
            print_json(validate_runtime_package(Path(args.package)))
        elif args.command == "package-probe":
            print_json(
                probe_runtime_package(
                    Path(args.package),
                    expected_source_platform=args.expect_source_platform,
                    require_cross_platform=args.require_cross_platform,
                )
            )
        elif args.command == "package-import":
            print_json(
                import_runtime_package(
                    Path(args.package),
                    data_dir=Path(args.data_dir),
                    replace=args.replace,
                    activate=not args.no_activate,
                )
            )
        elif args.command == "backup-create":
            print_json(
                create_runtime_backup(
                    Path(args.output),
                    data_dir=Path(args.data_dir),
                    overwrite=args.overwrite,
                    actor=args.actor,
                    maintenance_window=args.maintenance_window,
                )
            )
        elif args.command == "backup-validate":
            print_json(validate_runtime_backup(Path(args.backup)))
        elif args.command == "backup-restore":
            print_json(
                restore_runtime_backup(
                    Path(args.backup),
                    data_dir=Path(args.data_dir),
                    replace=args.replace,
                    actor=args.actor,
                    maintenance_window=args.maintenance_window,
                )
            )
    except (BuildPreflightError, KnowledgePackageError, RuntimeBackupError) as exc:
        print_json({"ok": False, "error": str(exc)})
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
