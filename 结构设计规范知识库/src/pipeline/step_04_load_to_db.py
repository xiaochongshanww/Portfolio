import os
import json
import logging
import chromadb
from zhipuai import ZhipuAI
from dotenv import load_dotenv
import hashlib

# 加载 .env 文件中的环境变量
load_dotenv()

# ---
# 配置
# ---

# 设置日志记录
LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'logs'))
os.makedirs(LOGS_DIR, exist_ok=True)
log_file_path = os.path.join(LOGS_DIR, 'load_to_db.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 定义项目根目录和数据目录
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'processed')
DB_DIR = os.path.join(PROJECT_ROOT, 'db')
COLLECTION_NAME = "design_specs"

# --- 
# 初始化客户端
# ---

def initialize_clients():
    """初始化并返回ZhipuAI和ChromaDB的客户端实例。"""
    # 1. 初始化智谱AI客户端
    try:
        zhipuai_api_key = os.environ.get("ZHIPUAI_API_KEY")
        if not zhipuai_api_key:
            raise ValueError("未找到环境变量 ZHIPUAI_API_KEY")
        zhipu_client = ZhipuAI(api_key=zhipuai_api_key)
        logging.info("智谱AI客户端初始化成功。")
    except Exception as e:
        logging.error(f"初始化智谱AI客户端失败: {e}")
        zhipu_client = None

    # 2. 初始化ChromaDB客户端
    try:
        db_client = chromadb.PersistentClient(path=DB_DIR)
        collection = db_client.get_or_create_collection(name=COLLECTION_NAME)
        logging.info(f"ChromaDB客户端初始化成功，数据将存储在: {DB_DIR}")
        logging.info(f"当前集合 '{COLLECTION_NAME}' 中已有 {collection.count()} 个条目。")
    except Exception as e:
        logging.error(f"初始化ChromaDB失败: {e}")
        db_client = None
        collection = None

    return zhipu_client, db_client, collection

# ---
# 核心功能函数
# ---

def transform_elements_to_chunks(elements: list[dict]) -> list[dict]:
    """
    将unstructured输出的elements列表转换为数据库需要的chunks格式。
    核心逻辑变更：
    1.  对普通文本元素，直接使用其文本内容。
    2.  对表格（Table）元素，进行“上下文增强”处理：
        -   向前查找紧邻的标题（Title）或叙述文本（NarrativeText）作为表格的标题。
        -   解析表格的HTML，提取表头（thead/tr）。
        -   将“表格标题”和“表头”作为上下文，添加到每一行（tr）的文本中。
        -   将表格的每一行作为一个独立的chunk，而不是整个表格作为一个chunk。
    """
    chunks = []
    seen_ids = set()
    
    for i, el in enumerate(elements):
        element_type = el.get('type', '')
        text_to_embed = el.get('text', '')

        if not text_to_embed or not text_to_embed.strip():
            continue

        # --- 上下文增强逻辑 ---
        if element_type == 'Table':
            # 1. 提取表格HTML
            html_text = el.get('metadata', {}).get('text_as_html')
            if not html_text:
                continue

            # 2. 向前查找表格标题
            table_title = ""
            if i > 0:
                prev_el = elements[i-1]
                if prev_el.get('type') in ['Title', 'NarrativeText']:
                    title_text = prev_el.get('text', '').strip()
                    # 避免过长的叙述文本成为标题
                    if title_text and len(title_text) < 100:
                        table_title = f"表格标题：{title_text}。"

            # 3. 解析HTML，提取表头和行
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_text, 'html.parser')
                
                header_row = soup.find('thead')
                if not header_row:
                    header_row = soup.find('tr')
                
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])] if header_row else []
                header_text = f"表头：{{', '.join(headers)}}。" if headers else ""

                # 4. 为每一行创建增强的chunk
                rows = soup.find_all('tr')
                for row in rows:
                    row_cells = [td.get_text(strip=True) for td in row.find_all('td')]
                    if not any(row_cells):  # 跳过空行
                        continue
                    
                    row_text = ', '.join(row_cells)
                    
                    # 组合成最终的文本
                    enriched_text = f"{table_title}{header_text}行内容：{row_text}"
                    
                    # 使用增强后的文本创建ID
                    stable_id = hashlib.md5(enriched_text.encode('utf-8')).hexdigest()

                    if stable_id not in seen_ids:
                        chunk = {
                            "id": stable_id,
                            "text": enriched_text,
                            "metadata": {
                                "source": el.get('metadata', {}).get('filename', 'N/A'),
                                "page": el.get('metadata', {}).get('page_number', -1),
                                "type": 'TableRow',  # 自定义类型，表明这是表格的一行
                                "element_id": el.get('id', 'N/A')
                            }
                        }
                        chunks.append(chunk)
                        seen_ids.add(stable_id)

            except ImportError:
                logging.warning("BeautifulSoup4未安装(pip install beautifulsoup4)，表格处理将退回为纯文本模式。")
                # Fallback to plain text if bs4 is not available
                text_to_embed = el.get('text', '')
            except Exception as e:
                logging.error(f"处理表格HTML时出错: {e}", exc_info=True)
                text_to_embed = el.get('text', '') # Fallback

        # --- 普通文本元素的处理逻辑 ---
        if element_type != 'Table':
            stable_id = hashlib.md5((el.get('id', '') + text_to_embed).encode('utf-8')).hexdigest()
            if stable_id not in seen_ids:
                chunk = {
                    "id": stable_id,
                    "text": text_to_embed,
                    "metadata": {
                        "source": el.get('metadata', {}).get('filename', 'N/A'),
                        "page": el.get('metadata', {}).get('page_number', -1),
                        "type": element_type,
                        "element_id": el.get('id', 'N/A')
                    }
                }
                chunks.append(chunk)
                seen_ids.add(stable_id)

    return chunks

def embed_and_load(collection, zhipu_client, chunks: list[dict]):
    """
    将一批文本块进行向量化并加载到ChromaDB中，会跳过已存在的ID。
    """
    if not collection or not zhipu_client:
        logging.error("客户端未初始化，无法加载数据。")
        return 0

    batch_size = 10  # 智谱API的批处理大小限制
    loaded_count = 0

    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        
        ids_to_add = [chunk['id'] for chunk in batch_chunks]
        
        # 检查数据库中是否已存在这些ID
        existing = collection.get(ids=ids_to_add)
        existing_ids = set(existing['ids'])
        
        # 过滤掉已存在的块
        new_chunks = [chunk for chunk in batch_chunks if chunk['id'] not in existing_ids]

        if not new_chunks:
            logging.info(f"批次 {i//batch_size + 1} 中的所有条目均已存在，跳过。")
            continue

        logging.info(f"正在处理批次 {i//batch_size + 1}，包含 {len(new_chunks)} 个新条目。")

        texts_to_embed = [chunk['text'] for chunk in new_chunks]
        metadatas_to_add = [chunk['metadata'] for chunk in new_chunks]
        ids_to_add_new = [chunk['id'] for chunk in new_chunks]

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
                ids=ids_to_add_new
            )
            loaded_count += len(new_chunks)
            logging.info(f"批次 {i//batch_size + 1} 成功加载 {len(new_chunks)} 条数据到数据库。")

        except Exception as e:
            logging.error(f"处理批次 {i//batch_size + 1} 时发生错误: {e}", exc_info=True)
    
    return loaded_count

def process_all_json_files(processed_dir: str, collection, zhipu_client):
    """
    处理所有已提取的JSON文件，转换并加载到数据库。
    """
    if not os.path.isdir(processed_dir):
        logging.error(f"错误：处理后的数据目录不存在: {processed_dir}")
        return

    total_loaded = 0
    json_files = [f for f in os.listdir(processed_dir) if f.endswith('.json')]
    logging.info(f"在 {processed_dir} 发现 {len(json_files)} 个JSON文件。")

    for filename in json_files:
        json_path = os.path.join(processed_dir, filename)
        logging.info(f"--- 正在处理文件: {filename} ---")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                elements = json.load(f)
            
            if not elements:
                logging.warning(f"文件 {filename} 为空，跳过。")
                continue
            
            # 转换数据结构
            chunks = transform_elements_to_chunks(elements)
            logging.info(f"从 {filename} 中转换出 {len(chunks)} 个有效文本块。")

            # 向量化并加载
            if chunks:
                total_loaded += embed_and_load(collection, zhipu_client, chunks)

        except json.JSONDecodeError:
            logging.error(f"文件 {filename} 不是有效的JSON格式，跳过。")
        except Exception as e:
            logging.error(f"处理文件 {filename} 时发生未知错误: {e}", exc_info=True)
    
    logging.info(f"本次运行总共加载了 {total_loaded} 个新条目到数据库。")

# ---
# 脚本执行入口
# ---

if __name__ == '__main__':
    zhipu_client, db_client, collection = initialize_clients()

    if zhipu_client and db_client and collection:
        logging.info("--- 开始执行知识库加载流水线 ---")
        process_all_json_files(PROCESSED_DATA_DIR, collection, zhipu_client)
        logging.info(f"--- 知识库加载流水线执行完毕 ---")
        try:
            final_count = collection.count()
            logging.info(f"当前集合 '{COLLECTION_NAME}' 中总条目数: {final_count}")
        except Exception as e:
            logging.error(f"获取最终条目数时出错: {e}")
    else:
        logging.error("由于客户端未能正确初始化，流水线无法执行。")