import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.app.admin.models import Job
from src.app.admin.storage import JobStore
from src.app.admin.workflows import CandidateActivationBlocked, rebuild_workflow
from src.app.core.config import Settings
from src.app.retrieval.hybrid_search import RetrievalState
from src.quality.candidate import CandidateActivationAssessment, assess_candidate_activation


def _manifest(path: Path, *, chunks: int = 3) -> dict:
    payload = {
        "document_count": 1,
        "chunk_count": chunks,
        "image_count": 2,
        "collection_name": "design_specs",
        "embedding_model": "embedding-2",
        "artifact_status": {"missing_required_count": 0},
        "audit_status": {"high_risk_count": 0},
        "correction_status": {"applied_count": 1},
        "data_version_hash": "a" * 64,
        "built_at": "2026-08-08T00:00:00+00:00",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _evaluation(path: Path, *, structured: bool = False) -> dict:
    return {
        "ok": True,
        "case_count": 12 if structured else 100,
        "failures": [],
        "top1_source_hit_rate": 1.0,
        "authority_hit_rate": 1.0,
        "structured_table_hit_rate": 1.0,
        "data_version_hash": "a" * 64,
        "evaluation_set_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _assessment(*, passed: bool, candidate_state: object | None = None) -> CandidateActivationAssessment:
    failed = [] if passed else ["regular_evaluation"]
    return CandidateActivationAssessment(
        result={
            "passed": passed,
            "failed_checks": failed,
            "data_version_hash": "a" * 64,
            "generated_at": "2026-08-08T00:01:00+00:00",
            "checks": [],
        },
        retrieval_state=candidate_state,
        regular_evaluation={"ok": passed, "case_count": 100, "failures": failed},
        structured_evaluation={"ok": True, "case_count": 12, "failures": []},
    )


def _patch_workflow_paths(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    import src.app.admin.workflows as workflows

    data = tmp_path / "data"
    pointer = data / "active_db.json"
    root_manifest = data / "manifest.json"
    monkeypatch.setattr(workflows, "DB_VERSIONS_DIR", data / "db_versions")
    monkeypatch.setattr(workflows, "ACTIVE_DB_PATH", pointer)
    monkeypatch.setattr(workflows, "MANIFEST_PATH", root_manifest)
    monkeypatch.setattr(workflows, "AUDIT_DIR", data / "audit")
    monkeypatch.setattr(workflows, "write_manual_structuring_queue", lambda _path: {})
    return pointer, root_manifest


def test_candidate_gate_evaluates_injected_database_without_active_state(tmp_path: Path, monkeypatch):
    manifest_path = tmp_path / "candidate" / "manifest.json"
    _manifest(manifest_path)
    regular_path = tmp_path / "regular.jsonl"
    structured_path = tmp_path / "structured.jsonl"
    regular_path.write_text("regular", encoding="utf-8")
    structured_path.write_text("structured", encoding="utf-8")
    fake_state = SimpleNamespace(ready=True, chroma_count=lambda: 3)
    monkeypatch.setattr(
        "src.quality.candidate.RetrievalState.load_candidate",
        lambda *_args, **_kwargs: fake_state,
    )

    def fake_run(path, **kwargs):
        assert kwargs["state"] is fake_state
        assert kwargs["manifest_path"] == manifest_path
        return _evaluation(path, structured=path == structured_path)

    monkeypatch.setattr("src.quality.candidate.run_evaluation", fake_run)
    result = assess_candidate_activation(
        manifest_path=manifest_path,
        db_dir=tmp_path / "candidate" / "db",
        config=Settings(zhipuai_api_key="test"),
        regular_eval_path=regular_path,
        structured_eval_path=structured_path,
    )

    assert result.result["passed"] is True
    assert result.retrieval_state is fake_state
    assert result.result["answer_evaluation_included"] is False


def test_candidate_gate_turns_evaluation_exceptions_into_blocking_evidence(tmp_path: Path, monkeypatch):
    manifest_path = tmp_path / "candidate" / "manifest.json"
    _manifest(manifest_path)
    regular_path = tmp_path / "regular.jsonl"
    structured_path = tmp_path / "structured.jsonl"
    regular_path.write_text("regular", encoding="utf-8")
    structured_path.write_text("structured", encoding="utf-8")
    fake_state = SimpleNamespace(ready=True, chroma_count=lambda: 3)
    monkeypatch.setattr(
        "src.quality.candidate.RetrievalState.load_candidate",
        lambda *_args, **_kwargs: fake_state,
    )
    monkeypatch.setattr(
        "src.quality.candidate.run_evaluation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("evaluation crashed")),
    )

    result = assess_candidate_activation(
        manifest_path=manifest_path,
        db_dir=tmp_path / "candidate" / "db",
        config=Settings(zhipuai_api_key="test"),
        regular_eval_path=regular_path,
        structured_eval_path=structured_path,
    )

    assert result.result["passed"] is False
    assert result.result["failed_checks"] == ["regular_evaluation", "structured_evaluation"]
    assert result.regular_evaluation["error"] == "evaluation crashed"
    assert result.structured_evaluation["error"] == "evaluation crashed"


def test_candidate_gate_rejects_incomplete_versioned_runtime_assets(tmp_path: Path, monkeypatch):
    manifest_path = tmp_path / "candidate" / "manifest.json"
    _manifest(manifest_path)
    regular_path = tmp_path / "regular.jsonl"
    structured_path = tmp_path / "structured.jsonl"
    regular_path.write_text("regular", encoding="utf-8")
    structured_path.write_text("structured", encoding="utf-8")
    processed_dir = tmp_path / "candidate" / "processed"
    images_dir = tmp_path / "candidate" / "images"
    processed_dir.mkdir()
    images_dir.mkdir()
    (images_dir / "only-one.png").write_bytes(b"png")
    fake_state = SimpleNamespace(ready=True, chroma_count=lambda: 3)
    monkeypatch.setattr(
        "src.quality.candidate.RetrievalState.load_candidate",
        lambda *_args, **_kwargs: fake_state,
    )
    monkeypatch.setattr(
        "src.quality.candidate.run_evaluation",
        lambda path, **_kwargs: _evaluation(path, structured=path == structured_path),
    )

    result = assess_candidate_activation(
        manifest_path=manifest_path,
        db_dir=tmp_path / "candidate" / "db",
        processed_dir=processed_dir,
        images_dir=images_dir,
        config=Settings(zhipuai_api_key="test"),
        regular_eval_path=regular_path,
        structured_eval_path=structured_path,
    )

    assert result.result["passed"] is False
    assert "processed_assets" in result.result["failed_checks"]
    assert "image_assets" in result.result["failed_checks"]


def test_rebuild_gate_failure_preserves_active_files(tmp_path: Path, monkeypatch):
    import src.app.admin.workflows as workflows

    pointer, root_manifest = _patch_workflow_paths(monkeypatch, tmp_path)
    pointer.parent.mkdir(parents=True)
    pointer.write_text('{"active_db_dir":"old"}', encoding="utf-8")
    root_manifest.write_text('{"data_version_hash":"old"}', encoding="utf-8")
    old_pointer = pointer.read_bytes()
    old_manifest = root_manifest.read_bytes()

    def fake_rebuild(*_args, **kwargs):
        return _manifest(kwargs["manifest_path"])

    monkeypatch.setattr(workflows.builder, "rebuild", fake_rebuild)
    monkeypatch.setattr(workflows, "assess_candidate_activation", lambda **_kwargs: _assessment(passed=False))
    store = JobStore(tmp_path / "jobs")
    job = Job(type="rebuild", params={}, job_id="candidate-fail")

    with pytest.raises(CandidateActivationBlocked):
        rebuild_workflow(job, store)

    assert pointer.read_bytes() == old_pointer
    assert root_manifest.read_bytes() == old_manifest
    assert (tmp_path / "data" / "db_versions" / "candidate-fail" / "quality" / "candidate_activation_gate.json").is_file()


def test_rebuild_activation_failure_rolls_back_pointer_and_manifest(tmp_path: Path, monkeypatch):
    import src.app.admin.workflows as workflows

    pointer, root_manifest = _patch_workflow_paths(monkeypatch, tmp_path)
    pointer.parent.mkdir(parents=True)
    pointer.write_text('{"active_db_dir":"old"}', encoding="utf-8")
    root_manifest.write_text('{"data_version_hash":"old"}', encoding="utf-8")
    old_pointer = pointer.read_bytes()
    old_manifest = root_manifest.read_bytes()

    def fake_rebuild(*_args, **kwargs):
        return _manifest(kwargs["manifest_path"])

    candidate_state = object()
    monkeypatch.setattr(workflows.builder, "rebuild", fake_rebuild)
    monkeypatch.setattr(
        workflows,
        "assess_candidate_activation",
        lambda **_kwargs: _assessment(passed=True, candidate_state=candidate_state),
    )
    monkeypatch.setattr(workflows.retrieval_state, "adopt", lambda _state: (_ for _ in ()).throw(RuntimeError("swap failed")))
    store = JobStore(tmp_path / "jobs")
    job = Job(type="rebuild", params={}, job_id="activation-fail")

    with pytest.raises(RuntimeError, match="swap failed"):
        rebuild_workflow(job, store)

    assert pointer.read_bytes() == old_pointer
    assert root_manifest.read_bytes() == old_manifest


def test_rebuild_success_activates_all_versioned_runtime_paths(tmp_path: Path, monkeypatch):
    import src.app.admin.workflows as workflows

    pointer, root_manifest = _patch_workflow_paths(monkeypatch, tmp_path)

    def fake_rebuild(*_args, **kwargs):
        for key in ("db_dir", "processed_dir", "images_dir", "mineru_output_dir", "audit_dir"):
            kwargs[key].mkdir(parents=True, exist_ok=True)
        return _manifest(kwargs["manifest_path"])

    candidate_state = object()
    adopted = []
    monkeypatch.setattr(workflows.builder, "rebuild", fake_rebuild)
    monkeypatch.setattr(
        workflows,
        "assess_candidate_activation",
        lambda **_kwargs: _assessment(passed=True, candidate_state=candidate_state),
    )
    monkeypatch.setattr(workflows.retrieval_state, "adopt", adopted.append)
    store = JobStore(tmp_path / "jobs")
    job = Job(type="rebuild", params={}, job_id="activation-ok")

    result = rebuild_workflow(job, store)
    active = json.loads(pointer.read_text(encoding="utf-8"))

    assert result["answer_evaluation_required"] is True
    assert adopted == [candidate_state]
    assert active["active_db_dir"].endswith("db_versions/activation-ok/db")
    assert active["processed_dir"].endswith("db_versions/activation-ok/processed")
    assert active["images_dir"].endswith("db_versions/activation-ok/images")
    assert active["mineru_dir"].endswith("db_versions/activation-ok/mineru")
    assert json.loads(root_manifest.read_text(encoding="utf-8"))["data_version_hash"] == "a" * 64


def test_rebuild_keeps_activation_success_when_latest_report_copy_fails(tmp_path: Path, monkeypatch):
    import src.app.admin.workflows as workflows

    _patch_workflow_paths(monkeypatch, tmp_path)

    def fake_rebuild(*_args, **kwargs):
        for key in ("db_dir", "processed_dir", "images_dir", "mineru_output_dir", "audit_dir"):
            kwargs[key].mkdir(parents=True, exist_ok=True)
        return _manifest(kwargs["manifest_path"])

    monkeypatch.setattr(workflows.builder, "rebuild", fake_rebuild)
    monkeypatch.setattr(
        workflows,
        "assess_candidate_activation",
        lambda **_kwargs: _assessment(passed=True, candidate_state=object()),
    )
    monkeypatch.setattr(workflows.retrieval_state, "adopt", lambda _state: None)
    monkeypatch.setattr(
        workflows,
        "_write_json_atomic",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("report disk full")),
    )
    store = JobStore(tmp_path / "jobs")
    job = Job(type="rebuild", params={}, job_id="report-warning")

    result = rebuild_workflow(job, store)

    assert result["latest_reports_published"] is False
    assert any(item["level"] == "warning" for item in store.logs(job.job_id))


def test_retrieval_reload_failure_preserves_previous_state(tmp_path: Path, monkeypatch):
    import src.app.retrieval.hybrid_search as hybrid

    state = RetrievalState(Settings(zhipuai_api_key="test"))
    old_client = object()
    old_collection = SimpleNamespace(count=lambda: 7)
    old_bm25 = object()
    state.chroma_client = old_client
    state.chroma_collection = old_collection
    state.bm25_index = old_bm25
    state.bm25_texts = ["old"]
    state.db_dir = tmp_path / "old"
    monkeypatch.setattr(hybrid, "chromadb", SimpleNamespace(PersistentClient=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("open failed"))))

    with pytest.raises(RuntimeError, match="open failed"):
        state.reload(tmp_path / "candidate")

    assert state.chroma_client is old_client
    assert state.chroma_collection is old_collection
    assert state.bm25_index is old_bm25
    assert state.bm25_texts == ["old"]
