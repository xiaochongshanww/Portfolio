import logging
import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

from src.app.core.config import settings

load_dotenv()


class PipelineError(RuntimeError):
    pass


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
        "pages": ",".join(str(page) for page in chunk["pages"]),
        "images": ",".join(chunk["images"])[:500],
        "chunk_id": chunk["chunk_id"],
        "metadata_status": chunk["metadata_status"],
    }


def load_chunks_to_db(chunks_by_file: dict[str, list[dict[str, Any]]], db_dir: Path) -> int:
    try:
        import chromadb
        from zhipuai import ZhipuAI
    except ImportError as exc:
        raise PipelineError(f"缺少入库依赖: {exc}") from exc

    api_key = os.environ.get("ZHIPUAI_API_KEY")
    if not api_key:
        raise PipelineError("ZHIPUAI_API_KEY 未设置，无法执行向量化入库")

    zhipu = ZhipuAI(api_key=api_key)
    db = chromadb.PersistentClient(path=str(db_dir))
    try:
        db.delete_collection(settings.collection_name)
        logging.info("已删除旧集合")
    except Exception:
        pass
    collection = db.get_or_create_collection(name=settings.collection_name)

    total = 0
    for source_file, chunks in chunks_by_file.items():
        logging.info("入库 %s: %s 个 chunk", source_file, len(chunks))
        for index in range(0, len(chunks), 10):
            batch = chunks[index : index + 10]
            texts = [chunk["text"] for chunk in batch]
            try:
                response = zhipu.embeddings.create(model=settings.embedding_model, input=texts)
                embeddings = [item.embedding for item in response.data]
                ids = [chunk["chunk_id"] for chunk in batch]
                metadatas = [_metadata_for_chroma(chunk) for chunk in batch]
                collection.add(embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids)
                total += len(batch)
            except Exception as exc:
                raise PipelineError(f"{source_file} 批次 {index // 10 + 1} 入库失败: {exc}") from exc

    logging.info("入库完成: %s 条, 集合总条目: %s", total, collection.count())
    return total
