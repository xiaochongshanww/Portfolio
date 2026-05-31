from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from src.evaluation.runner import DEFAULT_EVAL_PATH, load_cases
from src.pipeline.audit.corrections import list_candidate_files, promote_approved_candidates, read_candidate_file, update_candidate_status
from src.pipeline.manifest import read_manifest
from src.pipeline.paths import CORRECTIONS_DIR, MANIFEST_PATH

router = APIRouter()


class CandidateStatusUpdate(BaseModel):
    status: str


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
            "parser_backend": "",
            "missing_artifact_count": 0,
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
        "parser_backend": manifest.get("build_params", {}).get("parser_backend", ""),
        "missing_artifact_count": manifest.get("artifact_status", {}).get("missing_count", 0),
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


@router.get("/corrections/candidates")
async def correction_candidates():
    return {"documents": list_candidate_files(CORRECTIONS_DIR)}


@router.get("/corrections/candidates/{doc}")
async def correction_candidate_detail(doc: str):
    return read_candidate_file(doc, CORRECTIONS_DIR)


@router.patch("/corrections/candidates/{doc}/{candidate_id}")
async def correction_candidate_update(doc: str, candidate_id: str, request: CandidateStatusUpdate):
    try:
        return update_candidate_status(doc, candidate_id, request.status, CORRECTIONS_DIR)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/corrections/promote/{doc}")
async def correction_promote(doc: str):
    return promote_approved_candidates(doc, CORRECTIONS_DIR)
