import argparse
from pathlib import Path

from .builder import BuildPreflightError, build, print_json, rebuild, status
from .paths import RAW_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="结构设计规范知识库构建工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("build", "rebuild"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--source", default=str(RAW_DIR), help="PDF 源目录，默认 data/raw")
        command_parser.add_argument("--dry-run", action="store_true", help="只列出将处理的 PDF，不写入产物")
        command_parser.add_argument(
            "--parser-backend",
            default="mineru",
            choices=["mineru", "pymupdf"],
            help="PDF 解析后端，默认 mineru",
        )

    subparsers.add_parser("status")
    args = parser.parse_args()

    try:
        if args.command == "status":
            print_json(status())
        elif args.command == "build":
            print_json(build(Path(args.source), dry_run_only=args.dry_run, parser_backend=args.parser_backend))
        elif args.command == "rebuild":
            print_json(rebuild(Path(args.source), dry_run_only=args.dry_run, parser_backend=args.parser_backend))
    except BuildPreflightError as exc:
        print_json({"ok": False, "error": str(exc)})
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
