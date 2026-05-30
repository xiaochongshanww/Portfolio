import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from src.app.core.config import settings

from .manifest import build_manifest, read_manifest, write_manifest
from .metadata import load_spec_metadata
from .paths import DB_DIR, IMAGES_DIR, MANIFEST_PATH, METADATA_DIR, PROCESSED_DIR, RAW_DIR


class BuildPreflightError(RuntimeError):
    pass


def configure_pipeline_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def list_pdf_files(source_dir: Path) -> list[Path]:
    return sorted(path for path in source_dir.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")


def clean_generated_outputs() -> None:
    for path in [PROCESSED_DIR, IMAGES_DIR, DB_DIR]:
        if path.exists():
            shutil.rmtree(path)
    for path in [PROCESSED_DIR, IMAGES_DIR, DB_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()


def dry_run(source_dir: Path = RAW_DIR) -> dict[str, Any]:
    pdf_files = list_pdf_files(source_dir)
    metadata = load_spec_metadata(pdf_files, METADATA_DIR / "specs.json")
    return {
        "mode": "dry-run",
        "source_dir": str(source_dir),
        "document_count": len(pdf_files),
        "documents": [metadata[pdf.name].to_dict() for pdf in pdf_files],
    }


def rebuild(source_dir: Path = RAW_DIR, *, dry_run_only: bool = False) -> dict[str, Any]:
    configure_pipeline_logging()
    source_dir = source_dir.resolve()
    pdf_files = list_pdf_files(source_dir)
    metadata = load_spec_metadata(pdf_files, METADATA_DIR / "specs.json")

    if dry_run_only:
        return dry_run(source_dir)

    if not os.environ.get("ZHIPUAI_API_KEY"):
        raise BuildPreflightError("ZHIPUAI_API_KEY 未设置，无法执行全量构建和向量化入库")

    clean_generated_outputs()

    from .load_to_db import load_chunks_to_db
    from .process_documents import process_pdfs

    chunks_by_file = process_pdfs(pdf_files, metadata, PROCESSED_DIR, IMAGES_DIR)
    total_loaded = load_chunks_to_db(chunks_by_file, DB_DIR)
    chunk_counts = {source_file: len(chunks) for source_file, chunks in chunks_by_file.items()}
    image_count = len(list(IMAGES_DIR.glob("*.png")))
    manifest = build_manifest(
        pdf_files=pdf_files,
        metadata=metadata,
        chunk_counts=chunk_counts,
        image_count=image_count,
        embedding_model=settings.embedding_model,
        collection_name=settings.collection_name,
        build_params={
            "source_dir": str(source_dir),
            "mode": "rebuild",
            "loaded_chunks": total_loaded,
        },
    )
    write_manifest(MANIFEST_PATH, manifest)
    return manifest


def build(source_dir: Path = RAW_DIR, *, dry_run_only: bool = False) -> dict[str, Any]:
    return rebuild(source_dir=source_dir, dry_run_only=dry_run_only)


def status() -> dict[str, Any]:
    manifest = read_manifest(MANIFEST_PATH)
    if not manifest:
        return {"built": False, "message": "知识库尚未构建，未找到 data/manifest.json"}
    return {
        "built": True,
        "built_at": manifest.get("built_at"),
        "document_count": manifest.get("document_count", 0),
        "chunk_count": manifest.get("chunk_count", 0),
        "image_count": manifest.get("image_count", 0),
        "data_version_hash": manifest.get("data_version_hash", ""),
        "metadata_status": manifest.get("metadata_status", "unknown"),
    }


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))
