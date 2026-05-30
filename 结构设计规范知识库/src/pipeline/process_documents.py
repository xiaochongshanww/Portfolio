"""PyMuPDF 提取文本 + 渲染每页为图片。"""
import json
import logging
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.pipeline.chunks import normalize_chunks
from src.pipeline.metadata import SpecMetadata, load_spec_metadata
from src.pipeline.paths import IMAGES_DIR, METADATA_DIR, PROCESSED_DIR, RAW_DIR


# ── 条文编号模式 ──
CLAUSE_RE = re.compile(r'^(\d+\.\d+[\d\.\-]*(\s+[A-Z]|\s+[一-鿿])?)')
# 匹配: "3.7" "5.1.1" "8.1.1-1" "5.1.4-1" "3.7 非结构构件"
# 以及英文 "A.0.1" 附录编号
APPENDIX_RE = re.compile(r'^(附录|Appendix)\s+[A-Z]')
TABLE_RE = re.compile(r'^(表|图)\s+[\d\.]+')


# 非标题过滤（这些不应作为章节标题）
PAGE_NUM_RE = re.compile(r'^\d{1,3}$')
DECIMAL_RE = re.compile(r'^[\d\.\s]{1,5}$')
URL_RE = re.compile(r'^[a-zA-Z0-9]+\.[a-z]')
SHORT_SYMBOL_RE = re.compile(r'^[\d\.\-—·]+$')


def is_title_block(text: str, lines_in_block: int, font_size: float) -> bool:
    """判断一个 text block 是否为标题/条文号。"""
    t = text.strip()
    if not t:
        return False
    # 排除页码、表格中的孤立数值、水印、短符号
    if PAGE_NUM_RE.match(t):
        return False
    if DECIMAL_RE.match(t):
        return False
    if URL_RE.match(t):
        return False
    if SHORT_SYMBOL_RE.match(t):
        return False
    if len(t) <= 2 and not CLAUSE_RE.match(t):
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
    if lines_in_block <= 2 and font_size >= 12 and len(t) >= 4:
        return True
    if lines_in_block == 1 and font_size >= 10 and len(t) >= 6:
        return True
    return False


def render_page_as_image(doc, page_num, out_dir: Path, basename):
    page = doc[page_num]
    import fitz

    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))  # 3x 分辨率
    fn = f"{basename}_p{page_num+1:04d}.png"
    pix.save(out_dir / fn)
    return fn


def extract_text_from_pdf(pdf_path: Path, image_dir: Path):
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("缺少 PyMuPDF 依赖，请先安装 requirements.txt") from exc

    doc = fitz.open(pdf_path)
    filename = pdf_path.name
    basename = pdf_path.stem
    elements = []

    for pn in range(len(doc)):
        page = doc[pn]
        img_file = render_page_as_image(doc, pn, image_dir, basename)
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


def process_pdf(pdf_path: Path, spec: SpecMetadata, out_dir: Path, image_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    logging.info("处理: %s", pdf_path.name)
    elements = extract_text_from_pdf(pdf_path, image_dir)
    raw_chunks = chunk_to_paragraphs(elements)
    chunks = normalize_chunks(raw_chunks, spec)
    logging.info("  元素: %s, 段落块: %s", len(elements), len(chunks))

    basename = pdf_path.stem
    (out_dir / f"{basename}.json").write_text(json.dumps(elements, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"{basename}_chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    return chunks


def process_pdfs(
    pdf_files: list[Path],
    metadata: dict[str, SpecMetadata],
    out_dir: Path = PROCESSED_DIR,
    image_dir: Path = IMAGES_DIR,
) -> dict[str, list[dict]]:
    chunks_by_file: dict[str, list[dict]] = {}
    for pdf_file in pdf_files:
        chunks_by_file[pdf_file.name] = process_pdf(pdf_file, metadata[pdf_file.name], out_dir, image_dir)

    images = list(image_dir.glob("*.png"))
    size = sum(image.stat().st_size for image in images)
    logging.info("完成! %s 页图片, %.1fMB", len(images), size / 1024 / 1024)
    return chunks_by_file


def process_all():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    pdfs = sorted(path for path in RAW_DIR.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")
    metadata = load_spec_metadata(pdfs, METADATA_DIR / "specs.json")
    logging.info("发现 %s 个 PDF", len(pdfs))
    process_pdfs(pdfs, metadata, PROCESSED_DIR, IMAGES_DIR)


if __name__ == "__main__":
    process_all()
