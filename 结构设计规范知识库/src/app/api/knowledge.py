from fastapi import APIRouter

from src.evaluation.runner import DEFAULT_EVAL_PATH, load_cases
from src.pipeline.manifest import read_manifest
from src.pipeline.paths import MANIFEST_PATH

router = APIRouter()


@router.get("/knowledge/documents")
async def knowledge_documents():
    manifest = read_manifest(MANIFEST_PATH)
    if not manifest:
        return {
            "built": False,
            "documents": [],
            "document_count": 0,
            "chunk_count": 0,
            "image_count": 0,
            "data_version_hash": "",
            "built_at": "",
        }
    return {
        "built": True,
        "documents": manifest.get("documents", []),
        "document_count": manifest.get("document_count", 0),
        "chunk_count": manifest.get("chunk_count", 0),
        "image_count": manifest.get("image_count", 0),
        "data_version_hash": manifest.get("data_version_hash", ""),
        "built_at": manifest.get("built_at", ""),
        "metadata_status": manifest.get("metadata_status", "unknown"),
    }


@router.get("/evaluation/status")
async def evaluation_status():
    cases = load_cases(DEFAULT_EVAL_PATH)
    by_type: dict[str, int] = {}
    for case in cases:
        by_type[case.type] = by_type.get(case.type, 0) + 1
    return {
        "case_count": len(cases),
        "by_type": by_type,
        "file": str(DEFAULT_EVAL_PATH),
        "command": "python -m src.evaluation run --top-k 5",
    }
