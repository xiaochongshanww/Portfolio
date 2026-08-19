import json
import subprocess
from pathlib import Path

import pytest
from src.pipeline import builder
from src.pipeline.metadata import SpecMetadata
from src.pipeline.parsers.base import ParserUnavailableError
from src.pipeline.parsers.mineru import (
    MineruParser,
    ParserCompatibilityError,
    probe_mineru_cli,
)


def _completed(
    stdout: str = "", stderr: str = "", returncode: int = 0
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["parser", "--version"], returncode, stdout, stderr)


def test_verified_magic_pdf_version_is_accepted(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "src.pipeline.parsers.mineru.shutil.which", lambda _binary: "/tools/magic-pdf"
    )
    monkeypatch.setattr(
        "src.pipeline.parsers.mineru.subprocess.run",
        lambda *_args, **_kwargs: _completed(stdout="magic-pdf, version 1.3.12\n"),
    )

    probe = probe_mineru_cli("magic-pdf")

    assert probe.implementation == "magic-pdf"
    assert probe.version == "1.3.12"
    assert probe.compatibility == "verified"
    assert probe.verified is True
    assert probe.policy == "strict"


def test_unverified_new_mineru_is_rejected_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("src.pipeline.parsers.mineru.shutil.which", lambda _binary: "/tools/mineru")
    monkeypatch.setattr(
        "src.pipeline.parsers.mineru.subprocess.run",
        lambda *_args, **_kwargs: _completed(stdout="mineru version 3.4.4"),
    )

    with pytest.raises(ParserCompatibilityError, match="未验证.*mineru 3.4.4"):
        probe_mineru_cli("mineru")


def test_allow_unverified_policy_preserves_warning(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("src.pipeline.parsers.mineru.shutil.which", lambda _binary: "/tools/mineru")
    monkeypatch.setattr(
        "src.pipeline.parsers.mineru.subprocess.run",
        lambda *_args, **_kwargs: _completed(stderr="mineru, version 3.4.4"),
    )

    probe = probe_mineru_cli("mineru", policy="allow-unverified")

    assert probe.verified is False
    assert probe.compatibility == "unverified"
    assert probe.policy == "allow-unverified"
    assert "magic-pdf 1.3.12" in probe.warning


def test_invalid_compatibility_policy_is_rejected_before_execution(monkeypatch: pytest.MonkeyPatch):
    executed = False

    def unexpected_run(*_args, **_kwargs):
        nonlocal executed
        executed = True
        return _completed()

    monkeypatch.setattr("src.pipeline.parsers.mineru.subprocess.run", unexpected_run)

    with pytest.raises(ParserCompatibilityError, match="MINERU_COMPATIBILITY_POLICY"):
        probe_mineru_cli("magic-pdf", policy="permissive")

    assert executed is False


@pytest.mark.parametrize(
    ("completed", "message"),
    [
        (_completed(stderr="failed", returncode=2), "版本探测失败"),
        (_completed(stdout="version unknown"), "无法识别"),
    ],
)
def test_version_probe_rejects_invalid_results(
    monkeypatch: pytest.MonkeyPatch,
    completed: subprocess.CompletedProcess[str],
    message: str,
):
    monkeypatch.setattr("src.pipeline.parsers.mineru.shutil.which", lambda _binary: "/tools/parser")
    monkeypatch.setattr(
        "src.pipeline.parsers.mineru.subprocess.run", lambda *_args, **_kwargs: completed
    )

    with pytest.raises(ParserUnavailableError, match=message):
        probe_mineru_cli("parser")


def test_version_probe_rejects_missing_cli(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("src.pipeline.parsers.mineru.shutil.which", lambda _binary: None)

    with pytest.raises(ParserUnavailableError, match="requirements-parser.txt"):
        probe_mineru_cli("missing-parser")


def test_version_probe_rejects_timeout(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("src.pipeline.parsers.mineru.shutil.which", lambda _binary: "/tools/parser")

    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(["parser", "--version"], 1)

    monkeypatch.setattr("src.pipeline.parsers.mineru.subprocess.run", timeout)

    with pytest.raises(ParserUnavailableError, match="版本探测超时"):
        probe_mineru_cli("parser", timeout_seconds=1)


def test_parser_compatibility_failure_preserves_existing_document_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    parser = MineruParser(tmp_path / "mineru")
    pdf_path = tmp_path / "existing.pdf"
    doc_dir = parser.output_dir / "existing"
    doc_dir.mkdir(parents=True)
    marker = doc_dir / "keep.txt"
    marker.write_text("existing", encoding="utf-8")

    def reject():
        raise ParserCompatibilityError("unsupported parser")

    monkeypatch.setattr(parser, "probe", reject)

    with pytest.raises(ParserCompatibilityError, match="unsupported"):
        parser.parse(pdf_path, tmp_path / "images")

    assert marker.read_text(encoding="utf-8") == "existing"


def test_parser_records_cli_compatibility_in_artifact_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    resolved = str((tmp_path / "magic-pdf").resolve())
    monkeypatch.setattr("src.pipeline.parsers.mineru.shutil.which", lambda _binary: resolved)

    def fake_run(command: list[str], **_kwargs):
        if command[-1] == "--version":
            return _completed(stdout="magic-pdf, version 1.3.12")
        raw_dir = Path(command[command.index("-o") + 1])
        output = raw_dir / "document" / "auto"
        output.mkdir(parents=True)
        (output / "document_content_list.json").write_text(
            json.dumps([{"type": "text", "text": "正文", "page_idx": 0}]),
            encoding="utf-8",
        )
        (output / "document.md").write_text("正文", encoding="utf-8")
        return _completed()

    monkeypatch.setattr("src.pipeline.parsers.mineru.subprocess.run", fake_run)
    parser = MineruParser(tmp_path / "mineru")
    result = parser.parse(tmp_path / "document.pdf", tmp_path / "images")

    assert result.metadata["parser_cli"]["verified"] is True
    assert result.metadata["parser_cli"]["implementation"] == "magic-pdf"
    artifact_index = json.loads(
        (tmp_path / "mineru" / "document" / "artifacts.json").read_text(encoding="utf-8")
    )
    assert artifact_index["metadata"]["parser_cli"]["compatibility"] == "verified"
    assert artifact_index["metadata"]["parser_cli"]["resolved_binary"] == resolved


def test_unverified_parser_run_is_audited_in_artifact_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    resolved = str((tmp_path / "mineru").resolve())
    monkeypatch.setattr("src.pipeline.parsers.mineru.shutil.which", lambda _binary: resolved)

    def fake_run(command: list[str], **_kwargs):
        if command[-1] == "--version":
            return _completed(stdout="mineru, version 3.4.4")
        raw_dir = Path(command[command.index("-o") + 1])
        output = raw_dir / "document" / "auto"
        output.mkdir(parents=True)
        (output / "document_content_list.json").write_text(
            json.dumps([{"type": "text", "text": "试验正文", "page_idx": 0}]),
            encoding="utf-8",
        )
        (output / "document.md").write_text("试验正文", encoding="utf-8")
        return _completed()

    monkeypatch.setattr("src.pipeline.parsers.mineru.subprocess.run", fake_run)
    parser = MineruParser(
        tmp_path / "outputs",
        binary="mineru",
        compatibility_policy="allow-unverified",
    )

    result = parser.parse(tmp_path / "document.pdf", tmp_path / "images")
    artifact_index = json.loads(
        (tmp_path / "outputs" / "document" / "artifacts.json").read_text(encoding="utf-8")
    )

    assert result.metadata["parser_cli"]["compatibility"] == "unverified"
    assert result.metadata["parser_cli"]["warning"]
    assert artifact_index["metadata"]["parser_cli"]["verified"] is False
    assert artifact_index["metadata"]["parser_cli"]["policy"] == "allow-unverified"


def test_build_preflight_failure_happens_before_output_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source = tmp_path / "raw"
    source.mkdir()
    cleanup_called = False

    def reject(_backend: str):
        raise builder.BuildPreflightError("incompatible parser")

    def mark_cleanup(**_kwargs):
        nonlocal cleanup_called
        cleanup_called = True

    monkeypatch.setattr(builder, "validate_parser_backend", reject)
    monkeypatch.setattr(builder, "clean_generated_outputs", mark_cleanup)
    monkeypatch.setenv("ZHIPUAI_API_KEY", "test-key")

    with pytest.raises(builder.BuildPreflightError, match="incompatible"):
        builder.rebuild(source)

    assert cleanup_called is False


def test_production_source_selection_excludes_test_fixtures():
    production = Path("production.pdf")
    fixture = Path("test_image.pdf")
    metadata = {
        production.name: SpecMetadata(
            source_file=production.name,
            code="GB 50009-2012",
            name="建筑结构荷载规范",
        ),
        fixture.name: SpecMetadata(
            source_file=fixture.name,
            code="TEST",
            name="测试图片文档",
            status="test",
        ),
    }

    selected, excluded = builder.select_production_sources([production, fixture], metadata)

    assert selected == [production]
    assert excluded == [fixture.name]


def test_build_manifest_records_parser_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source = tmp_path / "raw"
    source.mkdir()
    parser_environment = {
        "backend": "mineru",
        "implementation": "magic-pdf",
        "version": "1.3.12",
        "compatibility": "verified",
        "verified": True,
        "policy": "strict",
    }
    monkeypatch.setattr(builder, "validate_parser_backend", lambda _backend: parser_environment)
    monkeypatch.setenv("ZHIPUAI_API_KEY", "test-key")
    monkeypatch.setattr("src.pipeline.load_to_db.load_chunks_to_db", lambda *_args, **_kwargs: 0)

    manifest = builder.rebuild(
        source,
        db_dir=tmp_path / "db",
        manifest_path=tmp_path / "manifest.json",
        processed_dir=tmp_path / "processed",
        images_dir=tmp_path / "images",
        mineru_output_dir=tmp_path / "mineru",
        audit_dir=tmp_path / "audit",
    )

    assert manifest["build_params"]["parser_environment"] == parser_environment


def test_parser_status_returns_structured_environment(monkeypatch: pytest.MonkeyPatch):
    expected = {
        "backend": "mineru",
        "implementation": "magic-pdf",
        "version": "1.3.12",
        "compatibility": "verified",
        "verified": True,
    }
    monkeypatch.setattr(builder, "validate_parser_backend", lambda _backend: expected)

    assert builder.parser_status("mineru") == {
        "ok": True,
        "parser_environment": expected,
    }
