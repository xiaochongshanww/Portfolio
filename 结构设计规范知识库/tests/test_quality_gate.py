import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import src.quality.gate as quality_gate_module
from src.quality.gate import evaluate_quality_gate, render_quality_gate_markdown, summarize_jobs


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_job_summary_treats_later_success_as_resolution():
    now = datetime.now(UTC)
    jobs = [
        {
            "job_id": "old",
            "type": "rebuild",
            "status": "failed",
            "finished_at": (now - timedelta(days=2)).isoformat(),
        },
        {
            "job_id": "new",
            "type": "rebuild",
            "status": "succeeded",
            "finished_at": (now - timedelta(days=1)).isoformat(),
        },
    ]

    result = summarize_jobs(jobs, now=now)

    assert result["historical_failed_count"] == 1
    assert result["unresolved_failed_count"] == 0


def test_job_summary_detects_unresolved_and_stale_jobs():
    now = datetime.now(UTC)
    jobs = [
        {
            "job_id": "failed",
            "type": "evaluate",
            "status": "failed",
            "finished_at": (now - timedelta(minutes=5)).isoformat(),
        },
        {
            "job_id": "stale",
            "type": "rebuild",
            "status": "running",
            "started_at": (now - timedelta(hours=3)).isoformat(),
        },
    ]

    result = summarize_jobs(jobs, now=now)

    assert result["unresolved_failed_count"] == 1
    assert result["stale_active_count"] == 1


def test_quality_gate_passes_matching_artifacts(tmp_path: Path):
    regular_set = tmp_path / "regular.jsonl"
    structured_set = tmp_path / "structured.jsonl"
    answer_set = tmp_path / "answer.jsonl"
    regular_set.write_text("regular", encoding="utf-8")
    structured_set.write_text("structured", encoding="utf-8")
    answer_set.write_text("answer", encoding="utf-8")
    import hashlib

    data_version = "version-1"
    manifest = tmp_path / "manifest.json"
    active_db = tmp_path / "active_db.json"
    regular = tmp_path / "regular.json"
    structured = tmp_path / "structured.json"
    answer = tmp_path / "answer.json"
    _write_json(
        manifest,
        {
            "document_count": 2,
            "chunk_count": 10,
            "data_version_hash": data_version,
            "artifact_status": {"missing_required_count": 0},
            "audit_status": {"high_risk_count": 0},
        },
    )
    _write_json(
        active_db,
        {
            "manifest": str(manifest),
            "data_version_hash": data_version,
            "chunk_count": 10,
        },
    )
    provenance = {
        "ok": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "data_version_hash": data_version,
        "evidence_context_schema": 1,
        "verification_run_id": "a" * 32,
        "runtime_config_hash": "b" * 64,
    }
    _write_json(
        regular,
        {
            **provenance,
            "case_count": 100,
            "failures": [],
            "top1_source_hit_rate": 1.0,
            "authority_hit_rate": 1.0,
            "evaluation_set_hash": hashlib.sha256(regular_set.read_bytes()).hexdigest(),
        },
    )
    _write_json(
        structured,
        {
            **provenance,
            "case_count": 12,
            "failures": [],
            "structured_table_hit_rate": 1.0,
            "evaluation_set_hash": hashlib.sha256(structured_set.read_bytes()).hexdigest(),
        },
    )
    _write_json(
        answer,
        {
            **provenance,
            "case_count": 24,
            "pass_rate": 1.0,
            "refusal_pass_rate": 1.0,
            "check_rates": {
                "citations": 1.0,
                "citation_grounded": 1.0,
                "image_routes": 1.0,
                "image_offered": 1.0,
                "image_http": 1.0,
            },
            "evaluation_set_hash": hashlib.sha256(answer_set.read_bytes()).hexdigest(),
        },
    )

    result = evaluate_quality_gate(
        manifest_path=manifest,
        regular_report_path=regular,
        structured_report_path=structured,
        answer_report_path=answer,
        regular_eval_path=regular_set,
        structured_eval_path=structured_set,
        answer_eval_path=answer_set,
        active_db_path=active_db,
        jobs=[],
        runtime_collection_count=10,
        expected_verification_run_id="a" * 32,
        expected_runtime_config_hash="b" * 64,
    )

    assert result["passed"] is True
    assert result["verification_run_id"] == "a" * 32
    assert result["runtime_config_hash"] == "b" * 64
    assert "结论：通过" in render_quality_gate_markdown(result)

    mixed_structured = json.loads(structured.read_text(encoding="utf-8"))
    mixed_structured["verification_run_id"] = "c" * 32
    _write_json(structured, mixed_structured)
    mixed_run_result = evaluate_quality_gate(
        manifest_path=manifest,
        regular_report_path=regular,
        structured_report_path=structured,
        answer_report_path=answer,
        regular_eval_path=regular_set,
        structured_eval_path=structured_set,
        answer_eval_path=answer_set,
        active_db_path=active_db,
        jobs=[],
        expected_runtime_config_hash="b" * 64,
    )
    assert "evaluation_run_consistency" in mixed_run_result["failed_checks"]

    mixed_structured["verification_run_id"] = "a" * 32
    mixed_structured["runtime_config_hash"] = "d" * 64
    _write_json(structured, mixed_structured)
    mixed_config_result = evaluate_quality_gate(
        manifest_path=manifest,
        regular_report_path=regular,
        structured_report_path=structured,
        answer_report_path=answer,
        regular_eval_path=regular_set,
        structured_eval_path=structured_set,
        answer_eval_path=answer_set,
        active_db_path=active_db,
        jobs=[],
        expected_verification_run_id="a" * 32,
        expected_runtime_config_hash="b" * 64,
    )
    assert "runtime_config_consistency" in mixed_config_result["failed_checks"]

    mixed_structured["runtime_config_hash"] = "b" * 64
    _write_json(structured, mixed_structured)

    stale_regular = json.loads(regular.read_text(encoding="utf-8"))
    stale_regular["generated_at"] = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    _write_json(regular, stale_regular)
    stale_result = evaluate_quality_gate(
        manifest_path=manifest,
        regular_report_path=regular,
        structured_report_path=structured,
        answer_report_path=answer,
        regular_eval_path=regular_set,
        structured_eval_path=structured_set,
        answer_eval_path=answer_set,
        active_db_path=active_db,
        jobs=[],
        runtime_collection_count=10,
        expected_verification_run_id="a" * 32,
        expected_runtime_config_hash="b" * 64,
    )

    assert stale_result["passed"] is False
    assert "regular_report_freshness" in stale_result["failed_checks"]


def test_quality_gate_rejects_stale_report(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    active_db = tmp_path / "active_db.json"
    _write_json(
        manifest,
        {
            "document_count": 1,
            "chunk_count": 1,
            "data_version_hash": "new",
            "artifact_status": {"missing_required_count": 0},
            "audit_status": {"high_risk_count": 0},
        },
    )
    _write_json(
        active_db,
        {
            "manifest": str(manifest),
            "data_version_hash": "new",
            "chunk_count": 1,
        },
    )

    result = evaluate_quality_gate(
        manifest_path=manifest,
        regular_report_path=tmp_path / "missing-regular.json",
        structured_report_path=tmp_path / "missing-structured.json",
        answer_report_path=tmp_path / "missing-answer.json",
        regular_eval_path=tmp_path / "missing-regular.jsonl",
        structured_eval_path=tmp_path / "missing-structured.jsonl",
        answer_eval_path=tmp_path / "missing-answer.jsonl",
        active_db_path=active_db,
        jobs=[],
    )

    assert result["passed"] is False
    assert "evaluation_report_integrity" in result["failed_checks"]
    assert "regular_report_freshness" in result["failed_checks"]


def test_quality_gate_rejects_corrupt_latest_run_pointer(tmp_path: Path, monkeypatch):
    audit_dir = tmp_path / "audit"
    reports_dir = audit_dir / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "quality_run_latest.json").write_text("not-json", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    active_db = tmp_path / "active_db.json"
    _write_json(
        manifest,
        {
            "document_count": 1,
            "chunk_count": 1,
            "data_version_hash": "version",
            "artifact_status": {"missing_required_count": 0},
            "audit_status": {"high_risk_count": 0},
        },
    )
    _write_json(
        active_db,
        {"manifest": str(manifest), "data_version_hash": "version"},
    )
    monkeypatch.setattr(quality_gate_module, "AUDIT_DIR", audit_dir)

    result = evaluate_quality_gate(
        manifest_path=manifest,
        active_db_path=active_db,
        regular_eval_path=tmp_path / "regular.jsonl",
        structured_eval_path=tmp_path / "structured.jsonl",
        answer_eval_path=tmp_path / "answer.jsonl",
        jobs=[],
    )

    assert result["passed"] is False
    integrity = next(
        check for check in result["checks"] if check["name"] == "evaluation_report_integrity"
    )
    assert integrity["status"] == "failed"
    assert set(integrity["details"]["errors"].values()) == {"latest_pointer_invalid"}
