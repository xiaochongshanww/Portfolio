from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JsonObject = dict[str, Any]


class AdminResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OpenAdminResponse(AdminResponse):
    model_config = ConfigDict(extra="allow")


class JobDiagnostics(AdminResponse):
    stalled: bool = False
    heartbeat_stale: bool = False
    reason: str = ""
    progress_age_seconds: float | None = None
    heartbeat_age_seconds: float | None = None
    stale_after_seconds: int = 0
    heartbeat_timeout_seconds: int = 0


class JobResponse(AdminResponse):
    type: str
    params: JsonObject = Field(default_factory=dict)
    request_id: str = ""
    job_id: str
    status: str
    step: str
    progress: JsonObject = Field(default_factory=dict)
    outputs: JsonObject = Field(default_factory=dict)
    error: str = ""
    error_code: str = ""
    created_at: str
    started_at: str = ""
    finished_at: str = ""
    worker_id: str = ""
    heartbeat_at: str = ""
    progress_at: str = ""
    updated_at: str = ""
    recovery: JsonObject = Field(default_factory=dict)
    diagnostics: JobDiagnostics | None = None


class JobsResponse(AdminResponse):
    jobs: list[JobResponse]


class JobLogsResponse(AdminResponse):
    job_id: str
    logs: list[JsonObject]


class AdminStatusResponse(AdminResponse):
    built: bool
    manifest: JsonObject
    quality_evidence_context: JsonObject
    raw_documents: list[str]
    jobs: list[JobResponse]


class DocumentsResponse(AdminResponse):
    raw_documents: list[str]
    manifest_documents: list[JsonObject | str]


class ManifestResponse(OpenAdminResponse):
    schema_version: int | str | None = None
    data_version_hash: str | None = None
    documents: list[JsonObject | str] = Field(default_factory=list)


class ActiveDatabaseResponse(AdminResponse):
    active_db_dir: str = ""
    manifest: str = ""
    processed_dir: str | None = None
    images_dir: str | None = None
    mineru_dir: str | None = None
    audit_dir: str | None = None
    db_dir: str | None = None
    job_id: str = ""
    package_id: str = ""
    data_version_hash: str | None = None
    chunk_count: int = 0
    activated_at: str = ""
    activation_source: str = ""
    candidate_gate_report: str | None = None
    loaded_db_dir: str
    collection_count: int


class RetrievalReloadResponse(AdminResponse):
    loaded_db_dir: str
    collection_count: int


class VersionSummary(AdminResponse):
    version_id: str
    path: str
    size_bytes: int = 0
    file_count: int = 0
    modified_at: str = ""
    age_hours: float = 0
    state: str
    gate_passed: bool | None = None
    pinned: bool = False
    pin_marker_invalid: bool = False
    pin_note: str = ""
    fingerprint: str = ""
    safe: bool
    scan_error: str | None = None
    protected: bool
    protection_reasons: list[str]
    cleanup_eligible: bool
    cleanup_reason: str


class VersionInventoryResponse(AdminResponse):
    schema_version: int
    generated_at: str
    active_version_id: str | None
    policy: JsonObject
    version_count: int
    total_bytes: int
    cleanup_candidate_count: int
    cleanup_candidate_bytes: int
    projected_bytes: int
    target_unmet_bytes: int
    versions: list[VersionSummary]


class VersionRetentionResponse(AdminResponse):
    version_id: str
    schema_version: int
    pinned: bool
    note: str
    updated_at: str


class VersionCleanupCandidate(AdminResponse):
    version_id: str
    fingerprint: str
    size_bytes: int
    modified_at: str
    reason: str


class VersionCleanupPlanResponse(AdminResponse):
    schema_version: int
    plan_id: str
    status: Literal["planned"]
    created_at: str
    expires_at: str
    policy: JsonObject
    total_bytes: int
    projected_bytes: int
    target_unmet_bytes: int
    candidate_count: int
    candidate_bytes: int
    candidates: list[VersionCleanupCandidate]
    plan_path: str


class EvaluationStatusResponse(AdminResponse):
    case_count: int
    by_type: dict[str, int]
    latest: JsonObject | None
    structured_case_count: int
    structured_latest: JsonObject | None
    answer_case_count: int
    answer_latest: JsonObject | None
    quality_evidence_errors: dict[str, str]


class CandidateActivationSummary(AdminResponse):
    available: bool
    passed: bool | None = None
    failed_checks: list[str] = Field(default_factory=list)
    generated_at: str | None = None
    data_version_hash: str | None = None
    answer_evaluation_included: bool = False


class EvaluationSummary(AdminResponse):
    case_count: int = 0
    failure_count: int = 0
    authority_hit_rate: float | None = None
    structured_table_hit_rate: float | None = None
    pass_rate: float | None = None
    citation_grounded_rate: float | None = None
    image_http_rate: float | None = None
    refusal_pass_rate: float | None = None


class QualityStatusResponse(AdminResponse):
    logical_task_count: int
    pending_task_count: int
    suggestion_count: int
    suggestion_missing_count: int
    blocked_suggestion_count: int
    draft_statuses: dict[str, int]
    manual_publication_count: int
    recent_failed_job_count: int
    unresolved_failed_job_count: int
    historical_failed_job_count: int
    stale_active_job_count: int
    quality_gate: JsonObject
    quality_evidence_errors: dict[str, str]
    candidate_activation: CandidateActivationSummary
    regular_evaluation: EvaluationSummary
    structured_evaluation: EvaluationSummary
    answer_evaluation: EvaluationSummary
    external_dependencies: dict[str, str]


class CandidateDocumentSummary(AdminResponse):
    doc: str
    path: str
    source_file: str
    candidate_count: int
    pending_count: int
    approved_count: int
    rejected_count: int


class CandidateDocumentsResponse(AdminResponse):
    documents: list[CandidateDocumentSummary]


class CandidateDetailResponse(OpenAdminResponse):
    doc: str
    source_file: str
    corrections: list[JsonObject]


class CandidateStatusResponse(AdminResponse):
    doc: str
    candidate_id: str
    review_status: str


class CandidatePromotionResponse(AdminResponse):
    source_file: str
    candidate_count: int
    promoted_count: int
    skipped_count: int
    approved_path: str
    skipped: list[JsonObject]


class ManualQueueDocument(AdminResponse):
    doc: str
    path: str
    item_count: int


class ManualQueueScanResponse(AdminResponse):
    document_count: int
    candidate_count: int
    documents: list[ManualQueueDocument]


class ManualDocumentSummary(AdminResponse):
    doc: str
    path: str
    item_count: int
    task_count: int
    pending_count: int
    approved_count: int
    rejected_count: int
    pending_task_count: int
    approved_task_count: int
    rejected_task_count: int
    suggestion_count: int
    suggestion_missing_count: int


class ManualDocumentsResponse(AdminResponse):
    documents: list[ManualDocumentSummary]


class ManualDetailResponse(OpenAdminResponse):
    doc: str
    updated_at: int | None = None
    items: list[JsonObject]


class ManualStatusResponse(AdminResponse):
    doc: str
    item_id: str
    review_status: str


class ManualDraftResponse(OpenAdminResponse):
    schema_version: str
    draft_status: str
    created_at: int
    updated_at: int
    source: JsonObject
    columns: list[JsonObject]
    rows: list[JsonObject]
    table_aliases: list[str]
    notes: list[Any]
    review_context: JsonObject
    draft_path: str
    validation: JsonObject | None = None
    publication: JsonObject | None = None


class ManualValidationMessage(AdminResponse):
    code: str
    path: str
    message: str


class ManualValidationResponse(AdminResponse):
    valid: bool
    validated_at: int
    error_count: int
    warning_count: int
    errors: list[ManualValidationMessage]
    warnings: list[ManualValidationMessage]
    draft_status: str


class ManualPublicationResponse(AdminResponse):
    draft_status: str
    target_path: str
    target_filename: str
    version_id: str
    replaced_existing: bool
    smoke_test: JsonObject


class ManualVersionSummary(AdminResponse):
    version_id: str
    created_at: int | None = None
    target_filename: str
    replaced_existing: bool
    rolled_back_at: int | None = None
    smoke_test: JsonObject | None = None
    automatic_rollback: JsonObject | None = None


class ManualVersionsResponse(AdminResponse):
    versions: list[ManualVersionSummary]


class ManualRollbackResponse(AdminResponse):
    draft_status: str
    target_path: str
    version_id: str
    rollback_action: str


class StructuringSuggestionResponse(OpenAdminResponse):
    schema_version: int | str | None = None
    doc: str | None = None
    item_id: str | None = None
    proposal: JsonObject | None = None


class ApprovedCorrectionsResponse(OpenAdminResponse):
    doc: str | None = None
    source_file: str | None = None
    corrections: list[JsonObject]


class ApprovedCorrectionMutationResponse(AdminResponse):
    doc: str
    approved_path: str
    correction_count: int


class ApprovedCorrectionDeleteResponse(AdminResponse):
    deleted: int
    correction_count: int


class ElementsResponse(AdminResponse):
    doc: str
    source_file: str
    elements: list[JsonObject]


class ElementResponse(OpenAdminResponse):
    doc: str
    element_index: int
