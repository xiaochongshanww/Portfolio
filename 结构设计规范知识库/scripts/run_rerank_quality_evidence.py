from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_API_BASE = "http://127.0.0.1:8019"
DEFAULT_COMPARISON_REPORT = (
    PROJECT_ROOT / "data" / "audit" / "reports" / "rerank_comparison_latest.json"
)
DEFAULT_COMPARISON_MARKDOWN = (
    PROJECT_ROOT / "data" / "audit" / "reports" / "rerank_comparison_latest.md"
)
DEFAULT_ANSWER_REPORT = PROJECT_ROOT / "data" / "audit" / "reports" / "rerank_answer_latest.json"
DEFAULT_ANSWER_MARKDOWN = PROJECT_ROOT / "data" / "audit" / "reports" / "rerank_answer_latest.md"
RERANK_ENVIRONMENT_KEYS = (
    "ZHIPUAI_API_KEY",
    "RERANK_ENABLED",
    "RERANK_PROVIDER",
    "MIMO_API_KEY",
)


class RerankQualityEvidenceError(RuntimeError):
    pass


def _read_secret(path: Path, label: str) -> str:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise RerankQualityEvidenceError(f"{label}文件不存在：{resolved}")
    try:
        value = resolved.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as exc:
        raise RerankQualityEvidenceError(f"无法读取{label}文件：{resolved}") from exc
    if not value:
        raise RerankQualityEvidenceError(f"{label}文件为空：{resolved}")
    return value


@contextmanager
def _temporary_environment(values: dict[str, str]) -> Iterator[None]:
    previous = {name: os.environ.get(name) for name in RERANK_ENVIRONMENT_KEYS}
    os.environ.update(values)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _configure_cli_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def _safe_failure(stage: str, exc: BaseException) -> dict[str, Any]:
    return {
        "ok": False,
        "comparison_complete": False,
        "stage": stage,
        "error": f"{stage}执行失败：{type(exc).__name__}",
    }


def _build_child_environment(*, api_key: str, zhipu_key: str, mimo_key: str) -> dict[str, str]:
    """构造临时 API 环境；目标鉴权 Key 只进入子进程。"""
    child_environment = dict(os.environ)
    child_environment.update(
        {
            "ZHIPUAI_API_KEY": zhipu_key,
            "RERANK_ENABLED": "true",
            "RERANK_PROVIDER": "zhipu",
        }
    )
    if api_key:
        child_environment["API_KEYS"] = api_key
    if mimo_key:
        child_environment["MIMO_API_KEY"] = mimo_key
    return child_environment


def run_rerank_quality_evidence(
    *,
    zhipu_key_file: Path,
    api_key_file: Path | None = None,
    mimo_key_file: Path | None = None,
    api_base: str = DEFAULT_API_BASE,
    comparison_report: Path = DEFAULT_COMPARISON_REPORT,
    comparison_markdown: Path = DEFAULT_COMPARISON_MARKDOWN,
    answer_report: Path = DEFAULT_ANSWER_REPORT,
    answer_markdown: Path = DEFAULT_ANSWER_MARKDOWN,
) -> dict[str, Any]:
    zhipu_key = _read_secret(zhipu_key_file, "智谱 Key")
    api_key = _read_secret(api_key_file, "目标 API Key") if api_key_file else ""
    mimo_key = _read_secret(mimo_key_file, "Mimo Key") if mimo_key_file else ""
    child_environment = _build_child_environment(
        api_key=api_key,
        zhipu_key=zhipu_key,
        mimo_key=mimo_key,
    )

    with _temporary_environment(
        {
            name: value
            for name, value in child_environment.items()
            if name in RERANK_ENVIRONMENT_KEYS and value
        }
    ):
        try:
            from scripts.verify_quality import (  # noqa: PLC0415
                ManagedApiProcess,
                _parse_managed_api_target,
            )
            from src.evaluation.answer_runner import (  # noqa: PLC0415
                ANSWER_EVAL_PATH,
                render_answer_evaluation_markdown,
                run_answer_evaluation,
            )
            from src.evaluation.rerank_comparison import (  # noqa: PLC0415
                render_rerank_comparison_markdown,
                run_rerank_comparison,
            )
            from src.pipeline.active_db import read_active_manifest  # noqa: PLC0415
        except Exception as exc:
            raise RerankQualityEvidenceError("加载精排质量运行依赖失败") from exc

        try:
            comparison = run_rerank_comparison()
        except Exception as exc:
            comparison = _safe_failure("精排对照", exc)
        _write_json(comparison_report, comparison)
        comparison_markdown_path = comparison_markdown.expanduser().resolve()
        comparison_markdown_path.parent.mkdir(parents=True, exist_ok=True)
        comparison_markdown_path.write_text(
            render_rerank_comparison_markdown(comparison), encoding="utf-8"
        )
        if comparison.get("ok") is not True or comparison.get("comparison_complete") is not True:
            return {
                "ok": False,
                "stage": "comparison",
                "comparison_complete": False,
                "comparison_report": str(comparison_report.expanduser().resolve()),
                "answer_report": str(answer_report.expanduser().resolve()),
                "error": comparison.get("error", "精排对照未完成"),
            }

        target = _parse_managed_api_target(api_base)
        manager = ManagedApiProcess(
            target=target,
            log_path=PROJECT_ROOT / "data" / "audit" / "reports" / "rerank_quality_api_latest.log",
            environ=child_environment,
        )
        try:
            manager.start()
            answer = run_answer_evaluation(
                api_base=api_base,
                api_key=api_key,
                path=ANSWER_EVAL_PATH,
            )
        except Exception as exc:
            answer = _safe_failure("回答盲测", exc)
        finally:
            manager.stop()

        manifest = read_active_manifest()
        answer["rerank_enabled"] = True
        answer["rerank_provider"] = "zhipu"
        answer["data_version_hash"] = str(manifest.get("data_version_hash") or "")
        answer["api_base"] = api_base
        answer["credential_source"] = "command_file" if api_key_file else "environment_or_none"
        _write_json(answer_report, answer)
        answer_markdown_path = answer_markdown.expanduser().resolve()
        answer_markdown_path.parent.mkdir(parents=True, exist_ok=True)
        answer_markdown_path.write_text(render_answer_evaluation_markdown(answer), encoding="utf-8")
        pass_rate = answer.get("pass_rate", 0)
        answer_ok = (
            answer.get("ok") is True
            and isinstance(pass_rate, (int, float))
            and not isinstance(pass_rate, bool)
            and pass_rate >= 0.9
        )
        return {
            "ok": answer_ok,
            "comparison_complete": True,
            "answer_pass_rate": answer.get("pass_rate", 0),
            "comparison_report": str(comparison_report.expanduser().resolve()),
            "answer_report": str(answer_report.expanduser().resolve()),
            "error": answer.get("error", "") if not answer_ok else "",
        }


def main() -> int:
    _configure_cli_streams()
    parser = argparse.ArgumentParser(description="执行启用精排的完整对照与回答盲测")
    parser.add_argument("--zhipu-key-file", type=Path, required=True, help="智谱精排 Key 文件")
    parser.add_argument("--api-key-file", type=Path, help="目标 API 鉴权 Key 文件")
    parser.add_argument("--mimo-key-file", type=Path, help="Mimo Key 文件；未提供时使用当前环境")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--comparison-report", type=Path, default=DEFAULT_COMPARISON_REPORT)
    parser.add_argument("--comparison-markdown", type=Path, default=DEFAULT_COMPARISON_MARKDOWN)
    parser.add_argument("--answer-report", type=Path, default=DEFAULT_ANSWER_REPORT)
    parser.add_argument("--answer-markdown", type=Path, default=DEFAULT_ANSWER_MARKDOWN)
    args = parser.parse_args()
    try:
        result = run_rerank_quality_evidence(
            zhipu_key_file=args.zhipu_key_file,
            api_key_file=args.api_key_file,
            mimo_key_file=args.mimo_key_file,
            api_base=args.api_base,
            comparison_report=args.comparison_report,
            comparison_markdown=args.comparison_markdown,
            answer_report=args.answer_report,
            answer_markdown=args.answer_markdown,
        )
    except RerankQualityEvidenceError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
