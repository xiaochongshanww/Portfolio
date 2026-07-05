from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.runner import (  # noqa: E402
    DEFAULT_EVAL_PATH,
    STRUCTURED_EVAL_PATH,
    render_evaluation_markdown,
    run_evaluation,
)
from src.pipeline.paths import AUDIT_DIR  # noqa: E402
from src.quality import evaluate_quality_gate, render_quality_gate_markdown  # noqa: E402


REPORTS_DIR = AUDIT_DIR / "reports"


def _run_command(command: list[str], cwd: Path) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return {
        "ok": completed.returncode == 0,
        "duration_seconds": round(time.monotonic() - started, 2),
        "command": command,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def _run_evaluation(path: Path, stem: str, title: str) -> dict[str, Any]:
    started = time.monotonic()
    result = run_evaluation(path, top_k=5)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / f"{stem}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (REPORTS_DIR / f"{stem}.md").write_text(
        render_evaluation_markdown(result, title),
        encoding="utf-8",
    )
    return {
        "ok": result.get("ok") is True and not result.get("failures"),
        "duration_seconds": round(time.monotonic() - started, 2),
        "case_count": result.get("case_count", 0),
        "failure_count": len(result.get("failures", [])),
        "error": result.get("error", ""),
    }


def _api_json(
    url: str,
    *,
    api_key: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Authorization": f"Bearer {api_key}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _run_api_evaluation(path: Path, api_base: str, api_key: str) -> dict[str, Any]:
    started = time.monotonic()
    job = _api_json(
        f"{api_base}/admin/jobs/evaluate",
        api_key=api_key,
        method="POST",
        payload={"top_k": 5, "file": str(path.resolve())},
    )
    job_id = str(job["job_id"])
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        current = _api_json(f"{api_base}/admin/jobs/{job_id}", api_key=api_key)
        if current.get("status") == "succeeded":
            outputs = current.get("outputs", {})
            return {
                "ok": outputs.get("ok") is True and not outputs.get("failures"),
                "duration_seconds": round(time.monotonic() - started, 2),
                "case_count": outputs.get("case_count", 0),
                "failure_count": len(outputs.get("failures", [])),
                "job_id": job_id,
            }
        if current.get("status") == "failed":
            return {
                "ok": False,
                "duration_seconds": round(time.monotonic() - started, 2),
                "error": current.get("error") or "评估后台任务失败",
                "job_id": job_id,
            }
        time.sleep(1)
    return {
        "ok": False,
        "duration_seconds": round(time.monotonic() - started, 2),
        "error": "评估后台任务等待超时",
        "job_id": job_id,
    }


def _run_api_answer_evaluation(api_base: str, api_key: str) -> dict[str, Any]:
    started = time.monotonic()
    job = _api_json(
        f"{api_base}/admin/jobs/evaluate-answers",
        api_key=api_key,
        method="POST",
        payload={},
    )
    job_id = str(job["job_id"])
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        current = _api_json(f"{api_base}/admin/jobs/{job_id}", api_key=api_key)
        if current.get("status") == "succeeded":
            outputs = current.get("outputs", {})
            return {
                "ok": (
                    outputs.get("ok") is True
                    and float(outputs.get("pass_rate", 0)) >= 0.90
                ),
                "duration_seconds": round(time.monotonic() - started, 2),
                "case_count": outputs.get("case_count", 0),
                "failure_count": outputs.get("failure_count", 0),
                "pass_rate": outputs.get("pass_rate", 0),
                "job_id": job_id,
            }
        if current.get("status") == "failed":
            return {
                "ok": False,
                "duration_seconds": round(time.monotonic() - started, 2),
                "error": current.get("error") or "回答评估后台任务失败",
                "job_id": job_id,
            }
        time.sleep(2)
    return {
        "ok": False,
        "duration_seconds": round(time.monotonic() - started, 2),
        "error": "回答评估后台任务等待超时",
        "job_id": job_id,
    }


def _execute_step(name: str, action: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return {"name": name, **action()}
    except Exception as exc:
        return {"name": name, "ok": False, "error": str(exc)}


def _render_verification_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 无人值守质量验证报告",
        "",
        f"- 结论：{'通过' if result.get('passed') else '未通过'}",
        f"- 生成时间：{result.get('generated_at')}",
        "",
        "| 步骤 | 状态 | 耗时 |",
        "| --- | --- | --- |",
    ]
    for step in result.get("steps", []):
        lines.append(
            f"| {step.get('name')} | {'通过' if step.get('ok') else '失败'} | {step.get('duration_seconds', '-')} s |"
        )
    failed = [step for step in result.get("steps", []) if not step.get("ok")]
    if failed:
        lines.extend(["", "## 失败详情", ""])
        for step in failed:
            detail = step.get("error") or step.get("stderr_tail") or step.get("stdout_tail") or "未知错误"
            lines.extend([f"### {step.get('name')}", "", "```text", str(detail).strip(), "```", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="执行完整的无人值守质量验证")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--skip-evaluations", action="store_true")
    parser.add_argument("--skip-answer-evaluation", action="store_true")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--evaluation-mode",
        choices=("api", "local"),
        default="api",
        help="默认通过已运行 API 执行评估，以复用其模型配置",
    )
    args = parser.parse_args()

    steps: list[dict[str, Any]] = []
    if not args.skip_tests:
        steps.append(
            _execute_step(
                "后端测试",
                lambda: _run_command([sys.executable, "-m", "pytest", "-q"], PROJECT_ROOT),
            )
        )
    if not args.skip_frontend:
        npm_command = "npm.cmd" if sys.platform == "win32" else "npm"
        steps.append(
            _execute_step(
                "前端生产构建",
                lambda: _run_command([npm_command, "run", "build"], PROJECT_ROOT / "frontend"),
            )
        )
    if not args.skip_evaluations:
        runtime_key_path = PROJECT_ROOT / ".runtime_api_key"
        runtime_key = runtime_key_path.read_text(encoding="utf-8").strip() if runtime_key_path.exists() else ""

        def evaluation_action(path: Path, stem: str, title: str) -> dict[str, Any]:
            if args.evaluation_mode == "api":
                if not runtime_key:
                    return {"ok": False, "error": "缺少 .runtime_api_key，无法调用本地评估 API"}
                try:
                    return _run_api_evaluation(path, args.api_base.rstrip("/"), runtime_key)
                except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
                    return {"ok": False, "error": f"无法调用本地评估 API：{exc}"}
            return _run_evaluation(path, stem, title)

        steps.append(
            _execute_step(
                "常规检索评估",
                lambda: evaluation_action(DEFAULT_EVAL_PATH, "evaluation_latest", "检索评估报告"),
            )
        )
        steps.append(
            _execute_step(
                "结构化专项评估",
                lambda: evaluation_action(
                    STRUCTURED_EVAL_PATH,
                    "evaluation_structured_latest",
                    "结构化检索专项评估",
                ),
            )
        )
    if not args.skip_answer_evaluation:
        runtime_key_path = PROJECT_ROOT / ".runtime_api_key"
        runtime_key = runtime_key_path.read_text(encoding="utf-8").strip() if runtime_key_path.exists() else ""
        if not runtime_key:
            steps.append({"name": "回答级盲测", "ok": False, "error": "缺少 .runtime_api_key"})
        else:
            steps.append(
                _execute_step(
                    "回答级盲测",
                    lambda: _run_api_answer_evaluation(
                        args.api_base.rstrip("/"),
                        runtime_key,
                    ),
                )
            )
    gate_result = evaluate_quality_gate()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "quality_gate_latest.json").write_text(
        json.dumps(gate_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (REPORTS_DIR / "quality_gate_latest.md").write_text(
        render_quality_gate_markdown(gate_result),
        encoding="utf-8",
    )
    steps.append({"name": "自动质量门禁", "ok": gate_result["passed"], "duration_seconds": 0})

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": all(step.get("ok") for step in steps),
        "steps": steps,
    }
    (REPORTS_DIR / "verification_latest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown = _render_verification_markdown(result)
    (REPORTS_DIR / "verification_latest.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
