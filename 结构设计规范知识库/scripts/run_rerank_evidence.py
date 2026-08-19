from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_OUTPUT_JSON = PROJECT_ROOT / "data" / "audit" / "reports" / "rerank_comparison_latest.json"
DEFAULT_OUTPUT_MARKDOWN = (
    PROJECT_ROOT / "data" / "audit" / "reports" / "rerank_comparison_latest.md"
)
DEFAULT_EVALUATION = PROJECT_ROOT / "data" / "evaluation" / "queries.jsonl"


class RerankEvidenceError(RuntimeError):
    pass


def _read_api_key(path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        value = resolved.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as exc:
        raise RerankEvidenceError(f"无法读取精排 Key 文件：{resolved}") from exc
    if not value:
        raise RerankEvidenceError(f"精排 Key 文件为空：{resolved}")
    return value


def _configure_rerank_environment(api_key: str, environ: dict[str, str] | None = None) -> None:
    # Configure before importing the application so Settings reads this run's secret only.
    values = os.environ if environ is None else environ
    values["ZHIPUAI_API_KEY"] = api_key
    values["RERANK_ENABLED"] = "true"
    values["RERANK_PROVIDER"] = "zhipu"


def run_rerank_evidence(
    *,
    api_key_file: Path,
    evaluation_file: Path = DEFAULT_EVALUATION,
    top_k: int = 5,
    json_output: Path = DEFAULT_OUTPUT_JSON,
    markdown_output: Path = DEFAULT_OUTPUT_MARKDOWN,
) -> dict[str, Any]:
    if top_k <= 0:
        raise RerankEvidenceError("top_k 必须大于 0")
    api_key = _read_api_key(api_key_file)
    _configure_rerank_environment(api_key)

    from src.evaluation.rerank_comparison import (
        render_rerank_comparison_markdown,
        run_rerank_comparison,
    )

    try:
        result = run_rerank_comparison(evaluation_file.resolve(), top_k=top_k)
    except Exception as exc:
        raise RerankEvidenceError(f"精排对照执行失败：{type(exc).__name__}") from exc

    result["credential_source"] = "command_file"
    result["credential_persisted"] = False
    json_output = json_output.expanduser().resolve()
    markdown_output = markdown_output.expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_output.write_text(
        render_rerank_comparison_markdown(result),
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="使用受控 Key 文件执行真实精排对照")
    parser.add_argument("--api-key-file", type=Path, required=True, help="智谱 Key 文件")
    parser.add_argument("--file", type=Path, default=DEFAULT_EVALUATION, help="评估集 JSONL")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_OUTPUT_MARKDOWN)
    args = parser.parse_args()
    try:
        result = run_rerank_evidence(
            api_key_file=args.api_key_file,
            evaluation_file=args.file,
            top_k=args.top_k,
            json_output=args.json_output,
            markdown_output=args.markdown_output,
        )
    except RerankEvidenceError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True, indent=2))
        return 1
    print(
        json.dumps(
            {
                "ok": result.get("ok") is True and result.get("comparison_complete") is True,
                "comparison_complete": result.get("comparison_complete", False),
                "case_count": result.get("case_count", 0),
                "reranked_case_count": result.get("reranked_case_count", 0),
                "fallback_case_count": result.get("fallback_case_count", 0),
                "data_version_hash": result.get("data_version_hash", ""),
                "error": result.get("error", ""),
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0 if result.get("ok") is True and result.get("comparison_complete") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
