
import os
import re
import json
import logging

# --- 配置日志 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 切分规则配置 ---

# 匹配章节标题，例如 "第 1 章 总则"
CHAPTER_PATTERN = re.compile(r'^\s*第\s*[一二三四五六七八九十百]+\s*章.*$')

# 匹配条文标题，例如 "3.1.1" 或 "3.1"
# 这是切分的核心依据
ARTICLE_PATTERN = re.compile(r'^\s*(\d+(\.\d+)+)\s+(.*)')

def split_text_into_chunks(text: str, source_filename: str) -> list[dict]:
    """
    将清洗后的文本根据章节和条文结构切分成块。

    Args:
        text: 清洗后的完整文本。
        source_filename: 来源文件名，用于元数据。

    Returns:
        一个包含多个块（chunk）的列表，每个块是一个字典。
    """
    chunks = []
    current_chapter = ""
    current_chunk = None

    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        chapter_match = CHAPTER_PATTERN.match(line)
        article_match = ARTICLE_PATTERN.match(line)

        if chapter_match:
            current_chapter = line
            logging.info(f"识别到新章节: {current_chapter}")
            continue

        if article_match:
            # 如果有正在处理的块，先保存它
            if current_chunk:
                chunks.append(current_chunk)
            
            article_number = article_match.group(1)
            article_title = article_match.group(3)
            
            # 创建新的块
            current_chunk = {
                "id": f"{os.path.splitext(source_filename)[0]}_{article_number}",
                "source": source_filename,
                "metadata": {
                    "chapter": current_chapter,
                    "article_number": article_number,
                    "article_title": article_title
                },
                "text": line
            }
            logging.info(f"识别到新条文: {article_number} {article_title}")
        elif current_chunk:
            # 如果不是新条文，将内容追加到当前块
            current_chunk["text"] += "\n" + line

    # 不要忘记添加最后一个块
    if current_chunk:
        chunks.append(current_chunk)

    logging.info(f"文件 {source_filename} 共切分出 {len(chunks)} 个块。")
    return chunks

def process_all_cleaned_files(processed_dir: str, chunks_dir: str):
    """
    处理所有清洗过的文本文件（_cleaned.txt）。

    Args:
        processed_dir: 存放清洗后txt文件的目录。
        chunks_dir: 存放切分后JSON文件的目录。
    """
    if not os.path.exists(chunks_dir):
        os.makedirs(chunks_dir)
        logging.info(f"已创建分块数据目录: {chunks_dir}")

    for filename in os.listdir(processed_dir):
        if filename.endswith("_cleaned.txt"):
            cleaned_txt_path = os.path.join(processed_dir, filename)
            json_filename = filename.replace("_cleaned.txt", "_chunks.json")
            json_path = os.path.join(chunks_dir, json_filename)

            if os.path.exists(json_path):
                logging.info(f"文件 {json_path} 已存在，跳过处理。")
                continue

            logging.info(f"正在读取清洗后文件: {cleaned_txt_path}")
            with open(cleaned_txt_path, 'r', encoding='utf-8') as f:
                cleaned_text = f.read()

            # 切分文本
            source_doc_name = filename.replace("_cleaned.txt", ".pdf") # 追溯回原始PDF名
            chunks = split_text_into_chunks(cleaned_text, source_doc_name)

            # 保存为JSON文件
            if chunks:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(chunks, f, ensure_ascii=False, indent=4)
                logging.info(f"已将分块数据保存到: {json_path}")

if __name__ == '__main__':
    CWD = os.getcwd()
    PROCESSED_DATA_DIR = os.path.join(CWD, 'data', 'processed')
    CHUNKS_DATA_DIR = os.path.join(CWD, 'data', 'chunks')

    logging.info("--- 开始执行文本切分流水线 ---")
    logging.info(f"输入目录: {PROCESSED_DATA_DIR}")
    logging.info(f"输出目录: {CHUNKS_DATA_DIR}")

    process_all_cleaned_files(PROCESSED_DATA_DIR, CHUNKS_DATA_DIR)

    logging.info("--- 文本切分流水线执行完毕 ---")
