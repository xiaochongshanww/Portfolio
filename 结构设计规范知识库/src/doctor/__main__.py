import argparse
import json
import sys

from .checks import SUPPORTED_PROFILES, render_text, run_doctor


def _configure_cli_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def main() -> None:
    _configure_cli_streams()
    parser = argparse.ArgumentParser(description="结构设计规范知识库部署环境只读自检")
    parser.add_argument(
        "--profile",
        choices=sorted(SUPPORTED_PROFILES),
        default="runtime",
        help="runtime 检查轻量问答运行环境；build 检查 PDF 知识生产环境",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="默认输出适合人工阅读的文本；json 用于自动化",
    )
    args = parser.parse_args()
    report = run_doctor(profile=args.profile)
    if args.format == "json":
        # JSON is consumed by shells and CI as well as humans; escaped Unicode
        # keeps the machine-readable stream portable across Windows code pages.
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print(render_text(report))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
