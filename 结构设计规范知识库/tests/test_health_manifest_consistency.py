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

    result = asyncio.run(health.ready())

    assert result["ready"] is True
    assert result["checks"]["collection_count_match"] == "ok"


def test_ready_rejects_collection_manifest_mismatch(monkeypatch):
    _prepare(monkeypatch, collection_count=11, manifest_count=12)

    result = asyncio.run(health.ready())

    assert result["ready"] is False
    assert result["checks"]["collection_count_match"] == "mismatch"
