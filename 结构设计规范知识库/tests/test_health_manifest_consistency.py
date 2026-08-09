import asyncio
import importlib
from types import SimpleNamespace

health = importlib.import_module("src.app.api.health")


def _prepare(monkeypatch, *, collection_count: int, manifest_count: int) -> None:
    configured = SimpleNamespace(
        app_version="test",
        collection_name="design_specs",
        zhipuai_api_key="test",
        mimo_api_key="test",
    )
    monkeypatch.setattr(health, "settings", configured)
    monkeypatch.setattr(health.retrieval_state, "chroma_collection", object())
    monkeypatch.setattr(health.retrieval_state, "bm25_index", object())
    monkeypatch.setattr(health.retrieval_state, "chroma_count", lambda: collection_count)
    monkeypatch.setattr(
        health,
        "read_active_manifest",
        lambda: {"chunk_count": manifest_count, "collection_name": configured.collection_name},
    )


def test_ready_accepts_matching_active_manifest(monkeypatch):
    _prepare(monkeypatch, collection_count=12, manifest_count=12)

    result = health.readiness_snapshot()

    assert result["ready"] is True
    assert result["status"] == "ready"
    assert result["reasons"] == []
    assert result["checks"]["collection_count_match"] == "ok"


def test_ready_rejects_collection_manifest_mismatch(monkeypatch):
    _prepare(monkeypatch, collection_count=11, manifest_count=12)

    snapshot = health.readiness_snapshot()
    response = asyncio.run(health.ready())

    assert snapshot["ready"] is False
    assert snapshot["status"] == "not_ready"
    assert snapshot["checks"]["collection_count_match"] == "mismatch"
    assert "COLLECTION_MANIFEST_MISMATCH" in snapshot["reasons"]
    assert response.status_code == 503
