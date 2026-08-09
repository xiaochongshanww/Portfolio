import hashlib
import re
from typing import Any

from .metadata import SpecMetadata

CLAUSE_RE = re.compile(r"(?P<clause>\d+\.\d+(?:\.\d+)?(?:-\d+)?)")
TABLE_RE = re.compile(
    r"(^|\n)\s*表\s*(?P<table_id>\d+(?:\.\d+)+(?:-\d+)?)\s*(?P<table_name>[^\n<]*)"
)


def extract_clause_number(title: str, text: str) -> str:
    for value in (title, text):
        match = CLAUSE_RE.search(value or "")
        if match:
            return match.group("clause")
    return ""


def detect_chunk_type(title: str, fallback: str = "text") -> str:
    stripped = (title or "").strip()
    if stripped.startswith("表"):
        return "table"
    if stripped.startswith("图"):
        return "figure"
    if "条文说明" in stripped:
        return "explanation"
    return fallback or "text"


def detect_section_type(title: str, text: str, chunk_type: str, clause_number: str = "") -> str:
    combined = f"{title}\n{text}".strip()
    if (
        clause_number.startswith("0.")
        or "条文说明" in combined
        or re.search(r"^\s*说明\s*$", title or "")
    ):
        return "explanation"
    if re.match(r"^\s*附录[A-ZＡ-Ｚ一二三四五六七八九十]", title or ""):
        return "appendix"
    if chunk_type == "table":
        return "body_table"
    if chunk_type == "figure":
        return "figure"
    if chunk_type == "formula":
        return "formula"
    return "body"


def authority_level(section_type: str) -> int:
    levels = {
        "body_table": 100,
        "body": 90,
        "formula": 85,
        "appendix": 70,
        "figure": 60,
        "explanation": 40,
    }
    return levels.get(section_type, 50)


def extract_table_info(title: str, text: str) -> tuple[str, str]:
    for value in (title, text):
        match = TABLE_RE.search(value or "")
        if match:
            table_id = match.group("table_id").replace(" ", "")
            table_name = re.sub(r"\s+", " ", match.group("table_name")).strip(" ：:　")
            return table_id, table_name[:120]
    return "", ""


def stable_chunk_id(source_file: str, index: int, text: str) -> str:
    digest = hashlib.sha256(f"{source_file}\n{index}\n{text}".encode()).hexdigest()
    return digest[:24]


def normalize_chunk(raw: dict[str, Any], spec: SpecMetadata, index: int) -> dict[str, Any]:
    title = str(raw.get("title", ""))
    text = str(raw.get("text", ""))
    pages = [int(page) for page in raw.get("pages", []) if str(page).isdigit()]
    images = [str(image) for image in raw.get("images", [])]
    chunk_id = stable_chunk_id(spec.source_file, index, text)
    clause_number = extract_clause_number(title, text)
    chunk_type = detect_chunk_type(title, str(raw.get("chunk_type") or "text"))
    section_type = detect_section_type(title, text, chunk_type, clause_number)
    table_id, table_name = extract_table_info(title, text)
    is_table = chunk_type == "table" or bool(table_id)
    if is_table and section_type == "body":
        section_type = "body_table"

    return {
        "chunk_id": chunk_id,
        "source_file": spec.source_file,
        "source": spec.source_file,
        "code": spec.code,
        "name": spec.name,
        "version": spec.version,
        "effective_date": spec.effective_date,
        "status": spec.status,
        "aliases": spec.aliases,
        "metadata_status": spec.metadata_status,
        "title": title[:200],
        "clause_number": clause_number,
        "chunk_type": chunk_type,
        "section_type": section_type,
        "authority_level": authority_level(section_type),
        "is_table": is_table,
        "table_id": table_id,
        "table_name": table_name,
        "pages": pages,
        "images": images,
        "original_images": [str(image) for image in raw.get("original_images", [])],
        "html": str(raw.get("html", "")),
        "text": text,
    }


def normalize_chunks(raw_chunks: list[dict[str, Any]], spec: SpecMetadata) -> list[dict[str, Any]]:
    return [normalize_chunk(chunk, spec, index) for index, chunk in enumerate(raw_chunks)]
