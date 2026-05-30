import json
from pathlib import Path

from src.pipeline.chunks import normalize_chunks
from src.pipeline.manifest import build_manifest
from src.pipeline.metadata import apply_metadata_override, parse_spec_filename


def test_parse_spec_filename_with_version():
    spec = parse_spec_filename("GB 50011-2010_建筑抗震设计规范_2016年版.pdf")
    assert spec.code == "GB 50011-2010"
    assert spec.name == "建筑抗震设计规范"
    assert spec.version == "2016年版"
    assert spec.metadata_status == "complete"


def test_parse_spec_filename_without_version_and_leading_dot_name():
    spec = parse_spec_filename("GB 50009-2012_.建筑结构荷载规范.pdf")
    assert spec.code == "GB 50009-2012"
    assert spec.name == "建筑结构荷载规范"
    assert spec.version == ""


def test_parse_unstructured_filename_is_partial():
    spec = parse_spec_filename("unknown.pdf")
    assert spec.code == "unknown"
    assert spec.name == "unknown"


def test_metadata_override_wins():
    base = parse_spec_filename("GB 50009-2012_.建筑结构荷载规范.pdf")
    spec = apply_metadata_override(base, {"name": "覆盖名称", "status": "retired", "aliases": ["荷载"]})
    assert spec.name == "覆盖名称"
    assert spec.status == "retired"
    assert spec.aliases == ["荷载"]


def test_normalize_chunk_contains_required_metadata():
    spec = parse_spec_filename("GB 50011-2010_建筑抗震设计规范_2016年版.pdf")
    chunks = normalize_chunks(
        [{"title": "8.2.1 构件要求", "text": "8.2.1 应符合要求", "pages": [10], "images": ["a.png"]}],
        spec,
    )
    chunk = chunks[0]
    for key in ["source_file", "code", "name", "pages", "images", "chunk_id", "title", "text", "chunk_type"]:
        assert key in chunk
    assert chunk["clause_number"] == "8.2.1"


def test_manifest_hash_is_stable(tmp_path: Path):
    pdf = tmp_path / "GB 50011-2010_建筑抗震设计规范_2016年版.pdf"
    pdf.write_bytes(b"pdf")
    spec = parse_spec_filename(pdf.name)
    kwargs = {
        "pdf_files": [pdf],
        "metadata": {pdf.name: spec},
        "chunk_counts": {pdf.name: 2},
        "image_count": 1,
        "embedding_model": "embedding-2",
        "collection_name": "design_specs",
        "build_params": {"mode": "rebuild"},
    }
    first = build_manifest(**kwargs)
    second = build_manifest(**kwargs)
    assert first["data_version_hash"] == second["data_version_hash"]


def test_cli_status_without_manifest(tmp_path: Path, monkeypatch):
    from src.pipeline import builder

    monkeypatch.setattr(builder, "MANIFEST_PATH", tmp_path / "missing.json")
    result = builder.status()
    assert result["built"] is False


def test_dry_run_does_not_create_outputs(tmp_path: Path):
    from src.pipeline.builder import dry_run

    source = tmp_path / "raw"
    source.mkdir()
    (source / "GB 50011-2010_建筑抗震设计规范_2016年版.pdf").write_bytes(b"pdf")
    result = dry_run(source)
    assert result["mode"] == "dry-run"
    assert result["document_count"] == 1
    assert not (tmp_path / "processed").exists()
