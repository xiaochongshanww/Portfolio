from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, TextIO

import pytest
from src.app.core.openwebui_probe import OpenWebUIProbeError, load_probe_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _stop_process(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def _wait_for_health(process: subprocess.Popen[Any], base_url: str, log_path: Path) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.2)
    details = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
    raise AssertionError(f"API did not start: {details}")


def _start_api(
    runtime_root: Path,
    *,
    auth_enabled: bool,
) -> tuple[subprocess.Popen[Any], str, dict[str, str], Path, TextIO]:
    runtime_root.mkdir(parents=True, exist_ok=True)
    data_dir = runtime_root / "data"
    data_dir.mkdir()
    log_path = runtime_root / "api.log"
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    connection_key = "probe-connection-key-never-print"
    environment = os.environ.copy()
    environment.update(
        {
            "DATA_DIR": str(data_dir),
            "DB_DIR": str(data_dir / "db"),
            "SOURCE_METADATA_PATH": str(data_dir / "metadata" / "specs.json"),
            "API_AUTH_ENABLED": "true" if auth_enabled else "false",
            "API_KEYS": connection_key if auth_enabled else "",
            "OPENWEBUI_API_KEY": connection_key if auth_enabled else "",
            "MIMO_MODEL": "mimo-v2-omni",
            "ASSET_SIGNING_KEY": "s" * 32 if auth_enabled else "",
            "RATE_LIMIT_ENABLED": "false",
            "ANONYMIZED_TELEMETRY": "FALSE",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": os.pathsep.join(
                filter(None, (str(PROJECT_ROOT), environment.get("PYTHONPATH", "")))
            ),
        }
    )
    log_file = log_path.open("w", encoding="utf-8")
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
            "--log-level",
            "warning",
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_for_health(process, base_url, log_path)
    except Exception:
        _stop_process(process)
        log_file.close()
        raise
    return process, base_url, environment, log_path, log_file


@pytest.fixture(scope="module")
def authenticated_api(tmp_path_factory):
    process, base_url, environment, log_path, log_file = _start_api(
        tmp_path_factory.mktemp("openwebui-auth-api"),
        auth_enabled=True,
    )
    try:
        yield base_url, environment, log_path
    finally:
        _stop_process(process)
        log_file.close()


@pytest.fixture(scope="module")
def public_api(tmp_path_factory):
    process, base_url, environment, log_path, log_file = _start_api(
        tmp_path_factory.mktemp("openwebui-public-api"),
        auth_enabled=False,
    )
    try:
        yield base_url, environment, log_path
    finally:
        _stop_process(process)
        log_file.close()


def _run_probe(base_url: str, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    values = environment.copy()
    values["OPENAI_API_BASE_URLS"] = f"{base_url}/v1"
    values["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "src.app.core.openwebui_probe",
            "--attempts",
            "1",
            "--timeout-seconds",
            "3",
        ],
        cwd=PROJECT_ROOT,
        env=values,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=20,
    )


def test_probe_accepts_authenticated_openwebui_connection(authenticated_api):
    base_url, environment, _ = authenticated_api
    completed = _run_probe(base_url, environment)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["auth_enabled"] is True
    assert payload["credential_source"] == "OPENWEBUI_API_KEY"
    assert payload["checks"] == {
        "health": 200,
        "models": 200,
        "anonymous_admin": 401,
        "connection_admin": 200,
        "anonymous_chat": 401,
        "connection_chat": 422,
    }
    assert payload["external_model_calls"] == 0
    assert "probe-connection-key-never-print" not in completed.stdout + completed.stderr


def test_probe_accepts_authentication_disabled_without_key(public_api):
    base_url, environment, _ = public_api
    completed = _run_probe(base_url, environment)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["auth_enabled"] is False
    assert payload["credential_source"] == "not_required"
    assert payload["checks"]["anonymous_admin"] == 200
    assert payload["checks"]["anonymous_chat"] == 422


@pytest.mark.parametrize(
    ("connection_key", "api_keys", "message"),
    [
        ("", "accepted-key", "OPENWEBUI_API_KEY 不能为空"),
        ("wrong-key", "accepted-key", "必须与 API_KEYS 中的一项一致"),
        ("accepted-key", "", "API_KEYS 不能为空"),
    ],
)
def test_probe_fails_closed_for_missing_or_mismatched_credentials(
    connection_key: str,
    api_keys: str,
    message: str,
):
    secret_values = {connection_key, api_keys} - {""}
    environment = os.environ.copy()
    environment.update(
        {
            "API_AUTH_ENABLED": "true",
            "API_KEYS": api_keys,
            "OPENWEBUI_API_KEY": connection_key,
            "OPENAI_API_BASE_URLS": "http://127.0.0.1:9/v1",
        }
    )
    completed = _run_probe("http://127.0.0.1:9", environment)

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["ok"] is False
    assert message in payload["error"]
    for secret in secret_values:
        assert secret not in completed.stdout + completed.stderr


def test_probe_detects_target_authentication_state_mismatch(authenticated_api, public_api):
    authenticated_base, authenticated_environment, _ = authenticated_api
    public_base, public_environment, _ = public_api

    expects_auth = authenticated_environment.copy()
    expects_auth["OPENAI_API_BASE_URLS"] = f"{public_base}/v1"
    public_target = _run_probe(public_base, expects_auth)
    assert public_target.returncode == 1
    assert "匿名管理接口 状态不符" in json.loads(public_target.stdout)["error"]

    expects_public = public_environment.copy()
    expects_public["OPENAI_API_BASE_URLS"] = f"{authenticated_base}/v1"
    protected_target = _run_probe(authenticated_base, expects_public)
    assert protected_target.returncode == 1
    assert "匿名管理接口 状态不符" in json.loads(protected_target.stdout)["error"]
    assert "probe-connection-key-never-print" not in public_target.stdout + public_target.stderr


@pytest.mark.parametrize(
    "api_base",
    [
        "ftp://api.example.com/v1",
        "http://user:secret@api.example.com/v1",
        "http://api.example.com/api",
        "http://api-one/v1;http://api-two/v1",
    ],
)
def test_probe_rejects_unsafe_or_ambiguous_api_base(api_base: str):
    with pytest.raises(OpenWebUIProbeError):
        load_probe_config(
            api_base=api_base,
            environ={"API_AUTH_ENABLED": "false"},
        )


def test_probe_default_model_matches_api_default():
    config = load_probe_config(environ={"API_AUTH_ENABLED": "false"})

    assert config.expected_model == "mimo-v2.5"
