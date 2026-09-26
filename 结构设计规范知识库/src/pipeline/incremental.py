from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.app.core.config import settings
from src.app.retrieval.dense_vector_store import VECTOR_SCHEMA_VERSION, load_dense_vector_store

from .active_db import (
    active_db_dir,
    active_images_dir,
    active_processed_dir,
    read_active_manifest,
)
from .artifacts import file_sha256
from .metadata import SpecMetadata
from .parsers.mineru import doc_id_for_pdf
from .paths import (
    ACTIVE_DB_PATH,
    CORRECTIONS_DIR,
    DOCUMENT_CACHE_DIR,
    STRUCTURED_TABLES_DIR,
)

INCREMENTAL_SCHEMA_VERSION = 1
BUILD_CONTRACT_SCHEMA_VERSION = 2
DOCUMENT_OUTPUT_CONTRACT_VERSION = 1
CHUNK_OUTPUT_CONTRACT_VERSION = 1
INDEX_CONTRACT_VERSION = 1

# The active Aug-2026 manifest predates progress reporting, Chroma persistence
# verification, and MinerU stage timing metadata. The current MinerU adapter also
# streams progress and supports managed cancellation without changing extracted artifacts.
# Approve only exact, reviewed non-semantic transitions; unknown legacy code still reparses.
LEGACY_V1_CODE_HASH_TRANSITIONS = {
    "process_documents_sha256": (
        "5b6abbfcb6e8adf3cb2da180f31e8427754eedd7b9c20fb8e24c45481c2a23cc",
        "84dc626717b4781099c2c308cd9317876fff94bfc8003d4db27a56a33cc8b5b6",
    ),
    "parser_adapter_sha256": (
        "fdc6e1b64f0503ad4198b77cd58a3f92ce5c533fa6603bd5328158902cd3f22b",
        "a28a161e44b5b19fde1ae69b4e7873cdbcecfa4f53d98984e532ebd29fc03d7f",
    ),
    "chunks_sha256": (
        "1793d185c7cafff672c52f4c2674cd77e835e975ea575635affab9fa944e9275",
        "1793d185c7cafff672c52f4c2674cd77e835e975ea575635affab9fa944e9275",
    ),
}


def _stable_hash(value: Any) -> str:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _source_hash(path: Path) -> str:
    return file_sha256(path) if path.is_file() else "missing"


def _approved_correction_path(source_file: str) -> Path:
    return CORRECTIONS_DIR / "approved" / f"{Path(source_file).stem}.json"


def _matching_structured_files(spec: SpecMetadata) -> list[Path]:
    code_token = "_".join(spec.code.replace("-", " ").split())
    if not code_token or not STRUCTURED_TABLES_DIR.is_dir():
        return []
    return sorted(
        path for path in STRUCTURED_TABLES_DIR.glob(f"{code_token}*.json") if path.is_file()
    )


def _embedding_contract() -> dict[str, Any]:
    return {
        "model": settings.embedding_model,
        "dimensions": settings.embedding_dimensions,
        "request_contract": "embedding_request_kwargs:v1",
    }


def document_fingerprint(
    pdf_path: Path,
    spec: SpecMetadata,
    *,
    apply_corrections: bool,
) -> dict[str, Any]:
    correction_path = _approved_correction_path(pdf_path.name)
    structured_files = _matching_structured_files(spec)
    payload = {
        "schema_version": INCREMENTAL_SCHEMA_VERSION,
        "source_sha256": file_sha256(pdf_path),
        "metadata_sha256": _stable_hash(spec.to_dict()),
        "corrections_sha256": (
            file_sha256(correction_path)
            if apply_corrections and correction_path.is_file()
            else "disabled"
            if not apply_corrections
            else "none"
        ),
        "structured_revision": _stable_hash(
            [{"name": path.name, "sha256": file_sha256(path)} for path in structured_files]
        ),
    }
    return {**payload, "fingerprint": _stable_hash(payload)}


def build_contract(
    *,
    parser_backend: str,
    parser_environment: dict[str, Any],
    apply_corrections: bool,
) -> dict[str, Any]:
    pipeline_dir = Path(__file__).resolve().parent
    parser_file = pipeline_dir / "parsers" / f"{parser_backend}.py"
    implementation_hashes = {
        "process_documents_sha256": _source_hash(pipeline_dir / "process_documents.py"),
        "chunks_sha256": _source_hash(pipeline_dir / "chunks.py"),
        "parser_adapter_sha256": _source_hash(parser_file),
        "load_to_db_sha256": _source_hash(pipeline_dir / "load_to_db.py"),
    }
    processing = {
        "version": DOCUMENT_OUTPUT_CONTRACT_VERSION,
        "chunk_output_version": CHUNK_OUTPUT_CONTRACT_VERSION,
        "parser_backend": parser_backend,
        "parser_implementation": parser_environment.get("implementation", parser_backend),
        "parser_version": parser_environment.get("version", ""),
        "parser_compatibility": parser_environment.get("compatibility", "not_applicable"),
        "mineru_args": os.environ.get("MINERU_ARGS", ""),
        "apply_corrections": apply_corrections,
        "implementation_hashes": implementation_hashes,
    }
    embedding = _embedding_contract()
    index = {
        "version": INDEX_CONTRACT_VERSION,
        "collection_name": settings.collection_name,
        "dense_vector_schema_version": VECTOR_SCHEMA_VERSION,
    }
    payload = {
        "schema_version": BUILD_CONTRACT_SCHEMA_VERSION,
        "processing": processing,
        "embedding": embedding,
        "index": index,
    }
    return {**payload, "fingerprint": _stable_hash(payload)}


@dataclass
class DocumentChange:
    source_file: str
    action: str
    reasons: list[str] = field(default_factory=list)
    fingerprint: dict[str, Any] = field(default_factory=dict)


@dataclass
class IncrementalPlan:
    mode: str
    requested_mode: str
    fallback_to_full: bool
    fallback_reasons: list[str]
    active_data_version_hash: str
    contract: dict[str, Any]
    documents: list[DocumentChange]
    embedding_cache_compatible: bool
    embedding_cache_reason: str

    def to_dict(self) -> dict[str, Any]:
        documents = [asdict(item) for item in self.documents]
        counts = {
            action: sum(1 for item in self.documents if item.action == action)
            for action in ("added", "changed", "reused", "removed")
        }
        return {
            "schema_version": INCREMENTAL_SCHEMA_VERSION,
            "mode": self.mode,
            "requested_mode": self.requested_mode,
            "fallback_to_full": self.fallback_to_full,
            "fallback_reasons": self.fallback_reasons,
            "active_data_version_hash": self.active_data_version_hash,
            "contract": self.contract,
            "embedding_cache_compatible": self.embedding_cache_compatible,
            "embedding_cache_reason": self.embedding_cache_reason,
            "counts": counts,
            "documents": documents,
        }


def _legacy_v1_processing_compatible(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    previous_processing = previous.get("processing")
    current_processing = current.get("processing")
    if not isinstance(previous_processing, dict) or not isinstance(current_processing, dict):
        return False
    expected_legacy_keys = {
        "version",
        "parser_backend",
        "parser_implementation",
        "parser_version",
        "parser_compatibility",
        "mineru_args",
        "apply_corrections",
        "process_documents_sha256",
        "chunks_sha256",
        "parser_adapter_sha256",
    }
    if set(previous_processing) != expected_legacy_keys:
        return False
    current_hashes = current_processing.get("implementation_hashes")
    if not isinstance(current_hashes, dict):
        return False
    for key in (
        "version",
        "parser_backend",
        "parser_implementation",
        "parser_version",
        "parser_compatibility",
        "mineru_args",
        "apply_corrections",
    ):
        if previous_processing.get(key) != current_processing.get(key):
            return False
    return all(
        previous_processing.get(key) == old_hash and current_hashes.get(key) == current_hash
        for key, (old_hash, current_hash) in LEGACY_V1_CODE_HASH_TRANSITIONS.items()
    )


def _processing_contract_compatible(previous: Any, current: dict[str, Any]) -> bool:
    if not isinstance(previous, dict):
        return False
    if previous.get("schema_version") == BUILD_CONTRACT_SCHEMA_VERSION:
        old_processing = previous.get("processing")
        new_processing = current.get("processing")
        if not isinstance(old_processing, dict) or not isinstance(new_processing, dict):
            return False
        old_semantics = {
            key: value for key, value in old_processing.items() if key != "implementation_hashes"
        }
        new_semantics = {
            key: value for key, value in new_processing.items() if key != "implementation_hashes"
        }
        return old_semantics == new_semantics
    if (
        previous.get("schema_version") == 1
        and current.get("schema_version") == BUILD_CONTRACT_SCHEMA_VERSION
    ):
        return _legacy_v1_processing_compatible(previous, current)
    return False


def _active_document_usable(source_file: str, document: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    processed_dir = active_processed_dir(ACTIVE_DB_PATH)
    stem = Path(source_file).stem
    for path in (processed_dir / f"{stem}.json", processed_dir / f"{stem}_chunks.json"):
        if not path.is_file():
            reasons.append(f"missing_cached_file:{path.name}")
    for artifact in document.get("artifacts", []):
        if artifact.get("status") != "ok":
            if artifact.get("required"):
                reasons.append(f"missing_required_artifact:{artifact.get('kind', 'unknown')}")
            continue
        path = Path(str(artifact.get("path") or ""))
        if not path.is_file():
            reasons.append(f"missing_artifact:{artifact.get('kind', 'unknown')}")
            continue
        expected_hash = str(artifact.get("sha256") or "")
        if expected_hash and file_sha256(path) != expected_hash:
            reasons.append(f"artifact_hash_mismatch:{artifact.get('kind', 'unknown')}")
    return not reasons, reasons


def plan_incremental_build(
    pdf_files: list[Path],
    metadata: dict[str, SpecMetadata],
    *,
    parser_backend: str,
    parser_environment: dict[str, Any],
    apply_corrections: bool,
    requested_mode: str = "incremental",
) -> IncrementalPlan:
    contract = build_contract(
        parser_backend=parser_backend,
        parser_environment=parser_environment,
        apply_corrections=apply_corrections,
    )
    active_manifest = read_active_manifest(ACTIVE_DB_PATH)
    fallback_reasons: list[str] = []
    embedding_cache_compatible = False
    embedding_cache_reason = "not_checked"
    if requested_mode == "full":
        fallback_reasons.append("full_rebuild_requested")
    elif not active_manifest:
        fallback_reasons.append("active_manifest_missing")
    elif not _processing_contract_compatible(active_manifest.get("build_contract", {}), contract):
        fallback_reasons.append("build_contract_incompatible")

    active_documents = {
        str(item.get("source_file")): item
        for item in active_manifest.get("documents", [])
        if item.get("source_file")
    }
    current_names = {path.name for path in pdf_files}
    changes: list[DocumentChange] = []
    for pdf_path in pdf_files:
        fingerprint = document_fingerprint(
            pdf_path,
            metadata[pdf_path.name],
            apply_corrections=apply_corrections,
        )
        previous = active_documents.get(pdf_path.name)
        if previous is None:
            changes.append(DocumentChange(pdf_path.name, "added", ["new_source"], fingerprint))
            continue
        previous_fingerprint = previous.get("build_fingerprint", {})
        if previous_fingerprint.get("fingerprint") != fingerprint["fingerprint"]:
            changed_fields = (
                ["legacy_build_fingerprint_missing"]
                if not previous_fingerprint
                else [
                    f"{key}_changed"
                    for key in (
                        "source_sha256",
                        "metadata_sha256",
                        "corrections_sha256",
                        "structured_revision",
                    )
                    if previous_fingerprint.get(key) != fingerprint.get(key)
                ]
            )
            changes.append(
                DocumentChange(
                    pdf_path.name,
                    "changed",
                    changed_fields or ["fingerprint_changed"],
                    fingerprint,
                )
            )
            continue
        usable, reasons = _active_document_usable(pdf_path.name, previous)
        changes.append(
            DocumentChange(
                pdf_path.name,
                "reused" if usable else "changed",
                [] if usable else reasons,
                fingerprint,
            )
        )

    changes.extend(
        DocumentChange(source_file, "removed", ["source_removed"])
        for source_file in sorted(set(active_documents) - current_names)
    )

    if not fallback_reasons:
        active_contract = active_manifest.get("build_contract")
        active_embedding_contract = (
            active_contract.get("embedding") if isinstance(active_contract, dict) else None
        )
        if active_embedding_contract != contract["embedding"]:
            embedding_cache_reason = "embedding_contract_incompatible"
        else:
            try:
                store = load_dense_vector_store(
                    active_db_dir(ACTIVE_DB_PATH),
                    embedding_model=settings.embedding_model,
                    dimensions=settings.embedding_dimensions,
                )
                if store is None:
                    embedding_cache_reason = "active_embedding_cache_missing"
                else:
                    embedding_cache_compatible = True
                    embedding_cache_reason = "compatible"
            except ValueError:
                embedding_cache_reason = "active_embedding_cache_invalid"

    fallback = bool(fallback_reasons)
    if fallback:
        for change in changes:
            if change.action == "reused":
                change.action = "changed"
                change.reasons.append("full_rebuild_fallback")
    return IncrementalPlan(
        mode="full" if fallback else "incremental",
        requested_mode=requested_mode,
        fallback_to_full=fallback,
        fallback_reasons=fallback_reasons,
        active_data_version_hash=str(active_manifest.get("data_version_hash") or ""),
        contract=contract,
        documents=changes,
        embedding_cache_compatible=embedding_cache_compatible,
        embedding_cache_reason=embedding_cache_reason,
    )


def load_reused_document(
    source_file: str,
    *,
    target_processed_dir: Path,
    target_images_dir: Path,
    target_mineru_dir: Path,
) -> dict[str, Any]:
    source_processed_dir = active_processed_dir(ACTIVE_DB_PATH)
    source_images_dir = active_images_dir(ACTIVE_DB_PATH)
    stem = Path(source_file).stem
    source_elements = source_processed_dir / f"{stem}.json"
    source_chunks = source_processed_dir / f"{stem}_chunks.json"
    payload = json.loads(source_elements.read_text(encoding="utf-8"))
    chunks = json.loads(source_chunks.read_text(encoding="utf-8"))

    target_processed_dir.mkdir(parents=True, exist_ok=True)
    target_images_dir.mkdir(parents=True, exist_ok=True)
    target_mineru_dir.mkdir(parents=True, exist_ok=True)
    for image in sorted(source_images_dir.glob(f"{stem}*")):
        if image.is_file():
            shutil.copy2(image, target_images_dir / image.name)

    rewritten_artifacts: list[dict[str, Any]] = []
    document_mineru_dir = target_mineru_dir / doc_id_for_pdf(Path(source_file))
    for artifact in payload.get("artifacts", []):
        rewritten = dict(artifact)
        if artifact.get("status") == "ok":
            source = Path(str(artifact["path"]))
            relative = Path(str(artifact.get("relative_path") or source.name))
            target = document_mineru_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            rewritten["path"] = str(target)
            rewritten["sha256"] = file_sha256(target)
            rewritten["size_bytes"] = target.stat().st_size
        rewritten_artifacts.append(rewritten)
    payload["artifacts"] = rewritten_artifacts
    parser_metadata = dict(payload.get("parser_metadata") or {})
    if "mineru_output_dir" in parser_metadata:
        parser_metadata["mineru_output_dir"] = str(document_mineru_dir)
    payload["parser_metadata"] = parser_metadata

    (target_processed_dir / source_elements.name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (target_processed_dir / source_chunks.name).write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    quality = _active_quality_entry(source_file, len(chunks), payload)
    return {
        "chunks": chunks,
        "artifacts": rewritten_artifacts,
        "quality": quality,
        "parser_metadata": parser_metadata,
        "audit": payload.get("audit", {}),
        "corrections": payload.get("corrections", {}),
        "media_files": [],
        "cache_status": "reused",
    }


def _active_quality_entry(
    source_file: str, chunk_count: int, payload: dict[str, Any]
) -> dict[str, Any]:
    quality_path = active_processed_dir(ACTIVE_DB_PATH) / "build_quality.json"
    if quality_path.is_file():
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        for item in quality.get("documents", []):
            if item.get("source_file") == source_file:
                return item
    elements = payload.get("elements", [])
    return {
        "source_file": source_file,
        "element_count": len(elements),
        "chunk_count": chunk_count,
        "table_count": sum(1 for item in elements if item.get("chunk_type") == "table"),
        "formula_count": sum(1 for item in elements if item.get("chunk_type") == "formula"),
        "figure_count": sum(1 for item in elements if item.get("chunk_type") == "figure"),
        "empty_text_ratio": 0,
        "missing_artifacts": [
            item.get("kind") for item in payload.get("artifacts", []) if item.get("status") != "ok"
        ],
        "missing_required_artifacts": [
            item.get("kind")
            for item in payload.get("artifacts", [])
            if item.get("required") and item.get("status") != "ok"
        ],
        "audit": {
            "finding_count": payload.get("audit", {}).get("finding_count", 0),
            "high_risk_count": payload.get("audit", {}).get("high_risk_count", 0),
        },
        "corrections": {
            "approved_count": payload.get("corrections", {}).get("approved_count", 0),
            "applied_count": payload.get("corrections", {}).get("applied_count", 0),
            "skipped_count": payload.get("corrections", {}).get("skipped_count", 0),
        },
    }


def reusable_embedding_map() -> dict[str, list[float]]:
    active_manifest = read_active_manifest(ACTIVE_DB_PATH) or {}
    active_contract = active_manifest.get("build_contract")
    active_embedding_contract = (
        active_contract.get("embedding") if isinstance(active_contract, dict) else None
    )
    if active_embedding_contract != _embedding_contract():
        return {}
    try:
        store = load_dense_vector_store(
            active_db_dir(ACTIVE_DB_PATH),
            embedding_model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )
    except ValueError:
        return {}
    if store is None:
        return {}
    return {item: store.vectors[index].tolist() for index, item in enumerate(store.ids)}


def publish_cache_index(manifest: dict[str, Any], plan: dict[str, Any]) -> Path:
    DOCUMENT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = DOCUMENT_CACHE_DIR / "index.json"
    payload = {
        "schema_version": INCREMENTAL_SCHEMA_VERSION,
        "data_version_hash": manifest.get("data_version_hash", ""),
        "build_contract": manifest.get("build_contract", {}),
        "documents": {
            item.get("source_file", ""): item.get("build_fingerprint", {})
            for item in manifest.get("documents", [])
        },
        "last_plan": plan,
    }
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return path
