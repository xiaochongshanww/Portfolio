import argparse
from pathlib import Path

from src.pipeline.paths import AUDIT_DIR

from .gate import evaluate_quality_gate, render_quality_gate_markdown
from .report_store import write_quality_report


def main() -> None:
    parser = argparse.ArgumentParser(description="结构设计规范知识库自动质量门禁")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=AUDIT_DIR / "reports",
        help="JSON 和 Markdown 报告输出目录",
    )
    args = parser.parse_args()

    result = evaluate_quality_gate()
    markdown = render_quality_gate_markdown(result)
    write_quality_report(args.output_dir, "gate", result, markdown)
    print(markdown)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
