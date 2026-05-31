import json
from pathlib import Path

from src.pipeline.chunks import normalize_chunks
from src.pipeline.artifacts import require_artifacts, scan_mineru_artifacts
from src.pipeline.manifest import build_manifest
from src.pipeline.metadata import apply_metadata_override, parse_spec_filename
from src.pipeline.parsers.mineru import content_list_to_elements
from src.pipeline.parsers.base import ParseResult
from src.pipeline.process_documents import chunk_to_paragraphs, process_pdf


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


def test_mineru_content_list_converts_tables_and_formulas(tmp_path: Path):
    artifact_dir = tmp_path / "mineru" / "doc"
    image_dir = tmp_path / "images"
    (artifact_dir / "images").mkdir(parents=True)
    (artifact_dir / "images" / "table.jpg").write_bytes(b"img")
    content = [
        {"type": "text", "text": "3.1.1 基本规定", "text_level": 1, "page_idx": 0},
        {"type": "text", "text": "结构设计应符合本规范。", "page_idx": 0},
        {
            "type": "table",
            "img_path": "images/table.jpg",
            "table_caption": ["表 3.1.1 荷载组合"],
            "table_body": "<table><tr><td>值</td></tr></table>",
            "page_idx": 1,
        },
        {"type": "equation", "text": "$$N=\\gamma G$$", "page_idx": 1},
    ]

    elements = content_list_to_elements(content, artifact_dir, image_dir, "doc")
    chunks = chunk_to_paragraphs(elements)
    normalized = normalize_chunks(chunks, parse_spec_filename("GB 50009-2012_.建筑结构荷载规范.pdf"))

    assert elements[0]["type"] == "Title"
    assert any(element["chunk_type"] == "table" for element in elements)
    assert any(element["chunk_type"] == "formula" for element in elements)
    assert any(chunk["chunk_type"] in {"table", "formula"} for chunk in normalized)
    assert list(image_dir.glob("doc_mineru_*.jpg"))


def test_mineru_artifact_scan_tracks_required_and_optional_outputs(tmp_path: Path):
    doc_dir = tmp_path / "data" / "mineru" / "doc"
    raw = doc_dir / "raw"
    (raw / "images").mkdir(parents=True)
    (raw / "doc_content_list.json").write_text("[]", encoding="utf-8")
    (raw / "doc.md").write_text("# doc", encoding="utf-8")
    (raw / "doc_middle.json").write_text("{}", encoding="utf-8")
    (raw / "doc_model.json").write_text("{}", encoding="utf-8")
    (raw / "images" / "a.png").write_bytes(b"img")

    artifacts = scan_mineru_artifacts(doc_dir)
    kinds = {item["kind"] for item in artifacts if item["status"] == "ok"}

    assert {"content_list", "markdown", "middle", "model", "media"}.issubset(kinds)
    assert all(item["sha256"] for item in artifacts if item["status"] == "ok")
    require_artifacts(artifacts)


def test_mineru_artifact_scan_marks_missing_required_outputs(tmp_path: Path):
    doc_dir = tmp_path / "data" / "mineru" / "doc"
    doc_dir.mkdir(parents=True)

    artifacts = scan_mineru_artifacts(doc_dir)
    missing_required = [item["kind"] for item in artifacts if item["required"] and item["status"] == "missing"]

    assert missing_required == ["content_list", "markdown"]
    try:
        require_artifacts(artifacts)
    except RuntimeError as exc:
        assert "content_list" in str(exc)
    else:
        raise AssertionError("required artifact validation should fail")


def test_process_pdf_writes_quality_report_shape(tmp_path: Path):
    class FakeParser:
        name = "mineru"

        def parse(self, pdf_path: Path, image_dir: Path):
            return ParseResult(
                elements=[
                    {"type": "Title", "text": "表 1 测试表", "page": 1, "img": "table.png", "chunk_type": "table"},
                    {"type": "Text", "text": "x", "page": 1, "img": "table.png", "chunk_type": "table"},
                ],
                artifacts=[
                    {"kind": "content_list", "required": True, "status": "ok"},
                    {"kind": "middle", "required": False, "status": "missing"},
                ],
                metadata={"parser_backend": "mineru"},
            )

    pdf = tmp_path / "GB 50009-2012_.建筑结构荷载规范.pdf"
    pdf.write_bytes(b"pdf")
    result = process_pdf(pdf, parse_spec_filename(pdf.name), tmp_path / "processed", tmp_path / "images", FakeParser())

    assert result["quality"]["table_count"] == 2
    assert result["quality"]["missing_artifacts"] == ["middle"]
    assert result["chunks"][0]["chunk_type"] == "table"


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
        "artifacts_by_file": {
            pdf.name: [
                {
                    "kind": "content_list",
                    "path": "data/mineru/doc/raw/doc_content_list.json",
                    "relative_path": "raw/doc_content_list.json",
                    "sha256": "abc",
                    "size_bytes": 2,
                    "required": True,
                    "status": "ok",
                }
            ]
        },
        "chunk_hashes_by_file": {pdf.name: ["chunk-a", "chunk-b"]},
        "build_params": {"mode": "rebuild"},
    }
    first = build_manifest(**kwargs)
    second = build_manifest(**kwargs)
    assert first["data_version_hash"] == second["data_version_hash"]
    assert first["documents"][0]["artifacts"][0]["kind"] == "content_list"
    assert first["documents"][0]["chunk_hashes"] == ["chunk-a", "chunk-b"]


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
    assert result["parser_backend"] == "mineru"
    assert result["document_count"] == 1
    assert not (tmp_path / "processed").exists()
