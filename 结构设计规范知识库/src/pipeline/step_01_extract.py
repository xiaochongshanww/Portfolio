
import os
import fitz  # PyMuPDF
from paddleocr import PaddleOCR
import logging

# --- 配置日志 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 全局变量 ---
# 初始化OCR引擎，仅需一次。指定使用中文和英文。
# The model will be downloaded automatically when the code is first executed.
try:
    ocr_engine = PaddleOCR(use_angle_cls=True, lang='ch')
    logging.info("PaddleOCR引擎初始化成功。")
except Exception as e:
    logging.error(f"初始化PaddleOCR引擎失败，请检查安装和环境配置: {e}")
    ocr_engine = None

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    从单个PDF文件中提取所有页面的文本。

    Args:
        pdf_path: PDF文件的路径。

    Returns:
        从PDF中提取的全部文本内容。
    """
    if not ocr_engine:
        logging.error("OCR引擎未初始化，无法处理文件。")
        return ""

    full_text = []
    try:
        doc = fitz.open(pdf_path)
        logging.info(f"正在处理文件: {pdf_path}，共 {doc.page_count} 页。")

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            
            # 将页面转换为高分辨率图像以提高OCR准确性
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            
            # 使用PaddleOCR进行文字识别
            result = ocr_engine.ocr(img_bytes, cls=True)
            
            # 从结果中提取文本
            if result and result[0] is not None:
                page_text = [line[1][0] for line in result[0]]
                full_text.extend(page_text)
            
            logging.info(f"已处理页面: {page_num + 1}/{doc.page_count}")

        doc.close()
        logging.info(f"文件处理完成: {pdf_path}")
        return "\n".join(full_text)

    except Exception as e:
        logging.error(f"处理PDF文件 {pdf_path} 时发生错误: {e}")
        return ""

def process_all_pdfs(raw_dir: str, processed_dir: str):
    """
    处理指定目录下的所有PDF文件，并将提取的文本保存到另一个目录。

    Args:
        raw_dir: 存放原始PDF的目录。
        processed_dir: 存放处理后txt文件的目录。
    """
    if not os.path.exists(processed_dir):
        os.makedirs(processed_dir)
        logging.info(f"已创建输出目录: {processed_dir}")

    for filename in os.listdir(raw_dir):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(raw_dir, filename)
            
            # 定义输出文件名
            txt_filename = os.path.splitext(filename)[0] + '_raw.txt'
            txt_path = os.path.join(processed_dir, txt_filename)

            # 如果文件已处理，则跳过
            if os.path.exists(txt_path):
                logging.info(f"文件 {txt_filename} 已存在，跳过处理。")
                continue

            # 提取文本
            extracted_text = extract_text_from_pdf(pdf_path)
            
            # 保存到文件
            if extracted_text:
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(extracted_text)
                logging.info(f"已将提取的文本保存到: {txt_path}")

if __name__ == '__main__':
    # 定义项目根目录下的数据目录
    CWD = os.getcwd()
    RAW_DATA_DIR = os.path.join(CWD, 'data', 'raw')
    PROCESSED_DATA_DIR = os.path.join(CWD, 'data', 'processed')

    logging.info("--- 开始执行数据提取流水线 ---")
    logging.info(f"输入目录: {RAW_DATA_DIR}")
    logging.info(f"输出目录: {PROCESSED_DATA_DIR}")
    
    if ocr_engine:
        process_all_pdfs(RAW_DATA_DIR, PROCESSED_DATA_DIR)
        logging.info("--- 数据提取流水线执行完毕 ---")
    else:
        logging.error("由于OCR引擎未能加载，流水线无法执行。")
