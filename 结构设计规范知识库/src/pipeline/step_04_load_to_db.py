
import os
import json
import logging
import chromadb
from zhipuai import ZhipuAI
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# --- 配置日志 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 全局配置 ---
CWD = os.getcwd()
CHUNKS_DATA_DIR = os.path.join(CWD, 'data', 'chunks')
DB_DIR = os.path.join(CWD, 'db')
COLLECTION_NAME = "design_specs"

# --- 初始化客户端 ---

# 1. 初始化智谱AI客户端
#    从环境变量 ZHIPUAI_API_KEY 中读取API密钥
try:
    ZHIPUAI_API_KEY = os.environ.get("ZHIPUAI_API_KEY")
    if not ZHIPUAI_API_KEY:
        raise ValueError("未找到环境变量 ZHIPUAI_API_KEY")
    zhipu_client = ZhipuAI(api_key=ZHIPUAI_API_KEY)
    logging.info("智谱AI客户端初始化成功。")
except Exception as e:
    logging.error(f"初始化智谱AI客户端失败: {e}")
    zhipu_client = None

# 2. 初始化ChromaDB客户端
#    数据将持久化存储在指定的db目录下
try:
    db_client = chromadb.PersistentClient(path=DB_DIR)
    # 获取或创建集合（Collection）
    collection = db_client.get_or_create_collection(name=COLLECTION_NAME)
    logging.info(f"ChromaDB客户端初始化成功，数据将存储在: {DB_DIR}")
    logging.info(f"当前集合 '{COLLECTION_NAME}' 中已有 {collection.count()} 个条目。")
except Exception as e:
    logging.error(f"初始化ChromaDB失败: {e}")
    db_client = None
    collection = None

def embed_and_load(chunks: list[dict]):
    """
    将一批文本块进行向量化并加载到ChromaDB中。

    Args:
        chunks: 从JSON文件中读取的文本块列表。
    """
    if not collection or not zhipu_client:
        logging.error("客户端未初始化，无法加载数据。")
        return

    batch_size = 10  # 智谱API的批处理大小限制，可以根据实际情况调整
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        
        # 提取批次中的ID、文本和元数据
        ids_to_check = [chunk['id'] for chunk in batch_chunks]
        
        # 检查数据库中是否已存在这些ID
        existing = collection.get(ids=ids_to_check)
        existing_ids = set(existing['ids'])
        
        # 过滤掉已存在的块
        new_chunks = [chunk for chunk in batch_chunks if chunk['id'] not in existing_ids]

        if not new_chunks:
            logging.info(f"批次 {i//batch_size + 1} 中的所有条目均已存在，跳过。")
            continue

        logging.info(f"正在处理批次 {i//batch_size + 1}，包含 {len(new_chunks)} 个新条目。")

        texts_to_embed = [chunk['text'] for chunk in new_chunks]
        metadatas_to_add = [chunk['metadata'] for chunk in new_chunks]
        ids_to_add = [chunk['id'] for chunk in new_chunks]

        try:
            # 调用智谱API进行向量化
            response = zhipu_client.embeddings.create(
                model="embedding-2",
                input=texts_to_embed
            )
            embeddings_to_add = [data.embedding for data in response.data]

            # 添加到ChromaDB
            collection.add(
                embeddings=embeddings_to_add,
                documents=texts_to_embed,
                metadatas=metadatas_to_add,
                ids=ids_to_add
            )
            logging.info(f"批次 {i//batch_size + 1} 成功加载到数据库。")

        except Exception as e:
            logging.error(f"处理批次 {i//batch_size + 1} 时发生错误: {e}")

def process_all_chunk_files(chunks_dir: str):
    """
    处理所有分块JSON文件。

    Args:
        chunks_dir: 存放分块JSON文件的目录。
    """
    for filename in os.listdir(chunks_dir):
        if filename.endswith("_chunks.json"):
            json_path = os.path.join(chunks_dir, filename)
            logging.info(f"正在处理文件: {json_path}")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            
            if chunks:
                embed_and_load(chunks)

if __name__ == '__main__':
    if zhipu_client and db_client:
        logging.info("--- 开始执行知识库加载流水线 ---")
        process_all_chunk_files(CHUNKS_DATA_DIR)
        logging.info(f"--- 知识库加载流水线执行完毕 ---")
        logging.info(f"当前集合 '{COLLECTION_NAME}' 中总条目数: {collection.count()}")
    else:
        logging.error("由于客户端未能正确初始化，流水线无法执行。")
