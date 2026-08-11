import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from scripts import export_openapi
from src.app.schemas.admin import ActiveDatabaseResponse, JobResponse, ManifestResponse


def _admin_operation(document: dict, path: str, method: str = "get") -> dict:
    return document["paths"][path][method]


def test_openapi_generator_requires_locked_framework_versions(monkeypatch) -> None:
    locked = export_openapi.locked_generator_versions()
    monkeypatch.setattr(
        export_openapi.importlib_metadata,
        "version",
        lambda package: "0.0.0" if package == "fastapi" else locked[package],
    )

    with pytest.raises(export_openapi.OpenApiContractError, match="fastapi=0.0.0"):
        export_openapi.validate_generator_environment()


def test_admin_openapi_contract_covers_every_operation() -> None:
    document = export_openapi.build_openapi_document()
    operations = [
        (path, method, operation)
        for path, methods in document["paths"].items()
        if path.startswith("/admin")
        for method, operation in methods.items()
        if method in export_openapi.HTTP_METHODS
    ]
    assert len(operations) == 45
    assert export_openapi.count_admin_operations(document) == len(operations)
    assert len({operation["operationId"] for _, _, operation in operations}) == 45

    for path, method, operation in operations:
        content = operation["responses"]["200"]["content"]
        if path == export_openapi.PAGE_IMAGE_PATH:
            assert method == "get"
            assert set(content) == {"image/png"}
        else:
            schema = content["application/json"]["schema"]
            assert schema
            assert "$ref" in schema


def test_contract_rejects_empty_json_response_schema() -> None:
    document = copy.deepcopy(export_openapi.build_openapi_document())
    operation = _admin_operation(document, "/admin/status")
    operation["responses"]["200"]["content"]["application/json"]["schema"] = {}
    with pytest.raises(export_openapi.OpenApiContractError, match="empty JSON"):
        export_openapi.validate_admin_contract(document)


def test_contract_rejects_page_image_json_media_type() -> None:
    document = copy.deepcopy(export_openapi.build_openapi_document())
    operation = _admin_operation(document, export_openapi.PAGE_IMAGE_PATH)
    operation["responses"]["200"]["content"] = {"application/json": {"schema": {}}}
    with pytest.raises(export_openapi.OpenApiContractError, match="image/png"):
        export_openapi.validate_admin_contract(document)


def test_contract_rejects_duplicate_operation_id() -> None:
    document = copy.deepcopy(export_openapi.build_openapi_document())
    first = _admin_operation(document, "/admin/status")["operationId"]
    _admin_operation(document, "/admin/documents")["operationId"] = first
    with pytest.raises(export_openapi.OpenApiContractError, match="duplicate operationId"):
        export_openapi.validate_admin_contract(document)


def test_snapshot_check_detects_drift_and_write_is_deterministic(tmp_path: Path) -> None:
    document = export_openapi.build_openapi_document()
    rendered = export_openapi.render_openapi(document)
    snapshot = tmp_path / "openapi.json"

    export_openapi.atomic_write_text(snapshot, rendered)
    export_openapi.check_snapshot(snapshot, rendered)
    assert json.loads(snapshot.read_text(encoding="utf-8"))["openapi"]

    snapshot.write_text("{}\n", encoding="utf-8")
    with pytest.raises(export_openapi.OpenApiContractError, match="drifted"):
        export_openapi.check_snapshot(snapshot, rendered)


def test_checked_in_snapshot_matches_application_contract() -> None:
    document = export_openapi.build_openapi_document()
    export_openapi.check_snapshot(
        export_openapi.DEFAULT_OUTPUT,
        export_openapi.render_openapi(document),
    )


def test_response_model_rejects_missing_required_fields() -> None:
    with pytest.raises(ValidationError):
        JobResponse.model_validate({"job_id": "incomplete"})


def test_active_database_response_accepts_legacy_null_runtime_paths() -> None:
    response = ActiveDatabaseResponse.model_validate(
        {
            "active_db_dir": "data/db_versions/import-package/db",
            "manifest": "data/db_versions/import-package/manifest.json",
            "processed_dir": None,
            "images_dir": "data/images",
            "mineru_dir": None,
            "audit_dir": None,
            "candidate_gate_report": None,
            "loaded_db_dir": "data/db_versions/import-package/db",
            "collection_count": 3,
        }
    )

    assert response.processed_dir is None


def test_response_models_only_allow_extensions_at_explicit_open_boundaries() -> None:
    with pytest.raises(ValidationError, match="unexpected"):
        JobResponse.model_validate(
            {
                "type": "audit",
                "job_id": "job-1",
                "status": "queued",
                "step": "queued",
                "created_at": "2026-08-12T00:00:00Z",
                "unexpected": True,
            }
        )

    manifest = ManifestResponse.model_validate({"schema_version": 1, "producer_extension": True})
    assert manifest.model_extra == {"producer_extension": True}


def test_openapi_only_exposes_declared_open_response_boundaries() -> None:
    schemas = export_openapi.build_openapi_document()["components"]["schemas"]
    open_schemas = {
        name for name, schema in schemas.items() if schema.get("additionalProperties") is True
    }

    assert open_schemas == {
        "ApprovedCorrectionsResponse",
        "CandidateDetailResponse",
        "ElementResponse",
        "ManifestResponse",
        "ManualDetailResponse",
        "ManualDraftResponse",
        "StructuringSuggestionResponse",
    }
