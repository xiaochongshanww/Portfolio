from fastapi import APIRouter

from ..core.config import settings
from ..core.metrics import metrics
from ..retrieval.hybrid_search import retrieval_state
from src.pipeline.manifest import read_manifest
from src.pipeline.paths import MANIFEST_PATH

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


@router.get("/ready")
async def ready():
    count = retrieval_state.chroma_count()
    manifest = read_manifest(MANIFEST_PATH)
    checks = {
        "chroma": "ok" if retrieval_state.chroma_collection else "missing",
        "collection_count": count,
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
    )
    return {
        "ready": is_ready,
        "version": settings.app_version,
        "checks": checks,
    }


@router.get("/metrics")
async def metrics_endpoint():
    return metrics.snapshot()
