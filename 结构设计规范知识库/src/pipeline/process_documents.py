import os
import json
import logging
from unstructured.partition.auto import partition

# ---
# 配置
# ---

# 设置日志记录，使其输出到文件和控制台
LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'logs'))
os.makedirs(LOGS_DIR, exist_ok=True)
log_file_path = os.path.join(LOGS_DIR, 'process_documents.log')

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
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'raw')
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'processed')

# ---
# 核心处理函数
# ---

def process_documents():
    """
    遍历data/raw目录下的所有PDF文件，使用unstructured进行处理，
    并将结构化的结果保存为JSON文件到data/processed目录。
    """
    logging.info("--- 开始执行文档处理流水线 ---")

    # 确保输出目录存在
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    logging.info(f"原始数据目录: {RAW_DATA_DIR}")
    logging.info(f"处理后数据目录: {PROCESSED_DATA_DIR}")

    # 检查原始数据目录是否存在
    if not os.path.isdir(RAW_DATA_DIR):
        logging.error(f"错误：原始数据目录不存在或不是一个目录: {RAW_DATA_DIR}")
        return

    # 获取所有PDF文件
    try:
        pdf_files = [f for f in os.listdir(RAW_DATA_DIR) if f.lower().endswith('.pdf')]
        if not pdf_files:
            logging.warning(f"在 {RAW_DATA_DIR} 目录中未找到任何PDF文件。")
            return
    except Exception as e:
        logging.error(f"读取原始数据目录时出错: {e}", exc_info=True)
        return

    logging.info(f"发现 {len(pdf_files)} 个PDF文件待处理: {pdf_files}")

    for pdf_file in pdf_files:
        input_path = os.path.join(RAW_DATA_DIR, pdf_file)
        output_filename = os.path.splitext(pdf_file)[0] + '.json'
        output_path = os.path.join(PROCESSED_DATA_DIR, output_filename)

        logging.info(f"========== 开始处理: {pdf_file} ==========")

        try:
            # 使用unstructured进行分区
            # strategy='hi_res' -> 高分辨率模式，适用于扫描件，会自动调用OCR
            # infer_table_structure=True -> 尝试推断表格结构并以HTML格式呈现
            # languages=['chi_sim', 'eng'] -> 指定语言为简体中文和英文，优化识别效果
            elements = partition(
                filename=input_path,
                strategy="auto",
                infer_table_structure=True,
                languages=["chi_sim", "eng"],
                pdf_infer_table_structure=True # 明确启用PDF的表格推断
            )

            # 将Element对象转换为字典列表以便序列化
            result_data = [el.to_dict() for el in elements]

            # 保存为JSON文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=4)

            logging.info(f"成功处理并保存至: {output_path}")

        except Exception as e:
            logging.error(f"处理文件 {pdf_file} 时发生严重错误: {e}", exc_info=True)

    logging.info("--- 所有文档处理完毕 ---")

# ---
# 脚本执行入口
# ---

if __name__ == "__main__":
    process_documents()
