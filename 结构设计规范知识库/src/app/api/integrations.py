from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.pipeline.active_db import read_active_manifest

from ..core.config import settings
from ..core.content_access import asset_access_scope
from ..core.errors import ErrorCode, error_payload
from ..core.security import sign_asset_url
from ..rag.structured_tables import StructuredTableMatch, find_structured_table_matches
from ..retrieval.hybrid_search import infer_is_table, infer_section_type, retrieval_state
from ..retrieval.query import analyze_query
from ..schemas.integration import (
    HarnessAsset,
    HarnessSearchRequest,
    HarnessSearchResponse,
    HarnessSearchResult,
)

router = APIRouter(prefix="/integrations/deepseek-harness", tags=["integrations"])


def _parse_pages(value: Any) -> list[int]:
    if isinstance(value, list):
        return sorted({int(page) for page in value if str(page).isdigit()})
    return sorted({int(page) for page in str(value or "").split(",") if page.strip().isdigit()})


def _matches_document(meta: dict[str, Any], document: str) -> bool:
    if not document.strip():
        return True
    needle = document.strip().casefold()
    values = (meta.get("source_file"), meta.get("source"), meta.get("code"), meta.get("name"))
    return any(needle in str(value or "").casefold() for value in values)


def _asset_url(path: str) -> str:
    scope = asset_access_scope("page_image", path.removeprefix("/page-images/").rsplit("/", 1)[0])
    if scope == "disabled":
        return ""
    if scope == "authenticated" and settings.api_auth_enabled:
        path = sign_asset_url(path)
    return f"{settings.public_asset_base_url}{path}"


def _page_assets(source_file: str, pages: list[int], include_assets: bool) -> list[HarnessAsset]:
    if not include_assets or not source_file:
        return []
    assets: list[HarnessAsset] = []
    for page in pages:
        path = f"/page-images/{quote(source_file, safe='')}/{page}"
        url = _asset_url(path)
        if url:
            assets.append(
                HarnessAsset(
                    kind="page_image",
                    path=path,
                    url=url,
                    source_file=source_file,
                    page=page,
                )
            )
    return assets


def _result_from_retrieval(result: Any, rank: int, request: HarnessSearchRequest) -> HarnessSearchResult:
    meta = dict(result.meta)
    pages = _parse_pages(meta.get("pages"))
    section_type = infer_section_type(meta, result.text)
    return HarnessSearchResult(
        rank=rank,
        source_kind="retrieval",
        source_file=str(meta.get("source_file") or meta.get("source") or ""),
        standard_code=str(meta.get("code") or ""),
        standard_name=str(meta.get("name") or ""),
        version=str(meta.get("version") or ""),
        section_type=section_type,
        authority_level=int(meta.get("authority_level") or 0),
        is_table=infer_is_table(meta, result.text),
        clause_number=str(meta.get("clause_number") or ""),
        table_id=str(meta.get("table_id") or ""),
        table_name=str(meta.get("table_name") or ""),
        pages=pages,
        excerpt=result.text[:4000],
        score=float(result.score),
        reason=str(result.reason),
        retrieval_sources=[item for item in str(result.source or "").split("+") if item],
        assets=_page_assets(
            str(meta.get("source_file") or meta.get("source") or ""), pages, request.include_assets
        ),
    )


def _result_from_table(match: StructuredTableMatch, rank: int, request: HarnessSearchRequest) -> HarnessSearchResult:
    source = dict(match.table.get("source") or {})
    source_file = str(source.get("source_file") or "")
    pages = _parse_pages(source.get("pages"))
    return HarnessSearchResult(
        rank=rank,
        source_kind="structured_table",
        source_file=source_file,
        standard_code=str(source.get("code") or ""),
        standard_name=str(source.get("name") or ""),
        version=str(source.get("version") or ""),
        section_type="body_table",
        authority_level=100,
        is_table=True,
        clause_number=str(source.get("clause_number") or ""),
        table_id=str(source.get("table_id") or ""),
        table_name=str(source.get("table_name") or ""),
        pages=pages,
        excerpt="\n".join(f"{key}: {value}" for key, value in match.row.items() if key != "aliases")[:4000],
        score=float(match.score),
        reason=match.reason,
        matched_terms=list(match.matched_terms),
        structured_row=dict(match.row),
        assets=_page_assets(source_file, pages, request.include_assets),
    )


def _error(status_code: int, code: ErrorCode, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=error_payload(code, message))


@router.get("/ready")
async def harness_ready() -> Any:
    manifest = read_active_manifest()
    if not retrieval_state.ready or not manifest:
        return _error(503, ErrorCode.KNOWLEDGE_BASE_NOT_READY, "知识库尚未就绪")
    return {
        "ready": True,
        "service": "deepseek-harness-structural-kb",
        "api_version": "1",
        "data_version_hash": str(manifest.get("data_version_hash") or ""),
    }


@router.get("/page")
async def harness_page(
    source_file: str = Query(min_length=1, max_length=500),
    page: int = Query(ge=1, le=100000),
) -> Any:
    path = f"/page-images/{quote(source_file, safe='')}/{page}"
    url = _asset_url(path)
    if not url:
        return _error(403, ErrorCode.ASSET_ACCESS_DENIED, "当前来源不允许访问页面截图")
    return {
        "source_file": source_file,
        "page": page,
        "path": path,
        "url": url,
    }


@router.post("/search", response_model=HarnessSearchResponse)
async def harness_search(request: HarnessSearchRequest) -> Any:
    if not retrieval_state.ready:
        return _error(503, ErrorCode.KNOWLEDGE_BASE_NOT_READY, "知识库尚未就绪")

    query_info = analyze_query(request.query)
    candidate_limit = min(max(request.top_k * 3, request.top_k), 30)
    retrieval_results = [
        result
        for result in retrieval_state.hybrid_search(request.query, candidate_limit)
        if _matches_document(result.meta, request.document)
    ]
    table_matches: list[StructuredTableMatch] = []
    if request.mode in {"auto", "table"}:
        table_matches = [
            match
            for match in find_structured_table_matches(request.query, limit=candidate_limit)
            if _matches_document(match.table.get("source") or {}, request.document)
        ]

    combined: list[tuple[float, str, Any]] = [
        (match.score + 100.0, "table", match) for match in table_matches
    ] + [(float(result.score), "retrieval", result) for result in retrieval_results]
    combined.sort(key=lambda item: item[0], reverse=True)

    results: list[HarnessSearchResult] = []
    seen: set[tuple[str, str, str, str]] = set()
    for _, kind, item in combined:
        if len(results) >= request.top_k:
            break
        if kind == "table":
            source = item.table.get("source") or {}
            identity = ("table", str(source.get("source_file")), str(source.get("table_id")), repr(item.row))
            if identity in seen:
                continue
            seen.add(identity)
            results.append(_result_from_table(item, len(results) + 1, request))
        else:
            meta = item.meta
            identity = ("retrieval", str(meta.get("source_file")), str(meta.get("chunk_id")), item.text[:80])
            if identity in seen:
                continue
            seen.add(identity)
            results.append(_result_from_retrieval(item, len(results) + 1, request))

    manifest = read_active_manifest() or {}
    warnings: list[str] = []
    if not results:
        warnings.append("未找到符合当前条件的规范依据")
    if request.document and not retrieval_results and not table_matches:
        warnings.append(f"未找到与文档筛选条件匹配的内容：{request.document}")

    return HarnessSearchResponse(
        query=request.query,
        normalized_query=query_info.normalized,
        mode=request.mode,
        data_version_hash=str(manifest.get("data_version_hash") or ""),
        result_count=len(results),
        results=results,
        warnings=warnings,
    )
