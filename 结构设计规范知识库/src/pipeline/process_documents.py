"""PDF 解析、chunk 生成和中间产物写入。"""
import json
import logging
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.pipeline.chunks import normalize_chunks
from src.pipeline.metadata import SpecMetadata, load_spec_metadata
from src.pipeline.parsers import PdfParser, create_parser
from src.pipeline.paths import IMAGES_DIR, METADATA_DIR, MINERU_DIR, PROCESSED_DIR, RAW_DIR


DEFAULT_PARSER_BACKEND = os.environ.get("PDF_PARSER_BACKEND", "mineru")


def chunk_to_paragraphs(elements: list[dict]) -> list[dict]:
    chunks = []
    current_title = ""
    buffer: list[str] = []
    pages: set[int] = set()
    images: set[str] = set()
    original_images: set[str] = set()
    chunk_types: set[str] = set()
    html_parts: list[str] = []
    last_page: int | None = None

    for element in elements:
        text = str(element.get("text", "")).strip()
        if not text:
            continue
        page = int(element.get("page") or 0)
        image = str(element.get("img") or "")
        original_image = str(element.get("original_img_path") or "")
        is_title = element.get("type") == "Title"
        page_changed = last_page is not None and page != last_page

        if (is_title or page_changed) and buffer:
            chunks.append(
                {
                    "title": current_title,
                    "text": "\n".join(buffer),
                    "pages": sorted(page for page in pages if page),
                    "images": sorted(image for image in images if image),
                    "original_images": sorted(image for image in original_images if image),
                    "html": "\n".join(html_parts),
                    "chunk_type": _dominant_chunk_type(chunk_types),
                }
            )
            buffer = []
            pages = set()
            images = set()
            original_images = set()
            chunk_types = set()
            html_parts = []

        if is_title:
            current_title = text

        buffer.append(text)
        if page:
            pages.add(page)
        if image:
            images.add(image)
        if original_image:
            original_images.add(original_image)
        if element.get("html"):
            html_parts.append(str(element["html"]))
        chunk_types.add(str(element.get("chunk_type") or "text"))
        last_page = page

    if buffer:
        chunks.append(
            {
                "title": current_title,
                "text": "\n".join(buffer),
                "pages": sorted(page for page in pages if page),
                "images": sorted(image for image in images if image),
                "original_images": sorted(image for image in original_images if image),
                "html": "\n".join(html_parts),
                "chunk_type": _dominant_chunk_type(chunk_types),
            }
        )
    return chunks


def _dominant_chunk_type(chunk_types: set[str]) -> str:
    for preferred in ("table", "formula", "figure", "explanation"):
        if preferred in chunk_types:
            return preferred
    return "text"


def build_quality_entry(
    pdf_path: Path,
    elements: list[dict],
    chunks: list[dict],
    artifacts: list[dict],
) -> dict:
    total_elements = len(elements)
    empty_text = sum(1 for element in elements if not str(element.get("text", "")).strip())
    counts: dict[str, int] = {"text": 0, "table": 0, "formula": 0, "figure": 0, "explanation": 0}
    for element in elements:
        chunk_type = str(element.get("chunk_type") or "text")
        counts[chunk_type] = counts.get(chunk_type, 0) + 1
    missing = [item["kind"] for item in artifacts if item.get("status") != "ok"]
    return {
        "source_file": pdf_path.name,
        "element_count": total_elements,
        "chunk_count": len(chunks),
        "table_count": counts.get("table", 0),
        "formula_count": counts.get("formula", 0),
        "figure_count": counts.get("figure", 0),
        "empty_text_ratio": round(empty_text / total_elements, 4) if total_elements else 0,
        "missing_artifacts": missing,
        "missing_required_artifacts": [item["kind"] for item in artifacts if item.get("required") and item.get("status") != "ok"],
    }


def process_pdf(pdf_path: Path, spec: SpecMetadata, out_dir: Path, image_dir: Path, parser: PdfParser) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    logging.info("处理: %s parser=%s", pdf_path.name, parser.name)

    parse_result = parser.parse(pdf_path, image_dir)
    raw_chunks = chunk_to_paragraphs(parse_result.elements)
    chunks = normalize_chunks(raw_chunks, spec)
    quality = build_quality_entry(pdf_path, parse_result.elements, chunks, parse_result.artifacts)
    logging.info("  元素: %s, 段落块: %s", len(parse_result.elements), len(chunks))

    basename = pdf_path.stem
    elements_payload = {
        "source_file": pdf_path.name,
        "parser_backend": parser.name,
        "parser_metadata": parse_result.metadata,
        "elements": parse_result.elements,
    }
    (out_dir / f"{basename}.json").write_text(json.dumps(elements_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"{basename}_chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "chunks": chunks,
        "artifacts": parse_result.artifacts,
        "quality": quality,
        "parser_metadata": parse_result.metadata,
        "media_files": parse_result.media_files,
    }


def process_pdfs(
    pdf_files: list[Path],
    metadata: dict[str, SpecMetadata],
    out_dir: Path = PROCESSED_DIR,
    image_dir: Path = IMAGES_DIR,
    *,
    parser_backend: str = DEFAULT_PARSER_BACKEND,
    mineru_output_dir: Path = MINERU_DIR,
) -> dict[str, dict]:
    parser = create_parser(parser_backend, mineru_output_dir=mineru_output_dir)
    results_by_file: dict[str, dict] = {}
    for pdf_file in pdf_files:
        results_by_file[pdf_file.name] = process_pdf(pdf_file, metadata[pdf_file.name], out_dir, image_dir, parser)

    images = list(image_dir.glob("*"))
    size = sum(image.stat().st_size for image in images if image.is_file())
    logging.info("完成! %s 张图片/媒体, %.1fMB", len(images), size / 1024 / 1024)
    quality_report = {
        "parser_backend": parser_backend,
        "documents": [result["quality"] for result in results_by_file.values()],
        "totals": {
            "document_count": len(results_by_file),
            "chunk_count": sum(len(result["chunks"]) for result in results_by_file.values()),
            "image_count": len(images),
            "missing_artifact_count": sum(len(result["quality"]["missing_artifacts"]) for result in results_by_file.values()),
        },
    }
    (out_dir / "build_quality.json").write_text(json.dumps(quality_report, ensure_ascii=False, indent=2), encoding="utf-8")
    return results_by_file


def process_all() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    pdfs = sorted(path for path in RAW_DIR.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")
    metadata = load_spec_metadata(pdfs, METADATA_DIR / "specs.json")
    logging.info("发现 %s 个 PDF", len(pdfs))
    process_pdfs(pdfs, metadata, PROCESSED_DIR, IMAGES_DIR)


if __name__ == "__main__":
    process_all()
