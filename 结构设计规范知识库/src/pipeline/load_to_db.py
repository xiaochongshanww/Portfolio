import logging
import math
import os
import shutil
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


def load_chunks_to_db(chunks_by_file: dict[str, list[dict[str, Any]]], db_dir: Path) -> int:
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

    pending_additions = _embed_chunks(zhipu, chunks_by_file)
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
    logging.info("入库完成: %s 条, 集合总条目: %s", total, collection.count())
    _wait_for_hnsw_sync(db_dir)
    try:
        db._system.stop()
    except Exception:
        logging.warning("ChromaDB flush/stop 未显式完成", exc_info=True)
    _repair_incomplete_hnsw_index(db_dir)
    return total


def migrate_collection_embeddings(
    chunks_by_file: dict[str, list[dict[str, Any]]],
    source_db_dir: Path,
    target_db_dir: Path,
) -> int:
    """Rebuild a copied collection by replacing all records without explicit Rust shutdown."""
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
    if not source_db_dir.is_dir():
        raise PipelineError(f"迁移源数据库不存在: {source_db_dir}")

    shutil.copytree(source_db_dir, target_db_dir)
    zhipu = ZhipuAiClient(api_key=api_key)
    db = chromadb.PersistentClient(path=str(target_db_dir))
    collection = db.get_collection(settings.collection_name)
    expected_count = sum(len(chunks) for chunks in chunks_by_file.values())
    if collection.count() != expected_count:
        raise PipelineError(
            f"迁移源集合条目数不一致: expected={expected_count}, actual={collection.count()}"
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
    logging.info("向量迁移完成: %s 条, 集合总条目: %s", len(ids), collection.count())
    _wait_for_hnsw_sync(target_db_dir)
    _wait_for_hnsw_index(target_db_dir)
    # Let the migration process exit naturally so Chroma can finish its Rust writer.
    _repair_incomplete_hnsw_index(target_db_dir)
    return len(ids)


def _embed_chunks(
    zhipu: Any,
    chunks_by_file: dict[str, list[dict[str, Any]]],
) -> list[tuple[list[str], list[str], list[dict[str, Any]], list[list[float]]]]:
    pending_additions: list[tuple[list[str], list[str], list[dict[str, Any]], list[list[float]]]] = []
    for source_file, chunks in chunks_by_file.items():
        logging.info("入库 %s: %s 个 chunk", source_file, len(chunks))
        for index in range(0, len(chunks), 10):
            batch = chunks[index : index + 10]
            texts = [chunk["text"] for chunk in batch]
            try:
                response = zhipu.embeddings.create(
                    **embedding_request_kwargs(settings, texts)
                )
                embeddings = [item.embedding for item in response.data]
                if len(embeddings) != len(batch) or any(
                    len(vector) != settings.embedding_dimensions
                    or any(not math.isfinite(float(value)) for value in vector)
                    for vector in embeddings
                ):
                    raise PipelineError(
                        f"{source_file} 批次 {index // 10 + 1} 返回了无效 embedding"
                    )
                ids = [chunk["chunk_id"] for chunk in batch]
                metadatas = [_metadata_for_chroma(chunk) for chunk in batch]
                pending_additions.append((ids, texts, metadatas, embeddings))
            except Exception as exc:
                raise PipelineError(
                    f"{source_file} 批次 {index // 10 + 1} 入库失败: {exc}"
                ) from exc
    return pending_additions


def _repair_incomplete_hnsw_index(db_dir: Path) -> None:
    """Fail closed when Chroma did not persist a readable HNSW index."""
    index_files = list(db_dir.glob("*/data_level0.bin"))
    if not index_files:
        raise PipelineError(f"Chroma HNSW 索引未落盘: {db_dir}")
    for metadata_path in db_dir.glob("*/index_metadata.pickle"):
        segment_dir = metadata_path.parent
        if not (segment_dir / "data_level0.bin").exists():
            raise PipelineError(f"Chroma HNSW 索引未落盘: {metadata_path}")


def _pending_embedding_count(db_dir: Path) -> int | None:
    database_path = db_dir / "chroma.sqlite3"
    if not database_path.is_file():
        return None
    try:
        with sqlite3.connect(database_path, timeout=5) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM embeddings_queue"
            ).fetchone()
    except sqlite3.Error:
        return None
    return int(row[0]) if row else None


def _wait_for_hnsw_index(db_dir: Path, *, timeout_seconds: float = 600.0) -> None:
    """Wait for Chroma's asynchronous HNSW writer to persist graph links."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        metadata_paths = list(db_dir.glob("*/index_metadata.pickle"))
        if metadata_paths and all(
            (path.parent / "data_level0.bin").is_file()
            and (path.parent / "link_lists.bin").is_file()
            and (path.parent / "link_lists.bin").stat().st_size > 0
            for path in metadata_paths
        ):
            return
        if time.monotonic() >= deadline:
            raise PipelineError(f"Chroma HNSW 图文件未落盘: {db_dir}")
        time.sleep(0.5)


def _wait_for_hnsw_sync(db_dir: Path, *, timeout_seconds: float = 600.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        pending = _pending_embedding_count(db_dir)
        if pending in {None, 0, 1}:
            return
        if time.monotonic() >= deadline:
            raise PipelineError(f"Chroma HNSW 索引队列未清空，剩余 {pending} 条")
        time.sleep(0.5)
