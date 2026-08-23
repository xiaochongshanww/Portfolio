from types import SimpleNamespace

import pytest


def _result(*, text="办公楼普通办公室：2.0 kN/m²"):
    return SimpleNamespace(
        meta={
            "chunk_id": "chunk-1",
            "source_file": "GB 50009-2012_建筑结构荷载规范.pdf",
            "source": "GB 50009-2012_建筑结构荷载规范.pdf",
            "code": "GB 50009-2012",
            "name": "建筑结构荷载规范",
            "version": "2012",
            "section_type": "body_table",
            "authority_level": 100,
            "is_table": True,
            "clause_number": "5.1.1",
            "table_id": "5.1.1",
            "table_name": "民用建筑楼面均布活荷载标准值",
            "pages": "32",
        },
        text=text,
        score=8.5,
        source="dense+bm25",
        reason="structured table match",
    )


@pytest.fixture
def integration_module(monkeypatch):
    from src.app.api import integrations

    monkeypatch.setattr(
        integrations,
        "retrieval_state",
        SimpleNamespace(ready=True, hybrid_search=lambda *_args: [_result()]),
    )
    monkeypatch.setattr(integrations, "find_structured_table_matches", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        integrations,
        "read_active_manifest",
        lambda: {"data_version_hash": "test-version"},
    )
    return integrations


def test_harness_search_contract_returns_structured_source(monkeypatch, integration_module):
    from fastapi.testclient import TestClient
    from src.app.main import app

    response = TestClient(app).post(
        "/integrations/deepseek-harness/search",
        json={"query": "办公楼楼面活荷载标准值", "include_assets": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_version_hash"] == "test-version"
    assert payload["result_count"] == 1
    result = payload["results"][0]
    assert result["source_kind"] == "retrieval"
    assert result["standard_code"] == "GB 50009-2012"
    assert result["section_type"] == "body_table"
    assert result["table_id"] == "5.1.1"
    assert result["pages"] == [32]


def test_harness_search_rejects_unknown_fields(integration_module):
    from fastapi.testclient import TestClient
    from src.app.main import app

    response = TestClient(app).post(
        "/integrations/deepseek-harness/search",
        json={"query": "办公楼", "admin": True},
    )

    assert response.status_code == 422


def test_harness_reports_not_ready_as_service_unavailable(monkeypatch, integration_module):
    from fastapi.testclient import TestClient
    from src.app.main import app

    monkeypatch.setattr(integration_module, "retrieval_state", SimpleNamespace(ready=False))
    client = TestClient(app)

    ready = client.get("/integrations/deepseek-harness/ready")
    search = client.post(
        "/integrations/deepseek-harness/search",
        json={"query": "办公楼楼面活荷载标准值"},
    )

    assert ready.status_code == 503
    assert ready.json()["error"]["code"] == "KNOWLEDGE_BASE_NOT_READY"
    assert search.status_code == 503
    assert search.json()["error"]["code"] == "KNOWLEDGE_BASE_NOT_READY"


def test_harness_routes_are_protected_when_api_auth_enabled(monkeypatch, integration_module):
    import src.app.core.security as security
    from fastapi.testclient import TestClient
    from src.app.main import app

    monkeypatch.setattr(
        security,
        "settings",
        SimpleNamespace(api_auth_enabled=True, api_keys=["test-key"]),
    )
    response = TestClient(app).post(
        "/integrations/deepseek-harness/search",
        json={"query": "办公楼"},
    )
    assert response.status_code == 401
