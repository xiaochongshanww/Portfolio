import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    api_key: str = "",
) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_health(base_url: str, process: subprocess.Popen, log_path: Path) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            if _request_json(f"{base_url}/health").get("status") == "ok":
                return
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
    log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    raise AssertionError(f"隔离 API 未能启动，退出码={process.poll()}\n{log[-4000:]}")


def _wait_for_job(base_url: str, job_id: str, *, api_key: str = "") -> dict:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        payload = _request_json(f"{base_url}/admin/jobs/{job_id}", api_key=api_key)
        if payload.get("status") in {"succeeded", "failed"}:
            return payload
        time.sleep(0.1)
    raise AssertionError(f"后台任务 {job_id} 未在时限内结束")


def test_custom_port_preflight_and_evaluation_failure_semantics(tmp_path: Path):
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    data_dir = tmp_path / "runtime"
    log_path = tmp_path / "api.log"
    env = os.environ.copy()
    env.update(
        {
            "DATA_DIR": str(data_dir),
            "DB_DIR": str(tmp_path / "db"),
            "IMG_DIR": str(data_dir / "images"),
            "SOURCE_METADATA_PATH": str(data_dir / "metadata" / "specs.json"),
            "ZHIPUAI_API_KEY": "",
            "MIMO_API_KEY": "",
            "API_AUTH_ENABLED": "false",
            "API_KEYS": "",
            "RATE_LIMIT_ENABLED": "false",
            "ANSWER_EVALUATION_API_BASE": base_url,
            "PYTHONUNBUFFERED": "1",
        }
    )
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "src.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=PROJECT_ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        try:
            _wait_for_health(base_url, process, log_path)

            verification = subprocess.run(
                [
                    sys.executable,
                    "scripts/verify_quality.py",
                    "--skip-tests",
                    "--skip-frontend",
                    "--skip-evaluations",
                    "--api-base",
                    base_url,
                    "--no-api-key",
                ],
                cwd=PROJECT_ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=30,
                creationflags=creationflags,
            )
            assert verification.returncode == 1
            report = json.loads(
                (data_dir / "audit" / "reports" / "verification_latest.json").read_text(
                    encoding="utf-8"
                )
            )
            reports_dir = data_dir / "audit" / "reports"
            pointer = json.loads(
                (reports_dir / "quality_run_latest.json").read_text(encoding="utf-8")
            )
            assert pointer["verification_run_id"] == report["verification_run_id"]
            run_dir = reports_dir / "runs" / pointer["verification_run_id"]
            assert {
                "evaluation.json",
                "evaluation.md",
                "evaluation_structured.json",
                "evaluation_structured.md",
                "evaluation_answer.json",
                "evaluation_answer.md",
                "quality_gate.json",
                "quality_gate.md",
                "verification.json",
                "verification.md",
                "manifest.json",
            } <= {path.name for path in run_dir.iterdir()}
            preflight = next(
                step for step in report["steps"] if step["name"] == "目标 API 就绪预检"
            )
            credential = next(step for step in report["steps"] if step["name"] == "API 凭据加载")
            access = next(step for step in report["steps"] if step["name"] == "目标 API 鉴权预检")
            answer = next(step for step in report["steps"] if step["name"] == "回答级盲测")
            assert preflight["api_base"] == base_url
            assert "COLLECTION_EMPTY" in preflight["reasons"]
            assert credential["credential_source"] == "explicit_none"
            assert credential["credential_supplied"] is False
            assert access["ok"] is True
            assert answer["skipped"] is True

            retrieval_job = _request_json(
                f"{base_url}/admin/jobs/evaluate",
                method="POST",
                payload={"evaluation_set": "regular", "top_k": 5},
            )
            retrieval_result = _wait_for_job(base_url, retrieval_job["job_id"])
            assert retrieval_result["status"] == "failed"
            assert "检索服务未就绪" in retrieval_result["error"]
            assert retrieval_result["outputs"]["evaluation_set_id"] == "regular"
            assert Path(retrieval_result["outputs"]["report_path"]).is_file()

            answer_job = _request_json(
                f"{base_url}/admin/jobs/evaluate-answers",
                method="POST",
                payload={},
            )
            answer_result = _wait_for_job(base_url, answer_job["job_id"])
            assert answer_result["status"] == "failed"
            assert answer_result["outputs"]["readiness"]["api_base"] == base_url
            assert "未就绪" in answer_result["error"]
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def test_authenticated_preflight_uses_key_file_and_never_logs_secret(tmp_path: Path):
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    data_dir = tmp_path / "runtime"
    log_path = tmp_path / "api-auth.log"
    correct_key = "quality-verification-correct-secret"
    wrong_key = "quality-verification-wrong-secret"
    correct_key_file = tmp_path / "correct.key"
    wrong_key_file = tmp_path / "wrong.key"
    correct_key_file.write_text(correct_key, encoding="utf-8")
    wrong_key_file.write_text(wrong_key, encoding="utf-8")
    env = os.environ.copy()
    env.update(
        {
            "DATA_DIR": str(data_dir),
            "DB_DIR": str(tmp_path / "db"),
            "IMG_DIR": str(data_dir / "images"),
            "SOURCE_METADATA_PATH": str(data_dir / "metadata" / "specs.json"),
            "ZHIPUAI_API_KEY": "",
            "MIMO_API_KEY": "",
            "API_AUTH_ENABLED": "true",
            "API_KEYS": correct_key,
            "ASSET_SIGNING_KEY": "s" * 32,
            "RATE_LIMIT_ENABLED": "false",
            "ANSWER_EVALUATION_API_BASE": base_url,
            "PYTHONUNBUFFERED": "1",
        }
    )
    env.pop("QUALITY_API_KEY", None)
    env.pop("QUALITY_API_KEY_FILE", None)
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "src.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=PROJECT_ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        try:
            _wait_for_health(base_url, process, log_path)

            for key_file, expected_access in (
                (correct_key_file, True),
                (wrong_key_file, False),
            ):
                verification = subprocess.run(
                    [
                        sys.executable,
                        "scripts/verify_quality.py",
                        "--skip-tests",
                        "--skip-frontend",
                        "--skip-evaluations",
                        "--api-base",
                        base_url,
                        "--api-key-file",
                        str(key_file),
                    ],
                    cwd=PROJECT_ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                    timeout=30,
                    creationflags=creationflags,
                )
                assert verification.returncode == 1
                report_path = data_dir / "audit" / "reports" / "verification_latest.json"
                report_text = report_path.read_text(encoding="utf-8")
                report = json.loads(report_text)
                credential = next(
                    step for step in report["steps"] if step["name"] == "API 凭据加载"
                )
                access = next(
                    step for step in report["steps"] if step["name"] == "目标 API 鉴权预检"
                )
                assert credential["credential_source"] == "command_file"
                assert credential["credential_supplied"] is True
                assert access["ok"] is expected_access
                if not expected_access:
                    assert access["status_code"] == 401
                combined_output = report_text + verification.stdout + verification.stderr
                assert correct_key not in combined_output
                assert wrong_key not in combined_output
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
