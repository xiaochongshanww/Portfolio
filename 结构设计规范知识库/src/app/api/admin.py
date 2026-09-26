import hashlib
import json
import re
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from src.evaluation.answer_runner import load_answer_cases
from src.evaluation.management import (
    EvaluationSetConflict,
    EvaluationSetError,
    EvaluationSetNotFound,
    list_quality_refresh_events,
    published_revision_id,
    resolve_published_asset,
)
from src.evaluation.management import (
    add_case as add_evaluation_case,
)
from src.evaluation.management import (
    create_draft as create_evaluation_draft,
)
from src.evaluation.management import (
    delete_case as delete_evaluation_case,
)
from src.evaluation.management import (
    diff_draft as diff_evaluation_draft,
)
from src.evaluation.management import (
    list_revisions as list_evaluation_revisions,
)
from src.evaluation.management import (
    list_sets as list_evaluation_sets,
)
from src.evaluation.management import (
    publish_draft as publish_evaluation_draft,
)
from src.evaluation.management import (
    read_revision as read_evaluation_revision,
)
from src.evaluation.management import (
    read_set as read_evaluation_set,
)
from src.evaluation.management import (
    rollback as rollback_evaluation_set,
)
from src.evaluation.management import (
    update_case as update_evaluation_case,
)
from src.evaluation.management import (
    validate_draft as validate_evaluation_draft,
)
from src.evaluation.runner import load_cases
from src.pipeline import builder
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
from src.pipeline.manifest import read_manifest
from src.pipeline.paths import (
    ACTIVE_DB_PATH,
    AUDIT_DIR,
    CORRECTIONS_DIR,
    DB_VERSIONS_DIR,
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
from src.quality import (
    QualityReportStoreError,
    compare_quality_runs,
    current_evidence_context,
    evaluate_quality_gate,
    list_complete_quality_runs,
    read_json_object,
    resolve_latest_quality_artifacts,
    validate_verification_run_id,
)

from ..admin.job_diagnostics import diagnose_job, diagnose_jobs
from ..admin.jobs import JobCancellationError, job_manager
from ..admin.source_management import source_catalog_store
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
from ..core.provider_probe import probe_model_providers
from ..retrieval.hybrid_search import retrieval_state
from ..schemas import admin as admin_schemas

router = APIRouter(prefix="/admin", tags=["admin"])
QUALITY_REPORTS_DIR = AUDIT_DIR / "reports"


def _quality_refresh_report_matches(
    report: dict[str, Any] | None,
    *,
    evaluation_set_id: str,
    revision_id: str,
    content_hash: str,
    data_version_hash: str,
) -> bool:
    if not isinstance(report, dict):
        return False
    if not all((evaluation_set_id, revision_id, content_hash, data_version_hash)):
        return False
    if report.get("evaluation_set_id") != evaluation_set_id:
        return False
    if report.get("evaluation_set_revision_id") != revision_id:
        return False
    if report.get("evaluation_set_hash") != content_hash:
        return False
    if report.get("data_version_hash") != data_version_hash:
        return False
    try:
        validate_verification_run_id(str(report.get("verification_run_id") or ""))
    except ValueError:
        return False
    return True


def _quality_refresh_status() -> dict[str, Any]:
    reports, _ = _read_latest_quality_reports(("regular_json", "structured_json", "answer_json"))
    try:
        active_manifest = read_active_manifest()
    except (OSError, TypeError, ValueError):
        active_manifest = {}
    active_data_version_hash = str(active_manifest.get("data_version_hash") or "")
    latest_by_type = {
        name: reports[key]
        for name, key in {
            "regular": "regular_json",
            "structured": "structured_json",
            "answer": "answer_json",
        }.items()
    }
    latest_events: dict[str, dict[str, Any]] = {}
    for event in list_quality_refresh_events(limit=500):
        set_id = str(event.get("evaluation_set_id") or "")
        if set_id in {"regular", "structured", "answer"} and set_id not in latest_events:
            latest_events[set_id] = event
    items: list[dict[str, Any]] = []
    for set_id, event in latest_events.items():
        report = latest_by_type.get(set_id)
        revision_id = str(event.get("revision_id") or "")
        content_hash = str(event.get("content_hash") or "")
        current = _quality_refresh_report_matches(
            report,
            evaluation_set_id=set_id,
            revision_id=revision_id,
            content_hash=content_hash,
            data_version_hash=active_data_version_hash,
        )
        items.append(
            {
                **event,
                "status": "completed" if current else "pending",
                "missing_report_types": [] if current else [set_id],
            }
        )
    pending = [item for item in items if item["status"] == "pending"]
    return {
        "pending_count": len(pending),
        "items": sorted(items, key=lambda item: str(item.get("created_at") or ""), reverse=True),
    }


def _read_latest_quality_reports(
    artifact_keys: tuple[str, ...],
) -> tuple[dict[str, dict[str, Any] | None], dict[str, str]]:
    try:
        paths = resolve_latest_quality_artifacts(QUALITY_REPORTS_DIR, artifact_keys)
    except (OSError, QualityReportStoreError, ValueError):
        return (
            {artifact_key: None for artifact_key in artifact_keys},
            {artifact_key: "quality_evidence_unavailable" for artifact_key in artifact_keys},
        )
    reports: dict[str, dict[str, Any] | None] = {}
    errors: dict[str, str] = {}
    for artifact_key, path in paths.items():
        try:
            reports[artifact_key] = read_json_object(path)
        except (OSError, QualityReportStoreError, ValueError):
            reports[artifact_key] = None
            errors[artifact_key] = "quality_evidence_unavailable"
    return reports, errors


def _diagnosed_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    diagnosed = diagnose_jobs(
        jobs,
        stale_after_seconds=settings.job_stale_after_seconds,
        heartbeat_timeout_seconds=max(60, settings.job_heartbeat_seconds * 3),
    )
    return [_candidate_republish_status(job) for job in diagnosed]


def _candidate_republish_status(job: dict[str, Any]) -> dict[str, Any]:
    result = {"candidate_republishable": False, "candidate_republish_reason": ""}
    if job.get("type") != "source_rebuild" or job.get("status") != "failed":
        return {**job, **result}
    params = job.get("params") if isinstance(job.get("params"), dict) else {}
    revision_id = str(params.get("source_catalog_revision") or "")
    if not revision_id:
        result["candidate_republish_reason"] = "任务没有关联来源版本，无法重试发布。"
        return {**job, **result}
    version_dir = DB_VERSIONS_DIR / str(job.get("job_id") or "")
    manifest_path = version_dir / "manifest.json"
    try:
        manifest = read_manifest(manifest_path)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        manifest = None
    if not manifest:
        result["candidate_republish_reason"] = "候选解析未完成，缺少版本清单。"
        return {**job, **result}
    build_params = manifest.get("build_params") if isinstance(manifest, dict) else None
    recorded_revision = (
        str(build_params.get("source_catalog_revision") or "")
        if isinstance(build_params, dict)
        else ""
    )
    if recorded_revision != revision_id:
        result["candidate_republish_reason"] = "候选版本与来源版本不一致，不能重试发布。"
        return {**job, **result}
    try:
        source_catalog_store.validate_republish_revision(revision_id)
    except (OSError, TypeError, ValueError, KeyError):
        result["candidate_republish_reason"] = "来源目录已变化或候选版本已失效，不能重试发布。"
        return {**job, **result}
    result["candidate_republishable"] = True
    return {**job, **result}


def _diagnosed_job(job: dict[str, Any]) -> dict[str, Any]:
    diagnosed = diagnose_job(
        job,
        stale_after_seconds=settings.job_stale_after_seconds,
        heartbeat_timeout_seconds=max(60, settings.job_heartbeat_seconds * 3),
    )
    return _candidate_republish_status(diagnosed)


def _candidate_evaluation_summary(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    failures = payload.get("failures")
    if not isinstance(failures, list):
        failures = []
    normalized_failures = [
        {
            "id": str(item.get("id") or ""),
            "type": str(item.get("type") or ""),
            "query": str(item.get("query") or ""),
            "expected_authority_type": str(item.get("expected_authority_type") or ""),
            **{
                key: item.get(key) if isinstance(item.get(key), bool) else None
                for key in (
                    "source_hit",
                    "top1_source_hit",
                    "clause_hit",
                    "keyword_hit",
                    "table_hit",
                    "authority_hit",
                    "structured_table_hit",
                )
            },
            "failed_checks": [
                str(value) for value in item.get("failed_checks", []) if isinstance(value, str)
            ]
            if isinstance(item.get("failed_checks"), list)
            else [],
            "top_results": [
                {
                    key: result[key]
                    for key in (
                        "source_file",
                        "clause_number",
                        "matched_clause_number",
                        "section_type",
                        "table_id",
                        "reason",
                        "score",
                    )
                    if key in result
                }
                for result in item.get("top_results", [])
                if isinstance(result, dict)
            ][:5]
            if isinstance(item.get("top_results"), list)
            else [],
            "top_structured_results": [
                {
                    key: result[key]
                    for key in ("table_id", "table_name", "reason", "score")
                    if key in result
                }
                for result in item.get("top_structured_results", [])
                if isinstance(result, dict)
            ][:5]
            if isinstance(item.get("top_structured_results"), list)
            else [],
        }
        for item in failures[:50]
        if isinstance(item, dict)
    ]
    return {
        "case_count": int(payload.get("case_count") or 0),
        "failure_count": len(failures),
        "top1_source_hit_rate": payload.get("top1_source_hit_rate"),
        "authority_hit_rate": payload.get("authority_hit_rate"),
        "structured_table_hit_rate": payload.get("structured_table_hit_rate"),
        "failures": normalized_failures,
        "failures_truncated": len(failures) > len(normalized_failures),
    }


def _candidate_evaluation_set_status(
    evaluation_set_id: Literal["regular", "structured"],
    gate_payload: dict[str, Any],
    evaluation_payload: dict[str, Any],
) -> dict[str, str]:
    snapshot_revision_id = str(
        gate_payload.get(f"{evaluation_set_id}_evaluation_set_revision_id") or ""
    )
    report_hash = str(evaluation_payload.get("evaluation_set_hash") or "")
    current_revision_id = ""
    current_hash = ""
    try:
        current_revision_id = published_revision_id(evaluation_set_id)
        current_path = resolve_published_asset(evaluation_set_id)
        current_hash = hashlib.sha256(current_path.read_bytes()).hexdigest()
    except (OSError, TypeError, ValueError):
        pass

    if report_hash and current_hash:
        hash_matches = report_hash == current_hash
        revision_matches = not snapshot_revision_id or snapshot_revision_id == current_revision_id
        freshness = "current" if hash_matches and revision_matches else "stale"
    elif snapshot_revision_id and current_revision_id:
        freshness = "current" if snapshot_revision_id == current_revision_id else "stale"
    else:
        freshness = "unknown"

    return {
        "evaluation_set_id": evaluation_set_id,
        "snapshot_revision_id": snapshot_revision_id,
        "current_revision_id": current_revision_id,
        "freshness": freshness,
    }


def _read_candidate_gate_details(job_id: str, job: dict[str, Any]) -> dict[str, Any]:
    job_type = str(job.get("type") or "")
    params = job.get("params") if isinstance(job.get("params"), dict) else {}
    candidate_version_id = (
        str(params.get("candidate_job_id") or "")
        if job_type in {"source_republish", "candidate_revalidation"}
        else job_id
    )
    allowed_job_types = {"source_rebuild", "source_republish", "candidate_revalidation"}
    if job_type not in allowed_job_types or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", candidate_version_id
    ):
        return {"job_id": job_id, "available": False, "reason": "该任务未关联有效的候选版本。"}

    report_source = "activation"
    gate_path: Path | None = None
    try:
        versions_root = DB_VERSIONS_DIR.resolve()
        candidate_root = (versions_root / candidate_version_id).resolve(strict=True)
        if not candidate_root.is_relative_to(versions_root):
            raise ValueError("candidate version is outside the versions directory")
        quality_root = candidate_root / "quality"
        revalidations_root = quality_root / "revalidations"
        if job_type == "candidate_revalidation":
            outputs = job.get("outputs") if isinstance(job.get("outputs"), dict) else {}
            report_reference = str(outputs.get("gate_report") or "")
            if not report_reference:
                return {
                    "job_id": job_id,
                    "available": False,
                    "reason": "本次独立复核未生成完整报告。",
                }
            report_source = "revalidation"
            gate_path = Path(report_reference)
        elif revalidations_root.is_dir():
            run_dirs = sorted(
                path
                for path in revalidations_root.iterdir()
                if path.is_dir() and re.fullmatch(r"\d{8}T\d{6}(?:\d{6})?Z", path.name)
            )
            if run_dirs:
                report_source = "revalidation"
                gate_path = run_dirs[-1] / "candidate_activation_gate.json"

        if gate_path is None and job_type != "candidate_revalidation":
            logs = job_store.logs(job_id, limit=1000)
            report_reference = next(
                (
                    str(item.get("gate_report"))
                    for item in reversed(logs)
                    if isinstance(item, dict) and item.get("gate_report")
                ),
                "",
            )
            if not report_reference:
                return {"job_id": job_id, "available": False, "reason": "该任务没有候选门禁报告。"}
            gate_path = Path(report_reference)

        gate_path = gate_path.resolve(strict=True)
        if report_source == "revalidation":
            expected_parent = (quality_root / "revalidations").resolve(strict=True)
            if (
                not gate_path.parent.parent.is_relative_to(candidate_root)
                or gate_path.parent.parent != expected_parent
                or not re.fullmatch(r"\d{8}T\d{6}(?:\d{6})?Z", gate_path.parent.name)
            ):
                raise ValueError("invalid candidate revalidation report path")
        else:
            expected_parent = quality_root.resolve(strict=True)
            if gate_path.parent != expected_parent:
                raise ValueError("invalid candidate activation report path")
        if (
            not gate_path.is_relative_to(versions_root)
            or gate_path.name != "candidate_activation_gate.json"
        ):
            raise ValueError("invalid candidate gate report reference")
        quality_dir = gate_path.parent
        gate_payload = json.loads(gate_path.read_text(encoding="utf-8"))
        regular_path = (quality_dir / "evaluation_regular.json").resolve(strict=True)
        structured_path = (quality_dir / "evaluation_structured.json").resolve(strict=True)
        if (
            not regular_path.is_relative_to(versions_root)
            or not structured_path.is_relative_to(versions_root)
            or regular_path.parent != quality_dir
            or structured_path.parent != quality_dir
        ):
            raise ValueError("candidate evaluation report is outside the versions directory")
        regular_payload = json.loads(regular_path.read_text(encoding="utf-8"))
        structured_payload = json.loads(structured_path.read_text(encoding="utf-8"))
        if not all(
            isinstance(item, dict) for item in (gate_payload, regular_payload, structured_payload)
        ):
            raise ValueError("candidate reports must be JSON objects")
        if report_source == "revalidation":
            manifest_path = (candidate_root / "manifest.json").resolve(strict=True)
            if not manifest_path.is_relative_to(candidate_root):
                raise ValueError("candidate manifest is outside its version directory")
            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(manifest_payload, dict):
                raise ValueError("candidate manifest must be a JSON object")
            candidate_hash = str(manifest_payload.get("data_version_hash") or "")
            report_hashes = [
                str(payload.get("data_version_hash") or "")
                for payload in (gate_payload, regular_payload, structured_payload)
            ]
            if not candidate_hash or any(value != candidate_hash for value in report_hashes):
                raise ValueError(
                    "candidate revalidation reports do not match the candidate manifest"
                )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return {"job_id": job_id, "available": False, "reason": "候选门禁报告不存在或引用无效。"}

    evaluation_set_status = [
        _candidate_evaluation_set_status("regular", gate_payload, regular_payload),
        _candidate_evaluation_set_status("structured", gate_payload, structured_payload),
    ]
    freshness_values = [item["freshness"] for item in evaluation_set_status]
    if "stale" in freshness_values:
        evaluation_sets_current = False
    elif "unknown" in freshness_values:
        evaluation_sets_current = None
    else:
        evaluation_sets_current = True

    return {
        "job_id": job_id,
        "available": True,
        "report_source": report_source,
        "candidate_version_id": candidate_version_id,
        "generated_at": str(gate_payload.get("generated_at") or ""),
        "passed": gate_payload.get("passed"),
        "failed_checks": [
            str(item) for item in gate_payload.get("failed_checks", []) if isinstance(item, str)
        ]
        if isinstance(gate_payload.get("failed_checks"), list)
        else [],
        "checks": [
            {
                key: str(item.get(key) or "")
                for key in ("name", "status", "severity", "message")
                if key in item
            }
            for item in gate_payload.get("checks", [])[:100]
            if isinstance(item, dict)
        ]
        if isinstance(gate_payload.get("checks"), list)
        else [],
        "evaluation_sets_current": evaluation_sets_current,
        "evaluation_set_status": evaluation_set_status,
        "regular_evaluation": _candidate_evaluation_summary(regular_payload),
        "structured_evaluation": _candidate_evaluation_summary(structured_payload),
    }


class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = "data/raw"
    parser_backend: str = "mineru"
    apply_corrections: bool = True
    mode: Literal["incremental", "full"] = "incremental"


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


@router.get("/status", response_model=admin_schemas.AdminStatusResponse)
async def admin_status():
    manifest = read_active_manifest()
    return {
        "built": bool(manifest),
        "manifest": manifest or {},
        "quality_evidence_context": current_evidence_context(),
        "raw_documents": [path.name for path in sorted(RAW_DIR.glob("*.pdf"))],
        "jobs": _diagnosed_jobs(job_store.list()[:10]),
    }


@router.post("/provider-probes", response_model=admin_schemas.ProviderProbesResponse)
async def admin_provider_probes():
    return await probe_model_providers(embedding_client=retrieval_state.zhipu_client)


@router.get("/documents", response_model=admin_schemas.DocumentsResponse)
async def admin_documents():
    manifest = read_active_manifest()
    return {
        "raw_documents": [path.name for path in sorted(RAW_DIR.glob("*.pdf"))],
        "manifest_documents": manifest.get("documents", []),
    }


@router.get(
    "/manifest",
    response_model=admin_schemas.ManifestResponse,
    response_model_exclude_unset=True,
)
async def admin_manifest():
    return read_active_manifest()


@router.get(
    "/active-db",
    response_model=admin_schemas.ActiveDatabaseResponse,
    response_model_exclude_unset=True,
)
async def admin_active_db():
    payload = read_active_db()
    return {
        **payload,
        "loaded_db_dir": str(retrieval_state.db_dir or ""),
        "collection_count": retrieval_state.chroma_count(),
    }


@router.post("/retrieval/reload", response_model=admin_schemas.RetrievalReloadResponse)
async def admin_retrieval_reload():
    retrieval_state.reload()
    return {
        "loaded_db_dir": str(retrieval_state.db_dir or ""),
        "collection_count": retrieval_state.chroma_count(),
    }


@router.post("/jobs/dry-run", response_model=admin_schemas.JobResponse)
async def start_dry_run(request: JobRequest):
    return job_manager.submit("dry_run", request.model_dump(), dry_run_workflow).to_dict()


@router.post("/rebuild-plan", response_model=admin_schemas.RebuildPlanResponse)
async def admin_rebuild_plan(request: JobRequest):
    try:
        return builder.incremental_plan(
            Path(request.source),
            parser_backend=request.parser_backend,
            apply_corrections=request.apply_corrections,
            requested_mode=request.mode,
        )
    except (FileNotFoundError, ValueError, builder.BuildPreflightError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/rebuild", response_model=admin_schemas.JobResponse)
async def start_rebuild(request: JobRequest):
    return job_manager.submit("rebuild", request.model_dump(), rebuild_workflow).to_dict()


@router.get("/versions", response_model=admin_schemas.VersionInventoryResponse)
def admin_versions(
    q: str = Query(default="", max_length=256, description="匹配版本 ID、错误或保护原因"),
    state: Literal[
        "",
        "active",
        "running",
        "passed",
        "failed_gate",
        "invalid_gate",
        "legacy_complete",
        "incomplete",
        "unsafe",
    ] = Query(default="", description="按版本状态筛选"),
    scope: Literal["", "cleanup", "protected", "pinned"] = Query(
        default="", description="按治理范围筛选"
    ),
    offset: int = Query(default=0, ge=0, description="匹配结果的起始偏移量"),
    limit: int = Query(default=0, ge=0, le=200, description="返回条数；0 表示返回全部"),
):
    return inventory_versions(
        policy=retention_policy_from_settings(settings),
        jobs=job_store.list(),
        query=q,
        state=state,
        scope=scope,
        offset=offset,
        limit=limit,
    )


@router.put(
    "/versions/{version_id}/retention",
    response_model=admin_schemas.VersionRetentionResponse,
)
def admin_version_retention(version_id: str, request: VersionRetentionUpdate):
    try:
        return set_version_pin(version_id, pinned=request.pinned, note=request.note)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VersionRetentionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/versions/cleanup-plans",
    response_model=admin_schemas.VersionCleanupPlanResponse,
)
def admin_version_cleanup_plan():
    return create_cleanup_plan(
        policy=retention_policy_from_settings(settings),
        jobs=job_store.list(),
    )


@router.post("/jobs/cleanup-versions", response_model=admin_schemas.JobResponse)
async def start_version_cleanup(request: VersionCleanupRequest):
    return job_manager.submit(
        "cleanup_versions", request.model_dump(), cleanup_versions_workflow
    ).to_dict()


@router.post("/jobs/audit", response_model=admin_schemas.JobResponse)
async def start_audit():
    return job_manager.submit("audit", {}, audit_workflow).to_dict()


@router.post("/jobs/review", response_model=admin_schemas.JobResponse)
async def start_review(request: ReviewRequest):
    return job_manager.submit("review", request.model_dump(), review_workflow).to_dict()


@router.post("/jobs/evaluate", response_model=admin_schemas.JobResponse)
async def start_evaluate(request: EvaluateRequest):
    return job_manager.submit("evaluate", request.model_dump(), evaluate_workflow).to_dict()


@router.post("/jobs/evaluate-answers", response_model=admin_schemas.JobResponse)
async def start_answer_evaluate(request: AnswerEvaluateRequest):
    return job_manager.submit(
        "answer_evaluate", request.model_dump(), answer_evaluate_workflow
    ).to_dict()


@router.get("/jobs", response_model=admin_schemas.JobsResponse)
async def list_jobs():
    return {"jobs": _diagnosed_jobs(job_store.list())}


@router.get("/jobs/{job_id}", response_model=admin_schemas.JobResponse)
async def get_job(job_id: str):
    try:
        job = job_store.read(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return _diagnosed_job(job)


@router.post("/jobs/{job_id}/cancel", response_model=admin_schemas.JobResponse)
async def cancel_job(job_id: str):
    try:
        job = job_manager.cancel(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    except JobCancellationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _diagnosed_job(job.to_dict())


@router.post("/jobs/{job_id}/resolve", response_model=admin_schemas.JobResponse)
async def resolve_job(job_id: str, request: admin_schemas.JobResolutionRequest):
    try:
        job = job_store.resolve_failed(
            job_id,
            status=request.status,
            note=request.note,
            related_job_id=request.related_job_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _diagnosed_job(job)


@router.get("/jobs/{job_id}/logs", response_model=admin_schemas.JobLogsResponse)
async def get_job_logs(job_id: str, limit: int = 200):
    try:
        logs = job_store.logs(job_id, limit=max(1, min(limit, 1000)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job_id, "logs": logs}


@router.get(
    "/jobs/{job_id}/candidate-gate-report",
    response_model=admin_schemas.CandidateGateDetailsResponse,
)
async def get_candidate_gate_report(job_id: str):
    try:
        job = job_store.read(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return _read_candidate_gate_details(job_id, job)


@router.get("/evaluation/status", response_model=admin_schemas.EvaluationStatusResponse)
async def admin_evaluation_status():
    regular_path = resolve_published_asset("regular")
    structured_path = resolve_published_asset("structured")
    answer_path = resolve_published_asset("answer")
    cases = load_cases(regular_path)
    by_type: dict[str, int] = {}
    for case in cases:
        by_type[case.type] = by_type.get(case.type, 0) + 1
    reports, report_errors = _read_latest_quality_reports(
        ("regular_json", "structured_json", "answer_json")
    )
    latest = reports["regular_json"]
    structured_cases = load_cases(structured_path)
    structured_latest = reports["structured_json"]
    answer_cases = load_answer_cases(answer_path)
    answer_latest = reports["answer_json"]
    return {
        "case_count": len(cases),
        "by_type": by_type,
        "latest": latest,
        "structured_case_count": len(structured_cases),
        "structured_latest": structured_latest,
        "answer_case_count": len(answer_cases),
        "answer_latest": answer_latest,
        "quality_evidence_errors": {
            name: report_errors[key]
            for name, key in {
                "regular": "regular_json",
                "structured": "structured_json",
                "answer": "answer_json",
            }.items()
            if key in report_errors
        },
    }


def _load_evaluation_cases(
    evaluation_set: Literal["regular", "structured", "answer"],
):
    path = resolve_published_asset(evaluation_set)
    if evaluation_set == "structured":
        return load_cases(path)
    if evaluation_set == "answer":
        return load_answer_cases(path)
    return load_cases(path)


def _evaluation_case_search_text(case: Any) -> str:
    values: list[str] = [str(getattr(case, field, "")) for field in ("id", "query", "type")]
    for field in (
        "expected_sources",
        "expected_keywords",
        "expected_all",
        "forbidden_terms",
        "expected_citations",
        "expected_unit_groups",
    ):
        value = getattr(case, field, [])
        values.extend(str(item) for item in value)
    values.extend(
        str(getattr(case, field, ""))
        for field in ("expected_clause", "expected_authority_type", "expected_table_id")
    )
    return " ".join(values).casefold()


def _serialize_evaluation_case(case: Any) -> dict[str, Any]:
    return {
        "id": case.id,
        "query": case.query,
        "type": case.type,
        "expected_sources": list(getattr(case, "expected_sources", [])),
        "expected_clause": getattr(case, "expected_clause", ""),
        "expected_keywords": list(getattr(case, "expected_keywords", None) or []),
        "expected_authority_type": getattr(case, "expected_authority_type", ""),
        "top1_source_required": bool(getattr(case, "top1_source_required", True)),
        "keyword_required": bool(getattr(case, "keyword_required", True)),
        "expected_table_id": getattr(case, "expected_table_id", ""),
        "expected_all": list(getattr(case, "expected_all", [])),
        "expected_any_groups": [list(group) for group in getattr(case, "expected_any_groups", [])],
        "forbidden_terms": list(getattr(case, "forbidden_terms", [])),
        "expected_citations": list(getattr(case, "expected_citations", [])),
        "expected_unit_groups": [
            list(group) for group in getattr(case, "expected_unit_groups", [])
        ],
        "requires_refusal": bool(getattr(case, "requires_refusal", False)),
        "requires_image": bool(getattr(case, "requires_image", True)),
    }


@router.get("/evaluation/cases", response_model=admin_schemas.EvaluationCasesResponse)
async def admin_evaluation_cases(
    evaluation_set: Literal["regular", "structured", "answer"] = "regular",
    search: str = Query(default="", max_length=200),
    case_type: str = Query(default="", max_length=64),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
):
    cases = _load_evaluation_cases(evaluation_set)
    normalized_search = search.strip().casefold()
    filtered = [
        case
        for case in cases
        if (not case_type or case.type == case_type)
        and (not normalized_search or normalized_search in _evaluation_case_search_text(case))
    ]
    type_counts: dict[str, int] = {}
    for case in cases:
        type_counts[case.type] = type_counts.get(case.type, 0) + 1
    return {
        "evaluation_set": evaluation_set,
        "total": len(filtered),
        "offset": offset,
        "limit": limit,
        "type_counts": dict(sorted(type_counts.items())),
        "cases": [_serialize_evaluation_case(case) for case in filtered[offset : offset + limit]],
    }


def _evaluation_set_error(exc: EvaluationSetError) -> HTTPException:
    if isinstance(exc, EvaluationSetNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, EvaluationSetConflict):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/evaluation/sets", response_model=admin_schemas.EvaluationSetsResponse)
async def admin_evaluation_sets():
    try:
        return {"sets": list_evaluation_sets()}
    except EvaluationSetError as exc:
        raise _evaluation_set_error(exc) from exc


@router.get(
    "/evaluation/sets/{evaluation_set_id}/revisions",
    response_model=admin_schemas.EvaluationRevisionsResponse,
)
async def admin_evaluation_set_revisions(evaluation_set_id: str):
    try:
        return {
            "evaluation_set_id": evaluation_set_id,
            "revisions": list_evaluation_revisions(evaluation_set_id),
        }
    except EvaluationSetError as exc:
        raise _evaluation_set_error(exc) from exc


@router.get(
    "/evaluation/sets/{evaluation_set_id}/revisions/{revision_id}",
    response_model=admin_schemas.EvaluationRevisionResponse,
)
async def admin_evaluation_set_revision(evaluation_set_id: str, revision_id: str):
    try:
        revision, cases = read_evaluation_revision(evaluation_set_id, revision_id)
        return {"evaluation_set_id": evaluation_set_id, "revision": revision, "cases": cases}
    except EvaluationSetError as exc:
        raise _evaluation_set_error(exc) from exc


@router.get(
    "/evaluation/sets/{evaluation_set_id}", response_model=admin_schemas.EvaluationSetResponse
)
async def admin_evaluation_set(evaluation_set_id: str):
    try:
        return read_evaluation_set(evaluation_set_id)
    except EvaluationSetError as exc:
        raise _evaluation_set_error(exc) from exc


@router.post(
    "/evaluation/sets/{evaluation_set_id}/drafts",
    response_model=admin_schemas.EvaluationDraftResponse,
)
async def admin_evaluation_set_create_draft(
    evaluation_set_id: str, request: admin_schemas.EvaluationDraftRequest | None = None
):
    try:
        return create_evaluation_draft(evaluation_set_id, reset=bool(request and request.reset))
    except EvaluationSetError as exc:
        raise _evaluation_set_error(exc) from exc


@router.patch(
    "/evaluation/sets/{evaluation_set_id}/drafts/{case_id}",
    response_model=admin_schemas.EvaluationDraftResponse,
)
async def admin_evaluation_set_update_case(
    evaluation_set_id: str,
    case_id: str,
    request: admin_schemas.EvaluationCaseMutationRequest,
):
    try:
        return update_evaluation_case(evaluation_set_id, case_id, request.case)
    except EvaluationSetError as exc:
        raise _evaluation_set_error(exc) from exc


@router.post(
    "/evaluation/sets/{evaluation_set_id}/drafts/cases",
    response_model=admin_schemas.EvaluationDraftResponse,
)
async def admin_evaluation_set_add_case(
    evaluation_set_id: str, request: admin_schemas.EvaluationCaseMutationRequest
):
    try:
        return add_evaluation_case(evaluation_set_id, request.case)
    except EvaluationSetError as exc:
        raise _evaluation_set_error(exc) from exc


@router.delete(
    "/evaluation/sets/{evaluation_set_id}/drafts/{case_id}",
    response_model=admin_schemas.EvaluationDraftResponse,
)
async def admin_evaluation_set_delete_case(evaluation_set_id: str, case_id: str):
    try:
        return delete_evaluation_case(evaluation_set_id, case_id)
    except EvaluationSetError as exc:
        raise _evaluation_set_error(exc) from exc


@router.post(
    "/evaluation/sets/{evaluation_set_id}/validate",
    response_model=admin_schemas.EvaluationValidationResponse,
)
async def admin_evaluation_set_validate(evaluation_set_id: str):
    try:
        return validate_evaluation_draft(evaluation_set_id)
    except EvaluationSetError as exc:
        raise _evaluation_set_error(exc) from exc


@router.get(
    "/evaluation/sets/{evaluation_set_id}/diff",
    response_model=admin_schemas.EvaluationDiffResponse,
)
async def admin_evaluation_set_diff(evaluation_set_id: str):
    try:
        return diff_evaluation_draft(evaluation_set_id)
    except EvaluationSetError as exc:
        raise _evaluation_set_error(exc) from exc


@router.post(
    "/evaluation/sets/{evaluation_set_id}/publish",
    response_model=admin_schemas.EvaluationPublishResponse,
)
async def admin_evaluation_set_publish(evaluation_set_id: str):
    try:
        return publish_evaluation_draft(evaluation_set_id)
    except EvaluationSetError as exc:
        raise _evaluation_set_error(exc) from exc


@router.post(
    "/evaluation/sets/{evaluation_set_id}/rollback",
    response_model=admin_schemas.EvaluationPublishResponse,
)
async def admin_evaluation_set_rollback(
    evaluation_set_id: str, request: admin_schemas.EvaluationRollbackRequest
):
    try:
        return rollback_evaluation_set(evaluation_set_id, request.revision_id)
    except EvaluationSetError as exc:
        raise _evaluation_set_error(exc) from exc


@router.get("/quality/runs", response_model=admin_schemas.QualityRunsResponse)
async def admin_quality_runs(limit: int = Query(default=50, ge=1, le=200)):
    try:
        return {"runs": list_complete_quality_runs(QUALITY_REPORTS_DIR, limit=limit)}
    except (OSError, QualityReportStoreError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/quality/runs/compare",
    response_model=admin_schemas.QualityReportCompareResponse,
)
async def admin_quality_runs_compare(
    baseline_run_id: str = Query(..., min_length=32, max_length=32, pattern=r"^[0-9a-f]{32}$"),
    candidate_run_id: str = Query(..., min_length=32, max_length=32, pattern=r"^[0-9a-f]{32}$"),
):
    try:
        return {
            "comparison": compare_quality_runs(
                QUALITY_REPORTS_DIR,
                baseline_run_id,
                candidate_run_id,
            )
        }
    except (OSError, QualityReportStoreError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/quality/status", response_model=admin_schemas.QualityStatusResponse)
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
    reports, report_errors = _read_latest_quality_reports(
        ("regular_json", "structured_json", "answer_json")
    )
    latest_report = reports["regular_json"]
    structured_report = reports["structured_json"]
    answer_report = reports["answer_json"]
    latest = latest_report or {}
    structured = structured_report or {}
    answer = answer_report or {}
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
        "quality_evidence_errors": {
            name: report_errors[key]
            for name, key in {
                "regular": "regular_json",
                "structured": "structured_json",
                "answer": "answer_json",
            }.items()
            if key in report_errors
        },
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
        "evaluation_refresh": _quality_refresh_status(),
    }


@router.get("/corrections/candidates", response_model=admin_schemas.CandidateDocumentsResponse)
async def admin_candidate_files():
    return {"documents": list_candidate_files(CORRECTIONS_DIR)}


@router.get("/corrections/candidates/{doc}", response_model=admin_schemas.CandidateDetailResponse)
async def admin_candidate_detail(doc: str):
    return read_candidate_file(doc, CORRECTIONS_DIR)


@router.patch(
    "/corrections/candidates/{doc}/{candidate_id}",
    response_model=admin_schemas.CandidateStatusResponse,
)
async def admin_candidate_update(doc: str, candidate_id: str, request: CandidateStatusUpdate):
    try:
        return update_candidate_status(doc, candidate_id, request.status, CORRECTIONS_DIR)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/manual-structuring/scan", response_model=admin_schemas.ManualQueueScanResponse)
async def admin_manual_structuring_scan():
    return write_manual_structuring_queue(active_processed_dir())


@router.post("/manual-structuring/ai-suggestions/batch", response_model=admin_schemas.JobResponse)
async def admin_manual_structuring_batch_suggestions(request: StructuringSuggestionBatchRequest):
    return job_manager.submit(
        "structuring_suggestion_batch",
        request.model_dump(),
        structuring_suggestion_batch_workflow,
    ).to_dict()


@router.get("/manual-structuring", response_model=admin_schemas.ManualDocumentsResponse)
async def admin_manual_structuring_files():
    return {"documents": list_manual_structuring_files()}


@router.get("/manual-structuring/{doc}", response_model=admin_schemas.ManualDetailResponse)
async def admin_manual_structuring_detail(doc: str):
    return read_manual_structuring_file(doc)


@router.patch(
    "/manual-structuring/{doc}/{item_id}", response_model=admin_schemas.ManualStatusResponse
)
async def admin_manual_structuring_update(doc: str, item_id: str, request: CandidateStatusUpdate):
    try:
        return update_manual_structuring_status(doc, item_id, request.status, notes=request.notes)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/manual-structuring/{doc}/{item_id}/draft",
    response_model=admin_schemas.ManualDraftResponse,
)
async def admin_manual_structuring_build_draft(doc: str, item_id: str):
    try:
        return build_manual_structuring_draft(doc, item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/manual-structuring/{doc}/{item_id}/draft",
    response_model=admin_schemas.ManualDraftResponse,
)
async def admin_manual_structuring_read_draft(doc: str, item_id: str):
    try:
        return read_manual_structuring_draft(doc, item_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put(
    "/manual-structuring/{doc}/{item_id}/draft",
    response_model=admin_schemas.ManualDraftResponse,
)
async def admin_manual_structuring_save_draft(
    doc: str, item_id: str, request: ManualStructuringDraftRequest
):
    try:
        return save_manual_structuring_draft(doc, item_id, request.draft)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/manual-structuring/{doc}/{item_id}/ai-suggestion",
    response_model=admin_schemas.JobResponse,
)
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


@router.get(
    "/manual-structuring/{doc}/{item_id}/ai-suggestion",
    response_model=admin_schemas.StructuringSuggestionResponse,
    response_model_exclude_unset=True,
)
async def admin_manual_structuring_read_suggestion(doc: str, item_id: str):
    try:
        return read_structuring_suggestion(doc, item_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/manual-structuring/{doc}/{item_id}/validate",
    response_model=admin_schemas.ManualValidationResponse,
)
async def admin_manual_structuring_validate(doc: str, item_id: str):
    try:
        return validate_manual_structuring_draft(doc, item_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/manual-structuring/{doc}/{item_id}/publish",
    response_model=admin_schemas.ManualPublicationResponse,
)
async def admin_manual_structuring_publish(doc: str, item_id: str):
    try:
        return publish_manual_structuring_draft(doc, item_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/manual-structuring/{doc}/{item_id}/versions",
    response_model=admin_schemas.ManualVersionsResponse,
)
async def admin_manual_structuring_versions(doc: str, item_id: str):
    return {"versions": list_manual_structuring_versions(doc, item_id)}


@router.post(
    "/manual-structuring/{doc}/{item_id}/rollback",
    response_model=admin_schemas.ManualRollbackResponse,
)
async def admin_manual_structuring_rollback(doc: str, item_id: str):
    try:
        return rollback_manual_structuring_publication(doc, item_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/corrections/promote/{doc}", response_model=admin_schemas.CandidatePromotionResponse)
async def admin_promote(doc: str):
    return promote_approved_candidates(doc, CORRECTIONS_DIR)


@router.get(
    "/corrections/approved/{doc}",
    response_model=admin_schemas.ApprovedCorrectionsResponse,
    response_model_exclude_unset=True,
)
async def admin_get_approved(doc: str):
    path = _approved_path(doc)
    if not path.exists():
        return {"doc": _safe_doc_stem(doc), "corrections": []}
    return json.loads(path.read_text(encoding="utf-8"))


@router.post(
    "/corrections/approved/{doc}",
    response_model=admin_schemas.ApprovedCorrectionMutationResponse,
)
async def admin_add_approved(doc: str, request: ApprovedCorrectionRequest):
    path = _approved_path(doc)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"corrections": []}
    corrections = payload.get("corrections", [])
    by_id = {str(item.get("id", index)): item for index, item in enumerate(corrections)}
    by_id[request.id] = request.model_dump()
    payload["corrections"] = list(by_id.values())
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "doc": _safe_doc_stem(doc),
        "approved_path": str(path),
        "correction_count": len(payload["corrections"]),
    }


@router.delete(
    "/corrections/approved/{doc}/{correction_id}",
    response_model=admin_schemas.ApprovedCorrectionDeleteResponse,
)
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


@router.get("/elements/{doc}", response_model=admin_schemas.ElementsResponse)
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


@router.get(
    "/elements/{doc}/{element_index}",
    response_model=admin_schemas.ElementResponse,
    response_model_exclude_unset=True,
)
async def admin_element(doc: str, element_index: int):
    try:
        payload = _load_processed_doc(doc)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    elements = payload.get("elements", [])
    if element_index < 0 or element_index >= len(elements):
        raise HTTPException(status_code=404, detail="element not found")
    return {"doc": doc, "element_index": element_index, **elements[element_index]}


@router.get(
    "/page-image/{doc}/{page}",
    response_class=FileResponse,
    responses={200: {"content": {"image/png": {}}}},
)
async def admin_page_image(doc: str, page: int):
    pdf_path = find_source_pdf(doc, RAW_DIR)
    if not pdf_path:
        raise HTTPException(status_code=404, detail=f"source pdf not found: {doc}")
    rendered = render_pdf_pages(pdf_path, [page], AUDIT_DIR / "page_images")
    image_path = rendered.get(page)
    if not image_path or not image_path.exists():
        raise HTTPException(status_code=404, detail=f"page image not found: {doc} page {page}")
    return FileResponse(image_path, media_type="image/png")
