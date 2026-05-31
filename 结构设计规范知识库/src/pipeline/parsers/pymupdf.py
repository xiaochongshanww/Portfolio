import re
from pathlib import Path

from .base import ParseResult, ParserUnavailableError


CLAUSE_RE = re.compile(r"^(\d+\.\d+[\d\.\-]*(\s+[A-Z]|\s+[一-鿿])?)")
APPENDIX_RE = re.compile(r"^(附录|Appendix)\s+[A-Z]")
TABLE_RE = re.compile(r"^(表|图)\s+[\d\.]+")
PAGE_NUM_RE = re.compile(r"^\d{1,3}$")
DECIMAL_RE = re.compile(r"^[\d\.\s]{1,5}$")
URL_RE = re.compile(r"^[a-zA-Z0-9]+\.[a-z]")
SHORT_SYMBOL_RE = re.compile(r"^[\d\.\-—·]+$")


def is_title_block(text: str, lines_in_block: int, font_size: float) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if PAGE_NUM_RE.match(stripped) or DECIMAL_RE.match(stripped) or URL_RE.match(stripped):
        return False
    if SHORT_SYMBOL_RE.match(stripped):
        return False
    if len(stripped) <= 2 and not CLAUSE_RE.match(stripped):
        return False
    if CLAUSE_RE.match(stripped) or APPENDIX_RE.match(stripped) or TABLE_RE.match(stripped):
        return True
    if font_size >= 14:
        return True
    if lines_in_block <= 2 and font_size >= 12 and len(stripped) >= 4:
        return True
    return lines_in_block == 1 and font_size >= 10 and len(stripped) >= 6


class PyMuPdfParser:
    name = "pymupdf"

    def parse(self, pdf_path: Path, image_dir: Path) -> ParseResult:
        try:
            import fitz
        except ImportError as exc:
            raise ParserUnavailableError("缺少 PyMuPDF 依赖，请先安装 requirements.txt") from exc

        image_dir.mkdir(parents=True, exist_ok=True)
        doc = fitz.open(pdf_path)
        elements: list[dict] = []
        basename = pdf_path.stem

        try:
            for page_index in range(len(doc)):
                page = doc[page_index]
                image_name = f"{basename}_p{page_index + 1:04d}.png"
                pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
                pix.save(image_dir / image_name)

                for block in page.get_text("dict")["blocks"]:
                    if block["type"] != 0:
                        continue
                    lines = []
                    for line in block["lines"]:
                        text = "".join(span["text"] for span in line["spans"]).strip()
                        if text:
                            lines.append(text)
                    if not lines:
                        continue
                    text = " ".join(lines)
                    font_size = block["lines"][0]["spans"][0]["size"]
                    elements.append(
                        {
                            "type": "Title" if is_title_block(text, len(lines), font_size) else "Text",
                            "text": text,
                            "page": page_index + 1,
                            "img": image_name,
                            "parser": self.name,
                        }
                    )
        finally:
            doc.close()

        return ParseResult(elements=elements, metadata={"parser_backend": self.name})
