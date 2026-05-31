import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .metadata import SpecMetadata


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compute_data_version_hash(payload: dict[str, Any]) -> str:
    stable_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable_payload.encode("utf-8")).hexdigest()


def build_manifest(
    *,
    pdf_files: list[Path],
    metadata: dict[str, SpecMetadata],
    chunk_counts: dict[str, int],
    image_count: int,
    embedding_model: str,
    collection_name: str,
    artifacts_by_file: dict[str, list[dict[str, Any]]] | None = None,
    parser_metadata_by_file: dict[str, dict[str, Any]] | None = None,
    audit_by_file: dict[str, dict[str, Any]] | None = None,
    corrections_by_file: dict[str, dict[str, Any]] | None = None,
    chunk_hashes_by_file: dict[str, list[str]] | None = None,
    build_params: dict[str, Any],
) -> dict[str, Any]:
    artifacts_by_file = artifacts_by_file or {}
    parser_metadata_by_file = parser_metadata_by_file or {}
    audit_by_file = audit_by_file or {}
    corrections_by_file = corrections_by_file or {}
    chunk_hashes_by_file = chunk_hashes_by_file or {}
    documents = []
    for pdf in pdf_files:
        spec = metadata[pdf.name]
        artifacts = artifacts_by_file.get(pdf.name, [])
        documents.append(
            {
                **spec.to_dict(),
                "sha256": file_sha256(pdf),
                "size_bytes": pdf.stat().st_size,
                "chunk_count": chunk_counts.get(pdf.name, 0),
                "chunk_hashes": chunk_hashes_by_file.get(pdf.name, []),
                "artifacts": artifacts,
                "parser_metadata": parser_metadata_by_file.get(pdf.name, {}),
                "audit": audit_by_file.get(pdf.name, {}),
                "corrections": corrections_by_file.get(pdf.name, {}),
                "missing_artifacts": [item["kind"] for item in artifacts if item.get("status") != "ok"],
            }
        )

    missing_artifacts = [
        {"source_file": doc["source_file"], "kind": artifact["kind"], "required": artifact["required"]}
        for doc in documents
        for artifact in doc.get("artifacts", [])
        if artifact.get("status") != "ok"
    ]
    audit_status = {
        "finding_count": sum(doc.get("audit", {}).get("finding_count", 0) for doc in documents),
        "high_risk_count": sum(doc.get("audit", {}).get("high_risk_count", 0) for doc in documents),
    }
    correction_status = {
        "approved_count": sum(doc.get("corrections", {}).get("approved_count", 0) for doc in documents),
        "applied_count": sum(doc.get("corrections", {}).get("applied_count", 0) for doc in documents),
        "skipped_count": sum(doc.get("corrections", {}).get("skipped_count", 0) for doc in documents),
    }

    version_payload = {
        "documents": documents,
        "embedding_model": embedding_model,
        "collection_name": collection_name,
        "build_params": build_params,
    }
    return {
        "schema_version": 1,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "documents": documents,
        "document_count": len(documents),
        "chunk_count": sum(chunk_counts.values()),
        "image_count": image_count,
        "embedding_model": embedding_model,
        "collection_name": collection_name,
        "build_params": build_params,
        "metadata_status": "partial" if any(doc["metadata_status"] == "partial" for doc in documents) else "complete",
        "audit_status": audit_status,
        "correction_status": correction_status,
        "artifact_status": {
            "missing_count": len(missing_artifacts),
            "missing_required_count": sum(1 for item in missing_artifacts if item["required"]),
            "missing": missing_artifacts,
        },
        "data_version_hash": compute_data_version_hash(version_payload),
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def read_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
