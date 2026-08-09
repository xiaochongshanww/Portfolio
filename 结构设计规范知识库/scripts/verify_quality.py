from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.app.core.urls import normalize_http_base_url  # noqa: E402
from src.evaluation.answer_runner import (  # noqa: E402
    ANSWER_EVAL_PATH,
    render_answer_evaluation_markdown,
    run_answer_evaluation,
)
from src.evaluation.api_target import probe_api_readiness  # noqa: E402
from src.evaluation.runner import (  # noqa: E402
    DEFAULT_EVAL_PATH,
    STRUCTURED_EVAL_PATH,
    render_evaluation_markdown,
    run_evaluation,
)
from src.pipeline.paths import AUDIT_DIR  # noqa: E402
from src.quality import (  # noqa: E402
    QualityReportStoreError,
    atomic_write_json,
    current_evidence_context,
    evaluate_quality_gate,
    finalize_quality_run,
    new_verification_run_id,
    quality_run_artifact_path,
    read_json_object,
    render_quality_gate_markdown,
    validate_runtime_config_hash,
    validate_verification_run_id,
    write_quality_report,
)

REPORTS_DIR = AUDIT_DIR / "reports"
LEGACY_API_KEY_PATH = PROJECT_ROOT / ".runtime_api_key"
MANAGED_API_LOG_NAME = "managed_quality_api_latest.log"
VERIFICATION_JSON_NAME = "verification_latest.json"
DEFERRED_RESULT_FILE_PATTERN = re.compile(r"^managed_child_result_[0-9a-f]{32}\.json$")
SECRET_ENV_NAMES = (
    "ZHIPUAI_API_KEY",
    "MIMO_API_KEY",
    "API_KEYS",
    "QUALITY_API_KEY",
    "OPENWEBUI_API_KEY",
    "ASSET_SIGNING_KEY",
)


class ManagedApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class ManagedApiTarget:
    api_base: str
    host: str
    bind_host: str
    port: int


def _parse_managed_api_target(api_base: str) -> ManagedApiTarget:
    parsed = urlsplit(api_base)
    if parsed.scheme != "http":
        raise ManagedApiError("托管 API 只支持 loopback HTTP 地址")
    if parsed.username is not None or parsed.password is not None:
        raise ManagedApiError("托管 API 地址不能包含用户名或密码")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ManagedApiError("托管 API 地址不能包含路径前缀、查询或片段")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ManagedApiError(f"托管 API 端口无效：{exc}") from exc
    if port is None:
        raise ManagedApiError("托管 API 地址必须显式指定端口")

    host = (parsed.hostname or "").lower()
    if host == "localhost":
        bind_host = "127.0.0.1"
    else:
        try:
            address = ipaddress.ip_address(host)
        except ValueError as exc:
            raise ManagedApiError("托管 API 只允许 localhost 或 loopback IP") from exc
        if not address.is_loopback:
            raise ManagedApiError("托管 API 只允许 localhost 或 loopback IP")
        bind_host = host

    return ManagedApiTarget(
        api_base=api_base,
        host=host,
        bind_host=bind_host,
        port=port,
    )


def _redact_secrets(text: str, environ: dict[str, str]) -> str:
    secrets: set[str] = set()
    for name in SECRET_ENV_NAMES:
        raw = environ.get(name, "").strip()
        if not raw:
            continue
        secrets.add(raw)
        if name == "API_KEYS":
            secrets.update(value.strip() for value in raw.split(",") if value.strip())
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, "<redacted>")
    return text


def _read_log_tail(path: Path, *, environ: dict[str, str], limit: int = 4000) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return _redact_secrets(content[-limit:], environ)


@dataclass
class ManagedApiProcess:
    target: ManagedApiTarget
    log_path: Path
    app: str = "src.app.main:app"
    cwd: Path = PROJECT_ROOT
    environ: dict[str, str] | None = field(default=None, repr=False)
    process: subprocess.Popen[str] | None = field(default=None, init=False, repr=False)
    _log_handle: Any = field(default=None, init=False, repr=False)

    def _child_environment(self) -> dict[str, str]:
        values = dict(os.environ if self.environ is None else self.environ)
        values["ANSWER_EVALUATION_API_BASE"] = self.target.api_base
        return values

    def _assert_port_available(self) -> None:
        family = socket.AF_INET6 if ":" in self.target.bind_host else socket.AF_INET
        try:
            with socket.socket(family, socket.SOCK_STREAM) as probe:
                probe.bind((self.target.bind_host, self.target.port))
        except OSError as exc:
            raise ManagedApiError(
                f"托管 API 端口已占用或不可绑定：{self.target.bind_host}:{self.target.port}"
            ) from exc

    def start(self, *, timeout_seconds: float = 60) -> dict[str, Any]:
        if timeout_seconds <= 0:
            raise ManagedApiError("API 启动等待时间必须大于 0")
        if self.process is not None:
            raise ManagedApiError("托管 API 进程已经启动")
        self._assert_port_available()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_handle = self.log_path.open("w", encoding="utf-8")
        environment = self._child_environment()
        command = [
            sys.executable,
            "-m",
            "uvicorn",
            self.app,
            "--host",
            self.target.bind_host,
            "--port",
            str(self.target.port),
        ]
        popen_options: dict[str, Any] = {
            "cwd": self.cwd,
            "env": environment,
            "stdout": self._log_handle,
            "stderr": subprocess.STDOUT,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
        }
        if sys.platform == "win32":
            popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_options["start_new_session"] = True
        self.process = subprocess.Popen(command, **popen_options)

        deadline = time.monotonic() + timeout_seconds
        try:
            while time.monotonic() < deadline:
                exit_code = self.process.poll()
                if exit_code is not None:
                    tail = _read_log_tail(self.log_path, environ=environment)
                    detail = f"；日志摘要：{tail}" if tail else ""
                    raise ManagedApiError(f"托管 API 在健康检查前退出，退出码 {exit_code}{detail}")
                try:
                    with urllib.request.urlopen(
                        f"{self.target.api_base}/health",
                        timeout=1,
                    ) as response:
                        if response.status == 200:
                            return {
                                "ok": True,
                                "api_base": self.target.api_base,
                                "pid": self.process.pid,
                                "log_path": str(self.log_path.resolve()),
                            }
                except (OSError, urllib.error.URLError):
                    pass
                time.sleep(0.25)
            tail = _read_log_tail(self.log_path, environ=environment)
            detail = f"；日志摘要：{tail}" if tail else ""
            raise ManagedApiError(f"托管 API 健康检查等待超时{detail}")
        except BaseException:
            self.stop()
            raise

    def stop(self, *, timeout_seconds: float = 10) -> dict[str, Any]:
        forced = False
        process = self.process
        try:
            if process is None:
                return {"ok": True, "already_stopped": True, "forced": False}
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    forced = True
                    process.kill()
                    process.wait(timeout=timeout_seconds)
            return {
                "ok": True,
                "forced": forced,
                "exit_code": process.returncode,
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "forced": forced, "error": f"托管 API 回收失败：{exc}"}
        finally:
            if self._log_handle is not None:
                self._log_handle.close()
                self._log_handle = None


@dataclass(frozen=True)
class ApiCredential:
    key: str = field(repr=False)
    source: str


def _read_api_key_file(path: Path, *, source: str) -> ApiCredential:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"API Key 文件不存在：{resolved}")
    try:
        key = resolved.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError(f"无法读取 API Key 文件 {resolved}：{exc}") from exc
    if not key:
        raise ValueError(f"API Key 文件为空：{resolved}")
    return ApiCredential(key=key, source=source)


def _resolve_api_credential(
    *,
    api_key_file: str | None,
    no_api_key: bool,
    environ: dict[str, str] | None = None,
    legacy_path: Path = LEGACY_API_KEY_PATH,
) -> ApiCredential:
    values = os.environ if environ is None else environ
    if no_api_key:
        return ApiCredential(key="", source="explicit_none")
    environment_key = values.get("QUALITY_API_KEY", "").strip()
    if environment_key:
        return ApiCredential(key=environment_key, source="environment")
    if api_key_file:
        return _read_api_key_file(Path(api_key_file), source="command_file")
    environment_file = values.get("QUALITY_API_KEY_FILE", "").strip()
    if environment_file:
        return _read_api_key_file(Path(environment_file), source="environment_file")
    if legacy_path.is_file():
        return _read_api_key_file(legacy_path, source="legacy_file")
    return ApiCredential(key="", source="none")


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


def _run_evaluation(
    path: Path,
    stem: str,
    title: str,
    evaluation_set_id: str,
    verification_run_id: str = "",
) -> dict[str, Any]:
    started = time.monotonic()
    result = run_evaluation(path, top_k=5)
    result.update(current_evidence_context())
    result["evaluation_set_id"] = evaluation_set_id
    if verification_run_id:
        result["verification_run_id"] = validate_verification_run_id(verification_run_id)
    report_kind = "structured" if evaluation_set_id == "structured" else "regular"
    report_path, markdown_path = write_quality_report(
        REPORTS_DIR,
        report_kind,
        result,
        render_evaluation_markdown(result, title),
        verification_run_id=verification_run_id or None,
    )
    failure_count = len(result.get("failures", []))
    passed = result.get("ok") is True and failure_count == 0
    return {
        "ok": passed,
        "duration_seconds": round(time.monotonic() - started, 2),
        "case_count": result.get("case_count", 0),
        "failure_count": failure_count,
        "evaluation_set_id": evaluation_set_id,
        "report_path": str(report_path),
        "markdown_report_path": str(markdown_path),
        "error": (
            result.get("error")
            or (f"检索评估完成但有 {failure_count} 个失败用例" if failure_count else "")
            or ("检索评估执行结果为 ok=false" if not passed else "")
        ),
    }


def _api_json(
    url: str,
    *,
    api_key: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _http_error_message(error: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(error.read().decode("utf-8"))
    except Exception:
        return str(error.reason or error)
    if isinstance(payload, dict):
        detail = payload.get("detail")
        api_error = payload.get("error")
        if isinstance(api_error, dict):
            return str(api_error.get("message") or api_error.get("code") or error.reason)
        if detail:
            return str(detail)
    return str(error.reason or error)


def _probe_api_access(
    api_base: str,
    credential: ApiCredential,
) -> dict[str, Any]:
    started = time.monotonic()
    common = {
        "credential_source": credential.source,
        "credential_supplied": bool(credential.key),
    }
    try:
        status = _api_json(f"{api_base}/admin/status", api_key=credential.key)
    except urllib.error.HTTPError as exc:
        message = _http_error_message(exc)
        if exc.code in {401, 403}:
            error = (
                f"目标 API 鉴权失败（HTTP {exc.code}）：{message}。"
                "请设置 QUALITY_API_KEY、--api-key-file 或 QUALITY_API_KEY_FILE；"
                "目标关闭鉴权时可使用 --no-api-key。"
            )
        else:
            error = f"目标 API 受保护端点预检失败（HTTP {exc.code}）：{message}"
        return {
            "ok": False,
            **common,
            "status_code": exc.code,
            "duration_seconds": round(time.monotonic() - started, 2),
            "error": error,
        }
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            **common,
            "duration_seconds": round(time.monotonic() - started, 2),
            "error": f"无法验证目标 API 访问权限：{exc}",
        }
    context = status.get("quality_evidence_context", {})
    runtime_hash = str(context.get("runtime_config_hash") or "")
    try:
        runtime_hash = validate_runtime_config_hash(runtime_hash)
    except ValueError:
        runtime_hash = ""
    return {
        "ok": True,
        **common,
        "status_code": 200,
        "evidence_context_schema": context.get("evidence_context_schema"),
        "runtime_config_hash": runtime_hash,
        "duration_seconds": round(time.monotonic() - started, 2),
    }


def _collect_api_preflight(
    api_base: str,
    *,
    api_key_file: str | None,
    no_api_key: bool,
) -> tuple[dict[str, Any], ApiCredential]:
    steps: list[dict[str, Any]] = []
    try:
        credential = _resolve_api_credential(
            api_key_file=api_key_file,
            no_api_key=no_api_key,
        )
        steps.append(
            {
                "name": "API 凭据加载",
                "ok": True,
                "credential_source": credential.source,
                "credential_supplied": bool(credential.key),
                "duration_seconds": 0,
            }
        )
        credential_loaded = True
    except ValueError as exc:
        credential = ApiCredential(key="", source="invalid")
        steps.append(
            {
                "name": "API 凭据加载",
                "ok": False,
                "credential_source": "invalid",
                "credential_supplied": False,
                "duration_seconds": 0,
                "error": str(exc),
            }
        )
        credential_loaded = False

    readiness = probe_api_readiness(api_base)
    steps.append({"name": "目标 API 就绪预检", **readiness})
    if credential_loaded:
        access = _probe_api_access(api_base, credential)
        steps.append({"name": "目标 API 鉴权预检", **access})
    else:
        steps.append(
            {
                "name": "目标 API 鉴权预检",
                "ok": False,
                "skipped": True,
                "duration_seconds": 0,
                "error": "未执行：API 凭据加载失败",
            }
        )

    return (
        {
            "ok": all(step.get("ok") is True for step in steps),
            "generated_at": datetime.now(UTC).isoformat(),
            "mode": "existing_api",
            "api_base": api_base,
            "steps": steps,
        },
        credential,
    )


def _run_api_preflight(
    api_base: str,
    *,
    api_key_file: str | None,
    no_api_key: bool,
) -> dict[str, Any]:
    result, _credential = _collect_api_preflight(
        api_base,
        api_key_file=api_key_file,
        no_api_key=no_api_key,
    )
    return result


def _run_api_evaluation(
    evaluation_set_id: str,
    api_base: str,
    api_key: str,
    verification_run_id: str = "",
    expected_runtime_config_hash: str = "",
) -> dict[str, Any]:
    started = time.monotonic()
    payload: dict[str, Any] = {"top_k": 5, "evaluation_set": evaluation_set_id}
    if verification_run_id:
        payload["verification_run_id"] = validate_verification_run_id(verification_run_id)
    job = _api_json(
        f"{api_base}/admin/jobs/evaluate",
        api_key=api_key,
        method="POST",
        payload=payload,
    )
    job_id = str(job["job_id"])
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        current = _api_json(f"{api_base}/admin/jobs/{job_id}", api_key=api_key)
        if current.get("status") == "succeeded":
            outputs = current.get("outputs", {})
            _write_api_evaluation_report(
                evaluation_set_id,
                outputs,
                verification_run_id=verification_run_id,
                expected_runtime_config_hash=expected_runtime_config_hash,
            )
            failure_count = len(outputs.get("failures", []))
            context_matches = (
                (not verification_run_id)
                or outputs.get("verification_run_id") == verification_run_id
            ) and (
                (not expected_runtime_config_hash)
                or outputs.get("runtime_config_hash") == expected_runtime_config_hash
            )
            passed = outputs.get("ok") is True and failure_count == 0 and context_matches
            return {
                "ok": passed,
                "duration_seconds": round(time.monotonic() - started, 2),
                "case_count": outputs.get("case_count", 0),
                "failure_count": failure_count,
                "evaluation_set_id": outputs.get("evaluation_set_id", evaluation_set_id),
                "verification_run_id": outputs.get("verification_run_id"),
                "runtime_config_hash": outputs.get("runtime_config_hash"),
                "error": (
                    outputs.get("error")
                    or (f"检索评估完成但有 {failure_count} 个失败用例" if failure_count else "")
                    or (
                        "评估任务返回的质量证据上下文与当前验证不一致"
                        if not context_matches
                        else ""
                    )
                    or ("评估后台任务返回 ok=false" if not passed else "")
                ),
                "job_id": job_id,
            }
        if current.get("status") == "failed":
            outputs = current.get("outputs", {})
            _write_api_evaluation_report(
                evaluation_set_id,
                outputs,
                verification_run_id=verification_run_id,
                expected_runtime_config_hash=expected_runtime_config_hash,
            )
            return {
                "ok": False,
                "duration_seconds": round(time.monotonic() - started, 2),
                "error": current.get("error") or outputs.get("error") or "评估后台任务失败",
                "report_path": outputs.get("report_path", ""),
                "job_id": job_id,
            }
        time.sleep(1)
    return {
        "ok": False,
        "duration_seconds": round(time.monotonic() - started, 2),
        "error": "评估后台任务等待超时",
        "job_id": job_id,
    }


def _write_api_evaluation_report(
    evaluation_set_id: str,
    outputs: Any,
    *,
    verification_run_id: str,
    expected_runtime_config_hash: str,
) -> None:
    if not isinstance(outputs, dict) or not outputs:
        return
    report = {
        key: value
        for key, value in outputs.items()
        if key not in {"report_path", "markdown_report_path"}
    }
    report.setdefault("generated_at", datetime.now(UTC).isoformat())
    report.setdefault("evaluation_set_id", evaluation_set_id)
    report.setdefault(
        "evidence_context_schema",
        current_evidence_context()["evidence_context_schema"],
    )
    if verification_run_id:
        run_id = validate_verification_run_id(verification_run_id)
        source_run_id = str(report.get("verification_run_id") or "")
        if source_run_id and source_run_id != run_id:
            report["source_verification_run_id"] = source_run_id
            report["ok"] = False
            report["error"] = "评估任务返回的验证运行身份不一致"
        report["verification_run_id"] = run_id
    if expected_runtime_config_hash:
        runtime_hash = validate_runtime_config_hash(expected_runtime_config_hash)
        source_runtime_hash = str(report.get("runtime_config_hash") or "")
        if source_runtime_hash and source_runtime_hash != runtime_hash:
            report["source_runtime_config_hash"] = source_runtime_hash
            report["ok"] = False
            report["error"] = "评估任务返回的运行配置指纹不一致"
        report["runtime_config_hash"] = runtime_hash
    report_kind = "structured" if evaluation_set_id == "structured" else "regular"
    title = "结构化检索专项评估" if report_kind == "structured" else "检索评估报告"
    write_quality_report(
        REPORTS_DIR,
        report_kind,
        report,
        render_evaluation_markdown(report, title),
        verification_run_id=verification_run_id or None,
    )


def _run_answer_evaluation_against_api(
    api_base: str,
    api_key: str,
    verification_run_id: str = "",
    runtime_config_hash: str = "",
) -> dict[str, Any]:
    started = time.monotonic()
    result = run_answer_evaluation(
        api_base=api_base,
        api_key=api_key,
        path=ANSWER_EVAL_PATH,
    )
    result["evidence_context_schema"] = current_evidence_context()["evidence_context_schema"]
    result["runtime_config_hash"] = validate_runtime_config_hash(
        runtime_config_hash or current_evidence_context()["runtime_config_hash"]
    )
    if verification_run_id:
        result["verification_run_id"] = validate_verification_run_id(verification_run_id)
    result["evaluation_set_id"] = "answer"
    report_path, markdown_path = write_quality_report(
        REPORTS_DIR,
        "answer",
        result,
        render_answer_evaluation_markdown(result),
        verification_run_id=verification_run_id or None,
    )
    pass_rate = float(result.get("pass_rate", 0))
    passed = result.get("ok") is True and pass_rate >= 0.90
    return {
        "ok": passed,
        "duration_seconds": round(time.monotonic() - started, 2),
        "case_count": result.get("case_count", 0),
        "failure_count": result.get("failure_count", 0),
        "pass_rate": pass_rate,
        "api_base": result.get("api_base", api_base),
        "evaluation_set_id": "answer",
        "verification_run_id": result.get("verification_run_id"),
        "runtime_config_hash": result.get("runtime_config_hash"),
        "report_path": str(report_path),
        "markdown_report_path": str(markdown_path),
        "error": (
            result.get("error")
            or (f"回答级盲测通过率 {pass_rate:.1%}，低于 90.0%" if not passed else "")
        ),
    }


def _execute_step(name: str, action: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    started = time.monotonic()
    try:
        return {"name": name, **action()}
    except Exception as exc:
        return {
            "name": name,
            "ok": False,
            "duration_seconds": round(time.monotonic() - started, 2),
            "error": str(exc),
        }


def _render_verification_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 无人值守质量验证报告",
        "",
        f"- 结论：{'通过' if result.get('passed') else '未通过'}",
        f"- 生成时间：{result.get('generated_at')}",
        f"- 验证运行：`{result.get('verification_run_id') or '-'}`",
        f"- 运行配置指纹：`{result.get('runtime_config_hash') or '-'}`",
        "",
        "| 步骤 | 状态 | 耗时 |",
        "| --- | --- | --- |",
    ]
    for step in result.get("steps", []):
        status = "跳过" if step.get("skipped") else ("通过" if step.get("ok") else "失败")
        lines.append(f"| {step.get('name')} | {status} | {step.get('duration_seconds', '-')} s |")
    failed = [step for step in result.get("steps", []) if not step.get("ok")]
    if failed:
        lines.extend(["", "## 失败详情", ""])
        for step in failed:
            detail = (
                step.get("error")
                or step.get("stderr_tail")
                or step.get("stdout_tail")
                or "未知错误"
            )
            lines.extend([f"### {step.get('name')}", "", "```text", str(detail).strip(), "```", ""])
    return "\n".join(lines)


def _write_verification_result(
    result: dict[str, Any],
    *,
    verification_run_id: str | None = None,
) -> str:
    markdown = _render_verification_markdown(result)
    write_quality_report(
        REPORTS_DIR,
        "verification",
        result,
        markdown,
        verification_run_id=verification_run_id,
    )
    return markdown


def _ensure_quality_run_reports(
    verification_run_id: str,
    runtime_config_hash: str,
    steps: list[dict[str, Any]],
) -> None:
    step_names = {
        "regular": "常规检索评估",
        "structured": "结构化专项评估",
        "answer": "回答级盲测",
    }
    step_by_name = {str(step.get("name")): step for step in steps}
    context = current_evidence_context()
    for report_kind, step_name in step_names.items():
        report_path = quality_run_artifact_path(
            REPORTS_DIR,
            verification_run_id,
            f"{report_kind}_json",
        )
        if report_path.is_file():
            continue
        step = step_by_name.get(step_name, {})
        error = str(step.get("error") or "未执行：完整验证显式跳过该评估")
        report: dict[str, Any] = {
            "ok": False,
            "generated_at": datetime.now(UTC).isoformat(),
            "evidence_context_schema": context["evidence_context_schema"],
            "runtime_config_hash": validate_runtime_config_hash(runtime_config_hash),
            "verification_run_id": validate_verification_run_id(verification_run_id),
            "evaluation_set_id": report_kind,
            "execution_status": "skipped",
            "case_count": 0,
            "failure_count": 0,
            "failures": [],
            "error": error,
        }
        if report_kind == "answer":
            report.update(
                {
                    "passed_count": 0,
                    "pass_rate": 0,
                    "check_rates": {},
                    "refusal_pass_rate": 0,
                    "results": [],
                }
            )
            markdown = render_answer_evaluation_markdown(report)
        else:
            title = "结构化检索专项评估" if report_kind == "structured" else "检索评估报告"
            markdown = render_evaluation_markdown(report, title)
        write_quality_report(
            REPORTS_DIR,
            report_kind,
            report,
            markdown,
            verification_run_id=verification_run_id,
        )


def _managed_child_args(argv: list[str]) -> list[str]:
    return [value for value in argv if value != "--manage-api"]


def _validate_deferred_result_file(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.parent != REPORTS_DIR.resolve() or not DEFERRED_RESULT_FILE_PATTERN.fullmatch(
        resolved.name
    ):
        raise ValueError("托管子进程结果文件必须位于质量报告目录并使用受控名称")
    return resolved


def _load_deferred_verification_result(path: Path) -> tuple[str, dict[str, Any]]:
    handoff = read_json_object(path)
    if handoff.get("schema_version") != 1:
        raise QualityReportStoreError("托管子进程结果契约版本无效")
    run_id = validate_verification_run_id(str(handoff.get("verification_run_id") or ""))
    expected_relative = Path("runs", run_id, "verification.json").as_posix()
    if handoff.get("verification_report") != expected_relative:
        raise QualityReportStoreError("托管子进程验证报告路径无效")
    report_path = quality_run_artifact_path(
        REPORTS_DIR,
        run_id,
        "verification_json",
    )
    result = read_json_object(report_path)
    if result.get("verification_run_id") != run_id:
        raise QualityReportStoreError("托管子进程验证报告运行身份不一致")
    return run_id, result


def _write_deferred_verification_result(
    path: Path,
    verification_run_id: str,
) -> None:
    run_id = validate_verification_run_id(verification_run_id)
    atomic_write_json(
        _validate_deferred_result_file(path),
        {
            "schema_version": 1,
            "verification_run_id": run_id,
            "verification_report": Path("runs", run_id, "verification.json").as_posix(),
        },
    )


def _run_managed_verification(
    api_base: str,
    argv: list[str],
    *,
    startup_timeout_seconds: float,
) -> int:
    target = _parse_managed_api_target(api_base)
    manager = ManagedApiProcess(
        target=target,
        log_path=REPORTS_DIR / MANAGED_API_LOG_NAME,
    )
    handoff_path = REPORTS_DIR / f"managed_child_result_{new_verification_run_id()}.json"
    handoff_path.unlink(missing_ok=True)
    started_at = time.monotonic()
    startup_step: dict[str, Any]
    cleanup_step: dict[str, Any] | None = None

    try:
        startup = manager.start(timeout_seconds=startup_timeout_seconds)
        startup_step = {
            "name": "托管 API 启动",
            "ok": True,
            "duration_seconds": round(time.monotonic() - started_at, 2),
            "api_base": startup["api_base"],
            "log_path": startup["log_path"],
        }
    except (ManagedApiError, OSError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
        cleanup = manager.stop()
        cleanup_step = {
            "name": "托管 API 回收",
            "duration_seconds": 0,
            **cleanup,
        }
        result = {
            "generated_at": datetime.now(UTC).isoformat(),
            "passed": False,
            "managed_api": {
                "enabled": True,
                "api_base": api_base,
                "log_path": str(manager.log_path.resolve()),
            },
            "steps": [
                {
                    "name": "托管 API 启动",
                    "ok": False,
                    "duration_seconds": round(time.monotonic() - started_at, 2),
                    "error": _redact_secrets(str(exc), manager._child_environment()),
                },
                cleanup_step,
            ],
        }
        print(_write_verification_result(result))
        return 130 if isinstance(exc, KeyboardInterrupt) else 1

    child_started_at = time.monotonic()
    child: subprocess.CompletedProcess[str] | None = None
    interrupted = False
    child_error = ""
    try:
        child_environment = dict(os.environ)
        child_environment["ANSWER_EVALUATION_API_BASE"] = api_base
        child = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                *_managed_child_args(argv),
                "--defer-quality-publish",
                "--deferred-result-file",
                str(handoff_path),
            ],
            cwd=PROJECT_ROOT,
            env=child_environment,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
    except KeyboardInterrupt:
        interrupted = True
        child_error = "托管质量验证被中断"
    except (OSError, subprocess.SubprocessError) as exc:
        child_error = f"无法执行质量验证子进程：{exc}"
    finally:
        cleanup_started_at = time.monotonic()
        cleanup = manager.stop()
        cleanup_step = {
            "name": "托管 API 回收",
            "duration_seconds": round(time.monotonic() - cleanup_started_at, 2),
            **cleanup,
        }

    verification_run_id: str | None = None
    try:
        verification_run_id, result = _load_deferred_verification_result(handoff_path)
    except (OSError, QualityReportStoreError, ValueError):
        result = None
    finally:
        handoff_path.unlink(missing_ok=True)
    if result is None:
        environment = manager._child_environment()
        output_tail = ""
        if child is not None:
            output_tail = (child.stderr or child.stdout or "")[-4000:]
        result = {
            "generated_at": datetime.now(UTC).isoformat(),
            "passed": False,
            "steps": [
                {
                    "name": "质量验证子进程",
                    "ok": False,
                    "duration_seconds": round(time.monotonic() - child_started_at, 2),
                    "error": _redact_secrets(
                        child_error or output_tail or "子进程未生成新的验证报告",
                        environment,
                    ),
                    "exit_code": child.returncode if child is not None else None,
                }
            ],
        }
    elif child_error or interrupted:
        result.setdefault("steps", []).append(
            {
                "name": "质量验证子进程",
                "ok": False,
                "duration_seconds": round(time.monotonic() - child_started_at, 2),
                "error": child_error,
            }
        )
    elif child is not None and child.returncode == 0 and result.get("passed") is not True:
        result.setdefault("steps", []).append(
            {
                "name": "质量验证子进程结果一致性",
                "ok": False,
                "duration_seconds": 0,
                "error": "子进程退出码为 0，但验证报告未标记为通过",
            }
        )
    elif child is not None and child.returncode != 0 and result.get("passed") is True:
        result.setdefault("steps", []).append(
            {
                "name": "质量验证子进程结果一致性",
                "ok": False,
                "duration_seconds": 0,
                "error": f"子进程退出码为 {child.returncode}，但验证报告标记为通过",
            }
        )

    result["managed_api"] = {
        "enabled": True,
        "api_base": api_base,
        "log_path": str(manager.log_path.resolve()),
        "child_exit_code": child.returncode if child is not None else None,
        "interrupted": interrupted,
    }
    result["steps"] = [startup_step, *result.get("steps", []), cleanup_step]
    result["passed"] = bool(
        result.get("passed")
        and child is not None
        and child.returncode == 0
        and cleanup_step.get("ok") is True
        and not interrupted
    )
    if verification_run_id:
        result["verification_run_id"] = verification_run_id
        markdown = _write_verification_result(
            result,
            verification_run_id=verification_run_id,
        )
        try:
            finalize_quality_run(
                REPORTS_DIR,
                verification_run_id,
                passed=result["passed"],
                completed_at=datetime.now(UTC).isoformat(),
            )
        except (OSError, QualityReportStoreError) as exc:
            result["passed"] = False
            result["steps"].append(
                {
                    "name": "质量证据原子发布",
                    "ok": False,
                    "duration_seconds": 0,
                    "error": str(exc),
                }
            )
            markdown = _render_verification_markdown(result)
    else:
        markdown = _write_verification_result(result)
    print(markdown)
    if interrupted:
        return 130
    return 0 if result["passed"] else 1


def _run_managed_preflight(
    api_base: str,
    *,
    api_key_file: str | None,
    no_api_key: bool,
    startup_timeout_seconds: float,
) -> int:
    target = _parse_managed_api_target(api_base)
    manager = ManagedApiProcess(
        target=target,
        log_path=REPORTS_DIR / MANAGED_API_LOG_NAME,
    )
    steps: list[dict[str, Any]] = []
    started_at = time.monotonic()
    interrupted = False
    try:
        startup = manager.start(timeout_seconds=startup_timeout_seconds)
        steps.append(
            {
                "name": "托管 API 启动",
                "ok": True,
                "duration_seconds": round(time.monotonic() - started_at, 2),
                "api_base": startup["api_base"],
                "log_path": startup["log_path"],
            }
        )
        preflight = _run_api_preflight(
            api_base,
            api_key_file=api_key_file,
            no_api_key=no_api_key,
        )
        steps.extend(preflight["steps"])
    except KeyboardInterrupt:
        interrupted = True
        steps.append(
            {
                "name": "托管 API 预检",
                "ok": False,
                "duration_seconds": round(time.monotonic() - started_at, 2),
                "error": "托管 API 预检被中断",
            }
        )
    except (ManagedApiError, OSError, subprocess.SubprocessError) as exc:
        steps.append(
            {
                "name": "托管 API 启动",
                "ok": False,
                "duration_seconds": round(time.monotonic() - started_at, 2),
                "error": _redact_secrets(str(exc), manager._child_environment()),
            }
        )
    finally:
        cleanup_started_at = time.monotonic()
        cleanup = manager.stop()
        steps.append(
            {
                "name": "托管 API 回收",
                "duration_seconds": round(time.monotonic() - cleanup_started_at, 2),
                **cleanup,
            }
        )

    result = {
        "ok": all(step.get("ok") is True for step in steps) and not interrupted,
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "managed_api",
        "api_base": api_base,
        "writes_quality_reports": False,
        "steps": steps,
    }
    print(json.dumps(result, ensure_ascii=True))
    if interrupted:
        return 130
    return 0 if result["ok"] else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="执行完整的无人值守质量验证")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--skip-evaluations", action="store_true")
    parser.add_argument("--skip-answer-evaluation", action="store_true")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--manage-api",
        action="store_true",
        help="在空闲 loopback 端口启动并回收本地 API，再执行完整验证",
    )
    parser.add_argument(
        "--api-start-timeout-seconds",
        type=float,
        default=60,
        help="托管模式等待本地 API /health 就绪的最长秒数",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="只检查目标 API 就绪与鉴权，不执行测试、评估、门禁或写入质量报告",
    )
    parser.add_argument(
        "--defer-quality-publish",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--deferred-result-file",
        type=Path,
        help=argparse.SUPPRESS,
    )
    credential_group = parser.add_mutually_exclusive_group()
    credential_group.add_argument(
        "--api-key-file",
        help="从 UTF-8 文件读取目标 API Key；不把原始 Key 放入命令行",
    )
    credential_group.add_argument(
        "--no-api-key",
        action="store_true",
        help="忽略所有 Key 来源，显式验证关闭鉴权的目标",
    )
    parser.add_argument(
        "--evaluation-mode",
        choices=("api", "local"),
        default="api",
        help="默认通过已运行 API 执行评估，以复用其模型配置",
    )
    args = parser.parse_args()
    if args.defer_quality_publish != (args.deferred_result_file is not None):
        parser.error("托管子进程延迟发布参数必须成对使用")
    if args.defer_quality_publish and (args.manage_api or args.preflight_only):
        parser.error("延迟发布只允许由托管父进程启动的完整验证子进程使用")
    if args.deferred_result_file is not None:
        try:
            args.deferred_result_file = _validate_deferred_result_file(args.deferred_result_file)
        except ValueError as exc:
            parser.error(str(exc))
    try:
        api_base = normalize_http_base_url(args.api_base, field_name="--api-base")
    except ValueError as exc:
        parser.error(str(exc))
    if args.manage_api:
        try:
            if args.preflight_only:
                exit_code = _run_managed_preflight(
                    api_base,
                    api_key_file=args.api_key_file,
                    no_api_key=args.no_api_key,
                    startup_timeout_seconds=args.api_start_timeout_seconds,
                )
            else:
                exit_code = _run_managed_verification(
                    api_base,
                    sys.argv[1:],
                    startup_timeout_seconds=args.api_start_timeout_seconds,
                )
        except ManagedApiError as exc:
            parser.error(str(exc))
        raise SystemExit(exit_code)

    if args.preflight_only:
        result = _run_api_preflight(
            api_base,
            api_key_file=args.api_key_file,
            no_api_key=args.no_api_key,
        )
        print(json.dumps(result, ensure_ascii=True))
        raise SystemExit(0 if result["ok"] else 1)

    verification_run_id = new_verification_run_id()
    local_evidence_context = current_evidence_context()
    runtime_hash = str(local_evidence_context["runtime_config_hash"])
    steps: list[dict[str, Any]] = []
    api_required = (
        not args.skip_evaluations and args.evaluation_mode == "api"
    ) or not args.skip_answer_evaluation
    api_ready = True
    api_accessible = True
    credential = ApiCredential(key="", source="none")
    if api_required:
        preflight, credential = _collect_api_preflight(
            api_base,
            api_key_file=args.api_key_file,
            no_api_key=args.no_api_key,
        )
        steps.extend(preflight["steps"])
        readiness_step = next(
            step for step in preflight["steps"] if step["name"] == "目标 API 就绪预检"
        )
        access_step = next(
            step for step in preflight["steps"] if step["name"] == "目标 API 鉴权预检"
        )
        api_ready = readiness_step.get("ok") is True
        api_accessible = access_step.get("ok") is True
        runtime_hash = str(access_step.get("runtime_config_hash") or runtime_hash)

    api_available = api_ready and api_accessible
    unavailable_reasons = []
    if not api_ready:
        unavailable_reasons.append("就绪预检失败")
    if not api_accessible:
        unavailable_reasons.append("鉴权预检失败")
    api_unavailable_error = "未执行：目标 API " + "、".join(unavailable_reasons)

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

        def evaluation_action(
            evaluation_set_id: str,
            path: Path,
            stem: str,
            title: str,
        ) -> dict[str, Any]:
            if args.evaluation_mode == "api":
                try:
                    return _run_api_evaluation(
                        evaluation_set_id,
                        api_base,
                        credential.key,
                        verification_run_id,
                        runtime_hash,
                    )
                except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
                    return {"ok": False, "error": f"无法调用本地评估 API：{exc}"}
            return _run_evaluation(
                path,
                stem,
                title,
                evaluation_set_id,
                verification_run_id,
            )

        if args.evaluation_mode == "api" and not api_available:
            for name in ("常规检索评估", "结构化专项评估"):
                steps.append(
                    {
                        "name": name,
                        "ok": False,
                        "skipped": True,
                        "duration_seconds": 0,
                        "error": api_unavailable_error,
                    }
                )
        else:
            steps.append(
                _execute_step(
                    "常规检索评估",
                    lambda: evaluation_action(
                        "regular",
                        DEFAULT_EVAL_PATH,
                        "evaluation_latest",
                        "检索评估报告",
                    ),
                )
            )
            steps.append(
                _execute_step(
                    "结构化专项评估",
                    lambda: evaluation_action(
                        "structured",
                        STRUCTURED_EVAL_PATH,
                        "evaluation_structured_latest",
                        "结构化检索专项评估",
                    ),
                )
            )
    else:
        for name in ("常规检索评估", "结构化专项评估"):
            steps.append(
                {
                    "name": name,
                    "ok": False,
                    "skipped": True,
                    "duration_seconds": 0,
                    "error": "未执行：命令显式跳过检索评估",
                }
            )
    if not args.skip_answer_evaluation:
        if not api_available:
            steps.append(
                {
                    "name": "回答级盲测",
                    "ok": False,
                    "skipped": True,
                    "duration_seconds": 0,
                    "error": api_unavailable_error,
                }
            )
        else:
            steps.append(
                _execute_step(
                    "回答级盲测",
                    lambda: _run_answer_evaluation_against_api(
                        api_base,
                        credential.key,
                        verification_run_id,
                        runtime_hash,
                    ),
                )
            )
    else:
        steps.append(
            {
                "name": "回答级盲测",
                "ok": False,
                "skipped": True,
                "duration_seconds": 0,
                "error": "未执行：命令显式跳过回答级盲测",
            }
        )
    _ensure_quality_run_reports(verification_run_id, runtime_hash, steps)
    gate_result = evaluate_quality_gate(
        regular_report_path=quality_run_artifact_path(
            REPORTS_DIR, verification_run_id, "regular_json"
        ),
        structured_report_path=quality_run_artifact_path(
            REPORTS_DIR, verification_run_id, "structured_json"
        ),
        answer_report_path=quality_run_artifact_path(
            REPORTS_DIR, verification_run_id, "answer_json"
        ),
        expected_verification_run_id=verification_run_id,
        expected_runtime_config_hash=runtime_hash,
    )
    write_quality_report(
        REPORTS_DIR,
        "gate",
        gate_result,
        render_quality_gate_markdown(gate_result),
        verification_run_id=verification_run_id,
    )
    failed_gate_checks = [str(value) for value in gate_result.get("failed_checks", [])]
    steps.append(
        {
            "name": "自动质量门禁",
            "ok": gate_result["passed"],
            "duration_seconds": 0,
            "error": (
                "自动质量门禁未通过：" + ", ".join(failed_gate_checks)
                if not gate_result["passed"]
                else ""
            ),
        }
    )

    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "passed": all(step.get("ok") for step in steps),
        "verification_run_id": verification_run_id,
        "runtime_config_hash": runtime_hash,
        "steps": steps,
    }
    markdown = _write_verification_result(
        result,
        verification_run_id=verification_run_id,
    )
    if args.defer_quality_publish:
        _write_deferred_verification_result(
            args.deferred_result_file,
            verification_run_id,
        )
        print(markdown)
        if not result["passed"]:
            raise SystemExit(1)
        return
    try:
        finalize_quality_run(
            REPORTS_DIR,
            verification_run_id,
            passed=result["passed"],
            completed_at=result["generated_at"],
        )
    except (OSError, QualityReportStoreError) as exc:
        result["passed"] = False
        result["steps"].append(
            {
                "name": "质量证据原子发布",
                "ok": False,
                "duration_seconds": 0,
                "error": str(exc),
            }
        )
        markdown = _render_verification_markdown(result)
    print(markdown)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
