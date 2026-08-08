import json
import os
import platform
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import scripts.verify_runtime_package_cold_start as cold_start_module
from scripts.create_portability_package import create_portability_package
from scripts.verify_runtime_package_cold_start import RuntimePackageColdStartError, verify_runtime_package_cold_start
from src.pipeline.knowledge_package import probe_runtime_package, validate_runtime_package


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_real_chroma_package_can_be_exported_imported_and_probed(tmp_path: Path):
    package = tmp_path / "跨平台知识包.zip"

    created = create_portability_package(package)
    validation = validate_runtime_package(package)
    probe = probe_runtime_package(package)
    cold_start = verify_runtime_package_cold_start(package)

    assert created["schema_version"] == 4
    assert validation["schema_version"] == 4
    assert validation["chunk_count"] == 3
    assert probe["expected_count"] == 3
    assert probe["actual_count"] == 3
    assert probe["source_machine"] == probe["target_machine"]
    assert probe["copied_asset_count"] == 3
    assert probe["warnings"] == []
    assert cold_start["ok"] is True
    assert cold_start["chunk_count"] == 3
    assert cold_start["document_count"] == 1
    assert cold_start["external_model_calls"] == 0
    assert all(cold_start["checks"].values())

    with zipfile.ZipFile(package) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("knowledge-package.json"))

    assert "runtime/structured_tables/表5.1.1-活荷载.json" in names
    assert "runtime/images/第1页-示意图.png" in names
    assert manifest["compatibility"]["machine"] in {"x86_64", "aarch64"}


def test_cross_platform_probe_requires_only_expected_os_warning(tmp_path: Path, monkeypatch):
    package = tmp_path / "foreign-platform.zip"
    local_platform = platform.system().lower()
    source_platform = "windows" if local_platform != "windows" else "linux"
    original_system = platform.system
    monkeypatch.setattr(
        "src.pipeline.knowledge_package.platform.system",
        lambda: source_platform.title(),
    )
    create_portability_package(package)
    monkeypatch.setattr("src.pipeline.knowledge_package.platform.system", original_system)

    probe = probe_runtime_package(
        package,
        expected_source_platform=source_platform,
        require_cross_platform=True,
    )

    assert probe["cross_platform"] is True
    assert probe["source_platform"] == source_platform
    assert probe["target_platform"] == local_platform
    assert len(probe["warnings"]) == 1
    assert probe["warnings"][0].startswith("操作系统不同:")


def test_api_cold_start_failure_stops_child_process(tmp_path: Path, monkeypatch):
    package = tmp_path / "cleanup-package.zip"
    create_portability_package(package)
    processes = []
    real_popen = cold_start_module.subprocess.Popen
    real_read_json = cold_start_module._read_json

    def tracking_popen(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        processes.append(process)
        return process

    def fail_after_start(base_url: str, path: str):
        if path == "/ready":
            raise RuntimePackageColdStartError("injected readiness failure")
        return real_read_json(base_url, path)

    monkeypatch.setattr(cold_start_module.subprocess, "Popen", tracking_popen)
    monkeypatch.setattr(cold_start_module, "_read_json", fail_after_start)

    with pytest.raises(RuntimePackageColdStartError, match="injected readiness failure"):
        verify_runtime_package_cold_start(package)

    assert len(processes) == 1
    assert processes[0].poll() is not None


def test_portability_cli_outputs_are_ascii_safe(tmp_path: Path):
    package = tmp_path / "中文兼容包.zip"
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "cp1252"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.create_portability_package",
            "--output",
            str(package),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="cp1252",
        errors="strict",
        cwd=PROJECT_ROOT,
        env=environment,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 4
    assert package.exists()

    validation = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.pipeline",
            "package-validate",
            "--package",
            str(package),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="cp1252",
        errors="strict",
        cwd=PROJECT_ROOT,
        env=environment,
        timeout=120,
    )

    assert validation.returncode == 0, validation.stderr
    assert json.loads(validation.stdout)["schema_version"] == 4
