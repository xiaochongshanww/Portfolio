import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request

from src.pipeline.manifest import read_manifest
from src.pipeline.paths import DB_VERSIONS_DIR, METADATA_DIR, RAW_DIR
from src.pipeline.source_catalog import SourceCatalogError

from ..admin.jobs import job_manager
from ..admin.source_management import source_catalog_store
from ..admin.workflows import rebuild_workflow, republish_candidate_workflow
from ..core.config import settings
from ..schemas import source as schemas

router = APIRouter(prefix="/admin/sources", tags=["source-management"])


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail="规范来源不存在")
    return HTTPException(status_code=400, detail=str(exc))


async def _receive_pdf(request: Request) -> Path:
    source_catalog_store.staging_dir.mkdir(parents=True, exist_ok=True)
    path = source_catalog_store.staging_dir / f"{uuid4().hex}.upload"
    size = 0
    try:
        with path.open("xb") as handle:
            async for chunk in request.stream():
                size += len(chunk)
                if size > settings.source_upload_max_bytes:
                    raise HTTPException(status_code=413, detail="PDF 超过允许的上传大小")
                handle.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="上传内容为空")
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


@router.get("", response_model=schemas.SourceListResponse)
def list_sources():
    return source_catalog_store.list_sources()


@router.post("/bootstrap", response_model=schemas.SourceBootstrapResponse)
def bootstrap_sources():
    try:
        return source_catalog_store.bootstrap_legacy(RAW_DIR, METADATA_DIR / "specs.json")
    except (SourceCatalogError, OSError, ValueError) as exc:
        raise _http_error(exc) from exc


@router.post(
    "/uploads",
    response_model=schemas.SourceMutationResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def upload_source(request: Request, filename: str = Query(min_length=5, max_length=255)):
    path = await _receive_pdf(request)
    try:
        return {"source": source_catalog_store.register_upload(path, filename)}
    except (SourceCatalogError, OSError, ValueError) as exc:
        raise _http_error(exc) from exc
    finally:
        path.unlink(missing_ok=True)


@router.post("/changes/plan", response_model=schemas.SourceChangesResponse)
def plan_source_changes():
    plan = source_catalog_store.plan_changes()
    plan.pop("desired", None)
    plan.pop("_retirements", None)
    return plan


@router.post("/changes/build", response_model=schemas.SourceBuildResponse)
def build_source_changes(request: schemas.SourceBuildRequest):
    try:
        snapshot = source_catalog_store.create_revision()
    except (SourceCatalogError, OSError, ValueError) as exc:
        raise _http_error(exc) from exc
    source_dir = source_catalog_store.data_dir / snapshot["input_dir"]
    metadata_path = source_catalog_store.data_dir / snapshot["metadata_path"]
    params = {
        "source": str(source_dir),
        "metadata_path": str(metadata_path),
        "source_catalog_revision": snapshot["revision_id"],
        "parser_backend": request.parser_backend,
        "apply_corrections": request.apply_corrections,
        "mode": request.mode,
    }
    try:
        job = job_manager.submit("source_rebuild", params, rebuild_workflow)
    except Exception as exc:
        source_catalog_store.fail_revision(snapshot["revision_id"], str(exc))
        raise HTTPException(status_code=503, detail="候选构建任务提交失败") from exc
    return {"revision_id": snapshot["revision_id"], "job": job.to_dict()}


@router.post(
    "/candidates/{job_id}/republish",
    response_model=schemas.SourceBuildResponse,
)
def republish_source_candidate(job_id: str):
    """Re-publish a failed candidate after re-running its activation gate only."""
    original = job_manager.store.read(job_id)
    if original is None:
        raise HTTPException(status_code=404, detail="候选构建任务不存在")
    if original.get("type") != "source_rebuild":
        raise HTTPException(status_code=409, detail="该任务不是来源候选构建任务")
    if original.get("status") != "failed":
        raise HTTPException(status_code=409, detail="只有失败的候选构建任务可以重试发布")

    params = original.get("params") if isinstance(original.get("params"), dict) else {}
    revision_id = str(params.get("source_catalog_revision") or "")
    if not revision_id:
        raise HTTPException(status_code=409, detail="候选构建任务缺少来源 revision，无法安全重试")

    try:
        source_catalog_store.validate_republish_revision(revision_id)
        version_dir = DB_VERSIONS_DIR / job_id
        manifest = read_manifest(version_dir / "manifest.json")
        if not manifest:
            raise SourceCatalogError("候选版本 manifest 不存在，无法重试发布")
        recorded_revision = str(
            manifest.get("build_params", {}).get("source_catalog_revision") or ""
        )
        if recorded_revision != revision_id:
            raise SourceCatalogError("候选版本与来源 revision 不一致，拒绝重试发布")
    except (SourceCatalogError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise _http_error(exc) from exc

    for existing in job_manager.store.list():
        existing_params = existing.get("params")
        if not isinstance(existing_params, dict):
            continue
        if (
            existing.get("type") == "source_republish"
            and existing.get("status") in {"queued", "running"}
            and str(existing_params.get("candidate_job_id") or "") == job_id
        ):
            raise HTTPException(status_code=409, detail="该候选已有正在执行的重试发布任务")

    try:
        job = job_manager.submit(
            "source_republish",
            {"candidate_job_id": job_id, "source_catalog_revision": revision_id},
            republish_candidate_workflow,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="候选重试发布任务提交失败") from exc
    return {"revision_id": revision_id, "job": job.to_dict()}


@router.get("/revisions", response_model=schemas.SourceRevisionsResponse)
def list_source_revisions():
    catalog = source_catalog_store.read()
    return {
        "active_revision_id": catalog.get("active_revision_id", ""),
        "revisions": list(reversed(catalog.get("revisions", []))),
    }


@router.get("/{source_id}", response_model=schemas.SourceResponse)
def get_source(source_id: str):
    try:
        return source_catalog_store.get_source(source_id)
    except KeyError as exc:
        raise _http_error(exc) from exc


@router.patch("/{source_id}", response_model=schemas.SourceMutationResponse)
def update_source(source_id: str, request: schemas.SourceUpdateRequest):
    try:
        return {
            "source": source_catalog_store.update_source(
                source_id, request.metadata, request.governance
            )
        }
    except (KeyError, SourceCatalogError, OSError, ValueError) as exc:
        raise _http_error(exc) from exc


@router.post(
    "/{source_id}/versions",
    response_model=schemas.SourceMutationResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def replace_source(
    source_id: str, request: Request, filename: str = Query(min_length=5, max_length=255)
):
    path = await _receive_pdf(request)
    try:
        return {"source": source_catalog_store.register_upload(path, filename, source_id=source_id)}
    except (KeyError, SourceCatalogError, OSError, ValueError) as exc:
        raise _http_error(exc) from exc
    finally:
        path.unlink(missing_ok=True)


@router.post("/{source_id}/retire", response_model=schemas.SourceMutationResponse)
def retire_source(source_id: str):
    try:
        return {"source": source_catalog_store.retire(source_id)}
    except (KeyError, SourceCatalogError, OSError, ValueError) as exc:
        raise _http_error(exc) from exc


@router.post("/{source_id}/validate", response_model=schemas.SourceMutationResponse)
def validate_source(source_id: str):
    try:
        return {"source": source_catalog_store.validate_source(source_id)}
    except (KeyError, SourceCatalogError, OSError, ValueError) as exc:
        raise _http_error(exc) from exc


@router.post("/{source_id}/discard-pending", response_model=schemas.SourceMutationResponse)
def discard_pending_source(source_id: str):
    try:
        return {"source": source_catalog_store.discard_pending(source_id)}
    except (KeyError, SourceCatalogError, OSError, ValueError) as exc:
        raise _http_error(exc) from exc


@router.delete("/{source_id}/draft", response_model=schemas.SourceDeleteResponse)
def delete_draft_source(source_id: str):
    try:
        source_catalog_store.delete_draft(source_id)
        return {"deleted": True, "source_id": source_id}
    except (KeyError, SourceCatalogError, OSError, ValueError) as exc:
        raise _http_error(exc) from exc
