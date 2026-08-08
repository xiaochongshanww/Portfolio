from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from src.pipeline.knowledge_package import import_runtime_package, validate_runtime_package


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RuntimePackageColdStartError(RuntimeError):
    pass


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _read_json(base_url: str, path: str) -> dict[str, Any]:
    try:
        with urlopen(f"{base_url}{path}", timeout=5) as response:  # noqa: S310 - fixed loopback URL
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimePackageColdStartError(f"{path} 返回 HTTP {exc.code}: {details}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimePackageColdStartError(f"{path} 请求失败: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimePackageColdStartError(f"{path} 未返回 JSON 对象")
    return payload


def _wait_for_health(process: subprocess.Popen[Any], base_url: str, log_path: Path, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        return_code = process.poll()
        if return_code is not None:
            details = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
            raise RuntimePackageColdStartError(f"API 在启动期间退出（{return_code}）: {details}")
        try:
            health = _read_json(base_url, "/health")
            if health.get("status") == "ok":
                return
            last_error = f"非预期健康响应: {health}"
        except RuntimePackageColdStartError as exc:
            last_error = str(exc)
        time.sleep(0.25)
    details = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
    raise RuntimePackageColdStartError(f"API 启动超时: {last_error}; logs={details}")


def _stop_process(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def verify_imported_runtime_api(
    data_dir: Path,
    validation: dict[str, Any],
    *,
    expected_db_dir: Path,
    startup_timeout: float = 60,
) -> dict[str, Any]:
    data_dir = data_dir.resolve()
    expected_db_dir = expected_db_dir.resolve()
    expected_count = int(validation.get("chunk_count", 0))
    expected_document_count = int(validation.get("document_count", 0))
    if expected_count <= 0:
        raise RuntimePackageColdStartError("知识包没有可验证的 chunk")

    with tempfile.TemporaryDirectory(prefix="knowledge-package-api-") as temporary_name:
        runtime_root = Path(temporary_name)
        log_path = runtime_root / "api.log"
        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"
        environment = os.environ.copy()
        environment.update(
            {
                "DATA_DIR": str(data_dir),
                "ZHIPUAI_API_KEY": "cold-start-zhipu-key",
                "MIMO_API_KEY": "cold-start-mimo-key",
                "API_AUTH_ENABLED": "false",
                "RATE_LIMIT_ENABLED": "false",
                "ANONYMIZED_TELEMETRY": "FALSE",
                "PYTHONIOENCODING": "utf-8",
                "PYTHONPATH": os.pathsep.join(
                    filter(None, (str(PROJECT_ROOT), environment.get("PYTHONPATH", "")))
                ),
            }
        )
        for name in ("DB_DIR", "IMG_DIR", "SOURCE_METADATA_PATH"):
            environment.pop(name, None)

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
                    "--log-level",
                    "warning",
                ],
                cwd=runtime_root,
                env=environment,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
            try:
                _wait_for_health(process, base_url, log_path, startup_timeout)
                ready = _read_json(base_url, "/ready")
                documents = _read_json(base_url, "/knowledge/documents")
                active = _read_json(base_url, "/admin/active-db")
            finally:
                _stop_process(process)

    loaded_db_dir = Path(str(active.get("loaded_db_dir") or "")).resolve()
    checks = {
        "ready": ready.get("ready") is True,
        "collection_count": int(active.get("collection_count", -1)) == expected_count,
        "manifest_chunk_count": int(documents.get("chunk_count", -1)) == expected_count,
        "document_count": int(documents.get("document_count", -1)) == expected_document_count,
        "data_version_hash": documents.get("data_version_hash") == validation.get("data_version_hash"),
        "active_data_version_hash": active.get("data_version_hash") == validation.get("data_version_hash"),
        "active_package_id": active.get("package_id") == validation.get("package_id"),
        "loaded_expected_db": loaded_db_dir == expected_db_dir,
        "loaded_within_data_dir": loaded_db_dir.is_relative_to(data_dir),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    if failed_checks:
        raise RuntimePackageColdStartError(
            "API 冷启动断言失败: "
            + ", ".join(failed_checks)
            + f"; ready={ready}; documents={documents}; active={active}"
        )
    return {
        "checks": checks,
        "loaded_db_dir": str(loaded_db_dir),
        "package_id": active.get("package_id"),
        "data_version_hash": documents.get("data_version_hash"),
        "chunk_count": int(documents.get("chunk_count", -1)),
        "document_count": int(documents.get("document_count", -1)),
    }


def verify_runtime_package_cold_start(
    package_path: Path,
    *,
    expected_source_platform: str = "",
    require_cross_platform: bool = False,
    startup_timeout: float = 60,
) -> dict[str, Any]:
    package_path = package_path.resolve()
    validation = validate_runtime_package(package_path)
    compatibility = validation.get("compatibility", {})
    source_platform = str(compatibility.get("platform") or "").lower()
    target_platform = platform.system().lower()
    if expected_source_platform and source_platform != expected_source_platform.lower():
        raise RuntimePackageColdStartError(
            f"知识包来源平台不匹配: expected={expected_source_platform.lower()}, actual={source_platform}"
        )
    if require_cross_platform and source_platform == target_platform:
        raise RuntimePackageColdStartError(
            f"要求跨平台冷启动，但来源和目标均为 {target_platform}"
        )

    with tempfile.TemporaryDirectory(prefix="knowledge-package-api-") as temporary_name:
        runtime_root = Path(temporary_name)
        data_dir = runtime_root / "runtime-data"
        imported = import_runtime_package(package_path, data_dir=data_dir)
        expected_db_dir = Path(imported["active_db_dir"]).resolve()
        runtime_result = verify_imported_runtime_api(
            data_dir,
            validation,
            expected_db_dir=expected_db_dir,
            startup_timeout=startup_timeout,
        )

    return {
        "ok": True,
        "package": str(package_path),
        "package_id": validation["package_id"],
        "source_platform": source_platform,
        "target_platform": target_platform,
        "cross_platform": source_platform != target_platform,
        "chunk_count": int(validation.get("chunk_count", 0)),
        "document_count": int(validation.get("document_count", 0)),
        "data_version_hash": validation["data_version_hash"],
        "checks": runtime_result["checks"],
        "external_model_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导入运行知识包并在隔离数据根冷启动 API")
    parser.add_argument("--package", required=True, type=Path, help="知识包 ZIP 文件")
    parser.add_argument("--expect-source-platform", default="", help="要求的来源平台")
    parser.add_argument("--require-cross-platform", action="store_true", help="要求来源平台与本机不同")
    parser.add_argument("--startup-timeout", type=float, default=60, help="API 启动超时秒数")
    args = parser.parse_args()
    try:
        result = verify_runtime_package_cold_start(
            args.package,
            expected_source_platform=args.expect_source_platform,
            require_cross_platform=args.require_cross_platform,
            startup_timeout=args.startup_timeout,
        )
    except Exception as exc:
        print(
            json.dumps(
                {"ok": False, "error": type(exc).__name__, "message": str(exc)},
                ensure_ascii=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
