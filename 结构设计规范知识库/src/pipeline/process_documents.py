"""PyMuPDF 提取文本 + 渲染每页为图片"""
import os, json, logging, re, fitz

LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'logs'))
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(os.path.join(LOGS_DIR, 'process_documents.log'), encoding='utf-8'), logging.StreamHandler()])

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAW_DIR, OUT_DIR, IMG_DIR = os.path.join(PROJECT_ROOT, 'data', 'raw'), os.path.join(PROJECT_ROOT, 'data', 'processed'), os.path.join(PROJECT_ROOT, 'data', 'images')
os.makedirs(OUT_DIR, exist_ok=True); os.makedirs(IMG_DIR, exist_ok=True)


# ── 条文编号模式 ──
CLAUSE_RE = re.compile(r'^(\d+\.\d+[\d\.\-]*(\s+[A-Z]|\s+[一-鿿])?)')
# 匹配: "3.7" "5.1.1" "8.1.1-1" "5.1.4-1" "3.7 非结构构件"
# 以及英文 "A.0.1" 附录编号
APPENDIX_RE = re.compile(r'^(附录|Appendix)\s+[A-Z]')
TABLE_RE = re.compile(r'^(表|图)\s+[\d\.]+')


def is_title_block(text: str, lines_in_block: int, font_size: float) -> bool:
    """判断一个 text block 是否为标题/条文号。"""
    t = text.strip()
    if not t:
        return False
    # 条文编号
    if CLAUSE_RE.match(t):
        return True
    # 附录
    if APPENDIX_RE.match(t):
        return True
    # 表 / 图
    if TABLE_RE.match(t):
        return True
    # 大字号 / 短行粗体
    if font_size >= 14:
        return True
    if lines_in_block <= 2 and font_size >= 12:
        return True
    if lines_in_block == 1 and font_size >= 10:
        return True
    return False


def render_page_as_image(doc, page_num, out_dir, basename):
    page = doc[page_num]
    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))  # 3x 分辨率
    fn = f"{basename}_p{page_num+1:04d}.png"
    pix.save(os.path.join(out_dir, fn))
    return fn


def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    filename = os.path.basename(pdf_path)
    basename = os.path.splitext(filename)[0]
    elements = []

    for pn in range(len(doc)):
        page = doc[pn]
        img_file = render_page_as_image(doc, pn, IMG_DIR, basename)
        blocks = page.get_text("dict")["blocks"]

        for blk in blocks:
            if blk["type"] != 0:
                continue
            lines = []
            for ln in blk["lines"]:
                t = "".join(s["text"] for s in ln["spans"]).strip()
                if t:
                    lines.append(t)
            if not lines:
                continue

            text = " ".join(lines)
            span0 = blk["lines"][0]["spans"][0]
            fs = span0["size"]

            el_type = "Title" if is_title_block(text, len(lines), fs) else "Text"
            elements.append({"type": el_type, "text": text, "page": pn + 1, "img": img_file})

    doc.close()
    return elements


def chunk_to_paragraphs(elements):
    """按标题/条文号 + 页码自然断点合并。"""
    chunks = []
    cur_title = ""
    buffer = []
    pages = set()
    imgs = set()
    last_page = None

    for el in elements:
        is_title = el["type"] == "Title"
        page_changed = last_page is not None and el["page"] != last_page

        # 遇到标题或换页时切分
        if is_title or page_changed:
            # 换页且当前块有内容时切分
            if (is_title or (page_changed and buffer)) and buffer:
                chunks.append({"title": cur_title, "text": "\n".join(buffer), "pages": sorted(pages), "images": sorted(imgs)})
                buffer = []
                pages = set()
                imgs = set()

            if is_title:
                cur_title = el["text"]

        buffer.append(el["text"])
        pages.add(el["page"])
        imgs.add(el["img"])
        last_page = el["page"]

    if buffer:
        chunks.append({"title": cur_title, "text": "\n".join(buffer), "pages": sorted(pages), "images": sorted(imgs)})
    return chunks


def process_all():
    pdfs = sorted([f for f in os.listdir(RAW_DIR) if f.lower().endswith('.pdf')])
    logging.info(f"发现 {len(pdfs)} 个 PDF")

    for pdf_file in pdfs:
        bn = os.path.splitext(pdf_file)[0]
        logging.info(f"处理: {pdf_file}")
        elements = extract_text_from_pdf(os.path.join(RAW_DIR, pdf_file))
        chunks = chunk_to_paragraphs(elements)
        logging.info(f"  元素: {len(elements)}, 段落块: {len(chunks)}")

        with open(os.path.join(OUT_DIR, f"{bn}.json"), 'w', encoding='utf-8') as f:
            json.dump(elements, f, ensure_ascii=False, indent=2)
        with open(os.path.join(OUT_DIR, f"{bn}_chunks.json"), 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

    imgs = [f for f in os.listdir(IMG_DIR) if f.endswith('.png')]
    sz = sum(os.path.getsize(os.path.join(IMG_DIR, f)) for f in imgs)
    logging.info(f"完成! {len(imgs)} 页图片, {sz/1024/1024:.1f}MB")


if __name__ == "__main__":
    process_all()
