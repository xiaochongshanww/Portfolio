import type { EvaluationSummary } from './generated/api'

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
