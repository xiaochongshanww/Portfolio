from pathlib import Path

from src.pipeline.paths import MINERU_DIR

from .mineru import MineruParser
from .pymupdf import PyMuPdfParser


SUPPORTED_BACKENDS = {"mineru", "pymupdf"}


def create_parser(backend: str, *, mineru_output_dir: Path = MINERU_DIR):
    normalized = backend.strip().lower()
    if normalized == "mineru":
        return MineruParser(mineru_output_dir)
    if normalized == "pymupdf":
        return PyMuPdfParser()
    raise ValueError(f"不支持的 PDF 解析后端：{backend}，可选值：{', '.join(sorted(SUPPORTED_BACKENDS))}")
