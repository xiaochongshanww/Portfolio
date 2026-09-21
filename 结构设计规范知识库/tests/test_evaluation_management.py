from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from src.app.main import app
from src.evaluation import management


@pytest.fixture
def isolated_evaluation_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    store = tmp_path / "evaluation_sets"
    monkeypatch.setattr(management, "EVALUATION_SETS_DIR", store)
    return store


def test_builtin_sets_are_read_only_fallbacks(isolated_evaluation_store: Path) -> None:
    sets = management.list_sets()

    assert [item["evaluation_set_id"] for item in sets] == ["regular", "structured", "answer"]
    assert [item["published_revision"]["source"] for item in sets] == [
        "builtin",
        "builtin",
        "builtin",
    ]
    assert [item["case_count"] for item in sets] == [100, 12, 24]
    assert not isolated_evaluation_store.exists()


def test_builtin_migration_materializes_a_stable_managed_revision(
    isolated_evaluation_store: Path,
) -> None:
    planned = management.migrate_builtin_assets("structured", dry_run=True)
    assert planned["planned_count"] == 1
    assert not isolated_evaluation_store.exists()

    migrated = management.migrate_builtin_assets("structured", actor="operator")
    assert migrated["migrated_count"] == 1
    revision = migrated["results"][0]["revision"]
    assert revision["source"] == "builtin_migrated"
    assert revision["created_by"] == "operator"
    assert management.published_revision_id("structured") == revision["revision_id"]
    assert management.resolve_published_asset("structured").is_file()
    assert (isolated_evaluation_store / "structured" / "manifest.json").is_file()

    repeated = management.migrate_builtin_assets("structured")
    assert repeated["unchanged_count"] == 1
    assert repeated["results"][0]["revision"]["revision_id"] == revision["revision_id"]
    refresh_events = management.list_quality_refresh_events()
    assert len(refresh_events) == 1
    assert refresh_events[0]["revision_id"] == revision["revision_id"]
    assert refresh_events[0]["status"] == "pending"


def test_builtin_migration_does_not_overwrite_draft_or_publish_on_manifest_failure(
    isolated_evaluation_store: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    management.create_draft("structured")
    with pytest.raises(management.EvaluationSetConflict, match="已有草稿"):
        management.migrate_builtin_assets("structured")

    draft_path = isolated_evaluation_store / "structured" / "draft.jsonl"
    draft_path.unlink()
    manifest_path = isolated_evaluation_store / "structured" / "manifest.json"
    manifest_before = manifest_path.read_text(encoding="utf-8")

    def fail_manifest(*args, **kwargs):
        raise OSError("injected manifest failure")

    monkeypatch.setattr(management, "_write_manifest", fail_manifest)
    with pytest.raises(OSError, match="injected manifest failure"):
        management.migrate_builtin_assets("structured")
    assert manifest_path.read_text(encoding="utf-8") == manifest_before
    assert not list((isolated_evaluation_store / "structured" / "revisions").glob("*.jsonl"))
    assert management.published_revision_id("structured").startswith("builtin-")


def test_corrupt_manifest_blocks_reads_without_using_builtin_fallback(
    isolated_evaluation_store: Path,
) -> None:
    management.migrate_builtin_assets("structured")
    manifest_path = isolated_evaluation_store / "structured" / "manifest.json"
    manifest_path.write_text("{", encoding="utf-8")

    with pytest.raises(management.EvaluationSetError, match="清单无法读取"):
        management.read_set("structured")


def test_validation_duplicate_warning_ignores_empty_queries(
    isolated_evaluation_store: Path,
) -> None:
    management.create_draft("structured")
    rows = management._draft_rows("structured")
    rows[0]["query"] = ""
    rows[1]["query"] = ""
    management._atomic_write(management._draft_path("structured"), management._jsonl_bytes(rows))
    result = management.validate_draft("structured")
    assert result["validation"]["warnings"] == []


def test_draft_validation_publish_and_rollback_create_immutable_revisions(
    isolated_evaluation_store: Path,
) -> None:
    draft = management.create_draft("structured")
    edited = deepcopy(draft["cases"][0])
    edited["query"] = "修改后的结构化评估问题"

    management.update_case("structured", str(edited["id"]), edited)
    validation = management.validate_draft("structured")
    assert validation["validation"]["ok"] is True
    assert management.diff_draft("structured")["changed_count"] == 1

    publication = management.publish_draft("structured")
    assert publication["affected_report_types"] == ["structured"]
    revision_id = publication["revision"]["revision_id"]
    assert revision_id.startswith("r-")
    assert management.published_revision_id("structured") == revision_id
    assert management.resolve_published_asset("structured").name == f"{revision_id}.jsonl"
    assert not (isolated_evaluation_store / "structured" / "draft.jsonl").exists()

    rollback = management.rollback(
        "structured", management.list_revisions("structured")[-1]["revision_id"]
    )
    assert rollback["affected_report_types"] == ["structured"]
    rollback_id = rollback["revision"]["revision_id"]
    assert rollback_id != revision_id
    assert management.published_revision_id("structured") == rollback_id
    assert management.read_set("structured")["cases"]
    refresh_events = management.list_quality_refresh_events()
    assert [item["revision_id"] for item in refresh_events][:2] == [rollback_id, revision_id]

    events = management.list_audit_events("structured")
    operations = {str(event["operation"]) for event in events}
    assert {
        "draft_create",
        "case_update",
        "draft_validate",
        "draft_publish",
        "revision_rollback",
    } <= operations
    assert all("修改后的结构化评估问题" not in str(event) for event in events)


def test_draft_case_mutations_are_scoped_to_existing_draft(
    isolated_evaluation_store: Path,
) -> None:
    with pytest.raises(management.EvaluationSetNotFound):
        management.update_case("regular", "missing", {"id": "missing"})

    management.create_draft("regular")
    case = {
        "id": "new-case",
        "query": "新问题",
        "expected_sources": ["GB 50009-2012"],
        "expected_clause": "5.1.1",
        "expected_keywords": ["标准值"],
        "type": "table",
        "expected_authority_type": "table",
        "top1_source_required": True,
        "keyword_required": True,
        "expected_table_id": "表5.1.1",
    }
    result = management.add_case("regular", case)
    assert any(item["id"] == "new-case" for item in result["cases"])

    result = management.delete_case("regular", "new-case")
    assert result["deleted_case_id"] == "new-case"
    with pytest.raises(management.EvaluationSetNotFound):
        management.delete_case("regular", "new-case")


def test_publish_failure_restores_previous_manifest_and_draft(
    isolated_evaluation_store: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    management.create_draft("structured")
    management.validate_draft("structured")
    draft_path = isolated_evaluation_store / "structured" / "draft.jsonl"
    draft_before = draft_path.read_bytes()
    revision_before = management.published_revision_id("structured")
    original_write_manifest = management._write_manifest
    failed = False

    def fail_once(evaluation_set_id: str, manifest: dict[str, object]) -> None:
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("injected publish manifest failure")
        original_write_manifest(evaluation_set_id, manifest)

    monkeypatch.setattr(management, "_write_manifest", fail_once)
    with pytest.raises(OSError, match="injected publish manifest failure"):
        management.publish_draft("structured")

    assert management.published_revision_id("structured") == revision_before
    assert draft_path.read_bytes() == draft_before
    assert not list((isolated_evaluation_store / "structured" / "revisions").glob("*.jsonl"))
    assert any(
        event["operation"] == "draft_publish" and event["status"] == "failed"
        for event in management.list_audit_events("structured")
    )


def test_publish_queue_failure_restores_published_state_and_queue(
    isolated_evaluation_store: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    management.create_draft("structured")
    management.validate_draft("structured")
    draft_path = isolated_evaluation_store / "structured" / "draft.jsonl"
    draft_before = draft_path.read_bytes()
    revision_before = management.published_revision_id("structured")

    def fail_queue(*args, **kwargs):
        raise OSError("injected refresh queue failure")

    monkeypatch.setattr(management, "_enqueue_quality_refresh", fail_queue)
    with pytest.raises(OSError, match="injected refresh queue failure"):
        management.publish_draft("structured")

    assert management.published_revision_id("structured") == revision_before
    assert draft_path.read_bytes() == draft_before
    assert not list((isolated_evaluation_store / "structured" / "revisions").glob("*.jsonl"))
    assert not (isolated_evaluation_store / management.REFRESH_QUEUE_NAME).exists()


def test_draft_write_failure_restores_previous_draft_and_manifest(
    isolated_evaluation_store: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    management.create_draft("structured")
    draft_path = isolated_evaluation_store / "structured" / "draft.jsonl"
    manifest_path = isolated_evaluation_store / "structured" / "manifest.json"
    draft_before = draft_path.read_bytes()
    manifest_before = manifest_path.read_bytes()
    original_write_manifest = management._write_manifest

    def fail_manifest(*args, **kwargs):
        raise OSError("injected draft manifest failure")

    monkeypatch.setattr(management, "_write_manifest", fail_manifest)
    with pytest.raises(OSError, match="injected draft manifest failure"):
        management.update_case(
            "structured",
            "structured-live-load-office",
            {"id": "structured-live-load-office", "query": "changed"},
        )

    assert draft_path.read_bytes() == draft_before
    assert manifest_path.read_bytes() == manifest_before
    assert any(
        event["operation"] == "case_update" and event["status"] == "failed"
        for event in management.list_audit_events("structured")
    )
    monkeypatch.setattr(management, "_write_manifest", original_write_manifest)


def test_concurrent_publish_has_one_winner_and_keeps_a_valid_state(
    isolated_evaluation_store: Path,
) -> None:
    management.create_draft("structured")
    management.validate_draft("structured")

    def publish_once() -> dict[str, object] | BaseException:
        try:
            return management.publish_draft("structured")
        except BaseException as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(publish_once) for _ in range(2)]
        outcomes = [future.result() for future in futures]

    successful = [outcome for outcome in outcomes if isinstance(outcome, dict)]
    failures = [outcome for outcome in outcomes if isinstance(outcome, BaseException)]
    assert len(successful) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], management.EvaluationSetError)
    assert management.read_set("structured")["published_revision"]["status"] == "published"
    assert len(list((isolated_evaluation_store / "structured" / "revisions").glob("*.jsonl"))) == 1


def test_evaluation_set_api_exposes_lifecycle_without_filesystem_paths(
    isolated_evaluation_store: Path,
) -> None:
    client = TestClient(app)

    response = client.get("/admin/evaluation/sets")
    assert response.status_code == 200
    assert {item["evaluation_set_id"] for item in response.json()["sets"]} == {
        "regular",
        "structured",
        "answer",
    }

    response = client.post("/admin/evaluation/sets/structured/drafts")
    assert response.status_code == 200
    assert response.json()["draft_status"] == "draft"

    response = client.post("/admin/evaluation/sets/structured/validate")
    assert response.status_code == 200
    assert response.json()["validation"]["ok"] is True

    response = client.get("/admin/evaluation/sets/structured/diff")
    assert response.status_code == 200
    assert response.json()["changed_count"] == 0

    response = client.post("/admin/evaluation/sets/structured/publish")
    assert response.status_code == 200
    assert response.json()["revision"]["source"] == "managed"
    assert "evaluation_sets" not in response.text

    response = client.get("/admin/evaluation/sets/unknown")
    assert response.status_code == 404
