from __future__ import annotations

import sys
import types
from pathlib import Path

import chromadb
from chromadb.api.client import SharedSystemClient
from src.app.retrieval.dense_vector_store import load_dense_vector_store
from src.pipeline import load_to_db

try:
    import zai
except ModuleNotFoundError:
    zai = types.ModuleType("zai")
    sys.modules["zai"] = zai


def _chunk(index: int) -> dict[str, object]:
    return {
        "source": "test",
        "source_file": "migration-test.pdf",
        "code": "TEST",
        "name": "迁移测试",
        "version": "1",
        "effective_date": "2026-01-01",
        "status": "active",
        "title": f"测试条文 {index}",
        "clause_number": str(index),
        "chunk_type": "text",
        "section_type": "body",
        "authority_level": 80,
        "is_table": False,
        "table_id": "",
        "table_name": "",
        "pages": [1],
        "images": [],
        "chunk_id": f"migration-{index}",
        "metadata_status": "complete",
        "text": f"迁移测试文本 {index}",
    }


class _EmbeddingResponse:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.data = [type("EmbeddingItem", (), {"embedding": vector})() for vector in vectors]


class _FakeEmbeddings:
    def create(self, *, input: list[str], **_: object) -> _EmbeddingResponse:
        vectors = []
        for index, _text in enumerate(input):
            vector = [0.0] * 1024
            vector[index % 1024] = 1.0
            vectors.append(vector)
        return _EmbeddingResponse(vectors)


class _FakeZhipuClient:
    def __init__(self, *, api_key: str) -> None:
        assert api_key
        self.embeddings = _FakeEmbeddings()


def _create_source_db(path: Path, chunks: list[dict[str, object]]) -> None:
    client = chromadb.PersistentClient(path=str(path))
    collection = client.get_or_create_collection(
        name=load_to_db.settings.collection_name,
        metadata=load_to_db.CHROMA_HNSW_METADATA,
    )
    collection.add(
        ids=[str(chunk["chunk_id"]) for chunk in chunks],
        embeddings=[[1.0 if index == 0 else 0.0] + [0.0] * 1023 for index in chunks],
        documents=[str(chunk["text"]) for chunk in chunks],
        metadatas=[load_to_db._metadata_for_chroma(chunk) for chunk in chunks],
    )
    client._system.stop()
    SharedSystemClient.clear_system_cache()


def test_embedding_migration_builds_a_fresh_persisted_vector_index(
    tmp_path: Path, monkeypatch
) -> None:
    metadata = dict(load_to_db.CHROMA_HNSW_METADATA)
    metadata.update({"hnsw:batch_size": 10, "hnsw:sync_threshold": 10})
    monkeypatch.setattr(load_to_db, "CHROMA_HNSW_METADATA", metadata)
    monkeypatch.setenv("ZHIPUAI_API_KEY", "migration-test-key")
    monkeypatch.setattr(zai, "ZhipuAiClient", _FakeZhipuClient, raising=False)

    chunks = [_chunk(index) for index in range(20)]
    source_db = tmp_path / "source"
    target_db = tmp_path / "target"
    _create_source_db(source_db, chunks)

    migrated = load_to_db.migrate_collection_embeddings(
        {"migration-test.pdf": chunks}, source_db, target_db
    )

    assert migrated == len(chunks)
    vector_store = load_dense_vector_store(
        target_db,
        expected_ids=[str(chunk["chunk_id"]) for chunk in chunks],
        dimensions=1024,
        embedding_model="embedding-3",
    )
    assert vector_store is not None
    assert len(vector_store.ids) == len(chunks)
    assert vector_store.query([1.0] + [0.0] * 1023, limit=1)
