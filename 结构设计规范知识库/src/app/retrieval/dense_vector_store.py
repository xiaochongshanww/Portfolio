from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

VECTOR_FILE_NAME = "dense_vectors.npy"
METADATA_FILE_NAME = "dense_vectors.json"
VECTOR_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class DenseVectorStore:
    """Portable exact cosine index for the current knowledge-base scale."""

    ids: tuple[str, ...]
    vectors: np.ndarray
    embedding_model: str
    dimensions: int

    def query(self, embedding: list[float], limit: int) -> list[tuple[str, float]]:
        if not 1 <= limit <= len(self.ids):
            raise ValueError("limit 必须在 1 到向量数量之间")
        query = np.asarray(embedding, dtype=np.float32)
        if query.ndim != 1 or query.shape[0] != self.dimensions:
            raise ValueError(
                f"查询向量维度不一致: expected={self.dimensions}, actual={query.shape[0] if query.ndim == 1 else 'invalid'}"
            )
        if not np.isfinite(query).all():
            raise ValueError("查询向量包含非有限数值")
        query_norm = float(np.linalg.norm(query))
        if query_norm == 0:
            raise ValueError("查询向量不能是零向量")
        scores = self.vectors @ (query / query_norm)
        candidate_count = min(limit, len(scores))
        candidate_indices = np.argpartition(-scores, candidate_count - 1)[:candidate_count]
        ordered = candidate_indices[np.argsort(-scores[candidate_indices], kind="stable")]
        return [(self.ids[int(index)], 1.0 - float(scores[index])) for index in ordered]


def build_dense_vector_store(
    db_dir: Path,
    ids: list[str],
    embeddings: list[list[float]],
    *,
    embedding_model: str,
    dimensions: int,
) -> DenseVectorStore:
    if not ids or len(ids) != len(embeddings):
        raise ValueError("向量索引的 ID 与向量数量不一致")
    if len(ids) != len(set(ids)) or any(not item for item in ids):
        raise ValueError("向量索引包含空 ID 或重复 ID")
    vectors = np.asarray(embeddings, dtype=np.float32)
    if vectors.shape != (len(ids), dimensions):
        raise ValueError(
            f"向量索引维度不一致: expected={(len(ids), dimensions)}, actual={vectors.shape}"
        )
    if not np.isfinite(vectors).all():
        raise ValueError("向量索引包含非有限数值")
    norms = np.linalg.norm(vectors, axis=1)
    if np.any(norms == 0):
        raise ValueError("向量索引包含零向量")
    normalized = vectors / norms[:, None]
    store = DenseVectorStore(tuple(ids), normalized, embedding_model, dimensions)

    db_dir.mkdir(parents=True, exist_ok=True)
    vector_path = db_dir / VECTOR_FILE_NAME
    metadata_path = db_dir / METADATA_FILE_NAME
    temporary_vector_path = db_dir / f".{VECTOR_FILE_NAME}.tmp"
    temporary_metadata_path = db_dir / f".{METADATA_FILE_NAME}.tmp"
    with temporary_vector_path.open("wb") as handle:
        np.save(handle, normalized, allow_pickle=False)
    temporary_metadata_path.write_text(
        json.dumps(
            {
                "schema_version": VECTOR_SCHEMA_VERSION,
                "embedding_model": embedding_model,
                "dimensions": dimensions,
                "count": len(ids),
                "ids": ids,
                "dtype": "float32",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    os.replace(temporary_vector_path, vector_path)
    os.replace(temporary_metadata_path, metadata_path)
    return store


def load_dense_vector_store(
    db_dir: Path,
    *,
    expected_ids: list[str] | None = None,
    embedding_model: str | None = None,
    dimensions: int | None = None,
) -> DenseVectorStore | None:
    vector_path = db_dir / VECTOR_FILE_NAME
    metadata_path = db_dir / METADATA_FILE_NAME
    if not vector_path.exists() and not metadata_path.exists():
        return None
    if not vector_path.is_file() or not metadata_path.is_file():
        raise ValueError(f"向量索引产物不完整: {db_dir}")
    try:
        metadata: dict[str, Any] = json.loads(metadata_path.read_text(encoding="utf-8"))
        vectors = np.load(vector_path, mmap_mode="r", allow_pickle=False)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"向量索引无法读取: {db_dir}") from exc

    ids = tuple(str(item) for item in metadata.get("ids", []))
    model = str(metadata.get("embedding_model") or "")
    stored_dimensions = int(metadata.get("dimensions", 0))
    if (
        metadata.get("schema_version") != VECTOR_SCHEMA_VERSION
        or metadata.get("count") != len(ids)
        or metadata.get("dtype") != "float32"
        or not ids
        or vectors.shape != (len(ids), stored_dimensions)
        or stored_dimensions <= 0
    ):
        raise ValueError(f"向量索引元数据无效: {db_dir}")
    if expected_ids is not None and set(ids) != set(expected_ids):
        raise ValueError("向量索引 ID 集合与运行数据不一致")
    if embedding_model is not None and model != embedding_model:
        raise ValueError(
            f"向量索引模型不一致: expected={embedding_model}, actual={model}"
        )
    if dimensions is not None and stored_dimensions != dimensions:
        raise ValueError(
            f"向量索引维度不一致: expected={dimensions}, actual={stored_dimensions}"
        )
    return DenseVectorStore(ids, vectors, model, stored_dimensions)
