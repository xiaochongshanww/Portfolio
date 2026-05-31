import hashlib
import re
from typing import Any

from .metadata import SpecMetadata


CLAUSE_RE = re.compile(r"(?P<clause>\d+\.\d+(?:\.\d+)?(?:-\d+)?)")


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


def stable_chunk_id(source_file: str, index: int, text: str) -> str:
    digest = hashlib.sha256(f"{source_file}\n{index}\n{text}".encode("utf-8")).hexdigest()
    return digest[:24]


def normalize_chunk(raw: dict[str, Any], spec: SpecMetadata, index: int) -> dict[str, Any]:
    title = str(raw.get("title", ""))
    text = str(raw.get("text", ""))
    pages = [int(page) for page in raw.get("pages", []) if str(page).isdigit()]
    images = [str(image) for image in raw.get("images", [])]
    chunk_id = stable_chunk_id(spec.source_file, index, text)
    clause_number = extract_clause_number(title, text)
    chunk_type = detect_chunk_type(title, str(raw.get("chunk_type") or "text"))

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
        "pages": pages,
        "images": images,
        "original_images": [str(image) for image in raw.get("original_images", [])],
        "html": str(raw.get("html", "")),
        "text": text,
    }


def normalize_chunks(raw_chunks: list[dict[str, Any]], spec: SpecMetadata) -> list[dict[str, Any]]:
    return [normalize_chunk(chunk, spec, index) for index, chunk in enumerate(raw_chunks)]
