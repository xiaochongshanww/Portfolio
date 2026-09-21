from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from scripts import export_openapi
from src.app.api import admin, sources
from src.app.main import app
from src.app.schemas import admin as admin_schemas
from src.app.schemas import source as source_schemas
from src.evaluation import management as evaluation_management
from starlette.responses import Response


@dataclass(frozen=True)
class RuntimeCase:
    operation_id: str
    method: str
    template: str
    path: str
    body: dict[str, Any] | None = None
    media_type: str = "application/json"
    content: bytes | None = None


SAMPLE_JOB = {
    "type": "audit",
    "params": {},
    "job_id": "contract-job",
    "status": "queued",
    "step": "queued",
    "created_at": "2026-08-12T00:00:00Z",
}

SAMPLE_DRAFT = {
    "schema_version": "1",
    "draft_status": "needs_review",
    "created_at": 1,
    "updated_at": 1,
    "source": {"doc": "contract-doc", "item_id": "item-1"},
    "columns": [{"key": "value", "label": "值"}],
    "rows": [{"value": "1.0"}],
    "table_aliases": ["表 1"],
    "notes": [],
    "review_context": {},
    "draft_path": "contract/draft.json",
}

RUNTIME_CASES = (
    RuntimeCase("admin_status_admin_status_get", "get", "/admin/status", "/admin/status"),
    RuntimeCase(
        "admin_provider_probes_admin_provider_probes_post",
        "post",
        "/admin/provider-probes",
        "/admin/provider-probes",
    ),
    RuntimeCase(
        "admin_documents_admin_documents_get", "get", "/admin/documents", "/admin/documents"
    ),
    RuntimeCase("admin_manifest_admin_manifest_get", "get", "/admin/manifest", "/admin/manifest"),
    RuntimeCase(
        "admin_active_db_admin_active_db_get", "get", "/admin/active-db", "/admin/active-db"
    ),
    RuntimeCase(
        "admin_retrieval_reload_admin_retrieval_reload_post",
        "post",
        "/admin/retrieval/reload",
        "/admin/retrieval/reload",
    ),
    RuntimeCase(
        "admin_rebuild_plan_admin_rebuild_plan_post",
        "post",
        "/admin/rebuild-plan",
        "/admin/rebuild-plan",
        {},
    ),
    RuntimeCase(
        "start_dry_run_admin_jobs_dry_run_post",
        "post",
        "/admin/jobs/dry-run",
        "/admin/jobs/dry-run",
        {},
    ),
    RuntimeCase(
        "start_rebuild_admin_jobs_rebuild_post",
        "post",
        "/admin/jobs/rebuild",
        "/admin/jobs/rebuild",
        {},
    ),
    RuntimeCase("admin_versions_admin_versions_get", "get", "/admin/versions", "/admin/versions"),
    RuntimeCase(
        "admin_version_retention_admin_versions__version_id__retention_put",
        "put",
        "/admin/versions/{version_id}/retention",
        "/admin/versions/version-1/retention",
        {"pinned": True, "note": "contract"},
    ),
    RuntimeCase(
        "admin_version_cleanup_plan_admin_versions_cleanup_plans_post",
        "post",
        "/admin/versions/cleanup-plans",
        "/admin/versions/cleanup-plans",
    ),
    RuntimeCase(
        "start_version_cleanup_admin_jobs_cleanup_versions_post",
        "post",
        "/admin/jobs/cleanup-versions",
        "/admin/jobs/cleanup-versions",
        {"plan_id": "0123456789abcdef"},
    ),
    RuntimeCase(
        "start_audit_admin_jobs_audit_post", "post", "/admin/jobs/audit", "/admin/jobs/audit"
    ),
    RuntimeCase(
        "start_review_admin_jobs_review_post",
        "post",
        "/admin/jobs/review",
        "/admin/jobs/review",
        {"doc": "contract-doc", "pages": "1"},
    ),
    RuntimeCase(
        "start_evaluate_admin_jobs_evaluate_post",
        "post",
        "/admin/jobs/evaluate",
        "/admin/jobs/evaluate",
        {"evaluation_set": "regular", "top_k": 5},
    ),
    RuntimeCase(
        "start_answer_evaluate_admin_jobs_evaluate_answers_post",
        "post",
        "/admin/jobs/evaluate-answers",
        "/admin/jobs/evaluate-answers",
        {"evaluation_set": "answer"},
    ),
    RuntimeCase("list_jobs_admin_jobs_get", "get", "/admin/jobs", "/admin/jobs"),
    RuntimeCase(
        "get_job_admin_jobs__job_id__get",
        "get",
        "/admin/jobs/{job_id}",
        "/admin/jobs/contract-job",
    ),
    RuntimeCase(
        "resolve_job_admin_jobs__job_id__resolve_post",
        "post",
        "/admin/jobs/{job_id}/resolve",
        "/admin/jobs/contract-job/resolve",
        {"status": "acknowledged", "note": "contract disposition"},
    ),
    RuntimeCase(
        "get_job_logs_admin_jobs__job_id__logs_get",
        "get",
        "/admin/jobs/{job_id}/logs",
        "/admin/jobs/contract-job/logs?limit=20",
    ),
    RuntimeCase(
        "admin_evaluation_status_admin_evaluation_status_get",
        "get",
        "/admin/evaluation/status",
        "/admin/evaluation/status",
    ),
    RuntimeCase(
        "admin_evaluation_cases_admin_evaluation_cases_get",
        "get",
        "/admin/evaluation/cases",
        "/admin/evaluation/cases?evaluation_set=regular&limit=10",
    ),
    RuntimeCase(
        "admin_evaluation_sets_admin_evaluation_sets_get",
        "get",
        "/admin/evaluation/sets",
        "/admin/evaluation/sets",
    ),
    RuntimeCase(
        "admin_evaluation_set_revisions_admin_evaluation_sets__evaluation_set_id__revisions_get",
        "get",
        "/admin/evaluation/sets/{evaluation_set_id}/revisions",
        "/admin/evaluation/sets/structured/revisions",
    ),
    RuntimeCase(
        "admin_evaluation_set_revision_admin_evaluation_sets__evaluation_set_id__revisions__revision_id__get",
        "get",
        "/admin/evaluation/sets/{evaluation_set_id}/revisions/{revision_id}",
        "/admin/evaluation/sets/structured/revisions/builtin-4b496d1a8282",
    ),
    RuntimeCase(
        "admin_evaluation_set_admin_evaluation_sets__evaluation_set_id__get",
        "get",
        "/admin/evaluation/sets/{evaluation_set_id}",
        "/admin/evaluation/sets/structured",
    ),
    RuntimeCase(
        "admin_evaluation_set_create_draft_admin_evaluation_sets__evaluation_set_id__drafts_post",
        "post",
        "/admin/evaluation/sets/{evaluation_set_id}/drafts",
        "/admin/evaluation/sets/structured/drafts",
    ),
    RuntimeCase(
        "admin_evaluation_set_update_case_admin_evaluation_sets__evaluation_set_id__drafts__case_id__patch",
        "patch",
        "/admin/evaluation/sets/{evaluation_set_id}/drafts/{case_id}",
        "/admin/evaluation/sets/structured/drafts/structured-live-load-office",
        {
            "case": {
                "id": "structured-live-load-office",
                "query": "办公楼楼面活荷载标准值取多少（契约测试）",
                "type": "structured_table",
                "expected_table_id": "5.1.1",
                "keyword_required": False,
                "top1_source_required": False,
            }
        },
    ),
    RuntimeCase(
        "admin_evaluation_set_delete_case_admin_evaluation_sets__evaluation_set_id__drafts__case_id__delete",
        "delete",
        "/admin/evaluation/sets/{evaluation_set_id}/drafts/{case_id}",
        "/admin/evaluation/sets/structured/drafts/structured-live-load-office",
    ),
    RuntimeCase(
        "admin_evaluation_set_add_case_admin_evaluation_sets__evaluation_set_id__drafts_cases_post",
        "post",
        "/admin/evaluation/sets/{evaluation_set_id}/drafts/cases",
        "/admin/evaluation/sets/structured/drafts/cases",
        {
            "case": {
                "id": "runtime-added",
                "query": "契约测试新增结构化问题",
                "type": "structured_table",
                "expected_table_id": "5.1.1",
                "keyword_required": False,
                "top1_source_required": False,
            }
        },
    ),
    RuntimeCase(
        "admin_evaluation_set_validate_admin_evaluation_sets__evaluation_set_id__validate_post",
        "post",
        "/admin/evaluation/sets/{evaluation_set_id}/validate",
        "/admin/evaluation/sets/structured/validate",
    ),
    RuntimeCase(
        "admin_evaluation_set_diff_admin_evaluation_sets__evaluation_set_id__diff_get",
        "get",
        "/admin/evaluation/sets/{evaluation_set_id}/diff",
        "/admin/evaluation/sets/structured/diff",
    ),
    RuntimeCase(
        "admin_evaluation_set_publish_admin_evaluation_sets__evaluation_set_id__publish_post",
        "post",
        "/admin/evaluation/sets/{evaluation_set_id}/publish",
        "/admin/evaluation/sets/structured/publish",
    ),
    RuntimeCase(
        "admin_evaluation_set_rollback_admin_evaluation_sets__evaluation_set_id__rollback_post",
        "post",
        "/admin/evaluation/sets/{evaluation_set_id}/rollback",
        "/admin/evaluation/sets/structured/rollback",
        {"revision_id": "builtin-4b496d1a8282"},
    ),
    RuntimeCase(
        "admin_quality_status_admin_quality_status_get",
        "get",
        "/admin/quality/status",
        "/admin/quality/status",
    ),
    RuntimeCase(
        "admin_quality_runs_admin_quality_runs_get",
        "get",
        "/admin/quality/runs",
        "/admin/quality/runs?limit=1",
    ),
    RuntimeCase(
        "admin_quality_runs_compare_admin_quality_runs_compare_get",
        "get",
        "/admin/quality/runs/compare",
        "/admin/quality/runs/compare?baseline_run_id=0123456789abcdef0123456789abcdef&candidate_run_id=fedcba9876543210fedcba9876543210",
    ),
    RuntimeCase(
        "admin_candidate_files_admin_corrections_candidates_get",
        "get",
        "/admin/corrections/candidates",
        "/admin/corrections/candidates",
    ),
    RuntimeCase(
        "admin_candidate_detail_admin_corrections_candidates__doc__get",
        "get",
        "/admin/corrections/candidates/{doc}",
        "/admin/corrections/candidates/contract-doc",
    ),
    RuntimeCase(
        "admin_candidate_update_admin_corrections_candidates__doc___candidate_id__patch",
        "patch",
        "/admin/corrections/candidates/{doc}/{candidate_id}",
        "/admin/corrections/candidates/contract-doc/candidate-1",
        {"status": "approved", "notes": "checked"},
    ),
    RuntimeCase(
        "admin_manual_structuring_scan_admin_manual_structuring_scan_post",
        "post",
        "/admin/manual-structuring/scan",
        "/admin/manual-structuring/scan",
    ),
    RuntimeCase(
        "admin_manual_structuring_batch_suggestions_admin_manual_structuring_ai_suggestions_batch_post",
        "post",
        "/admin/manual-structuring/ai-suggestions/batch",
        "/admin/manual-structuring/ai-suggestions/batch",
        {"documents": ["contract-doc"], "force": False},
    ),
    RuntimeCase(
        "admin_manual_structuring_files_admin_manual_structuring_get",
        "get",
        "/admin/manual-structuring",
        "/admin/manual-structuring",
    ),
    RuntimeCase(
        "admin_manual_structuring_detail_admin_manual_structuring__doc__get",
        "get",
        "/admin/manual-structuring/{doc}",
        "/admin/manual-structuring/contract-doc",
    ),
    RuntimeCase(
        "admin_manual_structuring_update_admin_manual_structuring__doc___item_id__patch",
        "patch",
        "/admin/manual-structuring/{doc}/{item_id}",
        "/admin/manual-structuring/contract-doc/item-1",
        {"status": "approved", "notes": "checked"},
    ),
    RuntimeCase(
        "admin_manual_structuring_build_draft_admin_manual_structuring__doc___item_id__draft_post",
        "post",
        "/admin/manual-structuring/{doc}/{item_id}/draft",
        "/admin/manual-structuring/contract-doc/item-1/draft",
    ),
    RuntimeCase(
        "admin_manual_structuring_read_draft_admin_manual_structuring__doc___item_id__draft_get",
        "get",
        "/admin/manual-structuring/{doc}/{item_id}/draft",
        "/admin/manual-structuring/contract-doc/item-1/draft",
    ),
    RuntimeCase(
        "admin_manual_structuring_save_draft_admin_manual_structuring__doc___item_id__draft_put",
        "put",
        "/admin/manual-structuring/{doc}/{item_id}/draft",
        "/admin/manual-structuring/contract-doc/item-1/draft",
        {"draft": {"rows": [{"value": "1.1"}]}},
    ),
    RuntimeCase(
        "admin_manual_structuring_start_suggestion_admin_manual_structuring__doc___item_id__ai_suggestion_post",
        "post",
        "/admin/manual-structuring/{doc}/{item_id}/ai-suggestion",
        "/admin/manual-structuring/contract-doc/item-1/ai-suggestion",
    ),
    RuntimeCase(
        "admin_manual_structuring_read_suggestion_admin_manual_structuring__doc___item_id__ai_suggestion_get",
        "get",
        "/admin/manual-structuring/{doc}/{item_id}/ai-suggestion",
        "/admin/manual-structuring/contract-doc/item-1/ai-suggestion",
    ),
    RuntimeCase(
        "admin_manual_structuring_validate_admin_manual_structuring__doc___item_id__validate_post",
        "post",
        "/admin/manual-structuring/{doc}/{item_id}/validate",
        "/admin/manual-structuring/contract-doc/item-1/validate",
    ),
    RuntimeCase(
        "admin_manual_structuring_publish_admin_manual_structuring__doc___item_id__publish_post",
        "post",
        "/admin/manual-structuring/{doc}/{item_id}/publish",
        "/admin/manual-structuring/contract-doc/item-1/publish",
    ),
    RuntimeCase(
        "admin_manual_structuring_versions_admin_manual_structuring__doc___item_id__versions_get",
        "get",
        "/admin/manual-structuring/{doc}/{item_id}/versions",
        "/admin/manual-structuring/contract-doc/item-1/versions",
    ),
    RuntimeCase(
        "admin_manual_structuring_rollback_admin_manual_structuring__doc___item_id__rollback_post",
        "post",
        "/admin/manual-structuring/{doc}/{item_id}/rollback",
        "/admin/manual-structuring/contract-doc/item-1/rollback",
    ),
    RuntimeCase(
        "admin_promote_admin_corrections_promote__doc__post",
        "post",
        "/admin/corrections/promote/{doc}",
        "/admin/corrections/promote/contract-doc",
    ),
    RuntimeCase(
        "admin_get_approved_admin_corrections_approved__doc__get",
        "get",
        "/admin/corrections/approved/{doc}",
        "/admin/corrections/approved/contract-doc",
    ),
    RuntimeCase(
        "admin_add_approved_admin_corrections_approved__doc__post",
        "post",
        "/admin/corrections/approved/{doc}",
        "/admin/corrections/approved/contract-doc",
        {
            "id": "correction-2",
            "action": "replace_text",
            "target": {"element_index": 0, "field": "text"},
            "value": "corrected",
        },
    ),
    RuntimeCase(
        "admin_delete_approved_admin_corrections_approved__doc___correction_id__delete",
        "delete",
        "/admin/corrections/approved/{doc}/{correction_id}",
        "/admin/corrections/approved/contract-doc/correction-1",
    ),
    RuntimeCase(
        "admin_elements_admin_elements__doc__get",
        "get",
        "/admin/elements/{doc}",
        "/admin/elements/contract-doc?page=1",
    ),
    RuntimeCase(
        "admin_element_admin_elements__doc___element_index__get",
        "get",
        "/admin/elements/{doc}/{element_index}",
        "/admin/elements/contract-doc/0",
    ),
    RuntimeCase(
        "admin_page_image_admin_page_image__doc___page__get",
        "get",
        "/admin/page-image/{doc}/{page}",
        "/admin/page-image/contract-doc/1",
        media_type="image/png",
    ),
    RuntimeCase("list_sources_admin_sources_get", "get", "/admin/sources", "/admin/sources"),
    RuntimeCase(
        "bootstrap_sources_admin_sources_bootstrap_post",
        "post",
        "/admin/sources/bootstrap",
        "/admin/sources/bootstrap",
    ),
    RuntimeCase(
        "upload_source_admin_sources_uploads_post",
        "post",
        "/admin/sources/uploads",
        "/admin/sources/uploads?filename=contract.pdf",
        content=b"%PDF-contract",
    ),
    RuntimeCase(
        "plan_source_changes_admin_sources_changes_plan_post",
        "post",
        "/admin/sources/changes/plan",
        "/admin/sources/changes/plan",
    ),
    RuntimeCase(
        "build_source_changes_admin_sources_changes_build_post",
        "post",
        "/admin/sources/changes/build",
        "/admin/sources/changes/build",
        {"parser_backend": "pymupdf", "mode": "incremental"},
    ),
    RuntimeCase(
        "republish_source_candidate_admin_sources_candidates__job_id__republish_post",
        "post",
        "/admin/sources/candidates/{job_id}/republish",
        "/admin/sources/candidates/candidate-job/republish",
    ),
    RuntimeCase(
        "list_source_revisions_admin_sources_revisions_get",
        "get",
        "/admin/sources/revisions",
        "/admin/sources/revisions",
    ),
    RuntimeCase(
        "get_source_admin_sources__source_id__get",
        "get",
        "/admin/sources/{source_id}",
        "/admin/sources/source-1",
    ),
    RuntimeCase(
        "update_source_admin_sources__source_id__patch",
        "patch",
        "/admin/sources/{source_id}",
        "/admin/sources/source-1",
        {"metadata": {"name": "contract"}, "governance": {}},
    ),
    RuntimeCase(
        "replace_source_admin_sources__source_id__versions_post",
        "post",
        "/admin/sources/{source_id}/versions",
        "/admin/sources/source-1/versions?filename=replacement.pdf",
        content=b"%PDF-replacement",
    ),
    RuntimeCase(
        "retire_source_admin_sources__source_id__retire_post",
        "post",
        "/admin/sources/{source_id}/retire",
        "/admin/sources/source-1/retire",
    ),
    RuntimeCase(
        "validate_source_admin_sources__source_id__validate_post",
        "post",
        "/admin/sources/{source_id}/validate",
        "/admin/sources/source-1/validate",
    ),
    RuntimeCase(
        "discard_pending_source_admin_sources__source_id__discard_pending_post",
        "post",
        "/admin/sources/{source_id}/discard-pending",
        "/admin/sources/source-1/discard-pending",
    ),
    RuntimeCase(
        "delete_draft_source_admin_sources__source_id__draft_delete",
        "delete",
        "/admin/sources/{source_id}/draft",
        "/admin/sources/source-1/draft",
    ),
)


class FakeJobStore:
    def list(self) -> list[dict[str, Any]]:
        return [dict(SAMPLE_JOB)]

    def read(self, job_id: str) -> dict[str, Any] | None:
        if job_id == "candidate-job":
            return {
                "job_id": "candidate-job",
                "type": "source_rebuild",
                "status": "failed",
                "params": {"source_catalog_revision": "src-contract"},
            }
        return dict(SAMPLE_JOB) if job_id == SAMPLE_JOB["job_id"] else None

    def logs(self, job_id: str, limit: int = 200) -> list[dict[str, Any]]:
        return [{"level": "info", "message": "contract", "limit": limit}]

    def resolve_failed(
        self,
        job_id: str,
        *,
        status: str,
        note: str,
        related_job_id: str = "",
    ) -> dict[str, Any]:
        assert job_id == "contract-job"
        return {
            **SAMPLE_JOB,
            "status": "failed",
            "error": "contract failure",
            "resolution": {
                "schema_version": 1,
                "status": status,
                "note": note,
                "resolved_at": "2026-08-12T00:00:00Z",
                "resolved_by": "contract",
                "related_job_id": related_job_id,
            },
        }


class FakeJobManager:
    def __init__(self) -> None:
        self.store = FakeJobStore()

    def submit(self, job_type: str, params: dict[str, Any], workflow: Any) -> SimpleNamespace:
        payload = {**SAMPLE_JOB, "type": job_type, "params": params}
        return SimpleNamespace(to_dict=lambda: payload)


class FakeRetrievalState:
    db_dir = Path("contract/db")
    zhipu_client = None

    def __init__(self) -> None:
        self.reload_count = 0

    def reload(self) -> None:
        self.reload_count += 1

    def chroma_count(self) -> int:
        return 1


def _source_record() -> dict[str, Any]:
    return {
        "source_id": "source-1",
        "lifecycle_status": "ready",
        "pending_action": "add",
        "active_asset_version_id": "",
        "pending_asset_version_id": "asset-1",
        "metadata": {"source_file": "contract.pdf", "code": "GB 1", "name": "contract"},
        "governance": {"rights_status": "B"},
        "versions": [{"asset_version_id": "asset-1", "sha256": "a" * 64}],
        "created_at": "2026-08-12T00:00:00Z",
        "updated_at": "2026-08-12T00:00:00Z",
    }


class FakeSourceStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.staging_dir = data_dir / "source_assets" / "staging"

    def list_sources(self):
        return {
            "catalog_revision": 1,
            "active_revision_id": "",
            "source_count": 1,
            "pending_count": 1,
            "sources": [_source_record()],
        }

    def bootstrap_legacy(self, *_args):
        return {"imported_count": 1, "revision_id": "src-contract"}

    def register_upload(self, *_args, **_kwargs):
        return _source_record()

    def plan_changes(self):
        return {
            "catalog_revision": 1,
            "active_revision_id": "",
            "changes": {"added": ["source-1"], "replaced": [], "retired": [], "unchanged": []},
            "desired_source_count": 1,
            "blockers": [],
            "ready": True,
            "desired": [],
        }

    def create_revision(self):
        input_dir = self.data_dir / "source_catalog" / "revisions" / "src-contract" / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = input_dir.parent / "specs.json"
        metadata_path.write_text('{"documents":[]}', encoding="utf-8")
        return {
            "revision_id": "src-contract",
            "input_dir": input_dir.relative_to(self.data_dir).as_posix(),
            "metadata_path": metadata_path.relative_to(self.data_dir).as_posix(),
        }

    def read(self):
        return {
            "active_revision_id": "",
            "revisions": [
                {
                    "revision_id": "src-contract",
                    "status": "candidate",
                    "created_at": "2026-08-12T00:00:00Z",
                    "source_count": 1,
                    "changes": {
                        "added": ["source-1"],
                        "replaced": [],
                        "retired": [],
                        "unchanged": [],
                    },
                    "error": "",
                    "data_version_hash": "",
                }
            ],
        }

    def validate_republish_revision(self, revision_id: str):
        assert revision_id == "src-contract"
        return {"revision_id": revision_id}

    def get_source(self, _source_id):
        return _source_record()

    def update_source(self, *_args):
        return _source_record()

    def retire(self, _source_id):
        return _source_record()

    def validate_source(self, _source_id):
        return _source_record()

    def discard_pending(self, _source_id):
        return _source_record()

    def delete_draft(self, _source_id):
        return None


def _version_inventory() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": "2026-08-12T00:00:00Z",
        "active_version_id": "version-1",
        "policy": {"keep": 2},
        "version_count": 1,
        "total_bytes": 100,
        "cleanup_candidate_count": 0,
        "cleanup_candidate_bytes": 0,
        "projected_bytes": 100,
        "target_unmet_bytes": 0,
        "versions": [
            {
                "version_id": "version-1",
                "path": "contract/version-1",
                "size_bytes": 100,
                "file_count": 1,
                "modified_at": "2026-08-12T00:00:00Z",
                "age_hours": 0,
                "state": "active",
                "pinned": True,
                "pin_marker_invalid": False,
                "pin_note": "contract",
                "fingerprint": "abc",
                "safe": True,
                "protected": True,
                "protection_reasons": ["active"],
                "cleanup_eligible": False,
                "cleanup_reason": "active",
            }
        ],
    }


def _cleanup_plan() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "plan_id": "0123456789abcdef",
        "status": "planned",
        "created_at": "2026-08-12T00:00:00Z",
        "expires_at": "2026-08-12T01:00:00Z",
        "policy": {},
        "total_bytes": 100,
        "projected_bytes": 100,
        "target_unmet_bytes": 0,
        "candidate_count": 0,
        "candidate_bytes": 0,
        "candidates": [],
        "plan_path": "contract/plan.json",
    }


def _manual_summary() -> dict[str, Any]:
    return {
        "doc": "contract-doc",
        "path": "contract/manual.json",
        "item_count": 1,
        "task_count": 1,
        "pending_count": 1,
        "approved_count": 0,
        "rejected_count": 0,
        "pending_task_count": 1,
        "approved_task_count": 0,
        "rejected_task_count": 0,
        "suggestion_count": 1,
        "suggestion_missing_count": 0,
    }


def _quality_reports(keys: tuple[str, ...]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    reports = {
        "regular_json": {"case_count": 1, "authority_hit_rate": 1.0, "failures": []},
        "structured_json": {"case_count": 1, "structured_table_hit_rate": 1.0, "failures": []},
        "answer_json": {
            "case_count": 1,
            "pass_rate": 1.0,
            "check_rates": {"citation_grounded": 1.0, "image_http": 1.0},
            "refusal_pass_rate": 1.0,
            "failure_count": 0,
        },
    }
    return ({key: reports[key] for key in keys}, {})


async def _provider_probes(**kwargs: Any) -> dict[str, Any]:
    assert kwargs["embedding_client"] is None
    return {
        "ok": True,
        "checked_at": "2026-08-12T00:00:00Z",
        "providers": [
            {
                "provider": "zhipuai",
                "capability": "embedding",
                "model": "embedding-2",
                "ok": True,
                "status": "ok",
                "latency_ms": 1,
                "http_status": None,
            },
            {
                "provider": "mimo",
                "capability": "chat",
                "model": "mimo-v2.5",
                "ok": True,
                "status": "ok",
                "latency_ms": 1,
                "http_status": None,
            },
        ],
    }


@pytest.fixture
def runtime_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    raw_dir = tmp_path / "raw"
    corrections_dir = tmp_path / "corrections"
    manual_dir = tmp_path / "manual"
    tables_dir = tmp_path / "tables"
    audit_dir = tmp_path / "audit"
    for path in (raw_dir, corrections_dir, manual_dir, tables_dir, audit_dir):
        path.mkdir(parents=True)
    (raw_dir / "contract-doc.pdf").write_bytes(b"contract pdf")

    approved = corrections_dir / "approved" / "contract-doc.json"
    approved.parent.mkdir(parents=True)
    approved.write_text(
        json.dumps(
            {
                "doc": "contract-doc",
                "corrections": [
                    {
                        "id": "correction-1",
                        "action": "replace_text",
                        "target": {"element_index": 0, "field": "text"},
                        "value": "corrected",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    png_path = audit_dir / "page-1.png"
    png_path.write_bytes(b"\x89PNG\r\n\x1a\ncontract")

    fake_state = FakeRetrievalState()
    monkeypatch.setattr(admin, "RAW_DIR", raw_dir)
    monkeypatch.setattr(admin, "CORRECTIONS_DIR", corrections_dir)
    monkeypatch.setattr(admin, "MANUAL_STRUCTURING_DIR", manual_dir)
    monkeypatch.setattr(admin, "STRUCTURED_TABLES_DIR", tables_dir)
    monkeypatch.setattr(admin, "AUDIT_DIR", audit_dir)
    monkeypatch.setattr(evaluation_management, "EVALUATION_SETS_DIR", tmp_path / "evaluation-sets")
    monkeypatch.setattr(admin, "job_store", FakeJobStore())
    monkeypatch.setattr(admin, "job_manager", FakeJobManager())
    monkeypatch.setattr(sources, "job_manager", FakeJobManager())
    monkeypatch.setattr(sources, "source_catalog_store", FakeSourceStore(tmp_path / "source-data"))
    monkeypatch.setattr(
        sources,
        "read_manifest",
        lambda _path: {"build_params": {"source_catalog_revision": "src-contract"}},
    )
    monkeypatch.setattr(admin, "retrieval_state", fake_state)
    monkeypatch.setattr(admin, "probe_model_providers", _provider_probes)
    monkeypatch.setattr(
        admin.builder,
        "incremental_plan",
        lambda *args, **kwargs: {
            "schema_version": 1,
            "mode": "incremental",
            "requested_mode": "incremental",
            "fallback_to_full": False,
            "fallback_reasons": [],
            "active_data_version_hash": "contract",
            "contract": {},
            "counts": {"added": 0, "changed": 0, "reused": 1, "removed": 0},
            "documents": [],
            "source_dir": "data/raw",
            "parser_backend": "mineru",
            "excluded_test_sources": [],
        },
    )
    monkeypatch.setattr(admin, "diagnose_jobs", lambda jobs, **kwargs: jobs)
    monkeypatch.setattr(admin, "diagnose_job", lambda job, **kwargs: job)
    monkeypatch.setattr(
        admin,
        "read_active_manifest",
        lambda: {
            "schema_version": 1,
            "data_version_hash": "contract",
            "documents": [{"name": "contract-doc"}],
        },
    )
    monkeypatch.setattr(
        admin,
        "read_active_db",
        lambda: {
            "active_db_dir": "contract/db",
            "manifest": "contract/manifest.json",
            "processed_dir": None,
        },
    )
    monkeypatch.setattr(admin, "current_evidence_context", lambda: {"run_id": "contract"})
    monkeypatch.setattr(admin, "retention_policy_from_settings", lambda settings: {})
    monkeypatch.setattr(admin, "inventory_versions", lambda **kwargs: _version_inventory())
    monkeypatch.setattr(
        admin,
        "set_version_pin",
        lambda version_id, pinned, note: {
            "version_id": version_id,
            "schema_version": 1,
            "pinned": pinned,
            "note": note,
            "updated_at": "2026-08-12T00:00:00Z",
        },
    )
    monkeypatch.setattr(admin, "create_cleanup_plan", lambda **kwargs: _cleanup_plan())
    monkeypatch.setattr(
        admin,
        "load_cases",
        lambda path: [SimpleNamespace(id="contract-case", query="contract query", type="clause")],
    )
    monkeypatch.setattr(admin, "load_answer_cases", lambda path: [SimpleNamespace()])
    monkeypatch.setattr(admin, "_read_latest_quality_reports", _quality_reports)
    monkeypatch.setattr(
        admin,
        "list_candidate_files",
        lambda path: [
            {
                "doc": "contract-doc",
                "path": "contract/candidates.json",
                "source_file": "contract-doc.pdf",
                "candidate_count": 1,
                "pending_count": 1,
                "approved_count": 0,
                "rejected_count": 0,
            }
        ],
    )
    monkeypatch.setattr(
        admin,
        "read_candidate_file",
        lambda doc, path: {
            "doc": doc,
            "source_file": "contract-doc.pdf",
            "corrections": [{"id": "candidate-1", "status": "pending"}],
        },
    )
    monkeypatch.setattr(
        admin,
        "update_candidate_status",
        lambda doc, candidate_id, status, path: {
            "doc": doc,
            "candidate_id": candidate_id,
            "review_status": status,
        },
    )
    monkeypatch.setattr(
        admin,
        "write_manual_structuring_queue",
        lambda path: {
            "document_count": 1,
            "candidate_count": 1,
            "documents": [{"doc": "contract-doc", "path": "contract/manual.json", "item_count": 1}],
        },
    )
    monkeypatch.setattr(admin, "active_processed_dir", lambda: tmp_path / "processed")
    monkeypatch.setattr(admin, "list_manual_structuring_files", lambda: [_manual_summary()])
    monkeypatch.setattr(
        admin,
        "read_manual_structuring_file",
        lambda doc: {"doc": doc, "updated_at": 1, "items": [{"id": "item-1"}]},
    )
    monkeypatch.setattr(
        admin,
        "update_manual_structuring_status",
        lambda doc, item_id, status, notes: {
            "doc": doc,
            "item_id": item_id,
            "review_status": status,
        },
    )
    monkeypatch.setattr(
        admin, "build_manual_structuring_draft", lambda doc, item_id: dict(SAMPLE_DRAFT)
    )
    monkeypatch.setattr(
        admin, "read_manual_structuring_draft", lambda doc, item_id: dict(SAMPLE_DRAFT)
    )
    monkeypatch.setattr(
        admin,
        "save_manual_structuring_draft",
        lambda doc, item_id, draft: {**SAMPLE_DRAFT, "rows": draft.get("rows", [])},
    )
    monkeypatch.setattr(
        admin,
        "read_structuring_suggestion",
        lambda doc, item_id: {
            "schema_version": 1,
            "doc": doc,
            "item_id": item_id,
            "proposal": {"rows": [{"value": "1.0"}]},
        },
    )
    monkeypatch.setattr(
        admin,
        "validate_manual_structuring_draft",
        lambda doc, item_id: {
            "valid": True,
            "validated_at": 1,
            "error_count": 0,
            "warning_count": 0,
            "errors": [],
            "warnings": [],
            "draft_status": "validated",
        },
    )
    monkeypatch.setattr(
        admin,
        "publish_manual_structuring_draft",
        lambda doc, item_id: {
            "draft_status": "published",
            "target_path": "contract/table.json",
            "target_filename": "table.json",
            "version_id": "version-1",
            "replaced_existing": False,
            "smoke_test": {"passed": True},
        },
    )
    monkeypatch.setattr(
        admin,
        "list_manual_structuring_versions",
        lambda doc, item_id: [
            {
                "version_id": "version-1",
                "created_at": 1,
                "target_filename": "table.json",
                "replaced_existing": False,
                "smoke_test": {"passed": True},
            }
        ],
    )
    monkeypatch.setattr(
        admin,
        "rollback_manual_structuring_publication",
        lambda doc, item_id: {
            "draft_status": "rolled_back",
            "target_path": "contract/table.json",
            "version_id": "version-1",
            "rollback_action": "removed",
        },
    )
    monkeypatch.setattr(
        admin,
        "promote_approved_candidates",
        lambda doc, path: {
            "source_file": "contract-doc.pdf",
            "candidate_count": 1,
            "promoted_count": 1,
            "skipped_count": 0,
            "approved_path": "contract/approved.json",
            "skipped": [],
        },
    )
    monkeypatch.setattr(
        admin,
        "_load_processed_doc",
        lambda doc: {
            "source_file": "contract-doc.pdf",
            "elements": [{"page": 1, "type": "text", "text": "contract"}],
        },
    )
    monkeypatch.setattr(admin, "find_source_pdf", lambda doc, path: raw_dir / "contract-doc.pdf")
    monkeypatch.setattr(admin, "render_pdf_pages", lambda pdf, pages, output: {1: png_path})
    monkeypatch.setattr(
        admin,
        "evaluate_quality_gate",
        lambda **kwargs: {
            "passed": True,
            "jobs": {
                "unresolved_failed_count": 0,
                "historical_failed_count": 0,
                "stale_active_count": 0,
            },
        },
    )
    monkeypatch.setattr(admin, "list_complete_quality_runs", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        admin,
        "compare_quality_runs",
        lambda *args, **kwargs: {"schema_version": 1, "summary": {}, "evaluation_sets": {}},
    )

    structured_set = evaluation_management.read_set("structured")
    structured_revision = structured_set["published_revision"]
    structured_cases = structured_set["cases"]
    draft_summary = {
        **structured_revision,
        "revision_id": "draft",
        "status": "draft",
        "source": "draft",
        "created_at": "2026-08-12T00:00:00Z",
        "published_at": None,
        "parent_revision_id": structured_revision["revision_id"],
        "validation_summary": None,
    }
    draft_response = {
        "evaluation_set_id": "structured",
        "draft_status": "draft",
        "draft": draft_summary,
        "case_count": len(structured_cases),
        "type_counts": {"structured_table": len(structured_cases)},
        "cases": structured_cases,
    }
    monkeypatch.setattr(admin, "create_evaluation_draft", lambda *args, **kwargs: draft_response)
    monkeypatch.setattr(admin, "update_evaluation_case", lambda *args, **kwargs: draft_response)
    monkeypatch.setattr(admin, "add_evaluation_case", lambda *args, **kwargs: draft_response)
    monkeypatch.setattr(admin, "delete_evaluation_case", lambda *args, **kwargs: draft_response)
    monkeypatch.setattr(
        admin,
        "validate_evaluation_draft",
        lambda *args, **kwargs: {
            "evaluation_set_id": "structured",
            "draft_status": "validated",
            "validation": {
                "ok": True,
                "errors": [],
                "warnings": [],
                "case_count": len(structured_cases),
                "type_counts": {"structured_table": len(structured_cases)},
                "content_hash": "contract",
                "validated_at": "2026-08-12T00:00:00Z",
            },
        },
    )
    monkeypatch.setattr(
        admin,
        "diff_evaluation_draft",
        lambda *args, **kwargs: {
            "evaluation_set_id": "structured",
            "base_revision_id": structured_revision["revision_id"],
            "draft_content_hash": "contract",
            "added": [],
            "removed": [],
            "modified": [],
            "changed_count": 0,
        },
    )
    monkeypatch.setattr(
        admin,
        "publish_evaluation_draft",
        lambda *args, **kwargs: {
            "evaluation_set_id": "structured",
            "previous_revision_id": structured_revision["revision_id"],
            "revision": structured_revision,
            "affected_report_types": ["structured"],
        },
    )
    monkeypatch.setattr(
        admin,
        "rollback_evaluation_set",
        lambda *args, **kwargs: {
            "evaluation_set_id": "structured",
            "previous_revision_id": structured_revision["revision_id"],
            "revision": structured_revision,
            "affected_report_types": ["structured"],
        },
    )

    return TestClient(app)


def _operation_map(document: dict[str, Any]) -> dict[str, tuple[str, str, str, str | None]]:
    operations: dict[str, tuple[str, str, str, str | None]] = {}
    for template, methods in document["paths"].items():
        if not template.startswith("/admin"):
            continue
        for method, operation in methods.items():
            if method not in export_openapi.HTTP_METHODS:
                continue
            content = operation["responses"]["200"]["content"]
            media_type = next(iter(content))
            schema = content[media_type].get("schema", {})
            model_name = schema.get("$ref", "").rsplit("/", 1)[-1] or None
            operations[operation["operationId"]] = (method, template, media_type, model_name)
    return operations


def _assert_complete_runtime_coverage(
    cases: tuple[RuntimeCase, ...], document: dict[str, Any]
) -> None:
    operations = _operation_map(document)
    case_ids = [case.operation_id for case in cases]
    duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    missing = sorted(set(operations) - set(case_ids))
    unknown = sorted(set(case_ids) - set(operations))
    mismatched = sorted(
        case.operation_id
        for case in cases
        if case.operation_id in operations
        and (case.method, case.template, case.media_type) != operations[case.operation_id][:3]
    )
    assert duplicates == [], f"duplicate runtime cases: {duplicates}"
    assert missing == [], f"missing runtime cases: {missing}"
    assert unknown == [], f"unknown runtime cases: {unknown}"
    assert mismatched == [], f"runtime case contract mismatch: {mismatched}"


def test_runtime_case_inventory_covers_every_admin_operation_exactly_once() -> None:
    _assert_complete_runtime_coverage(RUNTIME_CASES, export_openapi.build_openapi_document())
    assert len(RUNTIME_CASES) == 76


@pytest.mark.parametrize("case", RUNTIME_CASES, ids=lambda case: case.operation_id)
def test_admin_operation_success_response_matches_runtime_contract(
    case: RuntimeCase, runtime_client: TestClient
) -> None:
    request_kwargs = {"content": case.content} if case.content is not None else {"json": case.body}
    response: Response = runtime_client.request(case.method, case.path, **request_kwargs)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].split(";", 1)[0] == case.media_type
    if case.media_type == "image/png":
        assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
        return

    document = export_openapi.build_openapi_document()
    model_name = _operation_map(document)[case.operation_id][3]
    response_model = getattr(admin_schemas, str(model_name), None) or getattr(
        source_schemas, str(model_name)
    )
    assert issubclass(response_model, BaseModel)
    response_model.model_validate(response.json())


def test_runtime_response_validation_rejects_missing_required_fields(
    runtime_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(admin, "inventory_versions", lambda **kwargs: {})

    response = runtime_client.get("/admin/versions")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"


def test_runtime_response_validation_rejects_undeclared_fields(
    runtime_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        admin,
        "inventory_versions",
        lambda **kwargs: {**_version_inventory(), "undeclared": True},
    )

    response = runtime_client.get("/admin/versions")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"


def test_runtime_case_inventory_rejects_missing_unknown_duplicate_and_drift() -> None:
    document = export_openapi.build_openapi_document()
    with pytest.raises(AssertionError, match="missing runtime cases"):
        _assert_complete_runtime_coverage(RUNTIME_CASES[:-1], document)
    with pytest.raises(AssertionError, match="unknown runtime cases"):
        _assert_complete_runtime_coverage(
            (*RUNTIME_CASES, replace(RUNTIME_CASES[-1], operation_id="unknown")), document
        )
    with pytest.raises(AssertionError, match="duplicate runtime cases"):
        _assert_complete_runtime_coverage((*RUNTIME_CASES, RUNTIME_CASES[-1]), document)
    with pytest.raises(AssertionError, match="runtime case contract mismatch"):
        _assert_complete_runtime_coverage(
            (replace(RUNTIME_CASES[0], method="post"), *RUNTIME_CASES[1:]), document
        )
