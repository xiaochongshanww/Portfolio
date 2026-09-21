import json
from pathlib import Path
from types import SimpleNamespace

import fitz
from fastapi.testclient import TestClient
from src.app.api import sources as sources_api
from src.app.core.config import settings
from src.app.main import app
from src.pipeline.source_catalog import SourceCatalogStore


def pdf_bytes(text: str = "test") -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


def auth_headers() -> dict[str, str]:
    if settings.api_auth_enabled and settings.api_keys:
        return {"Authorization": f"Bearer {settings.api_keys[0]}"}
    return {}


def test_upload_edit_plan_and_revision_listing(tmp_path: Path, monkeypatch) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    monkeypatch.setattr(sources_api, "source_catalog_store", store)
    client = TestClient(app)

    response = client.post(
        "/admin/sources/uploads",
        params={"filename": "GB 50000-2026_测试规范.pdf"},
        content=pdf_bytes(),
        headers={**auth_headers(), "Content-Type": "application/pdf"},
    )
    assert response.status_code == 200, response.text
    source = response.json()["source"]

    update = client.patch(
        f"/admin/sources/{source['source_id']}",
        json={
            "metadata": {"code": "GB 50000-2026", "name": "测试规范"},
            "governance": {"rights_status": "B", "reference_index": "official-index"},
        },
        headers=auth_headers(),
    )
    assert update.status_code == 200
    assert update.json()["source"]["lifecycle_status"] == "ready"

    plan = client.post("/admin/sources/changes/plan", headers=auth_headers())
    assert plan.status_code == 200
    assert plan.json()["ready"] is True
    assert plan.json()["changes"]["added"] == [source["source_id"]]

    revisions = client.get("/admin/sources/revisions", headers=auth_headers())
    assert revisions.status_code == 200
    assert revisions.json()["revisions"] == []


def test_managed_build_submits_snapshot_paths(tmp_path: Path, monkeypatch) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    monkeypatch.setattr(sources_api, "source_catalog_store", store)
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(pdf_bytes())
    source = store.register_upload(pdf, "GB 50000-2026_测试规范.pdf")
    store.update_source(source["source_id"], {"code": "GB 50000-2026", "name": "测试规范"}, {})
    captured = {}

    def submit(job_type, params, workflow):
        captured.update({"job_type": job_type, "params": params, "workflow": workflow})
        return SimpleNamespace(
            to_dict=lambda: {
                "type": job_type,
                "params": params,
                "job_id": "job-1",
                "status": "queued",
                "step": "queued",
                "created_at": "2026-08-23T00:00:00Z",
            }
        )

    monkeypatch.setattr(sources_api.job_manager, "submit", submit)
    client = TestClient(app)
    response = client.post(
        "/admin/sources/changes/build",
        json={"parser_backend": "pymupdf", "mode": "incremental", "apply_corrections": True},
        headers=auth_headers(),
    )

    assert response.status_code == 200, response.text
    assert captured["job_type"] == "source_rebuild"
    assert Path(captured["params"]["source"]).is_dir()
    assert Path(captured["params"]["metadata_path"]).is_file()
    assert captured["params"]["source_catalog_revision"] == response.json()["revision_id"]


def test_managed_build_marks_revision_failed_when_job_submission_fails(
    tmp_path: Path, monkeypatch
) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    monkeypatch.setattr(sources_api, "source_catalog_store", store)
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(pdf_bytes())
    source = store.register_upload(pdf, "GB 50000-2026_测试规范.pdf")
    store.update_source(source["source_id"], {"code": "GB 50000-2026", "name": "测试规范"}, {})
    monkeypatch.setattr(
        sources_api.job_manager,
        "submit",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("executor unavailable")),
    )

    response = TestClient(app).post(
        "/admin/sources/changes/build",
        json={"parser_backend": "pymupdf", "mode": "incremental", "apply_corrections": True},
        headers=auth_headers(),
    )

    assert response.status_code == 503
    assert store.read()["revisions"][0]["status"] == "failed"


def test_republish_failed_candidate_submits_without_rebuilding(tmp_path: Path, monkeypatch) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(pdf_bytes())
    source = store.register_upload(pdf, "GB 50000-2026_测试规范.pdf")
    store.update_source(source["source_id"], {"code": "GB 50000-2026", "name": "测试规范"}, {})
    snapshot = store.create_revision()
    store.fail_revision(snapshot["revision_id"], "candidate gate failed")
    monkeypatch.setattr(sources_api, "source_catalog_store", store)

    candidate_job_id = "candidate-1"
    candidate_dir = tmp_path / "versions" / candidate_job_id
    candidate_dir.mkdir(parents=True)
    (candidate_dir / "manifest.json").write_text(
        json.dumps(
            {"build_params": {"source_catalog_revision": snapshot["revision_id"]}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sources_api, "DB_VERSIONS_DIR", tmp_path / "versions")
    monkeypatch.setattr(
        sources_api.job_manager.store,
        "read",
        lambda job_id: {
            "job_id": candidate_job_id,
            "type": "source_rebuild",
            "status": "failed",
            "params": {"source_catalog_revision": snapshot["revision_id"]},
        },
    )
    monkeypatch.setattr(sources_api.job_manager.store, "list", lambda: [])
    captured = {}

    def submit(job_type, params, workflow):
        captured.update({"job_type": job_type, "params": params, "workflow": workflow})
        return SimpleNamespace(
            to_dict=lambda: {
                "job_id": "republish-1",
                "type": job_type,
                "status": "queued",
                "params": params,
            }
        )

    monkeypatch.setattr(sources_api.job_manager, "submit", submit)
    response = TestClient(app).post(
        f"/admin/sources/candidates/{candidate_job_id}/republish",
        headers=auth_headers(),
    )

    assert response.status_code == 200, response.text
    assert captured["job_type"] == "source_republish"
    assert captured["params"] == {
        "candidate_job_id": candidate_job_id,
        "source_catalog_revision": snapshot["revision_id"],
    }
    assert captured["workflow"].__name__ == "republish_candidate_workflow"


def test_upload_rejects_unsafe_filename_and_duplicate(tmp_path: Path, monkeypatch) -> None:
    store = SourceCatalogStore(tmp_path / "data")
    monkeypatch.setattr(sources_api, "source_catalog_store", store)
    client = TestClient(app)
    payload = pdf_bytes()

    unsafe = client.post(
        "/admin/sources/uploads",
        params={"filename": "../unsafe.pdf"},
        content=payload,
        headers=auth_headers(),
    )
    assert unsafe.status_code == 400

    first = client.post(
        "/admin/sources/uploads",
        params={"filename": "first.pdf"},
        content=payload,
        headers=auth_headers(),
    )
    assert first.status_code == 200
    duplicate = client.post(
        "/admin/sources/uploads",
        params={"filename": "duplicate.pdf"},
        content=payload,
        headers=auth_headers(),
    )
    assert duplicate.status_code == 400
    assert "已存在" in duplicate.text
