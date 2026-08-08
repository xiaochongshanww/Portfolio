from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..core.config import settings
from ..core.metrics import metrics
from ..retrieval.hybrid_search import retrieval_state
from src.pipeline.active_db import read_active_manifest

router = APIRouter()


class ReadinessResponse(BaseModel):
    ready: bool
    status: str
    version: str
    checked_at: str
    reasons: list[str]
    data_version_hash: str
    built_at: str
    checks: dict[str, str | int]


@router.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse, "description": "问答依赖尚未就绪"}},
)
async def ready():
    snapshot = readiness_snapshot()
    if snapshot["ready"]:
        return snapshot
    return JSONResponse(status_code=503, content=snapshot)


def readiness_snapshot() -> dict[str, Any]:
    count = retrieval_state.chroma_count()
    manifest = read_active_manifest()
    manifest_chunk_count = int(manifest.get("chunk_count", 0)) if manifest else 0
    checks = {
        "chroma": "ok" if retrieval_state.chroma_collection else "missing",
        "collection_count": count,
        "manifest_chunk_count": manifest_chunk_count,
        "collection_count_match": "ok" if not manifest or count == manifest_chunk_count else "mismatch",
        "zhipuai_key": "ok" if settings.zhipuai_api_key else "missing",
        "mimo_key": "ok" if settings.mimo_api_key else "missing",
        "bm25": "ok" if retrieval_state.bm25_index is not None else "missing",
        "manifest": "ok" if manifest else "missing",
        "collection_name": "ok" if not manifest or manifest.get("collection_name") == settings.collection_name else "mismatch",
    }
    is_ready = (
        checks["chroma"] == "ok"
        and count > 0
        and checks["zhipuai_key"] == "ok"
        and checks["mimo_key"] == "ok"
        and checks["bm25"] == "ok"
        and checks["manifest"] == "ok"
        and checks["collection_name"] == "ok"
        and checks["collection_count_match"] == "ok"
    )
    reasons = []
    if checks["chroma"] != "ok":
        reasons.append("CHROMA_MISSING")
    elif count <= 0:
        reasons.append("COLLECTION_EMPTY")
    if checks["collection_count_match"] != "ok":
        reasons.append("COLLECTION_MANIFEST_MISMATCH")
    if checks["zhipuai_key"] != "ok":
        reasons.append("ZHIPUAI_KEY_MISSING")
    if checks["mimo_key"] != "ok":
        reasons.append("MIMO_KEY_MISSING")
    if checks["bm25"] != "ok":
        reasons.append("BM25_MISSING")
    if checks["manifest"] != "ok":
        reasons.append("MANIFEST_MISSING")
    if checks["collection_name"] != "ok":
        reasons.append("COLLECTION_NAME_MISMATCH")
    return {
        "ready": is_ready,
        "status": "ready" if is_ready else "not_ready",
        "version": settings.app_version,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "reasons": reasons,
        "data_version_hash": str(manifest.get("data_version_hash") or "") if manifest else "",
        "built_at": str(manifest.get("built_at") or "") if manifest else "",
        "checks": checks,
    }


@router.get("/metrics")
async def metrics_endpoint():
    return metrics.snapshot()
