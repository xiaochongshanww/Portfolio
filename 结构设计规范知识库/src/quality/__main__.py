import argparse
import json
from pathlib import Path

from src.pipeline.paths import AUDIT_DIR

from .gate import evaluate_quality_gate, render_quality_gate_markdown


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
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "quality_gate_latest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown = render_quality_gate_markdown(result)
    (args.output_dir / "quality_gate_latest.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
