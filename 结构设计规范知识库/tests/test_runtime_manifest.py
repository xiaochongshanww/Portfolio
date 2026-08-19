import json
from pathlib import Path

from scripts.validate_runtime_manifest import validate_runtime_manifest


def _write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def _valid_runtime_files(tmp_path: Path) -> tuple[Path, Path]:
    manifest = _write_json(
        tmp_path / "manifest.json",
        {
            "documents": [
                {"source_file": "a.pdf", "chunk_count": 2},
                {"source_file": "b.pdf", "chunk_count": 1},
            ],
            "document_count": 2,
            "chunk_count": 3,
            "data_version_hash": "a" * 64,
        },
    )
    active = _write_json(
        tmp_path / "active_db.json",
        {
            "manifest": str(manifest),
            "data_version_hash": "a" * 64,
            "chunk_count": 3,
        },
    )
    return active, manifest


def test_current_runtime_manifest_is_consistent_after_repair():
    result = validate_runtime_manifest()

    assert result["ok"] is True
    assert result["issues"] == []
    assert result["document_count"] == 5
    assert result["chunk_sum"] == 1635
    assert result["declared_chunk_count"] == 1635


def test_runtime_manifest_accepts_matching_pointer_and_document_totals(tmp_path):
    active, manifest = _valid_runtime_files(tmp_path)

    result = validate_runtime_manifest(active, manifest)

    assert result["ok"] is True
    assert result["issues"] == []


def test_runtime_manifest_resolves_project_relative_pointer(tmp_path):
    data_dir = tmp_path / "data"
    manifest = _write_json(
        data_dir / "db_versions" / "candidate" / "manifest.json",
        {
            "documents": [{"source_file": "a.pdf", "chunk_count": 1}],
            "document_count": 1,
            "chunk_count": 1,
            "data_version_hash": "b" * 64,
        },
    )
    active = _write_json(
        data_dir / "active_db.json",
        {
            "manifest": "data/db_versions/candidate/manifest.json",
            "data_version_hash": "b" * 64,
            "chunk_count": 1,
        },
    )

    result = validate_runtime_manifest(active)

    assert result["ok"] is True
    assert Path(result["manifest_path"]) == manifest.resolve()
