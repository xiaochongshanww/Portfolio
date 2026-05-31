import argparse
from pathlib import Path

from .builder import BuildPreflightError, audit, build, print_json, promote_corrections, rebuild, review, status
from .paths import RAW_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="结构设计规范知识库构建工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("build", "rebuild"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--source", default=str(RAW_DIR), help="PDF 源目录，默认 data/raw")
        command_parser.add_argument("--dry-run", action="store_true", help="只列出将处理的 PDF，不写入产物")
        command_parser.add_argument("--no-corrections", action="store_true", help="构建时不应用 approved corrections")
        command_parser.add_argument(
            "--parser-backend",
            default="mineru",
            choices=["mineru", "pymupdf"],
            help="PDF 解析后端，默认 mineru",
        )

    subparsers.add_parser("status")
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--processed-dir", default="data/processed", help="已生成 processed 目录")
    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("--doc", required=True, help="要校对的文档文件名或 doc id")
    review_parser.add_argument("--pages", default="", help="页码范围，例如 40-45")
    review_parser.add_argument("--source", default=str(RAW_DIR), help="PDF 源目录，默认 data/raw")
    review_parser.add_argument("--processed-dir", default="data/processed", help="已生成 processed 目录")
    promote_parser = subparsers.add_parser("promote-corrections")
    promote_parser.add_argument("--doc", required=True, help="要提升候选修正的文档文件名或 doc id")
    promote_parser.add_argument("--include-pending", action="store_true", help="同时提升 pending 候选；默认只提升 approved")
    args = parser.parse_args()

    try:
        if args.command == "status":
            print_json(status())
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
    except BuildPreflightError as exc:
        print_json({"ok": False, "error": str(exc)})
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
