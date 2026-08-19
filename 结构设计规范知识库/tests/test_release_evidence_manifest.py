import json
from pathlib import Path

import pytest
from scripts.create_release_evidence_manifest import build_manifest
from scripts.validate_release_evidence_manifest import (
    EvidenceManifestError,
    render_markdown,
    validate_release_evidence_manifest,
)


def _write_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "release-evidence.json"
    path.write_text(json.dumps(build_manifest(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_generator_includes_only_production_sources():
    manifest = build_manifest()

    assert manifest["schema_version"] == 1
    assert manifest["status"] == "draft"
    assert len(manifest["sources"]) == 5
    assert all(
        source["evidence"]["acquisition"]["status"] == "pending" for source in manifest["sources"]
    )
    assert "test_image.pdf" not in {source["source_file"] for source in manifest["sources"]}


def test_draft_manifest_is_valid_but_not_ready(tmp_path):
    result = validate_release_evidence_manifest(_write_manifest(tmp_path))

    assert result["ok"] is True
    assert result["ready"] is False
    assert result["source_count"] == 5
    assert any(item["id"] == "trial" for item in result["gaps"])
    assert any(item["id"] == "decisions.D-001" for item in result["gaps"])


def test_manifest_rejects_secret_fields(tmp_path):
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["api_key"] = "sk-abcdefghijklmnopqrstuvwxyz"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceManifestError, match="禁止保存密钥"):
        validate_release_evidence_manifest(path)


def test_manifest_rejects_source_set_drift(tmp_path):
    path = _write_manifest(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["sources"] = payload["sources"][:-1]
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceManifestError, match="一一对应"):
        validate_release_evidence_manifest(path)


def test_render_markdown_lists_open_gaps(tmp_path):
    result = validate_release_evidence_manifest(_write_manifest(tmp_path))

    markdown = render_markdown(result)

    assert "# 受控发布证据包索引校验" in markdown
    assert "## 待收口项" in markdown
    assert "sources[0].evidence.acquisition" in markdown
    assert "decisions.D-001" in markdown
