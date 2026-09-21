from typing import Any

from pydantic import BaseModel, ConfigDict, Field

JsonObject = dict[str, Any]


class SourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    lifecycle_status: str
    pending_action: str = ""
    active_asset_version_id: str = ""
    pending_asset_version_id: str = ""
    metadata: JsonObject
    governance: JsonObject
    active_metadata: JsonObject = Field(default_factory=dict)
    active_governance: JsonObject = Field(default_factory=dict)
    versions: list[JsonObject]
    created_at: str = ""
    updated_at: str = ""


class SourceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_revision: int
    active_revision_id: str
    source_count: int
    pending_count: int
    sources: list[SourceResponse]


class SourceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata: JsonObject = Field(default_factory=dict)
    governance: JsonObject = Field(default_factory=dict)


class SourceMutationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: SourceResponse | None


class SourceDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deleted: bool
    source_id: str


class SourceBootstrapResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    imported_count: int
    revision_id: str


class SourceChangesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_revision: int
    active_revision_id: str
    changes: dict[str, list[str]]
    desired_source_count: int
    blockers: list[dict[str, str]]
    ready: bool


class SourceRevisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: str
    status: str
    created_at: str
    source_count: int
    changes: dict[str, list[str]]
    error: str = ""
    data_version_hash: str = ""


class SourceRevisionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_revision_id: str
    revisions: list[SourceRevisionResponse]


class SourceBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parser_backend: str = "mineru"
    apply_corrections: bool = True
    mode: str = Field(default="incremental", pattern=r"^(incremental|full)$")


class SourceBuildResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: str
    job: JsonObject
