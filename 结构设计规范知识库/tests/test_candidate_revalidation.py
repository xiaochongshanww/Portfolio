from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import fitz
import pytest
from src.app.admin.models import Job
from src.app.admin.storage import JobStore
from src.app.admin.workflows import revalidate_candidate_workflow
from src.pipeline.source_catalog import SourceCatalogStore
from src.quality.candidate import CandidateActivationAssessment


def _setup(tmp_path: Path, monkeypatch):
    import src.app.admin.workflows as workflows

    candidate_job_id = "candidate-revalidate"
    source_store = SourceCatalogStore(tmp_path / "catalog")
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "candidate source")
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(pdf.tobytes())
    pdf.close()
    source = source_store.register_upload(pdf_path, "GB 50000-2026.pdf")
    source_store.update_source(
        source["source_id"], {"code": "GB 50000-2026", "name": "测试规范"}, {}
    )
    revision = source_store.create_revision()
    source_store.fail_revision(revision["revision_id"], "candidate gate failed")

    versions_dir = tmp_path / "versions"
    candidate_dir = versions_dir / candidate_job_id
    for name in ("db", "processed", "images"):
        (candidate_dir / name).mkdir(parents=True)
    data_version_hash = "a" * 64
    manifest_path = candidate_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "data_version_hash": data_version_hash,
                "build_params": {"source_catalog_revision": revision["revision_id"]},
            }
        ),
        encoding="utf-8",
    )

    evaluation_paths = {
        "regular": tmp_path / "regular.jsonl",
        "structured": tmp_path / "structured.jsonl",
    }
    evaluation_paths["regular"].write_text("regular-v1", encoding="utf-8")
    evaluation_paths["structured"].write_text("structured-v1", encoding="utf-8")
    revisions = {"regular": "regular-rev-1", "structured": "structured-rev-1"}

    monkeypatch.setattr(workflows, "source_catalog_store", source_store)
    monkeypatch.setattr(workflows, "DB_VERSIONS_DIR", versions_dir)
    monkeypatch.setattr(
        workflows,
        "resolve_evaluation_asset",
        lambda set_id, **_kwargs: evaluation_paths[set_id],
    )
    monkeypatch.setattr(workflows, "published_revision_id", lambda set_id: revisions[set_id])

    store = JobStore(tmp_path / "jobs")
    original = Job(
        type="source_rebuild",
        status="failed",
        job_id=candidate_job_id,
        params={"source_catalog_revision": revision["revision_id"]},
    )
    store.save(original)
    revalidation_job = Job(
        type="candidate_revalidation",
        job_id="revalidation-1",
        params={
            "candidate_job_id": candidate_job_id,
            "source_catalog_revision": revision["revision_id"],
        },
    )
    store.save(revalidation_job)

    active_db_path = tmp_path / "active_db.json"
    active_manifest_path = tmp_path / "active_manifest.json"
    active_db_path.write_text('{"job_id":"old-active"}', encoding="utf-8")
    active_manifest_path.write_text('{"data_version_hash":"old-active"}', encoding="utf-8")
    monkeypatch.setattr(workflows, "ACTIVE_DB_PATH", active_db_path)
    monkeypatch.setattr(workflows, "MANIFEST_PATH", active_manifest_path)

    return {
        "workflows": workflows,
        "candidate_dir": candidate_dir,
        "data_version_hash": data_version_hash,
        "evaluation_paths": evaluation_paths,
        "revisions": revisions,
        "store": store,
        "job": revalidation_job,
        "source_revision": revision["revision_id"],
        "active_db_path": active_db_path,
        "active_manifest_path": active_manifest_path,
    }


def _assessment(context: dict, *, passed: bool = False) -> CandidateActivationAssessment:
    evaluation_paths = context["evaluation_paths"]
    revisions = context["revisions"]
    data_version_hash = context["data_version_hash"]
    failed_checks = [] if passed else ["regular_evaluation"]
    return CandidateActivationAssessment(
        result={
            "passed": passed,
            "failed_checks": failed_checks,
            "checks": [],
            "data_version_hash": data_version_hash,
            "regular_evaluation_set_revision_id": revisions["regular"],
            "structured_evaluation_set_revision_id": revisions["structured"],
            "generated_at": "2026-09-26T00:00:00Z",
        },
        retrieval_state=None,
        regular_evaluation={
            "case_count": 100,
            "failures": [] if passed else [{"id": "case-1"}],
            "data_version_hash": data_version_hash,
            "evaluation_set_hash": hashlib.sha256(
                evaluation_paths["regular"].read_bytes()
            ).hexdigest(),
        },
        structured_evaluation={
            "case_count": 12,
            "failures": [],
            "data_version_hash": data_version_hash,
            "evaluation_set_hash": hashlib.sha256(
                evaluation_paths["structured"].read_bytes()
            ).hexdigest(),
        },
    )


def test_revalidation_persists_a_failed_report_without_activating_or_mutating_candidate(
    tmp_path: Path, monkeypatch
) -> None:
    context = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(
        context["workflows"],
        "assess_candidate_activation",
        lambda **_kwargs: _assessment(context, passed=False),
    )
    active_db_before = context["active_db_path"].read_bytes()
    active_manifest_before = context["active_manifest_path"].read_bytes()
    manifest_before = (context["candidate_dir"] / "manifest.json").read_bytes()

    output = revalidate_candidate_workflow(context["job"], context["store"])

    assert output["revalidation_only"] is True
    assert output["passed"] is False
    assert output["candidate_job_id"] == "candidate-revalidate"
    report_dir = Path(output["gate_report"]).parent
    assert re.fullmatch(r"\d{8}T\d{12}Z", report_dir.name)
    assert report_dir.parent == context["candidate_dir"] / "quality" / "revalidations"
    assert json.loads(Path(output["gate_report"]).read_text(encoding="utf-8"))["passed"] is False
    assert context["store"].read("candidate-revalidate")["status"] == "failed"
    assert context["active_db_path"].read_bytes() == active_db_before
    assert context["active_manifest_path"].read_bytes() == active_manifest_before
    assert (context["candidate_dir"] / "manifest.json").read_bytes() == manifest_before
    assert not list(report_dir.parent.glob(".pending-*"))


def test_revalidation_discards_report_if_evaluation_set_changes_mid_run(
    tmp_path: Path, monkeypatch
) -> None:
    context = _setup(tmp_path, monkeypatch)

    def change_eval_set(**_kwargs):
        result = _assessment(context, passed=True)
        context["evaluation_paths"]["regular"].write_text("regular-v2", encoding="utf-8")
        return result

    monkeypatch.setattr(context["workflows"], "assess_candidate_activation", change_eval_set)

    with pytest.raises(RuntimeError, match="评估集在复核期间发生变化"):
        revalidate_candidate_workflow(context["job"], context["store"])

    revalidations_dir = context["candidate_dir"] / "quality" / "revalidations"
    assert not list(revalidations_dir.iterdir())
    assert context["store"].read("candidate-revalidate")["status"] == "failed"
