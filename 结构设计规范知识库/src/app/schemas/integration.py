from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HarnessSearchRequest(BaseModel):
    """Read-only search contract consumed by external agent adapters."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)
    document: str = Field(default="", max_length=240)
    mode: Literal["auto", "table", "clause", "definition", "general"] = "auto"
    include_assets: bool = False


class HarnessAsset(BaseModel):
    kind: Literal["page_image", "image"]
    path: str
    url: str
    source_file: str
    page: int | None = None


class HarnessSearchResult(BaseModel):
    rank: int
    source_kind: Literal["retrieval", "structured_table"]
    source_file: str
    standard_code: str
    standard_name: str
    version: str
    section_type: str
    authority_level: int
    is_table: bool
    clause_number: str
    table_id: str
    table_name: str
    pages: list[int]
    excerpt: str
    score: float
    reason: str
    retrieval_sources: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)
    structured_row: dict[str, Any] | None = None
    assets: list[HarnessAsset] = Field(default_factory=list)


class HarnessSearchResponse(BaseModel):
    query: str
    normalized_query: str
    mode: str
    data_version_hash: str
    result_count: int
    results: list[HarnessSearchResult]
    warnings: list[str] = Field(default_factory=list)
