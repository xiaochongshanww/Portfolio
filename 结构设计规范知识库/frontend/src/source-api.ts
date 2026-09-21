import './api'

import {
  bootstrapSourcesAdminSourcesBootstrapPost,
  buildSourceChangesAdminSourcesChangesBuildPost,
  deleteDraftSourceAdminSourcesSourceIdDraftDelete,
  discardPendingSourceAdminSourcesSourceIdDiscardPendingPost,
  listSourcesAdminSourcesGet,
  planSourceChangesAdminSourcesChangesPlanPost,
  republishSourceCandidateAdminSourcesCandidatesJobIdRepublishPost,
  replaceSourceAdminSourcesSourceIdVersionsPost,
  retireSourceAdminSourcesSourceIdRetirePost,
  updateSourceAdminSourcesSourceIdPatch,
  uploadSourceAdminSourcesUploadsPost,
  validateSourceAdminSourcesSourceIdValidatePost,
} from './generated/api'

export type SourceAssetVersion = {
  asset_version_id: string
  sha256: string
  original_filename: string
  object_path: string
  size_bytes: number
  page_count: number
  uploaded_at: string
  validation_status: string
  validation_errors: string[]
}

export type SourceMetadata = {
  source_file?: string
  code?: string
  name?: string
  version?: string
  effective_date?: string
  aliases?: string[]
  notes?: string
  image_access?: string
  page_image_access?: string
  [key: string]: unknown
}

export type SourceGovernance = {
  source_kind?: string
  rights_status?: string
  reference_index?: string
  [key: string]: unknown
}

export type SourceRecord = {
  source_id: string
  lifecycle_status: string
  pending_action: string
  active_asset_version_id: string
  pending_asset_version_id: string
  metadata: SourceMetadata
  governance: SourceGovernance
  active_metadata: SourceMetadata
  active_governance: SourceGovernance
  versions: SourceAssetVersion[]
  created_at: string
  updated_at: string
}

export type SourceList = {
  catalog_revision: number
  active_revision_id: string
  source_count: number
  pending_count: number
  sources: SourceRecord[]
}

export type SourcePlan = {
  catalog_revision: number
  active_revision_id: string
  changes: Record<'added' | 'updated' | 'replaced' | 'retired' | 'unchanged', string[]>
  desired_source_count: number
  blockers: Array<{ source_id: string; message: string }>
  ready: boolean
}

export function listSources() {
  return listSourcesAdminSourcesGet() as Promise<SourceList>
}

export function bootstrapSources() {
  return bootstrapSourcesAdminSourcesBootstrapPost()
}

export function uploadSource(file: File) {
  return uploadSourceAdminSourcesUploadsPost({
    body: file,
    query: { filename: file.name },
    headers: { 'Content-Type': 'application/pdf' },
  }) as Promise<{ source: SourceRecord }>
}

export function replaceSource(sourceId: string, file: File) {
  return replaceSourceAdminSourcesSourceIdVersionsPost({
    body: file,
    path: { source_id: sourceId },
    query: { filename: file.name },
    headers: { 'Content-Type': 'application/pdf' },
  }) as Promise<{ source: SourceRecord }>
}

export function updateSource(sourceId: string, payload: { metadata: SourceMetadata; governance: SourceGovernance }) {
  return updateSourceAdminSourcesSourceIdPatch({
    path: { source_id: sourceId },
    body: payload,
  }) as Promise<{ source: SourceRecord }>
}

export function validateSource(sourceId: string) {
  return validateSourceAdminSourcesSourceIdValidatePost({ path: { source_id: sourceId } }) as Promise<{ source: SourceRecord }>
}

export function retireSource(sourceId: string) {
  return retireSourceAdminSourcesSourceIdRetirePost({ path: { source_id: sourceId } }) as Promise<{ source: SourceRecord }>
}

export function discardPendingSource(sourceId: string) {
  return discardPendingSourceAdminSourcesSourceIdDiscardPendingPost({ path: { source_id: sourceId } }) as Promise<{ source: SourceRecord | null }>
}

export function deleteDraftSource(sourceId: string) {
  return deleteDraftSourceAdminSourcesSourceIdDraftDelete({ path: { source_id: sourceId } })
}

export function planSourceChanges() {
  return planSourceChangesAdminSourcesChangesPlanPost() as Promise<SourcePlan>
}

export function buildSourceChanges(payload: { parser_backend: string; apply_corrections: boolean; mode: string }) {
  return buildSourceChangesAdminSourcesChangesBuildPost({ body: payload })
}

export function republishSourceCandidate(jobId: string) {
  return republishSourceCandidateAdminSourcesCandidatesJobIdRepublishPost({
    path: { job_id: jobId },
  }) as Promise<{ revision_id: string; job: Record<string, unknown> }>
}
