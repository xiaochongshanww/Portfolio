import json
from pathlib import Path

import fitz
import pytest
from src.app.admin import source_management
from src.app.admin.models import Job
from src.app.admin.storage import JobStore
from src.pipeline.audit import multimodal
from src.pipeline.source_catalog import SourceCatalogError, SourceCatalogStore


def make_pdf(path: Path, text: str = "test") -> Path:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()
    return path


def complete_source(
    store: SourceCatalogStore, pdf: Path, filename: str = "GB 50000-2026_测试规范.pdf"
):
    source = store.register_upload(pdf, filename)
    return store.update_source(
        source["source_id"],
        {"code": "GB 50000-2026", "name": "测试规范"},
        {"rights_status": "B"},
    )


def test_upload_is_content_addressed_and_rejects_duplicate(tmp_path: Path) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    pdf = make_pdf(tmp_path / "source.pdf")

    source = complete_source(store, pdf)

    version = source["versions"][0]
    assert version["validation_status"] == "validated"
    assert version["page_count"] == 1
    assert source["metadata"]["image_access"] == "disabled"
    assert source["metadata"]["page_image_access"] == "disabled"
    assert (store.data_dir / version["object_path"]).is_file()
    with pytest.raises(SourceCatalogError, match="已存在"):
        store.register_upload(pdf, "duplicate.pdf")


def test_invalid_and_encrypted_inputs_are_rejected(tmp_path: Path) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    invalid = tmp_path / "invalid.pdf"
    invalid.write_bytes(b"not a pdf")
    with pytest.raises(SourceCatalogError, match="不是 PDF"):
        store.register_upload(invalid, invalid.name)

    plain = make_pdf(tmp_path / "plain.pdf")
    document = fitz.open(plain)
    encrypted = tmp_path / "encrypted.pdf"
    document.save(encrypted, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
    document.close()
    with pytest.raises(SourceCatalogError, match="密码保护"):
        store.register_upload(encrypted, encrypted.name)


def test_revision_materializes_desired_state_and_activates_atomically(tmp_path: Path) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    first = complete_source(store, make_pdf(tmp_path / "first.pdf", "first"))

    plan = store.plan_changes()
    assert plan["ready"] is True
    assert plan["changes"]["added"] == [first["source_id"]]

    snapshot = store.create_revision()
    input_file = store.data_dir / snapshot["input_dir"] / first["metadata"]["source_file"]
    metadata = json.loads((store.data_dir / snapshot["metadata_path"]).read_text("utf-8"))
    assert input_file.is_file()
    assert metadata["documents"][0]["code"] == "GB 50000-2026"

    store.activate_revision(snapshot["revision_id"], "version-one")
    active = store.get_source(first["source_id"])
    assert active["lifecycle_status"] == "active"
    assert active["pending_action"] == ""

    updated = store.update_source(first["source_id"], {"name": "更新后的规范"}, {})
    assert updated["pending_action"] == "update"
    assert store.plan_changes()["changes"]["updated"] == [first["source_id"]]
    restored = store.discard_pending(first["source_id"])
    assert restored is not None
    assert restored["metadata"]["name"] == "测试规范"

    replacement = make_pdf(tmp_path / "replacement.pdf", "replacement")
    store.register_upload(replacement, "replacement.pdf", source_id=first["source_id"])
    replace_plan = store.plan_changes()
    assert replace_plan["changes"]["replaced"] == [first["source_id"]]
    assert (
        store.get_source(first["source_id"])["active_asset_version_id"]
        == active["active_asset_version_id"]
    )


def test_resolve_source_pdf_uses_active_revision_input(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    store = SourceCatalogStore(data_dir)
    source = complete_source(store, make_pdf(tmp_path / "source.pdf"))
    snapshot = store.create_revision()
    store.activate_revision(snapshot["revision_id"], "version-one")

    source_file = source["metadata"]["source_file"]
    resolved = store.resolve_source_pdf(source_file)

    assert resolved == data_dir / snapshot["input_dir"] / source_file
    assert store.resolve_source_pdf(Path(source_file).stem) == resolved


def test_find_source_pdf_falls_back_to_active_source_catalog(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True)
    store = SourceCatalogStore(data_dir)
    source = complete_source(store, make_pdf(tmp_path / "source.pdf"))
    snapshot = store.create_revision()
    store.activate_revision(snapshot["revision_id"], "version-one")
    monkeypatch.setattr(multimodal, "RAW_DIR", raw_dir)

    resolved = multimodal.find_source_pdf(Path(source["metadata"]["source_file"]).stem, raw_dir)

    assert resolved == data_dir / snapshot["input_dir"] / source["metadata"]["source_file"]


def test_failed_revision_can_be_revalidated_only_when_catalog_is_unchanged(tmp_path: Path) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    source = complete_source(store, make_pdf(tmp_path / "source.pdf"))
    snapshot = store.create_revision()
    store.fail_revision(snapshot["revision_id"], "candidate gate failed")

    validated = store.validate_republish_revision(snapshot["revision_id"])
    assert validated["revision_id"] == snapshot["revision_id"]

    store.update_source(source["source_id"], {"name": "候选生成后修改"}, {})
    with pytest.raises(SourceCatalogError, match="来源目录在候选生成后发生变化"):
        store.validate_republish_revision(snapshot["revision_id"])


def test_retire_and_discard_do_not_mutate_active_asset(tmp_path: Path) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    source = complete_source(store, make_pdf(tmp_path / "source.pdf"))
    snapshot = store.create_revision()
    store.activate_revision(snapshot["revision_id"], "version-one")

    retired = store.retire(source["source_id"])
    assert retired["active_asset_version_id"]
    assert store.plan_changes()["changes"]["retired"] == [source["source_id"]]

    restored = store.discard_pending(source["source_id"])
    assert restored is not None
    assert restored["lifecycle_status"] == "active"


def test_activation_preserves_changes_made_after_revision_snapshot(tmp_path: Path) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    source = complete_source(store, make_pdf(tmp_path / "source.pdf"))
    snapshot = store.create_revision()

    changed = store.update_source(source["source_id"], {"name": "稍后修改的名称"}, {})
    assert changed["pending_action"] == "add"
    store.activate_revision(snapshot["revision_id"], "version-one")

    current = store.get_source(source["source_id"])
    assert current["active_metadata"]["name"] == "测试规范"
    assert current["metadata"]["name"] == "稍后修改的名称"
    assert current["pending_action"] == "update"


def test_only_one_candidate_revision_can_be_open(tmp_path: Path) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    complete_source(store, make_pdf(tmp_path / "source.pdf"))
    store.create_revision()

    with pytest.raises(SourceCatalogError, match="已有候选"):
        store.create_revision()


def test_interrupted_source_job_releases_candidate_revision(tmp_path: Path, monkeypatch) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    complete_source(store, make_pdf(tmp_path / "source.pdf"))
    snapshot = store.create_revision()
    jobs = JobStore(tmp_path / "jobs")
    job = Job(
        type="source_rebuild",
        params={"source_catalog_revision": snapshot["revision_id"]},
        status="failed",
    )
    jobs.save(job)
    monkeypatch.setattr(source_management, "source_catalog_store", store)
    monkeypatch.setattr(source_management, "source_job_store", jobs)

    count = source_management.reconcile_interrupted_source_revisions(
        [{"job_id": job.job_id, "type": "source_rebuild"}]
    )

    assert count == 1
    assert store.read()["revisions"][0]["status"] == "failed"


def test_path_traversal_and_incomplete_metadata_are_blocked(tmp_path: Path) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    pdf = make_pdf(tmp_path / "source.pdf")
    with pytest.raises(SourceCatalogError, match="目录路径"):
        store.register_upload(pdf, "../source.pdf")

    source = store.register_upload(pdf, "unknown.pdf")
    store.update_source(source["source_id"], {"code": "", "name": ""}, {})
    plan = store.plan_changes()
    assert plan["ready"] is False
    assert plan["blockers"]


def test_catalog_asset_path_cannot_escape_object_store(tmp_path: Path) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    source = complete_source(store, make_pdf(tmp_path / "source.pdf"))
    catalog = store.read()
    catalog["sources"][0]["versions"][0]["object_path"] = "../source.pdf"
    store._write(catalog)

    with pytest.raises(SourceCatalogError, match="内容寻址对象目录"):
        store.create_revision()
    validated = store.validate_source(source["source_id"])
    assert validated["versions"][0]["validation_status"] == "invalid"
    assert "超出内容寻址对象目录" in validated["versions"][0]["validation_errors"][0]


def test_bootstrap_skips_test_only_sources(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True)
    make_pdf(raw_dir / "GB 50000-2026_生产规范.pdf")
    make_pdf(raw_dir / "TEST_测试夹具.pdf")
    metadata_path = data_dir / "metadata" / "specs.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "source_file": "TEST_测试夹具.pdf",
                        "code": "TEST",
                        "name": "测试夹具",
                        "status": "test",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    store = SourceCatalogStore(data_dir)
    result = store.bootstrap_legacy(raw_dir, metadata_path)

    assert result["imported_count"] == 1
    assert store.list_sources()["source_count"] == 1


def test_bootstrap_rolls_back_partial_catalog_on_invalid_pdf(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True)
    make_pdf(raw_dir / "A_valid.pdf")
    (raw_dir / "B_invalid.pdf").write_bytes(b"not a pdf")
    store = SourceCatalogStore(data_dir)

    with pytest.raises(SourceCatalogError, match="不是 PDF"):
        store.bootstrap_legacy(raw_dir, data_dir / "metadata" / "specs.json")

    assert store.list_sources()["source_count"] == 0
    assert not store.catalog_path.exists()
