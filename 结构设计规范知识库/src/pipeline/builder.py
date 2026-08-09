import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from src.app.core.config import settings

from .active_db import read_active_manifest
from .manifest import build_manifest, write_manifest
from .metadata import load_spec_metadata
from .parsers.base import ParserUnavailableError
from .parsers.mineru import DEFAULT_MINERU_BINARY, probe_mineru_cli
from .paths import (
    ACTIVE_DB_PATH,
    AUDIT_DIR,
    CORRECTIONS_DIR,
    DB_DIR,
    IMAGES_DIR,
    MANIFEST_PATH,
    METADATA_DIR,
    MINERU_DIR,
    PROCESSED_DIR,
    RAW_DIR,
)


class BuildPreflightError(RuntimeError):
    pass


def configure_pipeline_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def list_pdf_files(source_dir: Path) -> list[Path]:
    return sorted(
        path for path in source_dir.iterdir() if path.is_file() and path.suffix.lower() == ".pdf"
    )


DEFAULT_PARSER_BACKEND = os.environ.get("PDF_PARSER_BACKEND", "mineru")


def clean_generated_outputs(
    *,
    db_dir: Path = DB_DIR,
    manifest_path: Path = MANIFEST_PATH,
    processed_dir: Path = PROCESSED_DIR,
    images_dir: Path = IMAGES_DIR,
    mineru_dir: Path = MINERU_DIR,
    audit_dir: Path = AUDIT_DIR,
) -> None:
    for path in [processed_dir, images_dir, mineru_dir, audit_dir, db_dir]:
        if path.exists():
            shutil.rmtree(path)
    for path in [
        processed_dir,
        images_dir,
        mineru_dir,
        audit_dir,
        db_dir,
        CORRECTIONS_DIR / "candidates",
        CORRECTIONS_DIR / "approved",
    ]:
        path.mkdir(parents=True, exist_ok=True)
    if manifest_path.exists():
        manifest_path.unlink()


def dry_run(
    source_dir: Path = RAW_DIR, *, parser_backend: str = DEFAULT_PARSER_BACKEND
) -> dict[str, Any]:
    pdf_files = list_pdf_files(source_dir)
    metadata = load_spec_metadata(pdf_files, METADATA_DIR / "specs.json")
    return {
        "mode": "dry-run",
        "source_dir": str(source_dir),
        "parser_backend": parser_backend,
        "document_count": len(pdf_files),
        "documents": [metadata[pdf.name].to_dict() for pdf in pdf_files],
    }


def validate_parser_backend(parser_backend: str) -> dict[str, Any]:
    if parser_backend != "mineru":
        return {
            "backend": parser_backend,
            "compatibility": "not_applicable",
            "verified": False,
        }
    try:
        probe = probe_mineru_cli(os.environ.get("MINERU_BIN") or DEFAULT_MINERU_BINARY)
    except ParserUnavailableError as exc:
        raise BuildPreflightError(str(exc)) from exc
    return {"backend": parser_backend, **probe.to_dict()}


def parser_status(parser_backend: str = DEFAULT_PARSER_BACKEND) -> dict[str, Any]:
    return {
        "ok": True,
        "parser_environment": validate_parser_backend(parser_backend),
    }


def rebuild(
    source_dir: Path = RAW_DIR,
    *,
    dry_run_only: bool = False,
    parser_backend: str = DEFAULT_PARSER_BACKEND,
    apply_corrections: bool = True,
    db_dir: Path = DB_DIR,
    manifest_path: Path = MANIFEST_PATH,
    processed_dir: Path = PROCESSED_DIR,
    images_dir: Path = IMAGES_DIR,
    mineru_output_dir: Path = MINERU_DIR,
    audit_dir: Path = AUDIT_DIR,
) -> dict[str, Any]:
    configure_pipeline_logging()
    source_dir = source_dir.resolve()
    pdf_files = list_pdf_files(source_dir)
    metadata = load_spec_metadata(pdf_files, METADATA_DIR / "specs.json")

    if dry_run_only:
        return dry_run(source_dir, parser_backend=parser_backend)

    parser_environment = validate_parser_backend(parser_backend)
    if not os.environ.get("ZHIPUAI_API_KEY"):
        raise BuildPreflightError("ZHIPUAI_API_KEY 未设置，无法执行全量构建和向量化入库")

    clean_generated_outputs(
        db_dir=db_dir,
        manifest_path=manifest_path,
        processed_dir=processed_dir,
        images_dir=images_dir,
        mineru_dir=mineru_output_dir,
        audit_dir=audit_dir,
    )

    from .load_to_db import load_chunks_to_db
    from .process_documents import process_pdfs

    processed_by_file = process_pdfs(
        pdf_files,
        metadata,
        processed_dir,
        images_dir,
        parser_backend=parser_backend,
        mineru_output_dir=mineru_output_dir,
        apply_corrections=apply_corrections,
    )
    chunks_by_file = {
        source_file: result["chunks"] for source_file, result in processed_by_file.items()
    }
    total_loaded = load_chunks_to_db(chunks_by_file, db_dir)
    chunk_counts = {source_file: len(chunks) for source_file, chunks in chunks_by_file.items()}
    image_count = len([path for path in images_dir.glob("*") if path.is_file()])
    manifest = build_manifest(
        pdf_files=pdf_files,
        metadata=metadata,
        chunk_counts=chunk_counts,
        image_count=image_count,
        embedding_model=settings.embedding_model,
        collection_name=settings.collection_name,
        artifacts_by_file={
            source_file: result.get("artifacts", [])
            for source_file, result in processed_by_file.items()
        },
        parser_metadata_by_file={
            source_file: result.get("parser_metadata", {})
            for source_file, result in processed_by_file.items()
        },
        audit_by_file={
            source_file: result.get("audit", {})
            for source_file, result in processed_by_file.items()
        },
        corrections_by_file={
            source_file: result.get("corrections", {})
            for source_file, result in processed_by_file.items()
        },
        chunk_hashes_by_file={
            source_file: [chunk["chunk_id"] for chunk in result.get("chunks", [])]
            for source_file, result in processed_by_file.items()
        },
        build_params={
            "source_dir": str(source_dir),
            "mode": "rebuild",
            "parser_backend": parser_backend,
            "parser_environment": parser_environment,
            "processed_dir": str(processed_dir),
            "images_dir": str(images_dir),
            "mineru_output_dir": str(mineru_output_dir),
            "audit_dir": str(audit_dir),
            "db_dir": str(db_dir),
            "mineru_args": os.environ.get("MINERU_ARGS", ""),
            "apply_corrections": apply_corrections,
            "corrections_dir": str(CORRECTIONS_DIR),
            "loaded_chunks": total_loaded,
        },
    )
    write_manifest(manifest_path, manifest)
    return manifest


def build(
    source_dir: Path = RAW_DIR,
    *,
    dry_run_only: bool = False,
    parser_backend: str = DEFAULT_PARSER_BACKEND,
    apply_corrections: bool = True,
) -> dict[str, Any]:
    return rebuild(
        source_dir=source_dir,
        dry_run_only=dry_run_only,
        parser_backend=parser_backend,
        apply_corrections=apply_corrections,
    )


def audit(processed_dir: Path = PROCESSED_DIR) -> dict[str, Any]:
    from .audit import audit_processed_documents, write_audit_report

    report = audit_processed_documents(processed_dir)
    report_path = write_audit_report(report, AUDIT_DIR)
    return {**report, "report_path": str(report_path)}


def review(
    doc: str, pages: str = "", source_dir: Path = RAW_DIR, processed_dir: Path = PROCESSED_DIR
) -> dict[str, Any]:
    from .audit.multimodal import run_multimodal_review

    return run_multimodal_review(
        doc, pages, source_dir=source_dir, processed_dir=processed_dir, out_dir=AUDIT_DIR
    )


def promote_corrections(doc: str, *, include_pending: bool = False) -> dict[str, Any]:
    from .audit.corrections import promote_approved_candidates

    return promote_approved_candidates(doc, CORRECTIONS_DIR, include_pending=include_pending)


def status() -> dict[str, Any]:
    manifest = read_active_manifest(ACTIVE_DB_PATH, MANIFEST_PATH)
    if not manifest:
        return {"built": False, "message": "知识库尚未构建，未找到活动 manifest"}
    return {
        "built": True,
        "built_at": manifest.get("built_at"),
        "document_count": manifest.get("document_count", 0),
        "chunk_count": manifest.get("chunk_count", 0),
        "image_count": manifest.get("image_count", 0),
        "data_version_hash": manifest.get("data_version_hash", ""),
        "metadata_status": manifest.get("metadata_status", "unknown"),
        "parser_backend": manifest.get("build_params", {}).get("parser_backend", ""),
        "missing_artifact_count": manifest.get("artifact_status", {}).get("missing_count", 0),
        "high_risk_count": manifest.get("audit_status", {}).get("high_risk_count", 0),
        "applied_correction_count": manifest.get("correction_status", {}).get("applied_count", 0),
    }


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=True, indent=2))
