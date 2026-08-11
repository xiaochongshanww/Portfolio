import type {
  ActiveDatabaseResponse,
  AdminStatusResponse,
  AnswerEvaluateRequest,
  ApprovedCorrectionDeleteResponse,
  ApprovedCorrectionMutationResponse,
  ApprovedCorrectionRequest,
  ApprovedCorrectionsResponse,
  CandidateDetailResponse,
  CandidateDocumentsResponse,
  CandidatePromotionResponse,
  CandidateStatusResponse,
  DocumentsResponse,
  ElementResponse,
  ElementsResponse,
  EvaluateRequest,
  EvaluationStatusResponse,
  EvaluationSummary,
  JobLogsResponse,
  JobRequest,
  JobResponse,
  JobsResponse,
  ManifestResponse,
  ManualDetailResponse,
  ManualDocumentsResponse,
  ManualDraftResponse,
  ManualPublicationResponse,
  ManualQueueScanResponse,
  ManualRollbackResponse,
  ManualStatusResponse,
  ManualStructuringDraftRequest,
  ManualValidationResponse,
  ManualVersionsResponse,
  QualityStatusResponse,
  RetrievalReloadResponse,
  ReviewRequest,
  SrcAppApiAdminCandidateStatusUpdate as CandidateStatusUpdate,
  StructuringSuggestionBatchRequest,
  StructuringSuggestionResponse,
  VersionCleanupPlanResponse,
  VersionCleanupRequest,
  VersionInventoryResponse,
  VersionRetentionResponse,
  VersionRetentionUpdate,
} from './generated/api'

export type {
  AdminStatusResponse,
  CandidateDetailResponse,
  CandidateDocumentSummary,
  EvaluationStatusResponse,
  JobRequest,
  JobResponse,
  ManualDetailResponse,
  ManualDocumentSummary,
  ManualDraftResponse,
  ManualValidationResponse,
  ManualVersionSummary,
  QualityStatusResponse,
  ReadinessResponse,
  StructuringSuggestionResponse,
  VersionCleanupPlanResponse,
  VersionInventoryResponse,
  VersionSummary,
} from './generated/api'

export type AdminGetPath =
  | '/admin/status'
  | '/admin/documents'
  | '/admin/manifest'
  | '/admin/active-db'
  | '/admin/versions'
  | '/admin/jobs'
  | `/admin/jobs/${string}/logs${string}`
  | `/admin/jobs/${string}`
  | '/admin/evaluation/status'
  | '/admin/quality/status'
  | '/admin/corrections/candidates'
  | `/admin/corrections/candidates/${string}`
  | '/admin/manual-structuring'
  | `/admin/manual-structuring/${string}/${string}/draft`
  | `/admin/manual-structuring/${string}/${string}/ai-suggestion`
  | `/admin/manual-structuring/${string}/${string}/versions`
  | `/admin/manual-structuring/${string}`
  | `/admin/corrections/approved/${string}`
  | `/admin/elements/${string}/${number}`
  | `/admin/elements/${string}`

export type AdminGetResponse<P extends AdminGetPath> =
  P extends '/admin/status' ? AdminStatusResponse :
  P extends '/admin/documents' ? DocumentsResponse :
  P extends '/admin/manifest' ? ManifestResponse :
  P extends '/admin/active-db' ? ActiveDatabaseResponse :
  P extends '/admin/versions' ? VersionInventoryResponse :
  P extends '/admin/jobs' ? JobsResponse :
  P extends `/admin/jobs/${string}/logs${string}` ? JobLogsResponse :
  P extends `/admin/jobs/${string}` ? JobResponse :
  P extends '/admin/evaluation/status' ? EvaluationStatusResponse :
  P extends '/admin/quality/status' ? QualityStatusResponse :
  P extends '/admin/corrections/candidates' ? CandidateDocumentsResponse :
  P extends `/admin/corrections/candidates/${string}` ? CandidateDetailResponse :
  P extends '/admin/manual-structuring' ? ManualDocumentsResponse :
  P extends `/admin/manual-structuring/${string}/${string}/draft` ? ManualDraftResponse :
  P extends `/admin/manual-structuring/${string}/${string}/ai-suggestion` ? StructuringSuggestionResponse :
  P extends `/admin/manual-structuring/${string}/${string}/versions` ? ManualVersionsResponse :
  P extends `/admin/manual-structuring/${string}` ? ManualDetailResponse :
  P extends `/admin/corrections/approved/${string}` ? ApprovedCorrectionsResponse :
  P extends `/admin/elements/${string}/${number}` ? ElementResponse :
  P extends `/admin/elements/${string}` ? ElementsResponse :
  never

export type AdminPostPath =
  | '/admin/retrieval/reload'
  | '/admin/jobs/dry-run'
  | '/admin/jobs/rebuild'
  | '/admin/versions/cleanup-plans'
  | '/admin/jobs/cleanup-versions'
  | '/admin/jobs/audit'
  | '/admin/jobs/review'
  | '/admin/jobs/evaluate'
  | '/admin/jobs/evaluate-answers'
  | '/admin/manual-structuring/scan'
  | '/admin/manual-structuring/ai-suggestions/batch'
  | `/admin/manual-structuring/${string}/${string}/draft`
  | `/admin/manual-structuring/${string}/${string}/ai-suggestion`
  | `/admin/manual-structuring/${string}/${string}/validate`
  | `/admin/manual-structuring/${string}/${string}/publish`
  | `/admin/manual-structuring/${string}/${string}/rollback`
  | `/admin/corrections/promote/${string}`
  | `/admin/corrections/approved/${string}`

export type AdminPostBody<P extends AdminPostPath> =
  P extends '/admin/jobs/dry-run' | '/admin/jobs/rebuild' ? JobRequest :
  P extends '/admin/jobs/cleanup-versions' ? VersionCleanupRequest :
  P extends '/admin/jobs/review' ? ReviewRequest :
  P extends '/admin/jobs/evaluate' ? EvaluateRequest :
  P extends '/admin/jobs/evaluate-answers' ? AnswerEvaluateRequest :
  P extends '/admin/manual-structuring/ai-suggestions/batch' ? StructuringSuggestionBatchRequest :
  P extends `/admin/corrections/approved/${string}` ? ApprovedCorrectionRequest :
  undefined

export type AdminPostResponse<P extends AdminPostPath> =
  P extends '/admin/retrieval/reload' ? RetrievalReloadResponse :
  P extends '/admin/jobs/dry-run' | '/admin/jobs/rebuild' | '/admin/jobs/cleanup-versions' |
    '/admin/jobs/audit' | '/admin/jobs/review' | '/admin/jobs/evaluate' |
    '/admin/jobs/evaluate-answers' | '/admin/manual-structuring/ai-suggestions/batch' |
    `/admin/manual-structuring/${string}/${string}/ai-suggestion` ? JobResponse :
  P extends '/admin/versions/cleanup-plans' ? VersionCleanupPlanResponse :
  P extends '/admin/manual-structuring/scan' ? ManualQueueScanResponse :
  P extends `/admin/manual-structuring/${string}/${string}/draft` ? ManualDraftResponse :
  P extends `/admin/manual-structuring/${string}/${string}/validate` ? ManualValidationResponse :
  P extends `/admin/manual-structuring/${string}/${string}/publish` ? ManualPublicationResponse :
  P extends `/admin/manual-structuring/${string}/${string}/rollback` ? ManualRollbackResponse :
  P extends `/admin/corrections/promote/${string}` ? CandidatePromotionResponse :
  P extends `/admin/corrections/approved/${string}` ? ApprovedCorrectionMutationResponse :
  never

export type AdminPatchPath =
  | `/admin/corrections/candidates/${string}/${string}`
  | `/admin/manual-structuring/${string}/${string}`

export type AdminPatchBody = CandidateStatusUpdate
export type AdminPatchResponse<P extends AdminPatchPath> =
  P extends `/admin/corrections/candidates/${string}/${string}` ? CandidateStatusResponse :
  P extends `/admin/manual-structuring/${string}/${string}` ? ManualStatusResponse :
  never

export type AdminPutPath =
  | `/admin/versions/${string}/retention`
  | `/admin/manual-structuring/${string}/${string}/draft`

export type AdminPutBody<P extends AdminPutPath> =
  P extends `/admin/versions/${string}/retention` ? VersionRetentionUpdate :
  P extends `/admin/manual-structuring/${string}/${string}/draft` ? ManualStructuringDraftRequest :
  never

export type AdminPutResponse<P extends AdminPutPath> =
  P extends `/admin/versions/${string}/retention` ? VersionRetentionResponse :
  P extends `/admin/manual-structuring/${string}/${string}/draft` ? ManualDraftResponse :
  never

export type AdminDeletePath = `/admin/corrections/approved/${string}/${string}`
export type AdminDeleteResponse = ApprovedCorrectionDeleteResponse
export type AdminBlobPath = `/admin/page-image/${string}/${number}`

export type KnowledgeDocument = {
  source_file: string
  name?: string
  code?: string
  version?: string
  chunk_count?: number
  status?: string
}

export type KnowledgeDocumentsView = {
  built: boolean
  documents: KnowledgeDocument[]
  document_count: number
  chunk_count: number
  image_count: number
  data_version_hash: string
  built_at: string
  metadata_status?: string
  parser_backend: string
  missing_artifact_count: number
  applied_correction_count?: number
  correction_status?: { applied_count?: number }
}

export type EvaluationTopResultView = {
  source_file?: string
  clause_number?: string
  reason?: string
  score?: number
}

export type EvaluationFailureView = {
  id: string
  query?: string
  source_hit?: boolean
  clause_hit?: boolean
  keyword_hit?: boolean
  top_results?: EvaluationTopResultView[]
  failed_checks?: string[]
  answer?: string
  error?: string
}

export type EvaluationReportView = {
  ok?: boolean
  case_count?: number
  passed_count?: number
  failures?: EvaluationFailureView[]
  source_hit_rate?: number
  authority_hit_rate?: number
  clause_hit_rate?: number
  keyword_hit_rate?: number
  structured_table_hit_rate?: number
  pass_rate?: number
  refusal_pass_rate?: number
  check_rates?: Record<string, number>
}

export type EvaluationStatusView = {
  case_count?: number
  by_type?: Record<string, number>
  latest?: EvaluationReportView | null
  structured_case_count?: number
  structured_latest?: EvaluationReportView | null
  answer_case_count?: number
  answer_latest?: EvaluationReportView | null
  quality_evidence_errors?: Record<string, string>
}

export type QualityStatusView = {
  logical_task_count?: number
  pending_task_count?: number
  suggestion_count?: number
  suggestion_missing_count?: number
  blocked_suggestion_count?: number
  draft_statuses?: Record<string, number>
  manual_publication_count?: number
  recent_failed_job_count?: number
  unresolved_failed_job_count?: number
  historical_failed_job_count?: number
  stale_active_job_count?: number
  quality_gate?: { passed?: boolean; failed_checks?: string[] }
  candidate_activation?: { available?: boolean; passed?: boolean | null }
  regular_evaluation?: EvaluationSummary
  structured_evaluation?: EvaluationSummary
  answer_evaluation?: EvaluationSummary
}

export type StructuringSuggestionView = {
  model?: string
  stale?: boolean
  baseline?: { column_count?: number; row_count?: number }
  proposal?: {
    confidence?: number
    columns?: Array<Record<string, unknown>>
    rows?: Array<Record<string, unknown>>
    table_aliases?: string[]
    notes?: unknown[]
    assumptions?: string[]
    quality?: {
      applicable?: boolean
      warnings?: string[]
      blocking_errors?: string[]
    }
  }
}

export type CandidateTargetView = {
  element_index?: number
  field?: string
}

export type CorrectionCandidateView = {
  id: string
  status: string
  severity: string
  page: number
  element_index: number
  issue_type: string
  action: string
  target: CandidateTargetView
  current_text: string
  final_text: string
  suggested_text: string
  evidence_text: string
}

export type ManualRuleView = {
  id: string
  label: string
  reason: string
  matched_terms: string[]
}

export type ManualStructuringItemView = {
  id: string
  status: string
  severity: string
  page: number
  element_index: number
  issue_type: string
  title: string
  notes: string
  current_text: string
  group_id: string
  group_primary_item_id: string
  group_item_ids: string[]
  group_pages: number[]
  group_size: number
  group_reason: string
  group_confidence: string
  matched_rules: ManualRuleView[]
  generic_reasons: string[]
  target_schema: Record<string, unknown>
}
