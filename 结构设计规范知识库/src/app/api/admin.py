import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from src.evaluation.answer_runner import ANSWER_EVAL_PATH, load_answer_cases
from src.evaluation.runner import DEFAULT_EVAL_PATH, STRUCTURED_EVAL_PATH, load_cases
from src.pipeline.active_db import (
    active_processed_dir,
    read_active_db,
    read_active_manifest,
    resolve_pointer_path,
)
from src.pipeline.audit.corrections import (
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
    read_manual_structuring_draft,
    read_manual_structuring_file,
    rollback_manual_structuring_publication,
    save_manual_structuring_draft,
    update_manual_structuring_status,
    validate_manual_structuring_draft,
    write_manual_structuring_queue,
)
from src.pipeline.audit.multimodal import find_source_pdf, render_pdf_pages
from src.pipeline.audit.structuring_ai import read_structuring_suggestion
from src.pipeline.paths import (
    ACTIVE_DB_PATH,
    AUDIT_DIR,
    CORRECTIONS_DIR,
    MANUAL_STRUCTURING_DIR,
    RAW_DIR,
    STRUCTURED_TABLES_DIR,
)
from src.pipeline.version_retention import (
    VersionRetentionError,
    create_cleanup_plan,
    inventory_versions,
    retention_policy_from_settings,
    set_version_pin,
)
from src.quality import current_evidence_context, evaluate_quality_gate

from ..admin.job_diagnostics import diagnose_job, diagnose_jobs
from ..admin.jobs import job_manager
from ..admin.storage import job_store
from ..admin.workflows import (
    answer_evaluate_workflow,
    audit_workflow,
    cleanup_versions_workflow,
    dry_run_workflow,
    evaluate_workflow,
    rebuild_workflow,
    review_workflow,
    structuring_suggestion_batch_workflow,
    structuring_suggestion_workflow,
)
from ..core.config import settings
from ..retrieval.hybrid_search import retrieval_state

router = APIRouter(prefix="/admin", tags=["admin"])


def _diagnosed_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return diagnose_jobs(
        jobs,
        stale_after_seconds=settings.job_stale_after_seconds,
        heartbeat_timeout_seconds=max(60, settings.job_heartbeat_seconds * 3),
    )


class JobRequest(BaseModel):
    source: str = "data/raw"
    parser_backend: str = "mineru"
    apply_corrections: bool = True


class ReviewRequest(BaseModel):
    doc: str
    pages: str = ""


class EvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_k: int = Field(default=5, ge=1, le=100)
    evaluation_set: Literal["regular", "structured"] = "regular"
    verification_run_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")


class AnswerEvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation_set: Literal["answer"] = "answer"
    verification_run_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")


class CandidateStatusUpdate(BaseModel):
    status: str
    notes: str = ""


class ApprovedCorrectionRequest(BaseModel):
    id: str
    action: str = "replace_text"
    target: dict[str, Any]
    value: Any


class ManualStructuringDraftRequest(BaseModel):
    draft: dict[str, Any] = Field(default_factory=dict)


class StructuringSuggestionBatchRequest(BaseModel):
    documents: list[str] = Field(default_factory=list)
    force: bool = False


class VersionRetentionUpdate(BaseModel):
    pinned: bool
    note: str = Field(default="", max_length=500)


class VersionCleanupRequest(BaseModel):
    plan_id: str = Field(min_length=16, max_length=16)


def _safe_doc_stem(doc: str) -> str:
    return Path(doc).stem if doc.endswith((".pdf", ".json")) else doc


def _approved_path(doc: str) -> Path:
    return CORRECTIONS_DIR / "approved" / f"{_safe_doc_stem(doc)}.json"


def _load_processed_doc(doc: str) -> dict[str, Any]:
    stem = _safe_doc_stem(doc)
    candidates = sorted(active_processed_dir().glob(f"*{stem}*.json"))
    candidates = [path for path in candidates if not path.name.endswith("_chunks.json")]
    if not candidates:
        raise FileNotFoundError(f"processed document not found: {doc}")
    return json.loads(candidates[0].read_text(encoding="utf-8"))


@router.get("/status")
async def admin_status():
    manifest = read_active_manifest()
    return {
        "built": bool(manifest),
        "manifest": manifest or {},
        "quality_evidence_context": current_evidence_context(),
        "raw_documents": [path.name for path in sorted(RAW_DIR.glob("*.pdf"))],
        "jobs": _diagnosed_jobs(job_store.list()[:10]),
    }


@router.get("/documents")
async def admin_documents():
    manifest = read_active_manifest()
    return {
        "raw_documents": [path.name for path in sorted(RAW_DIR.glob("*.pdf"))],
        "manifest_documents": manifest.get("documents", []),
    }


@router.get("/manifest")
async def admin_manifest():
    return read_active_manifest()


@router.get("/active-db")
async def admin_active_db():
    payload = read_active_db()
    return {
        **payload,
        "loaded_db_dir": str(retrieval_state.db_dir or ""),
        "collection_count": retrieval_state.chroma_count(),
    }


@router.post("/retrieval/reload")
async def admin_retrieval_reload():
    retrieval_state.reload()
    return {
        "loaded_db_dir": str(retrieval_state.db_dir or ""),
        "collection_count": retrieval_state.chroma_count(),
    }


@router.post("/jobs/dry-run")
async def start_dry_run(request: JobRequest):
    return job_manager.submit("dry_run", request.dict(), dry_run_workflow).to_dict()


@router.post("/jobs/rebuild")
async def start_rebuild(request: JobRequest):
    return job_manager.submit("rebuild", request.dict(), rebuild_workflow).to_dict()


@router.get("/versions")
def admin_versions():
    return inventory_versions(
        policy=retention_policy_from_settings(settings),
        jobs=job_store.list(),
    )


@router.put("/versions/{version_id}/retention")
def admin_version_retention(version_id: str, request: VersionRetentionUpdate):
    try:
        return set_version_pin(version_id, pinned=request.pinned, note=request.note)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VersionRetentionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/versions/cleanup-plans")
def admin_version_cleanup_plan():
    return create_cleanup_plan(
        policy=retention_policy_from_settings(settings),
        jobs=job_store.list(),
    )


@router.post("/jobs/cleanup-versions")
async def start_version_cleanup(request: VersionCleanupRequest):
    return job_manager.submit(
        "cleanup_versions", request.dict(), cleanup_versions_workflow
    ).to_dict()


@router.post("/jobs/audit")
async def start_audit():
    return job_manager.submit("audit", {}, audit_workflow).to_dict()


@router.post("/jobs/review")
async def start_review(request: ReviewRequest):
    return job_manager.submit("review", request.dict(), review_workflow).to_dict()


@router.post("/jobs/evaluate")
async def start_evaluate(request: EvaluateRequest):
    return job_manager.submit("evaluate", request.model_dump(), evaluate_workflow).to_dict()


@router.post("/jobs/evaluate-answers")
async def start_answer_evaluate(request: AnswerEvaluateRequest):
    return job_manager.submit(
        "answer_evaluate", request.model_dump(), answer_evaluate_workflow
    ).to_dict()


@router.get("/jobs")
async def list_jobs():
    return {"jobs": _diagnosed_jobs(job_store.list())}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    try:
        job = job_store.read(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return diagnose_job(
        job,
        stale_after_seconds=settings.job_stale_after_seconds,
        heartbeat_timeout_seconds=max(60, settings.job_heartbeat_seconds * 3),
    )


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: str, limit: int = 200):
    try:
        logs = job_store.logs(job_id, limit=max(1, min(limit, 1000)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job_id, "logs": logs}


@router.get("/evaluation/status")
async def admin_evaluation_status():
    cases = load_cases(DEFAULT_EVAL_PATH)
    by_type: dict[str, int] = {}
    for case in cases:
        by_type[case.type] = by_type.get(case.type, 0) + 1
    latest_path = Path("data/audit/reports/evaluation_latest.json")
    latest = json.loads(latest_path.read_text(encoding="utf-8")) if latest_path.exists() else None
    structured_cases = load_cases(STRUCTURED_EVAL_PATH)
    structured_path = Path("data/audit/reports/evaluation_structured_latest.json")
    structured_latest = (
        json.loads(structured_path.read_text(encoding="utf-8"))
        if structured_path.exists()
        else None
    )
    answer_cases = load_answer_cases(ANSWER_EVAL_PATH)
    answer_path = Path("data/audit/reports/evaluation_answer_latest.json")
    answer_latest = (
        json.loads(answer_path.read_text(encoding="utf-8")) if answer_path.exists() else None
    )
    return {
        "case_count": len(cases),
        "by_type": by_type,
        "latest": latest,
        "structured_case_count": len(structured_cases),
        "structured_latest": structured_latest,
        "answer_case_count": len(answer_cases),
        "answer_latest": answer_latest,
    }


@router.get("/quality/status")
async def admin_quality_status():
    documents = list_manual_structuring_files()
    draft_statuses: dict[str, int] = {}
    for path in (MANUAL_STRUCTURING_DIR / "drafts").rglob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        status = str(payload.get("draft_status") or "needs_review")
        draft_statuses[status] = draft_statuses.get(status, 0) + 1
    blocked_suggestions = 0
    for path in (MANUAL_STRUCTURING_DIR / "suggestions").rglob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("proposal", {}).get("quality", {}).get("applicable") is False:
            blocked_suggestions += 1
    manual_publications = 0
    for path in STRUCTURED_TABLES_DIR.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("publication", {}).get("manual_item_id"):
            manual_publications += 1
    recent_jobs = job_store.list()[:100]
    quality_gate = evaluate_quality_gate(
        jobs=recent_jobs,
        runtime_collection_count=retrieval_state.chroma_count(),
        job_stale_after=timedelta(seconds=settings.job_stale_after_seconds),
    )
    job_status = quality_gate["jobs"]
    latest_path = AUDIT_DIR / "reports" / "evaluation_latest.json"
    structured_path = AUDIT_DIR / "reports" / "evaluation_structured_latest.json"
    answer_path = AUDIT_DIR / "reports" / "evaluation_answer_latest.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8")) if latest_path.exists() else {}
    structured = (
        json.loads(structured_path.read_text(encoding="utf-8")) if structured_path.exists() else {}
    )
    answer = json.loads(answer_path.read_text(encoding="utf-8")) if answer_path.exists() else {}
    active_db = read_active_db()
    candidate_gate_value = str(active_db.get("candidate_gate_report") or "")
    candidate_gate_path = (
        resolve_pointer_path(
            candidate_gate_value, ACTIVE_DB_PATH, AUDIT_DIR / "missing-candidate-gate.json"
        )
        if candidate_gate_value
        else None
    )
    candidate_gate = (
        json.loads(candidate_gate_path.read_text(encoding="utf-8"))
        if candidate_gate_path and candidate_gate_path.exists()
        else {}
    )
    return {
        "logical_task_count": sum(int(item.get("task_count", 0)) for item in documents),
        "pending_task_count": sum(int(item.get("pending_task_count", 0)) for item in documents),
        "suggestion_count": sum(int(item.get("suggestion_count", 0)) for item in documents),
        "suggestion_missing_count": sum(
            int(item.get("suggestion_missing_count", 0)) for item in documents
        ),
        "blocked_suggestion_count": blocked_suggestions,
        "draft_statuses": draft_statuses,
        "manual_publication_count": manual_publications,
        "recent_failed_job_count": job_status["unresolved_failed_count"],
        "unresolved_failed_job_count": job_status["unresolved_failed_count"],
        "historical_failed_job_count": job_status["historical_failed_count"],
        "stale_active_job_count": job_status["stale_active_count"],
        "quality_gate": quality_gate,
        "candidate_activation": {
            "available": bool(candidate_gate),
            "passed": candidate_gate.get("passed"),
            "failed_checks": candidate_gate.get("failed_checks", []),
            "generated_at": candidate_gate.get("generated_at"),
            "data_version_hash": candidate_gate.get("data_version_hash"),
            "answer_evaluation_included": candidate_gate.get("answer_evaluation_included", False),
        },
        "regular_evaluation": {
            "case_count": latest.get("case_count", 0),
            "authority_hit_rate": latest.get("authority_hit_rate"),
            "failure_count": len(latest.get("failures", [])),
        },
        "structured_evaluation": {
            "case_count": structured.get("case_count", 0),
            "structured_table_hit_rate": structured.get("structured_table_hit_rate"),
            "failure_count": len(structured.get("failures", [])),
        },
        "answer_evaluation": {
            "case_count": answer.get("case_count", 0),
            "pass_rate": answer.get("pass_rate"),
            "citation_grounded_rate": answer.get("check_rates", {}).get("citation_grounded"),
            "image_http_rate": answer.get("check_rates", {}).get("image_http"),
            "refusal_pass_rate": answer.get("refusal_pass_rate"),
            "failure_count": answer.get("failure_count", 0),
        },
        "external_dependencies": {
            "learned_reranker": (
                f"enabled:{settings.rerank_provider}"
                if settings.rerank_enabled
                else "available_disabled"
            ),
            "parser_upgrade": "external_infrastructure",
        },
    }


@router.get("/corrections/candidates")
async def admin_candidate_files():
    return {"documents": list_candidate_files(CORRECTIONS_DIR)}


@router.get("/corrections/candidates/{doc}")
async def admin_candidate_detail(doc: str):
    return read_candidate_file(doc, CORRECTIONS_DIR)


@router.patch("/corrections/candidates/{doc}/{candidate_id}")
async def admin_candidate_update(doc: str, candidate_id: str, request: CandidateStatusUpdate):
    try:
        return update_candidate_status(doc, candidate_id, request.status, CORRECTIONS_DIR)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/manual-structuring/scan")
async def admin_manual_structuring_scan():
    return write_manual_structuring_queue(active_processed_dir())


@router.post("/manual-structuring/ai-suggestions/batch")
async def admin_manual_structuring_batch_suggestions(request: StructuringSuggestionBatchRequest):
    return job_manager.submit(
        "structuring_suggestion_batch",
        request.dict(),
        structuring_suggestion_batch_workflow,
    ).to_dict()


@router.get("/manual-structuring")
async def admin_manual_structuring_files():
    return {"documents": list_manual_structuring_files()}


@router.get("/manual-structuring/{doc}")
async def admin_manual_structuring_detail(doc: str):
    return read_manual_structuring_file(doc)


@router.patch("/manual-structuring/{doc}/{item_id}")
async def admin_manual_structuring_update(doc: str, item_id: str, request: CandidateStatusUpdate):
    try:
        return update_manual_structuring_status(doc, item_id, request.status, notes=request.notes)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/manual-structuring/{doc}/{item_id}/draft")
async def admin_manual_structuring_build_draft(doc: str, item_id: str):
    try:
        return build_manual_structuring_draft(doc, item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/manual-structuring/{doc}/{item_id}/draft")
async def admin_manual_structuring_read_draft(doc: str, item_id: str):
    try:
        return read_manual_structuring_draft(doc, item_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/manual-structuring/{doc}/{item_id}/draft")
async def admin_manual_structuring_save_draft(
    doc: str, item_id: str, request: ManualStructuringDraftRequest
):
    try:
        return save_manual_structuring_draft(doc, item_id, request.draft)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/manual-structuring/{doc}/{item_id}/ai-suggestion")
async def admin_manual_structuring_start_suggestion(doc: str, item_id: str):
    try:
        read_manual_structuring_draft(doc, item_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return job_manager.submit(
        "structuring_suggestion",
        {"doc": doc, "item_id": item_id},
        structuring_suggestion_workflow,
    ).to_dict()


@router.get("/manual-structuring/{doc}/{item_id}/ai-suggestion")
async def admin_manual_structuring_read_suggestion(doc: str, item_id: str):
    try:
        return read_structuring_suggestion(doc, item_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/manual-structuring/{doc}/{item_id}/validate")
async def admin_manual_structuring_validate(doc: str, item_id: str):
    try:
        return validate_manual_structuring_draft(doc, item_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/manual-structuring/{doc}/{item_id}/publish")
async def admin_manual_structuring_publish(doc: str, item_id: str):
    try:
        return publish_manual_structuring_draft(doc, item_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/manual-structuring/{doc}/{item_id}/versions")
async def admin_manual_structuring_versions(doc: str, item_id: str):
    return {"versions": list_manual_structuring_versions(doc, item_id)}


@router.post("/manual-structuring/{doc}/{item_id}/rollback")
async def admin_manual_structuring_rollback(doc: str, item_id: str):
    try:
        return rollback_manual_structuring_publication(doc, item_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/corrections/promote/{doc}")
async def admin_promote(doc: str):
    return promote_approved_candidates(doc, CORRECTIONS_DIR)


@router.get("/corrections/approved/{doc}")
async def admin_get_approved(doc: str):
    path = _approved_path(doc)
    if not path.exists():
        return {"doc": _safe_doc_stem(doc), "corrections": []}
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/corrections/approved/{doc}")
async def admin_add_approved(doc: str, request: ApprovedCorrectionRequest):
    path = _approved_path(doc)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"corrections": []}
    corrections = payload.get("corrections", [])
    by_id = {str(item.get("id", index)): item for index, item in enumerate(corrections)}
    by_id[request.id] = request.dict()
    payload["corrections"] = list(by_id.values())
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "doc": _safe_doc_stem(doc),
        "approved_path": str(path),
        "correction_count": len(payload["corrections"]),
    }


@router.delete("/corrections/approved/{doc}/{correction_id}")
async def admin_delete_approved(doc: str, correction_id: str):
    path = _approved_path(doc)
    if not path.exists():
        raise HTTPException(status_code=404, detail="approved file not found")
    payload = json.loads(path.read_text(encoding="utf-8"))
    before = payload.get("corrections", [])
    after = [item for item in before if str(item.get("id")) != correction_id]
    payload["corrections"] = after
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"deleted": len(before) - len(after), "correction_count": len(after)}


@router.get("/elements/{doc}")
async def admin_elements(doc: str, page: int | None = None):
    try:
        payload = _load_processed_doc(doc)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    elements = payload.get("elements", [])
    rows = [
        {"element_index": index, **element}
        for index, element in enumerate(elements)
        if page is None or int(element.get("page", 0)) == page
    ]
    return {"doc": doc, "source_file": payload.get("source_file", ""), "elements": rows}


@router.get("/elements/{doc}/{element_index}")
async def admin_element(doc: str, element_index: int):
    try:
        payload = _load_processed_doc(doc)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    elements = payload.get("elements", [])
    if element_index < 0 or element_index >= len(elements):
        raise HTTPException(status_code=404, detail="element not found")
    return {"doc": doc, "element_index": element_index, **elements[element_index]}


@router.get("/page-image/{doc}/{page}")
async def admin_page_image(doc: str, page: int):
    pdf_path = find_source_pdf(doc, RAW_DIR)
    if not pdf_path:
        raise HTTPException(status_code=404, detail=f"source pdf not found: {doc}")
    rendered = render_pdf_pages(pdf_path, [page], AUDIT_DIR / "page_images")
    image_path = rendered.get(page)
    if not image_path or not image_path.exists():
        raise HTTPException(status_code=404, detail=f"page image not found: {doc} page {page}")
    return FileResponse(image_path, media_type="image/png")
