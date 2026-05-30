import argparse
import json
from pathlib import Path

from .runner import DEFAULT_EVAL_PATH, run_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="结构设计规范知识库检索评估工具")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--file", default=str(DEFAULT_EVAL_PATH), help="评估集 JSONL 文件")
    run_parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if args.command == "run":
        result = run_evaluation(Path(args.file), top_k=args.top_k)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result.get("ok", False):
            raise SystemExit(1)


if __name__ == "__main__":
    main()

