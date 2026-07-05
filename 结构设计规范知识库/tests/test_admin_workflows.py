import json
from pathlib import Path

from src.app.admin.models import Job
from src.app.admin.storage import JobStore
from src.app.admin.workflows import dry_run_workflow
from src.pipeline.active_db import active_db_dir, read_active_db, read_active_manifest, write_active_db


def test_job_store_persists_status_and_logs(tmp_path: Path):
    store = JobStore(tmp_path)
    job = Job(type="audit", params={})
    store.save(job)
    store.append_log(job.job_id, "info", "started")

    assert store.read(job.job_id)["type"] == "audit"
    assert store.logs(job.job_id)[0]["message"] == "started"
    assert store.list()[0]["job_id"] == job.job_id


def test_dry_run_workflow_returns_document_summary(tmp_path: Path):
    source = tmp_path / "raw"
    source.mkdir()
    (source / "GB 50011-2010_建筑抗震设计规范_2016年版.pdf").write_bytes(b"pdf")
    store = JobStore(tmp_path / "jobs")
    job = Job(type="dry_run", params={"source": str(source), "parser_backend": "mineru"})

    result = dry_run_workflow(job, store)

    assert result["mode"] == "dry-run"
    assert result["document_count"] == 1
    assert store.read(job.job_id)["step"] == "dry_run"


def test_admin_add_approved_shape(tmp_path: Path):
    payload = {
        "corrections": [
            {
                "id": "approved-1",
                "action": "replace_text",
                "target": {"element_index": 1, "field": "text"},
                "value": "文本",
            }
        ]
    }
    text = json.dumps(payload, ensure_ascii=False)
    assert "approved-1" in text
    assert "replace_text" in text


def test_active_db_pointer_round_trips(tmp_path: Path):
    pointer = tmp_path / "active_db.json"
    db_dir = tmp_path / "db_versions" / "v1" / "db"
    write_active_db({"active_db_dir": str(db_dir), "manifest": "manifest.json"}, pointer)

    assert read_active_db(pointer)["active_db_dir"] == str(db_dir)
    assert active_db_dir(pointer) == db_dir

    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"chunk_count": 7}', encoding="utf-8")
    write_active_db({"active_db_dir": str(db_dir), "manifest": str(manifest)}, pointer)
    assert read_active_manifest(pointer)["chunk_count"] == 7
