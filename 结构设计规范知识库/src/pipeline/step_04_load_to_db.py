"""加载段落块到 ChromaDB"""
import os
import json
import logging
import chromadb
import hashlib
from zhipuai import ZhipuAI
from dotenv import load_dotenv

load_dotenv()

LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'logs'))
os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'load_to_db.log'), encoding='utf-8'),
        logging.StreamHandler()
    ])

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB_DIR = os.path.join(PROJECT_ROOT, 'db')
CHUNK_DIR = os.path.join(PROJECT_ROOT, 'data', 'processed')
COLLECTION_NAME = "design_specs"


def main():
    # 初始化
    api_key = os.environ.get("ZHIPUAI_API_KEY")
    if not api_key:
        logging.error("ZHIPUAI_API_KEY 未设置")
        return
    zhipu = ZhipuAI(api_key=api_key)

    db = chromadb.PersistentClient(path=DB_DIR)

    # 删除旧集合重新创建
    try:
        db.delete_collection(COLLECTION_NAME)
        logging.info("已删除旧集合")
    except Exception:
        pass
    collection = db.get_or_create_collection(name=COLLECTION_NAME)

    # 遍历段落块文件
    chunk_files = sorted([f for f in os.listdir(CHUNK_DIR) if f.endswith('_chunks.json')])
    logging.info(f"发现 {len(chunk_files)} 个段落文件")

    total = 0
    for cf in chunk_files:
        path = os.path.join(CHUNK_DIR, cf)
        with open(path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)

        logging.info(f"处理 {cf}: {len(chunks)} 个段落")

        batch_size = 10
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c["text"] for c in batch]
            doc_id = hashlib.md5(f"{cf}{i}".encode()).hexdigest()

            meta_list = []
            for c in batch:
                meta = {
                    "source": cf.replace("_chunks.json", ".pdf"),
                    "title": c.get("title", "")[:200],
                    "pages": ",".join(str(p) for p in c.get("pages", [])),
                    "images": ",".join(c.get("images", []))[:500],
                    "chunk_id": doc_id,
                }
                meta_list.append(meta)

            try:
                resp = zhipu.embeddings.create(model="embedding-2", input=texts)
                embs = [d.embedding for d in resp.data]
                ids = [f"{doc_id}_{j}" for j in range(len(batch))]

                collection.add(embeddings=embs, documents=texts, metadatas=meta_list, ids=ids)
                total += len(batch)
            except Exception as e:
                logging.error(f"批次 {i // batch_size + 1} 出错: {e}")

        logging.info(f"  → 累计 {total} 条")

    logging.info(f"完成! 共 {total} 条, 集合总条目: {collection.count()}")


if __name__ == "__main__":
    main()
