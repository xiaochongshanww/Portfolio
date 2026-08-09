import argparse
import json
from pathlib import Path

from .rerank_comparison import render_rerank_comparison_markdown, run_rerank_comparison
from .runner import DEFAULT_EVAL_PATH, run_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="结构设计规范知识库检索评估工具")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--file", default=str(DEFAULT_EVAL_PATH), help="评估集 JSONL 文件")
    run_parser.add_argument("--top-k", type=int, default=5)
    compare_parser = subparsers.add_parser("compare-rerank")
    compare_parser.add_argument("--file", default=str(DEFAULT_EVAL_PATH), help="评估集 JSONL 文件")
    compare_parser.add_argument("--top-k", type=int, default=5)
    compare_parser.add_argument("--json-output", type=Path)
    compare_parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()

    if args.command == "run":
        result = run_evaluation(Path(args.file), top_k=args.top_k)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result.get("ok", False):
            raise SystemExit(1)
    elif args.command == "compare-rerank":
        result = run_rerank_comparison(Path(args.file), top_k=args.top_k)
        serialized = json.dumps(result, ensure_ascii=False, indent=2)
        if args.json_output:
            args.json_output.parent.mkdir(parents=True, exist_ok=True)
            args.json_output.write_text(serialized + "\n", encoding="utf-8")
        if args.markdown_output:
            args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
            args.markdown_output.write_text(
                render_rerank_comparison_markdown(result), encoding="utf-8"
            )
        print(serialized)
        if not result.get("ok", False):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
