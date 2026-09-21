import logging
import math
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv() -> bool:
        return False


from src.app.core.config import settings
from src.app.core.embeddings import embedding_request_kwargs
from src.app.retrieval.dense_vector_store import build_dense_vector_store
from src.pipeline.progress import ProgressCallback, emit_progress

load_dotenv()


class PipelineError(RuntimeError):
    pass


CHROMA_HNSW_METADATA = {
    "hnsw:batch_size": 100,
    "hnsw:sync_threshold": 1000,
    "hnsw:space": "cosine",
}


def _metadata_for_chroma(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": chunk["source"],
        "source_file": chunk["source_file"],
        "code": chunk["code"],
        "name": chunk["name"],
        "version": chunk["version"],
        "effective_date": chunk["effective_date"],
        "status": chunk["status"],
        "title": chunk["title"],
        "clause_number": chunk["clause_number"],
        "chunk_type": chunk["chunk_type"],
        "section_type": chunk.get("section_type", "body"),
        "authority_level": int(chunk.get("authority_level", 50)),
        "is_table": bool(chunk.get("is_table", False)),
        "table_id": chunk.get("table_id", ""),
        "table_name": chunk.get("table_name", ""),
        "pages": ",".join(str(page) for page in chunk["pages"]),
        "images": ",".join(chunk["images"])[:500],
        "chunk_id": chunk["chunk_id"],
        "metadata_status": chunk["metadata_status"],
    }


def load_chunks_to_db(
    chunks_by_file: dict[str, list[dict[str, Any]]],
    db_dir: Path,
    *,
    progress_callback: ProgressCallback | None = None,
) -> int:
    result = load_chunks_to_db_incremental(
        chunks_by_file,
        db_dir,
        reusable_embeddings={},
        progress_callback=progress_callback,
    )
    return int(result["loaded_chunks"])


def load_chunks_to_db_incremental(
    chunks_by_file: dict[str, list[dict[str, Any]]],
    db_dir: Path,
    *,
    reusable_embeddings: dict[str, list[float]],
    progress_callback: ProgressCallback | None = None,
) -> dict[str, int]:
    try:
        import chromadb
        from zai import ZhipuAiClient
    except ImportError as exc:
        raise PipelineError(f"缺少入库依赖: {exc}") from exc

    api_key = os.environ.get("ZHIPUAI_API_KEY")
    if not api_key:
        raise PipelineError("ZHIPUAI_API_KEY 未设置，无法执行向量化入库")

    zhipu = ZhipuAiClient(api_key=api_key)
    db = chromadb.PersistentClient(path=str(db_dir))
    try:
        db.delete_collection(settings.collection_name)
        logging.info("已删除旧集合")
    except Exception:
        pass
    collection = db.get_or_create_collection(
        name=settings.collection_name,
        metadata=CHROMA_HNSW_METADATA,
    )

    pending_additions, embedding_stats = _embed_chunks_with_reuse(
        zhipu,
        chunks_by_file,
        reusable_embeddings=reusable_embeddings,
        progress_callback=progress_callback,
    )
    total = sum(len(item[0]) for item in pending_additions)
    ids = [item for batch in pending_additions for item in batch[0]]
    documents = [item for batch in pending_additions for item in batch[1]]
    metadatas = [item for batch in pending_additions for item in batch[2]]
    embeddings = [item for batch in pending_additions for item in batch[3]]
    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )
    emit_progress(
        progress_callback,
        "write_vector_db",
        "向量已写入候选集合，正在生成精确索引",
        chunk_count=total,
        generated_embedding_count=embedding_stats["generated_embedding_count"],
        reused_embedding_count=embedding_stats["reused_embedding_count"],
    )
    build_dense_vector_store(
        db_dir,
        ids,
        embeddings,
        embedding_model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    emit_progress(
        progress_callback,
        "write_vector_db",
        "精确向量索引生成完成，正在等待 Chroma 持久化",
        chunk_count=total,
    )
    logging.info("入库完成: %s 条, 集合总条目: %s", total, collection.count())
    try:
        _wait_for_persisted_records(db_dir, expected_count=total)
    finally:
        try:
            db._system.stop()
        except Exception:
            logging.warning("ChromaDB flush/stop 未显式完成", exc_info=True)
        _clear_chroma_system_cache()
    _verify_persisted_chroma_index(
        db_dir,
        expected_count=total,
    )
    emit_progress(
        progress_callback,
        "write_vector_db",
        "向量库写入完成",
        chunk_count=total,
        generated_embedding_count=embedding_stats["generated_embedding_count"],
        reused_embedding_count=embedding_stats["reused_embedding_count"],
    )
    return {"loaded_chunks": total, **embedding_stats}


def migrate_collection_embeddings(
    chunks_by_file: dict[str, list[dict[str, Any]]],
    source_db_dir: Path,
    target_db_dir: Path,
) -> int:
    """Build a fresh target collection instead of mutating the source HNSW graph."""
    try:
        import chromadb
        from zai import ZhipuAiClient
    except ImportError as exc:
        raise PipelineError(f"缺少入库依赖: {exc}") from exc

    api_key = os.environ.get("ZHIPUAI_API_KEY")
    if not api_key:
        raise PipelineError("ZHIPUAI_API_KEY 未设置，无法执行向量迁移")
    if target_db_dir.exists():
        raise PipelineError(f"迁移目标目录已存在: {target_db_dir}")
    if not source_db_dir.is_dir() or not (source_db_dir / "chroma.sqlite3").is_file():
        raise PipelineError(f"迁移源数据库不存在: {source_db_dir}")

    target_db_dir.mkdir(parents=True, exist_ok=False)
    zhipu = ZhipuAiClient(api_key=api_key)
    db = chromadb.PersistentClient(path=str(target_db_dir))
    collection = db.get_or_create_collection(
        name=settings.collection_name,
        metadata=CHROMA_HNSW_METADATA,
    )
    pending_updates = _embed_chunks(zhipu, chunks_by_file)
    ids = [item for batch in pending_updates for item in batch[0]]
    documents = [item for batch in pending_updates for item in batch[1]]
    metadatas = [item for batch in pending_updates for item in batch[2]]
    embeddings = [item for batch in pending_updates for item in batch[3]]
    collection.delete(ids=ids)
    if collection.count() != 0:
        raise PipelineError(f"迁移源集合未能清空: actual={collection.count()}")
    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )
    build_dense_vector_store(
        target_db_dir,
        ids,
        embeddings,
        embedding_model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    logging.info("向量迁移完成: %s 条, 集合总条目: %s", len(ids), collection.count())
    try:
        _wait_for_persisted_records(target_db_dir, expected_count=len(ids))
    finally:
        try:
            db._system.stop()
        except Exception:
            logging.warning("目标 Chroma flush/stop 未显式完成", exc_info=True)
        _clear_chroma_system_cache()
    _verify_persisted_chroma_index(
        target_db_dir,
        expected_count=len(ids),
    )
    return len(ids)


def _embed_chunks(
    zhipu: Any,
    chunks_by_file: dict[str, list[dict[str, Any]]],
) -> list[tuple[list[str], list[str], list[dict[str, Any]], list[list[float]]]]:
    pending_additions, _stats = _embed_chunks_with_reuse(
        zhipu,
        chunks_by_file,
        reusable_embeddings={},
    )
    return pending_additions


def _valid_reusable_embedding(vector: Any) -> bool:
    return (
        isinstance(vector, list)
        and len(vector) == settings.embedding_dimensions
        and all(math.isfinite(float(value)) for value in vector)
        and any(float(value) != 0 for value in vector)
    )


def _embed_chunks_with_reuse(
    zhipu: Any,
    chunks_by_file: dict[str, list[dict[str, Any]]],
    *,
    reusable_embeddings: dict[str, list[float]],
    progress_callback: ProgressCallback | None = None,
) -> tuple[
    list[tuple[list[str], list[str], list[dict[str, Any]], list[list[float]]]],
    dict[str, int],
]:
    pending_additions: list[
        tuple[list[str], list[str], list[dict[str, Any]], list[list[float]]]
    ] = []
    reused_count = 0
    generated_count = 0
    total_chunks = sum(len(chunks) for chunks in chunks_by_file.values())
    processed_chunks = 0
    document_total = len(chunks_by_file)
    for document_index, (source_file, chunks) in enumerate(chunks_by_file.items(), start=1):
        logging.info("入库 %s: %s 个 chunk", source_file, len(chunks))
        emit_progress(
            progress_callback,
            "embedding",
            "开始处理文档向量",
            document=source_file,
            document_index=document_index,
            document_total=document_total,
            chunk_current=processed_chunks,
            chunk_total=total_chunks,
        )
        for index in range(0, len(chunks), 10):
            batch = chunks[index : index + 10]
            generated_batch = [
                chunk
                for chunk in batch
                if not _valid_reusable_embedding(reusable_embeddings.get(str(chunk["chunk_id"])))
            ]
            generated_vectors: dict[str, list[float]] = {}
            try:
                if generated_batch:
                    response = zhipu.embeddings.create(
                        **embedding_request_kwargs(
                            settings, [str(chunk["text"]) for chunk in generated_batch]
                        )
                    )
                    vectors = [item.embedding for item in response.data]
                    if len(vectors) != len(generated_batch) or any(
                        not _valid_reusable_embedding(vector) for vector in vectors
                    ):
                        raise PipelineError(
                            f"{source_file} 批次 {index // 10 + 1} 返回了无效 embedding"
                        )
                    generated_vectors = {
                        str(chunk["chunk_id"]): vector
                        for chunk, vector in zip(generated_batch, vectors, strict=True)
                    }
                texts = [str(chunk["text"]) for chunk in batch]
                ids = [chunk["chunk_id"] for chunk in batch]
                metadatas = [_metadata_for_chroma(chunk) for chunk in batch]
                embeddings = [
                    reusable_embeddings.get(str(chunk["chunk_id"]))
                    or generated_vectors[str(chunk["chunk_id"])]
                    for chunk in batch
                ]
                pending_additions.append((ids, texts, metadatas, embeddings))
                generated_count += len(generated_batch)
                reused_count += len(batch) - len(generated_batch)
                processed_chunks += len(batch)
                emit_progress(
                    progress_callback,
                    "embedding",
                    "正在生成或复用向量",
                    document=source_file,
                    document_index=document_index,
                    document_total=document_total,
                    chunk_current=processed_chunks,
                    chunk_total=total_chunks,
                    generated_embedding_count=generated_count,
                    reused_embedding_count=reused_count,
                    batch_size=len(batch),
                )
            except Exception as exc:
                raise PipelineError(
                    f"{source_file} 批次 {index // 10 + 1} 入库失败: {exc}"
                ) from exc
    return pending_additions, {
        "reused_embedding_count": reused_count,
        "generated_embedding_count": generated_count,
    }


def _verify_persisted_chroma_index(
    db_dir: Path,
    *,
    expected_count: int,
) -> None:
    """Verify Chroma's durable record layer without loading its native index."""
    database_path = db_dir / "chroma.sqlite3"
    if not database_path.is_file():
        raise PipelineError(f"Chroma 数据库文件未落盘: {db_dir}")
    try:
        with sqlite3.connect(database_path, timeout=5) as connection:
            actual_count = int(connection.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0])
        if actual_count != expected_count:
            raise PipelineError(
                f"Chroma 持久化条目数不一致: expected={expected_count}, actual={actual_count}"
            )
    except PipelineError:
        raise
    except (sqlite3.Error, TypeError, IndexError) as exc:
        raise PipelineError(f"Chroma 持久化验证失败: {db_dir}: {exc}") from exc


def _clear_chroma_system_cache() -> None:
    """Prevent a stopped PersistentClient from being reused for the next path."""
    try:
        from chromadb.api.client import SharedSystemClient

        SharedSystemClient.clear_system_cache()
    except (ImportError, AttributeError):
        logging.debug("当前 Chroma 版本不提供 SharedSystemClient 缓存清理", exc_info=True)


def _wait_for_persisted_records(
    db_dir: Path, *, expected_count: int, timeout_seconds: float = 60.0
) -> None:
    # Chroma retains replay logs below its HNSW sync threshold. They are not
    # outstanding writes; serving uses durable records plus our exact index.
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            _verify_persisted_chroma_index(db_dir, expected_count=expected_count)
            return
        except PipelineError as exc:
            if time.monotonic() >= deadline:
                raise PipelineError(f"Chroma 持久化记录等待超时: {exc}") from exc
        time.sleep(0.5)
