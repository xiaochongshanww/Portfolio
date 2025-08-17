
import os
import re
import logging

# --- 配置日志 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 清洗规则配置 ---

# 1. 页眉页脚的正则表达式模式
#    - 匹配包含 "GB", "JGJ", "DB" 等规范编号的行
#    - 匹配包含 "第...页", ".../...") 页码格式的行
#    - 匹配看起来像目录的行 (e.g., "目...录", "目...次")
HEADER_FOOTER_PATTERNS = [
    re.compile(r'^[\s\t]*([JGDB]B\s*\d+|T\/CECS|CJJ|PICC).*[\s\t]*$\n?', re.I),
    re.compile(r'^[\s\t]*第\s*\d+\s*页.*$\n?'),
    re.compile(r'^[\s\t]*\d+\s*\/\s*\d+.*$\n?'),
    re.compile(r'^[\s\t]*目[\s\t]*录[\s\t]*$\n?'),
    re.compile(r'^[\s\t]*目[\s\t]*次[\s\t]*$\n?'),
]

# 2. 常见OCR错误修正规则 (可根据实际情况扩展)
OCR_CORRECTIONS = {
    ' l ': ' 1 ',  # 例子：将独立的 l 替换为 1
    ' O ': ' 0 ',  # 例子：将独立的 O 替换为 0
}

def clean_text(text: str) -> str:
    """
    对给定的文本执行一系列清洗操作。

    Args:
        text: 从OCR提取的原始文本。

    Returns:
        清洗后的文本。
    """
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        # 1. 去除行首行尾的空白
        line = line.strip()
        if not line:
            continue

        # 2. 移除页眉页脚
        is_header_footer = False
        for pattern in HEADER_FOOTER_PATTERNS:
            if pattern.match(line):
                is_header_footer = True
                logging.debug(f"匹配到页眉/页脚，已移除: {line}")
                break
        if is_header_footer:
            continue

        cleaned_lines.append(line)

    # 3. 合并成单篇文本
    full_text = '\n'.join(cleaned_lines)

    # 4. 修正常见OCR错误
    for wrong, correct in OCR_CORRECTIONS.items():
        full_text = full_text.replace(wrong, correct)

    # 5. 移除连续的多个空行，保留一个
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)

    # 6. (高级) 尝试合并被错误断开的行
    #    如果一行不以标点符号结尾，并且下一行不是以大写字母或数字开头，则合并
    #    这是一个基本实现，可能需要根据具体文档格式进行调整
    lines = full_text.split('\n')
    merged_lines = []
    i = 0
    while i < len(lines):
        current_line = lines[i]
        if (i + 1) < len(lines):
            next_line = lines[i+1]
            # 简单的合并逻辑：如果当前行结尾不是标点，则与下一行合并
            if current_line and next_line and not current_line.endswith(tuple('。；：？！）)')):
                merged_lines.append(current_line + next_line)
                i += 2
                continue
        merged_lines.append(current_line)
        i += 1
    
    full_text = '\n'.join(merged_lines)

    return full_text

def process_all_raw_files(processed_dir: str):
    """
    处理指定目录下的所有原始文本文件（_raw.txt）。

    Args:
        processed_dir: 存放原始和处理后txt文件的目录。
    """
    for filename in os.listdir(processed_dir):
        if filename.endswith("_raw.txt"):
            raw_txt_path = os.path.join(processed_dir, filename)
            cleaned_txt_path = raw_txt_path.replace("_raw.txt", "_cleaned.txt")

            if os.path.exists(cleaned_txt_path):
                logging.info(f"文件 {cleaned_txt_path} 已存在，跳过处理。")
                continue

            logging.info(f"正在读取原始文件: {raw_txt_path}")
            with open(raw_txt_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
            
            # 清洗文本
            cleaned_text = clean_text(raw_text)
            
            # 保存清洗后的文件
            with open(cleaned_txt_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            logging.info(f"已将清洗后的文本保存到: {cleaned_txt_path}")

if __name__ == '__main__':
    CWD = os.getcwd()
    PROCESSED_DATA_DIR = os.path.join(CWD, 'data', 'processed')

    logging.info("--- 开始执行文本清洗流水线 ---")
    logging.info(f"处理目录: {PROCESSED_DATA_DIR}")
    
    process_all_raw_files(PROCESSED_DATA_DIR)
    
    logging.info("--- 文本清洗流水线执行完毕 ---")
