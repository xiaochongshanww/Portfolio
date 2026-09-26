from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.app.admin.models import Job
from src.app.admin.storage import JobStore
from src.app.api import admin


def test_candidate_gate_report_returns_failure_details_and_rejects_outside_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    versions_dir = tmp_path / "versions"
    quality_dir = versions_dir / "candidate-1" / "quality"
    quality_dir.mkdir(parents=True)
    gate_path = quality_dir / "candidate_activation_gate.json"
    current_regular_asset = tmp_path / "published-regular.jsonl"
    current_structured_asset = tmp_path / "published-structured.jsonl"
    current_regular_asset.write_text("current regular", encoding="utf-8")
    current_structured_asset.write_text("current structured", encoding="utf-8")
    current_assets = {
        "regular": current_regular_asset,
        "structured": current_structured_asset,
    }
    current_revisions = {"regular": "rev-regular-current", "structured": "rev-structured-current"}
    gate_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-09-26T00:23:00Z",
                "passed": False,
                "failed_checks": ["regular_evaluation"],
                "regular_evaluation_set_revision_id": "rev-regular-old",
                "structured_evaluation_set_revision_id": "rev-structured-current",
                "checks": [
                    {
                        "name": "regular_evaluation",
                        "status": "failed",
                        "severity": "blocking",
                        "message": "100 项中失败 1 项",
                        "details": {"report_path": "F:/private/candidate/report.json"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (quality_dir / "evaluation_regular.json").write_text(
        json.dumps(
            {
                "case_count": 100,
                "evaluation_set_hash": hashlib.sha256(b"old regular").hexdigest(),
                "top1_source_hit_rate": 1.0,
                "authority_hit_rate": 0.99,
                "failures": [
                    {
                        "id": "table-case",
                        "type": "table",
                        "query": "查哪个表？",
                        "expected_authority_type": "body_or_table",
                        "source_hit": True,
                        "top1_source_hit": True,
                        "clause_hit": True,
                        "keyword_hit": True,
                        "table_hit": True,
                        "authority_hit": False,
                        "structured_table_hit": True,
                        "failed_checks": ["authority"],
                        "top_results": [
                            {"section_type": "body", "score": 3.2},
                            {"section_type": "body_table", "score": 3.1},
                        ],
                        "top_structured_results": [
                            {"table_id": "4.0.6", "table_name": "分部工程划分", "score": 2.9}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (quality_dir / "evaluation_structured.json").write_text(
        json.dumps(
            {
                "case_count": 12,
                "evaluation_set_hash": hashlib.sha256(b"current structured").hexdigest(),
                "failures": [],
            }
        ),
        encoding="utf-8",
    )

    store = JobStore(tmp_path / "jobs")
    job = Job(type="source_rebuild", status="failed", job_id="candidate-1")
    store.save(job)
    store.append_log(job.job_id, "error", "candidate gate failed", gate_report=str(gate_path))
    outside_job = Job(type="source_rebuild", status="failed")
    store.save(outside_job)
    outside_report = tmp_path / "outside" / "candidate_activation_gate.json"
    outside_report.parent.mkdir()
    outside_report.write_text("{}", encoding="utf-8")
    store.append_log(
        outside_job.job_id,
        "error",
        "invalid report reference",
        gate_report=str(outside_report),
    )

    monkeypatch.setattr(admin, "DB_VERSIONS_DIR", versions_dir)
    monkeypatch.setattr(admin, "job_store", store)
    monkeypatch.setattr(admin, "resolve_published_asset", lambda set_id: current_assets[set_id])
    monkeypatch.setattr(admin, "published_revision_id", lambda set_id: current_revisions[set_id])
    app = FastAPI()
    app.include_router(admin.router)
    client = TestClient(app)

    response = client.get(f"/admin/jobs/{job.job_id}/candidate-gate-report")
    outside_response = client.get(f"/admin/jobs/{outside_job.job_id}/candidate-gate-report")

    assert response.status_code == 200
    report = response.json()
    assert report["available"] is True
    assert report["candidate_version_id"] == "candidate-1"
    assert report["failed_checks"] == ["regular_evaluation"]
    assert report["checks"] == [
        {
            "name": "regular_evaluation",
            "status": "failed",
            "severity": "blocking",
            "message": "100 项中失败 1 项",
        }
    ]
    assert report["evaluation_sets_current"] is False
    assert report["evaluation_set_status"] == [
        {
            "evaluation_set_id": "regular",
            "snapshot_revision_id": "rev-regular-old",
            "current_revision_id": "rev-regular-current",
            "freshness": "stale",
        },
        {
            "evaluation_set_id": "structured",
            "snapshot_revision_id": "rev-structured-current",
            "current_revision_id": "rev-structured-current",
            "freshness": "current",
        },
    ]
    assert report["regular_evaluation"]["failure_count"] == 1
    failure = report["regular_evaluation"]["failures"][0]
    assert failure["source_hit"] is True
    assert failure["authority_hit"] is False
    assert failure["expected_authority_type"] == "body_or_table"
    assert failure["top_results"][1]["section_type"] == "body_table"
    assert failure["top_structured_results"][0]["table_id"] == "4.0.6"
    assert "details" not in report["checks"][0]
    assert report["structured_evaluation"]["case_count"] == 12
    assert outside_response.status_code == 200
    assert outside_response.json()["available"] is False

    gate_payload = json.loads(gate_path.read_text(encoding="utf-8"))
    gate_payload.pop("structured_evaluation_set_revision_id")
    gate_path.write_text(json.dumps(gate_payload), encoding="utf-8")
    structured_payload = json.loads(
        (quality_dir / "evaluation_structured.json").read_text(encoding="utf-8")
    )
    structured_payload.pop("evaluation_set_hash")
    (quality_dir / "evaluation_structured.json").write_text(
        json.dumps(structured_payload), encoding="utf-8"
    )
    mixed_freshness_response = client.get(f"/admin/jobs/{job.job_id}/candidate-gate-report")
    assert mixed_freshness_response.json()["evaluation_sets_current"] is False
    assert mixed_freshness_response.json()["evaluation_set_status"][1]["freshness"] == "unknown"


def test_candidate_gate_report_prefers_latest_revalidation_without_changing_job(
    tmp_path: Path,
    monkeypatch,
) -> None:
    versions_dir = tmp_path / "versions"
    quality_dir = versions_dir / "candidate-1" / "quality"
    quality_dir.mkdir(parents=True)
    candidate_hash = "candidate-data-hash"
    (quality_dir.parent / "manifest.json").write_text(
        json.dumps({"data_version_hash": candidate_hash}), encoding="utf-8"
    )
    old_gate = quality_dir / "candidate_activation_gate.json"
    old_gate.write_text(json.dumps({"passed": False}), encoding="utf-8")

    regular_text = "current regular"
    structured_text = "current structured"
    current_regular_asset = tmp_path / "published-regular.jsonl"
    current_structured_asset = tmp_path / "published-structured.jsonl"
    current_regular_asset.write_text(regular_text, encoding="utf-8")
    current_structured_asset.write_text(structured_text, encoding="utf-8")
    current_assets = {
        "regular": current_regular_asset,
        "structured": current_structured_asset,
    }
    current_revisions = {"regular": "regular-current", "structured": "structured-current"}

    earlier = quality_dir / "revalidations" / "20260925T220000Z"
    latest = quality_dir / "revalidations" / "20260925T223655123456Z"
    for run_dir, passed in ((earlier, False), (latest, True)):
        run_dir.mkdir(parents=True)
        (run_dir / "candidate_activation_gate.json").write_text(
            json.dumps(
                {
                    "generated_at": run_dir.name,
                    "passed": passed,
                    "data_version_hash": candidate_hash,
                    "failed_checks": [] if passed else ["regular_evaluation"],
                    "regular_evaluation_set_revision_id": current_revisions["regular"],
                    "structured_evaluation_set_revision_id": current_revisions["structured"],
                    "checks": [],
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "evaluation_regular.json").write_text(
            json.dumps(
                {
                    "case_count": 100,
                    "data_version_hash": candidate_hash,
                    "evaluation_set_hash": hashlib.sha256(regular_text.encode()).hexdigest(),
                    "failures": [] if passed else [{"id": "failed-case", "type": "table"}],
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "evaluation_structured.json").write_text(
            json.dumps(
                {
                    "case_count": 12,
                    "data_version_hash": candidate_hash,
                    "evaluation_set_hash": hashlib.sha256(structured_text.encode()).hexdigest(),
                    "failures": [],
                }
            ),
            encoding="utf-8",
        )

    store = JobStore(tmp_path / "jobs")
    job = Job(type="source_rebuild", status="failed", job_id="candidate-1")
    store.save(job)
    store.append_log(job.job_id, "error", "original gate failed", gate_report=str(old_gate))
    monkeypatch.setattr(admin, "DB_VERSIONS_DIR", versions_dir)
    monkeypatch.setattr(admin, "job_store", store)
    monkeypatch.setattr(admin, "resolve_published_asset", lambda set_id: current_assets[set_id])
    monkeypatch.setattr(admin, "published_revision_id", lambda set_id: current_revisions[set_id])
    app = FastAPI()
    app.include_router(admin.router)
    client = TestClient(app)

    response = client.get(f"/admin/jobs/{job.job_id}/candidate-gate-report")

    assert response.status_code == 200
    report = response.json()
    assert report["available"] is True
    assert report["report_source"] == "revalidation"
    assert report["candidate_version_id"] == "candidate-1"
    assert report["generated_at"] == "20260925T223655123456Z"
    assert report["passed"] is True
    assert report["evaluation_sets_current"] is True
    assert report["regular_evaluation"]["failure_count"] == 0
    assert store.read(job.job_id)["status"] == "failed"

    revalidation_job = Job(
        type="candidate_revalidation",
        status="succeeded",
        job_id="revalidation-1",
        params={"candidate_job_id": "candidate-1"},
        outputs={"gate_report": str(latest / "candidate_activation_gate.json")},
    )
    store.save(revalidation_job)
    independent_report = client.get(f"/admin/jobs/{revalidation_job.job_id}/candidate-gate-report")
    assert independent_report.status_code == 200
    assert independent_report.json()["available"] is True
    assert independent_report.json()["report_source"] == "revalidation"
    assert independent_report.json()["passed"] is True

    incomplete_latest = quality_dir / "revalidations" / "20260925T230000Z"
    incomplete_latest.mkdir()
    (incomplete_latest / "candidate_activation_gate.json").write_text(
        json.dumps({"passed": True}), encoding="utf-8"
    )
    incomplete_response = client.get(f"/admin/jobs/{job.job_id}/candidate-gate-report")
    assert incomplete_response.status_code == 200
    assert incomplete_response.json()["available"] is False
    assert store.read(job.job_id)["status"] == "failed"
