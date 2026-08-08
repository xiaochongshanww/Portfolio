import json
from pathlib import Path
import pytest

from src.pipeline.chunks import normalize_chunks
from src.pipeline.artifacts import require_artifacts, scan_mineru_artifacts
from src.pipeline.audit.corrections import (
    apply_approved_corrections,
    list_candidate_files,
    promote_approved_candidates,
    read_candidate_file,
    update_candidate_status,
)
from src.pipeline.audit.manual_structuring import (
    build_manual_structuring_draft,
    list_manual_structuring_files,
    list_manual_structuring_versions,
    publish_manual_structuring_draft,
    read_manual_structuring_file,
    read_manual_structuring_draft,
    rollback_manual_structuring_publication,
    save_manual_structuring_draft,
    update_manual_structuring_status,
    validate_manual_structuring_draft,
    write_manual_structuring_queue,
)
from src.pipeline.audit.multimodal import _extract_json_object, parse_pages, run_multimodal_review
from src.pipeline.audit.structuring_ai import normalize_structuring_suggestion
from src.pipeline.audit.rules import audit_elements
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


def test_metadata_override_validates_asset_access_scope():
    base = parse_spec_filename("GB 50009-2012_.建筑结构荷载规范.pdf")
    spec = apply_metadata_override(base, {"image_access": "public", "page_image_access": "disabled"})
    assert spec.image_access == "public"
    assert spec.page_image_access == "disabled"

    with pytest.raises(ValueError, match="image_access 必须是"):
        apply_metadata_override(base, {"image_access": "private"})


def test_normalize_chunk_contains_required_metadata():
    spec = parse_spec_filename("GB 50011-2010_建筑抗震设计规范_2016年版.pdf")
    chunks = normalize_chunks(
        [{"title": "8.2.1 构件要求", "text": "8.2.1 应符合要求", "pages": [10], "images": ["a.png"]}],
        spec,
    )
    chunk = chunks[0]
    for key in [
        "source_file",
        "code",
        "name",
        "pages",
        "images",
        "chunk_id",
        "title",
        "text",
        "chunk_type",
        "section_type",
        "authority_level",
        "is_table",
        "table_id",
        "table_name",
    ]:
        assert key in chunk
    assert chunk["clause_number"] == "8.2.1"


def test_normalize_chunk_extracts_table_metadata():
    spec = parse_spec_filename("GB 50009-2012_.建筑结构荷载规范.pdf")
    chunks = normalize_chunks(
        [
            {
                "title": "表5.1.1 民用建筑楼面均布活荷载",
                "text": "<table><tr><td>办公室</td><td>2.0</td></tr></table>",
                "pages": [30],
                "chunk_type": "table",
            }
        ],
        spec,
    )
    chunk = chunks[0]
    assert chunk["section_type"] == "body_table"
    assert chunk["authority_level"] == 100
    assert chunk["is_table"] is True
    assert chunk["table_id"] == "5.1.1"
    assert chunk["table_name"] == "民用建筑楼面均布活荷载"


def test_normalize_chunk_marks_explanation_clause_before_table_priority():
    spec = parse_spec_filename("GB 50009-2012_.建筑结构荷载规范.pdf")
    chunks = normalize_chunks(
        [
            {
                "title": "表2全国部分城市建筑楼面活荷载统计分析表",
                "text": "0.386 对民用建筑楼面可粗略分档",
                "pages": [220],
                "chunk_type": "table",
            }
        ],
        spec,
    )
    assert chunks[0]["clause_number"] == "0.386"
    assert chunks[0]["section_type"] == "explanation"


def test_normalize_chunk_does_not_mark_table_reference_as_table():
    spec = parse_spec_filename("GB 50009-2012_.建筑结构荷载规范.pdf")
    chunks = normalize_chunks(
        [
            {
                "title": "5.1.2设计楼面梁、墙、柱及基础时，本规范表5.1.1中楼面活荷载标准值的折减系数",
                "text": "5.1.2设计楼面梁、墙、柱及基础时，本规范表5.1.1中楼面活荷载标准值的折减系数取值不应小于下列规定。",
                "pages": [32],
                "chunk_type": "text",
            }
        ],
        spec,
    )
    assert chunks[0]["is_table"] is False
    assert chunks[0]["section_type"] == "body"
    assert chunks[0]["table_id"] == ""


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
    assert result["audit"]["finding_count"] >= 0
    assert result["corrections"]["applied_count"] == 0


def test_approved_corrections_are_applied(tmp_path: Path):
    corrections_dir = tmp_path / "corrections"
    approved = corrections_dir / "approved"
    approved.mkdir(parents=True)
    source_file = "GB 50009-2012_.建筑结构荷载规范.pdf"
    (approved / "GB 50009-2012_.建筑结构荷载规范.json").write_text(
        json.dumps(
            {
                "corrections": [
                    {
                        "id": "fix-text",
                        "action": "replace_text",
                        "target": {"element_index": 0, "field": "text"},
                        "value": "修正后的文本",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    elements, summary = apply_approved_corrections(
        [{"type": "Text", "text": "错误文本", "page": 1}],
        source_file,
        corrections_dir,
    )

    assert elements[0]["text"] == "修正后的文本"
    assert summary["applied_count"] == 1


def test_promote_corrections_only_promotes_approved_candidates(tmp_path: Path):
    corrections_dir = tmp_path / "corrections"
    candidates = corrections_dir / "candidates"
    candidates.mkdir(parents=True)
    source_file = "doc.pdf"
    (candidates / "doc.json").write_text(
        json.dumps(
            {
                "corrections": [
                    {
                        "id": "approved-fix",
                        "review_status": "approved",
                        "target": {"element_index": 0, "field": "text"},
                        "suggested_patch": {"action": "replace_text", "value": "approved"},
                    },
                    {
                        "id": "pending-fix",
                        "review_status": "pending",
                        "target": {"element_index": 1, "field": "text"},
                        "suggested_patch": {"action": "replace_text", "value": "pending"},
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = promote_approved_candidates(source_file, corrections_dir)
    approved_payload = json.loads(Path(result["approved_path"]).read_text(encoding="utf-8"))

    assert result["promoted_count"] == 1
    assert result["skipped_count"] == 1
    assert approved_payload["corrections"][0]["id"] == "approved-fix"
    assert approved_payload["corrections"][0]["action"] == "replace_text"


def test_candidate_status_workbench_helpers(tmp_path: Path):
    corrections_dir = tmp_path / "corrections"
    candidates = corrections_dir / "candidates"
    candidates.mkdir(parents=True)
    (candidates / "doc.json").write_text(
        json.dumps(
            {
                "source_file": "doc.pdf",
                "corrections": [
                    {"id": "c1", "review_status": "pending", "suggested_patch": {"action": "replace_text", "value": "x"}}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = list_candidate_files(corrections_dir)
    assert summary[0]["pending_count"] == 1
    assert read_candidate_file("doc", corrections_dir)["corrections"][0]["id"] == "c1"
    result = update_candidate_status("doc", "c1", "approved", corrections_dir)
    assert result["review_status"] == "approved"
    assert read_candidate_file("doc", corrections_dir)["corrections"][0]["review_status"] == "approved"


def test_candidate_helpers_keep_dots_inside_chinese_doc_names(tmp_path: Path):
    corrections_dir = tmp_path / "corrections"
    candidates = corrections_dir / "candidates"
    candidates.mkdir(parents=True)
    doc = "GB 50009-2012_.建筑结构荷载规范"
    (candidates / f"{doc}.json").write_text(
        json.dumps(
            {
                "source_file": f"{doc}.pdf",
                "corrections": [
                    {"id": "c1", "review_status": "pending", "suggested_patch": {"action": "replace_text", "value": "x"}}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    detail = read_candidate_file(doc, corrections_dir)
    assert detail["corrections"][0]["id"] == "c1"
    update_candidate_status(doc, "c1", "approved", corrections_dir)
    assert read_candidate_file(doc, corrections_dir)["corrections"][0]["review_status"] == "approved"


def test_manual_structuring_queue_detects_complex_tables(tmp_path: Path):
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    manual_dir = tmp_path / "manual_structuring"
    rules_path = manual_dir / "rules.json"
    rules_path.parent.mkdir()
    rules_path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "id": "complex_table",
                        "label": "复杂表",
                        "severity": "high",
                        "terms": ["表7.2.1"],
                        "reason": "需要人工结构化",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (processed_dir / "doc.json").write_text(
        json.dumps(
            {
                "source_file": "doc.pdf",
                "elements": [
                    {
                        "page": 7,
                        "chunk_type": "table",
                        "img": "page7.png",
                        "text": "表7.2.1 屋面积雪分布系数\n<table><tr><td colspan=\"2\">图形□</td></tr></table>",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = write_manual_structuring_queue(processed_dir, manual_dir, rules_path)
    documents = list_manual_structuring_files(manual_dir)
    detail = read_manual_structuring_file("doc", manual_dir)
    item_id = detail["items"][0]["id"]
    status = update_manual_structuring_status("doc", item_id, "approved", manual_dir, notes="已转结构化表")

    assert result["candidate_count"] == 1
    assert documents[0]["pending_count"] == 1
    assert detail["items"][0]["issue_type"] == "complex_table"
    assert "merged_cells" in detail["items"][0]["generic_reasons"]
    assert status["review_status"] == "approved"
    assert read_manual_structuring_file("doc", manual_dir)["items"][0]["notes"] == "已转结构化表"


def test_manual_structuring_groups_cross_page_tables_and_shares_draft(tmp_path: Path):
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    manual_dir = tmp_path / "manual_structuring"
    rules_path = manual_dir / "rules.json"
    rules_path.parent.mkdir()
    rules_path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "id": "complex_wind_shape_factor",
                        "label": "复杂风荷载表",
                        "severity": "high",
                        "terms": ["表8.3.3"],
                        "reason": "需要人工结构化",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    same_header = (
        '<table><tr><td rowspan="2">省市名</td><td colspan="2">风压□</td></tr>'
        "<tr><td>R=10</td><td>R=50</td></tr>"
    )
    elements = [
        {
            "page": 10,
            "img": "p10.png",
            "text": '表8.3.3 封闭式房屋体型系数\n<table><tr><td colspan="2">分区□</td></tr></table>',
        },
        {
            "page": 11,
            "img": "p11.png",
            "text": '续表8.3.3\n<table><tr><td colspan="2">分区□</td></tr></table>',
        },
        {
            "page": 11,
            "img": "p11-note.png",
            "text": '注：按表8.3.3采用\n<table><tr><td colspan="2">说明□</td></tr></table>',
        },
        {"page": 20, "img": "p20.png", "text": same_header + "<tr><td>北京</td></tr></table>"},
        {"page": 21, "img": "p21.png", "text": same_header + "<tr><td>天津</td></tr></table>"},
    ]
    (processed_dir / "doc.json").write_text(
        json.dumps({"source_file": "doc.pdf", "elements": elements}, ensure_ascii=False),
        encoding="utf-8",
    )

    write_manual_structuring_queue(processed_dir, manual_dir, rules_path)
    detail = read_manual_structuring_file("doc", manual_dir)
    items = detail["items"]
    explicit = [item for item in items if item.get("group_reason") == "same_table_id:8.3.3"]
    generic = [item for item in items if item.get("group_reason") == "adjacent_same_header"]
    note = next(item for item in items if str(item["title"]).startswith("注："))

    assert len(explicit) == 2
    assert explicit[0]["group_confidence"] == "high"
    assert explicit[0]["group_pages"] == [10, 11]
    assert len(generic) == 2
    assert generic[0]["group_confidence"] == "medium"
    assert "group_id" not in note

    continuation = next(item for item in explicit if str(item["title"]).startswith("续表"))
    draft = build_manual_structuring_draft("doc", continuation["id"], manual_dir)
    owner = explicit[0]["group_primary_item_id"]
    owner_draft = read_manual_structuring_draft("doc", owner, manual_dir)

    assert draft["source"]["pages"] == [10, 11]
    assert len(draft["review_context"]["manual_item_ids"]) == 2
    assert len(draft["review_context"]["elements"]) == 2
    assert draft["draft_path"] == owner_draft["draft_path"]
    assert "page 10" in draft["review_context"]["current_text"]
    assert "page 11" in draft["review_context"]["current_text"]


def test_manual_structuring_draft_can_be_generated_and_saved(tmp_path: Path):
    manual_dir = tmp_path / "manual_structuring"
    queue_dir = manual_dir / "queue"
    queue_dir.mkdir(parents=True)
    doc = "GB 50009-2012_.建筑结构荷载规范"
    item_id = f"{doc}_p27_e248_complex_table"
    (queue_dir / f"{doc}.json").write_text(
        json.dumps(
            {
                "doc": doc,
                "items": [
                    {
                        "id": item_id,
                        "source_file": f"{doc}.pdf",
                        "page": 27,
                        "element_index": 248,
                        "issue_type": "complex_table",
                        "severity": "high",
                        "title": "表7.2.1 屋面积雪分布系数",
                        "current_text": "<table><tr><td>屋面形式</td></tr></table>",
                        "matched_rules": [{"id": "complex_table", "label": "复杂表"}],
                        "generic_reasons": ["merged_cells"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    draft = build_manual_structuring_draft(doc, item_id, manual_dir)
    draft["rows"].append({"item": "单跨单坡屋面", "value": "1.0", "aliases": ["屋面积雪分布系数"]})
    saved = save_manual_structuring_draft(doc, item_id, draft, manual_dir)
    loaded = read_manual_structuring_draft(doc, item_id, manual_dir)

    assert Path(saved["draft_path"]).exists()
    assert loaded["source"]["code"] == "GB 50009-2012"
    assert loaded["source"]["table_id"] == "7.2.1"
    assert loaded["source"]["table_name"] == "屋面积雪分布系数"
    assert loaded["rows"][0]["item"] == "单跨单坡屋面"
    assert next(column for column in loaded["columns"] if column["key"] == "value")["value_type"] == "number"

    stored_path = Path(saved["draft_path"])
    legacy = json.loads(stored_path.read_text(encoding="utf-8"))
    for column in legacy["columns"]:
        column.pop("value_type", None)
    stored_path.write_text(json.dumps(legacy, ensure_ascii=False, indent=2), encoding="utf-8")
    migrated = read_manual_structuring_draft(doc, item_id, manual_dir)
    assert next(column for column in migrated["columns"] if column["key"] == "value")["value_type"] == "number"
    assert next(column for column in migrated["columns"] if column["key"] == "aliases")["value_type"] == "list"


def test_manual_structuring_draft_validation_publish_and_rollback(tmp_path: Path, monkeypatch):
    from src.app.rag import structured_tables
    from src.pipeline.audit import manual_structuring

    original_structured_dir = structured_tables.STRUCTURED_TABLE_DIR
    manual_dir = tmp_path / "manual_structuring"
    structured_dir = tmp_path / "structured_tables"
    queue_dir = manual_dir / "queue"
    queue_dir.mkdir(parents=True)
    doc = "GB 50009-2012_.建筑结构荷载规范"
    item_id = f"{doc}_p27_e248_complex_table"
    (queue_dir / f"{doc}.json").write_text(
        json.dumps(
            {
                "doc": doc,
                "items": [
                    {
                        "id": item_id,
                        "source_file": f"{doc}.pdf",
                        "page": 27,
                        "element_index": 248,
                        "issue_type": "complex_table",
                        "severity": "high",
                        "title": "表7.2.1 屋面积雪分布系数",
                        "current_text": "<table><tr><td>屋面形式</td></tr></table>",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    draft = build_manual_structuring_draft(doc, item_id, manual_dir)
    invalid = validate_manual_structuring_draft(doc, item_id, manual_dir)
    assert invalid["valid"] is False
    assert any(error["path"] == "rows" for error in invalid["errors"])

    draft["rows"] = [{"item": "单跨单坡屋面", "condition": "均匀分布", "value": "1.0", "aliases": ["单坡屋面"]}]
    saved = save_manual_structuring_draft(doc, item_id, draft, manual_dir)
    assert saved["draft_status"] == "needs_review"
    typed_invalid = validate_manual_structuring_draft(doc, item_id, manual_dir)
    assert typed_invalid["valid"] is False
    assert any(error["path"] == "rows[0].value" for error in typed_invalid["errors"])

    draft["rows"][0]["value"] = 1.0
    save_manual_structuring_draft(doc, item_id, draft, manual_dir)
    valid = validate_manual_structuring_draft(doc, item_id, manual_dir)
    assert valid["valid"] is True
    assert valid["draft_status"] == "validated"

    monkeypatch.setattr(structured_tables, "STRUCTURED_TABLE_DIR", structured_dir)
    structured_tables.load_structured_tables.cache_clear()
    assert structured_tables.load_structured_tables() == []

    real_smoke_test = manual_structuring._publication_smoke_test
    monkeypatch.setattr(
        manual_structuring,
        "_publication_smoke_test",
        lambda *_args, **_kwargs: {"passed": False, "queries": [{"query": "smoke", "hit": False}]},
    )
    with pytest.raises(RuntimeError, match="smoke test failed"):
        publish_manual_structuring_draft(doc, item_id, manual_dir, structured_dir)
    assert list(structured_dir.glob("*.json")) == []
    assert read_manual_structuring_draft(doc, item_id, manual_dir)["draft_status"] == "validated"
    assert read_manual_structuring_file(doc, manual_dir)["items"][0].get("review_status", "pending") == "pending"
    monkeypatch.setattr(manual_structuring, "_publication_smoke_test", real_smoke_test)

    first = publish_manual_structuring_draft(doc, item_id, manual_dir, structured_dir)
    target = Path(first["target_path"])
    assert target.exists()
    assert first["replaced_existing"] is False
    assert first["smoke_test"]["passed"] is True
    assert structured_tables.load_structured_tables()[0]["rows"][0]["value"] == 1.0
    assert read_manual_structuring_file(doc, manual_dir)["items"][0]["review_status"] == "approved"

    revised = read_manual_structuring_draft(doc, item_id, manual_dir)
    revised["rows"][0]["value"] = 1.2
    revised = save_manual_structuring_draft(doc, item_id, revised, manual_dir)
    assert revised["draft_status"] == "needs_review"
    assert validate_manual_structuring_draft(doc, item_id, manual_dir)["valid"] is True
    second = publish_manual_structuring_draft(doc, item_id, manual_dir, structured_dir)
    assert second["replaced_existing"] is True
    assert structured_tables.load_structured_tables()[0]["rows"][0]["value"] == 1.2
    assert len(list_manual_structuring_versions(doc, item_id, manual_dir)) == 3

    restored = rollback_manual_structuring_publication(doc, item_id, manual_dir, structured_dir)
    assert restored["rollback_action"] == "restored"
    assert restored["draft_status"] == "published"
    assert structured_tables.load_structured_tables()[0]["rows"][0]["value"] == 1.0

    removed = rollback_manual_structuring_publication(doc, item_id, manual_dir, structured_dir)
    assert removed["rollback_action"] == "removed"
    assert removed["draft_status"] == "validated"
    assert structured_tables.load_structured_tables() == []
    assert read_manual_structuring_file(doc, manual_dir)["items"][0]["review_status"] == "pending"
    monkeypatch.setattr(structured_tables, "STRUCTURED_TABLE_DIR", original_structured_dir)
    structured_tables.load_structured_tables.cache_clear()


def test_ai_structuring_suggestion_is_normalized_without_overwriting_source():
    draft = {
        "source": {"code": "GB 50009-2012", "table_id": "5.4.1-1", "pages": [35, 36]},
        "columns": [{"key": "item", "label": "项目", "value_type": "text"}],
        "rows": [],
        "review_context": {"current_text": "机械厂铸造车间 0.50"},
    }
    parsed = {
        "source": {"code": "HALLUCINATED"},
        "columns": [
            {"key": "item", "label": "项目", "value_type": "text"},
            {"key": "value", "label": "标准值", "unit": "kN/m²", "value_type": "number"},
            {"key": "aliases", "label": "别名", "value_type": "list"},
            {"key": "item", "label": "重复字段", "value_type": "text"},
        ],
        "rows": [
            {"item": "机械厂铸造车间", "value": "0.50", "aliases": "铸造车间, 冲天炉", "unknown": "drop"},
            {"item": "待确认", "value": None, "aliases": []},
        ],
        "table_aliases": ["表5.4.1-1", "表5.4.1-1"],
        "notes": ["截图可见表注"],
        "confidence": 1.7,
        "assumptions": ["第二列边界需人工确认"],
    }

    proposal = normalize_structuring_suggestion(draft, parsed)

    assert proposal["source"] == draft["source"]
    assert [column["key"] for column in proposal["columns"]] == ["item", "value", "aliases"]
    assert proposal["rows"] == [
        {
            "item": "机械厂铸造车间",
            "value": 0.5,
            "aliases": ["铸造车间", "冲天炉"],
        },
        {"item": "待确认", "value": None, "aliases": []},
    ]
    assert proposal["table_aliases"] == ["表5.4.1-1"]
    assert proposal["model_confidence"] == 1.0
    assert proposal["confidence"] == 0.8
    assert proposal["assumptions"] == ["第二列边界需人工确认"]
    assert proposal["quality"]["needs_careful_review"] is True
    assert proposal["quality"]["null_cell_count"] == 1


def test_audit_elements_flags_empty_document():
    report = audit_elements("empty.pdf", [], [])
    assert report["high_risk_count"] == 1
    assert report["findings"][0]["code"] == "no_elements"


def test_multimodal_review_helpers_parse_pages_and_json():
    assert parse_pages("1,3-5,0,x") == [1, 3, 4, 5]
    parsed = _extract_json_object('```json\n{"candidates":[]}\n```')
    assert parsed == {"candidates": []}


def test_multimodal_review_without_key_writes_not_configured_report(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MIMO_API_KEY", "")
    source_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    source_dir.mkdir()
    processed_dir.mkdir()
    pdf = source_dir / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    def fake_render(_pdf_path, pages, out_dir):
        out_dir.mkdir(parents=True, exist_ok=True)
        image = out_dir / "doc_p0001.png"
        image.write_bytes(b"png")
        return {page: image for page in pages}

    monkeypatch.setattr("src.pipeline.audit.multimodal.render_pdf_pages", fake_render)
    result = run_multimodal_review("doc", "1", source_dir=source_dir, processed_dir=processed_dir, out_dir=tmp_path / "audit")

    assert result["status"] == "not_configured"
    assert result["candidate_count"] == 0
    assert Path(result["report_path"]).exists()


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
        "audit_by_file": {pdf.name: {"finding_count": 2, "high_risk_count": 1}},
        "corrections_by_file": {pdf.name: {"approved_count": 1, "applied_count": 1, "skipped_count": 0}},
        "chunk_hashes_by_file": {pdf.name: ["chunk-a", "chunk-b"]},
        "build_params": {"mode": "rebuild"},
    }
    first = build_manifest(**kwargs)
    second = build_manifest(**kwargs)
    assert first["data_version_hash"] == second["data_version_hash"]
    assert first["documents"][0]["artifacts"][0]["kind"] == "content_list"
    assert first["documents"][0]["chunk_hashes"] == ["chunk-a", "chunk-b"]
    assert first["audit_status"]["high_risk_count"] == 1
    assert first["correction_status"]["applied_count"] == 1


def test_cli_status_without_manifest(tmp_path: Path, monkeypatch):
    from src.pipeline import builder

    monkeypatch.setattr(builder, "ACTIVE_DB_PATH", tmp_path / "missing-active.json")
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
