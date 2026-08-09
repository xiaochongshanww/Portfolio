from __future__ import annotations

import json
import sys
from importlib import metadata
from pathlib import Path

import pytest
from src.doctor import __main__ as doctor_cli
from src.doctor import checks as doctor


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_project(root: Path, *, profile: str) -> dict[str, str]:
    _write(
        root / "dependency-lock.json",
        json.dumps({"schema_version": 1, "python_version": "3.11"}),
    )
    _write(root / "requirements-runtime.in", "fastapi\nuvicorn[standard]\n")
    _write(
        root / "requirements-runtime.txt",
        "fastapi==1.2.3 \\\n+    --hash=sha256:test\nuvicorn==4.5.6 \\\n+    --hash=sha256:test\n",
    )
    versions = {"fastapi": "1.2.3", "uvicorn": "4.5.6"}
    if profile == "build":
        _write(
            root / "requirements-parser.in", "-r requirements-runtime.in\nmagic-pdf[full]==1.3.12\n"
        )
        _write(
            root / "requirements-parser.txt",
            "fastapi==1.2.3 \\\n+    --hash=sha256:test\nuvicorn==4.5.6 \\\n+    --hash=sha256:test\nmagic-pdf==1.3.12 \\\n+    --hash=sha256:test\n",
        )
        versions["magic-pdf"] = "1.3.12"
        for name in ("processed", "images", "mineru", "audit", "corrections"):
            (root / "data" / name).mkdir(parents=True)
        _write(root / "data" / "raw" / "sample.pdf", "%PDF-test")
        _write(root / "data" / "metadata" / "specs.json", "{}")
    else:
        _write(root / "frontend" / "dist" / "index.html", "<html></html>")
        _write(
            root / "data" / "manifest.json",
            json.dumps({"document_count": 1, "chunk_count": 2, "data_version_hash": "abc"}),
        )
        _write(root / "data" / "metadata" / "specs.json", '[{"code": "TEST"}]')
        _write(root / "db" / "chroma.sqlite3", "db")
    return versions


def _installed(versions: dict[str, str]):
    def lookup(name: str) -> str:
        if name not in versions:
            raise metadata.PackageNotFoundError(name)
        return versions[name]

    return lookup


def _check(report: dict, check_id: str) -> dict:
    return next(item for item in report["checks"] if item["id"] == check_id)


def test_runtime_profile_passes_with_complete_static_environment(tmp_path: Path):
    versions = _create_project(tmp_path, profile="runtime")
    report = doctor.run_doctor(
        profile="runtime",
        project_root=tmp_path,
        environment={"ZHIPUAI_API_KEY": "secret-z", "MIMO_API_KEY": "secret-m"},
        version_info=(3, 11, 9),
        system="Windows",
        machine="AMD64",
        installed_version=_installed(versions),
        config_probe=lambda *_args: (True, []),
    )

    assert report["ok"] is True
    assert report["status"] == "ready"
    assert report["summary"] == {
        "total": 9,
        "passed": 9,
        "warnings": 0,
        "failed": 0,
        "failed_required": 0,
    }
    assert {item["id"] for item in report["checks"]} == {
        "python_version",
        "platform_compatibility",
        "locked_dependencies",
        "application_configuration",
        "required_credentials",
        "frontend_assets",
        "active_manifest",
        "active_database",
        "source_metadata",
    }
    rendered = json.dumps(report, ensure_ascii=False)
    assert "secret-z" not in rendered
    assert "secret-m" not in rendered


def test_build_profile_passes_and_warns_when_ai_review_key_is_absent(tmp_path: Path):
    versions = _create_project(tmp_path, profile="build")
    report = doctor.run_doctor(
        profile="build",
        project_root=tmp_path,
        environment={"ZHIPUAI_API_KEY": "secret-z"},
        version_info=(3, 11, 4),
        system="Linux",
        machine="x86_64",
        installed_version=_installed(versions),
        config_probe=lambda *_args: (True, []),
        parser_probe=lambda: {
            "implementation": "magic-pdf",
            "version": "1.3.12",
            "compatibility": "verified",
            "verified": True,
        },
    )

    assert report["ok"] is True
    assert report["summary"]["warnings"] == 1
    assert _check(report, "ai_review_credential")["status"] == "warning"
    assert _check(report, "pdf_parser")["status"] == "passed"
    assert "active_manifest" not in {item["id"] for item in report["checks"]}


def test_required_failures_have_stable_ids_and_summary(tmp_path: Path):
    versions = _create_project(tmp_path, profile="runtime")
    versions["fastapi"] = "9.9.9"
    (tmp_path / "frontend" / "dist" / "index.html").unlink()
    (tmp_path / "data" / "manifest.json").unlink()
    report = doctor.run_doctor(
        profile="runtime",
        project_root=tmp_path,
        environment={},
        version_info=(3, 12, 1),
        system="Darwin",
        machine="arm64",
        installed_version=_installed(versions),
        config_probe=lambda *_args: (False, ["RAG_TOP_K 必须在 1 到 100 之间"]),
    )

    assert report["ok"] is False
    assert report["status"] == "not_ready"
    assert report["summary"]["failed_required"] == 6
    assert report["summary"]["warnings"] == 1
    for check_id in (
        "python_version",
        "locked_dependencies",
        "application_configuration",
        "required_credentials",
        "frontend_assets",
        "active_manifest",
    ):
        assert _check(report, check_id)["status"] == "failed"
    assert _check(report, "platform_compatibility")["status"] == "warning"


def test_missing_distribution_is_reported_without_crashing(tmp_path: Path):
    versions = _create_project(tmp_path, profile="runtime")
    del versions["uvicorn"]
    report = doctor.run_doctor(
        project_root=tmp_path,
        environment={"ZHIPUAI_API_KEY": "z", "MIMO_API_KEY": "m"},
        version_info=(3, 11, 0),
        system="Windows",
        machine="AMD64",
        installed_version=_installed(versions),
        config_probe=lambda *_args: (True, []),
    )

    dependency_check = _check(report, "locked_dependencies")
    assert dependency_check["status"] == "failed"
    assert dependency_check["details"]["missing"] == ["uvicorn"]


def test_corrupt_manifest_fields_become_diagnostic_failure(tmp_path: Path):
    versions = _create_project(tmp_path, profile="runtime")
    _write(
        tmp_path / "data" / "manifest.json",
        json.dumps(
            {"document_count": "broken", "chunk_count": "broken", "data_version_hash": "abc"}
        ),
    )

    report = doctor.run_doctor(
        project_root=tmp_path,
        environment={"ZHIPUAI_API_KEY": "z", "MIMO_API_KEY": "m"},
        version_info=(3, 11, 0),
        system="Windows",
        machine="AMD64",
        installed_version=_installed(versions),
        config_probe=lambda *_args: (True, []),
    )

    assert report["ok"] is False
    assert _check(report, "active_manifest")["status"] == "failed"


def test_parser_failure_is_a_required_build_failure(tmp_path: Path):
    versions = _create_project(tmp_path, profile="build")

    def unavailable():
        raise doctor.ParserUnavailableError("not installed")

    report = doctor.run_doctor(
        profile="build",
        project_root=tmp_path,
        environment={"ZHIPUAI_API_KEY": "z", "MIMO_API_KEY": "m"},
        version_info=(3, 11, 0),
        system="Linux",
        machine="x86_64",
        installed_version=_installed(versions),
        config_probe=lambda *_args: (True, []),
        parser_probe=unavailable,
    )

    assert report["ok"] is False
    assert _check(report, "pdf_parser")["status"] == "failed"


def test_doctor_does_not_modify_project_tree(tmp_path: Path):
    versions = _create_project(tmp_path, profile="runtime")
    before = {
        path.relative_to(tmp_path).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    doctor.run_doctor(
        project_root=tmp_path,
        environment={"ZHIPUAI_API_KEY": "z", "MIMO_API_KEY": "m"},
        version_info=(3, 11, 0),
        system="Linux",
        machine="x86_64",
        installed_version=_installed(versions),
        config_probe=lambda *_args: (True, []),
    )

    after = {
        path.relative_to(tmp_path).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_sensitive_environment_values_are_redacted():
    text = "bad key top-secret and token abc-123"
    redacted = doctor._redact_sensitive_text(
        text,
        {"MIMO_API_KEY": "top-secret", "ACCESS_TOKEN": "abc-123", "NORMAL": "visible"},
    )

    assert redacted == "bad key [REDACTED] and token [REDACTED]"


def test_text_renderer_is_human_readable_and_keeps_quality_boundary(tmp_path: Path):
    versions = _create_project(tmp_path, profile="runtime")
    report = doctor.run_doctor(
        project_root=tmp_path,
        environment={"ZHIPUAI_API_KEY": "z", "MIMO_API_KEY": "m"},
        version_info=(3, 11, 0),
        system="Windows",
        machine="AMD64",
        installed_version=_installed(versions),
        config_probe=lambda *_args: (True, []),
    )

    rendered = doctor.render_text(report)
    assert "结果：可继续" in rendered
    assert "[通过] python_version" in rendered
    assert "环境自检通过不等于 API /ready 或发布质量门禁通过" in rendered


@pytest.mark.parametrize(("ok", "expected_exit"), [(True, 0), (False, 1)])
def test_cli_uses_report_status_as_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    ok: bool,
    expected_exit: int,
):
    report = {
        "schema_version": 1,
        "ok": ok,
        "status": "ready" if ok else "not_ready",
        "profile": "runtime",
        "checked_at": "2026-08-09T00:00:00+00:00",
        "platform": {"python": "3.11.0", "system": "Windows", "machine": "AMD64"},
        "summary": {
            "total": 0,
            "passed": 0,
            "warnings": 0,
            "failed": 0 if ok else 1,
            "failed_required": 0 if ok else 1,
        },
        "checks": [],
    }
    monkeypatch.setattr(doctor_cli, "run_doctor", lambda **_kwargs: report)
    monkeypatch.setattr(sys, "argv", ["doctor", "--format", "json"])

    with pytest.raises(SystemExit) as raised:
        doctor_cli.main()

    assert raised.value.code == expected_exit
    assert json.loads(capsys.readouterr().out)["ok"] is ok


@pytest.mark.parametrize("profile", ["invalid", "", "Runtime"])
def test_unknown_profile_is_rejected(profile: str, tmp_path: Path):
    with pytest.raises(ValueError, match="profile"):
        doctor.run_doctor(profile=profile, project_root=tmp_path)
