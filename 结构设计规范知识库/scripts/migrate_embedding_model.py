from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, "") and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.admin.workflows import write_candidate_activation_artifacts  # noqa: E402
from src.app.core.config import settings  # noqa: E402
from src.pipeline.active_db import (  # noqa: E402
    active_db_dir,
    active_images_dir,
    active_processed_dir,
    write_active_db,
)
from src.pipeline.load_to_db import PipelineError  # noqa: E402
from src.pipeline.manifest import (  # noqa: E402
    compute_data_version_hash,
    read_manifest,
    write_manifest,
)
from src.pipeline.paths import ACTIVE_DB_PATH, DB_VERSIONS_DIR, MANIFEST_PATH  # noqa: E402
from src.quality.candidate import assess_candidate_activation  # noqa: E402


class EmbeddingMigrationError(RuntimeError):
    pass


def _production_sources(manifest: dict[str, Any]) -> list[str]:
    documents = manifest.get("documents")
    if not isinstance(documents, list) or not documents:
        raise EmbeddingMigrationError("活动 manifest 缺少 documents")
    sources = [
        str(document.get("source_file") or "")
        for document in documents
        if isinstance(document, dict) and document.get("status") != "test"
    ]
    if not sources or any(not source for source in sources):
        raise EmbeddingMigrationError("活动 manifest 缺少有效生产 source_file")
    return sources


def _load_processed_chunks(processed_dir: Path, sources: list[str]) -> dict[str, list[dict[str, Any]]]:
    chunks_by_file: dict[str, list[dict[str, Any]]] = {}
    for source_file in sources:
        path = processed_dir / f"{Path(source_file).stem}_chunks.json"
        if not path.is_file():
            raise EmbeddingMigrationError(f"缺少已处理 chunk 文件: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EmbeddingMigrationError(f"无法读取 chunk 文件: {path}") from exc
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise EmbeddingMigrationError(f"chunk 文件格式无效: {path}")
        if any(str(item.get("source_file") or "") != source_file for item in payload):
            raise EmbeddingMigrationError(f"chunk 来源与 manifest 不一致: {path}")
        chunks_by_file[source_file] = payload
    return chunks_by_file


def _copy_processed_assets(
    source_dir: Path,
    target_dir: Path,
    sources: list[str],
) -> None:
    target_dir.mkdir(parents=True, exist_ok=False)
    for source_file in sources:
        stem = Path(source_file).stem
        for suffix in (".json", "_chunks.json"):
            source = source_dir / f"{stem}{suffix}"
            if source.is_file():
                shutil.copy2(source, target_dir / source.name)
    for name in ("build_quality.json",):
        source = source_dir / name
        if source.is_file():
            shutil.copy2(source, target_dir / name)


def _copy_images(source_dir: Path, target_dir: Path) -> None:
    if source_dir.is_dir():
        shutil.copytree(source_dir, target_dir)
    else:
        target_dir.mkdir(parents=True)


def _candidate_manifest(
    source_manifest: dict[str, Any],
    *,
    candidate_db_dir: Path,
    candidate_processed_dir: Path,
    candidate_images_dir: Path,
    chunk_count: int,
) -> dict[str, Any]:
    manifest = dict(source_manifest)
    build_params = dict(source_manifest.get("build_params") or {})
    build_params.update(
        {
            "mode": "embedding-migration",
            "source_data_version_hash": source_manifest.get("data_version_hash", ""),
            "source_embedding_model": source_manifest.get("embedding_model", ""),
            "source_embedding_dimensions": source_manifest.get("embedding_dimensions", 1024),
            "db_dir": str(candidate_db_dir),
            "processed_dir": str(candidate_processed_dir),
            "images_dir": str(candidate_images_dir),
            "loaded_chunks": chunk_count,
        }
    )
    manifest["built_at"] = datetime.now(UTC).isoformat()
    manifest["embedding_model"] = settings.embedding_model
    manifest["embedding_dimensions"] = settings.embedding_dimensions
    manifest["build_params"] = build_params
    manifest["data_version_hash"] = compute_data_version_hash(
        {
            "documents": manifest.get("documents", []),
            "embedding_model": manifest["embedding_model"],
            "embedding_dimensions": manifest["embedding_dimensions"],
            "collection_name": manifest.get("collection_name", settings.collection_name),
            "build_params": build_params,
        }
    )
    return manifest


def migrate_embedding_model(
    *,
    processed_dir: Path | None = None,
    images_dir: Path | None = None,
    output_dir: Path | None = None,
    activate: bool = False,
) -> dict[str, Any]:
    if not settings.zhipuai_api_key:
        raise EmbeddingMigrationError("ZHIPUAI_API_KEY 未设置")
    source_manifest = read_manifest(MANIFEST_PATH) or {}
    sources = _production_sources(source_manifest)
    source_processed_dir = (processed_dir or active_processed_dir()).resolve()
    source_images_dir = (images_dir or active_images_dir()).resolve()
    chunks_by_file = _load_processed_chunks(source_processed_dir, sources)
    expected_counts = {
        str(document.get("source_file")): int(document.get("chunk_count", 0))
        for document in source_manifest.get("documents", [])
        if isinstance(document, dict) and document.get("status") != "test"
    }
    actual_counts = {source: len(chunks) for source, chunks in chunks_by_file.items()}
    if actual_counts != expected_counts:
        raise EmbeddingMigrationError(
            f"活动 manifest 与 chunk 计数不一致: expected={expected_counts}, actual={actual_counts}"
        )

    version_dir = (output_dir or DB_VERSIONS_DIR / f"embedding-migration-{datetime.now(UTC):%Y%m%d%H%M%S}").resolve()
    if version_dir.exists():
        raise EmbeddingMigrationError(f"候选目录已存在: {version_dir}")
    candidate_db_dir = version_dir / "db"
    candidate_processed_dir = version_dir / "processed"
    candidate_images_dir = version_dir / "images"
    version_dir.mkdir(parents=True)
    try:
        _copy_processed_assets(source_processed_dir, candidate_processed_dir, sources)
        _copy_images(source_images_dir, candidate_images_dir)
        from src.pipeline.load_to_db import migrate_collection_embeddings

        loaded_chunks = migrate_collection_embeddings(
            chunks_by_file,
            active_db_dir(),
            candidate_db_dir,
        )
        manifest = _candidate_manifest(
            source_manifest,
            candidate_db_dir=candidate_db_dir,
            candidate_processed_dir=candidate_processed_dir,
            candidate_images_dir=candidate_images_dir,
            chunk_count=loaded_chunks,
        )
        candidate_manifest_path = version_dir / "manifest.json"
        write_manifest(candidate_manifest_path, manifest)
        result: dict[str, Any] = {
            "ok": True,
            "activated": False,
            "candidate_dir": str(version_dir),
            "candidate_manifest": str(candidate_manifest_path),
            "embedding_model": settings.embedding_model,
            "embedding_dimensions": settings.embedding_dimensions,
            "document_count": manifest.get("document_count", 0),
            "chunk_count": loaded_chunks,
            "data_version_hash": manifest.get("data_version_hash", ""),
        }
        assessment = assess_candidate_activation(
            manifest_path=candidate_manifest_path,
            db_dir=candidate_db_dir,
            processed_dir=candidate_processed_dir,
            images_dir=candidate_images_dir,
        )
        gate_artifacts = write_candidate_activation_artifacts(assessment, version_dir / "quality")
        result["candidate_gate"] = assessment.result
        result["candidate_gate_report"] = gate_artifacts["gate_report"]
        if not assessment.result.get("passed") or assessment.retrieval_state is None:
            result["ok"] = False
            result["error"] = "候选向量迁移未通过预激活门禁"
            return result
        if not activate:
            return result

        pointer_payload = {
            "active_db_dir": str(candidate_db_dir),
            "processed_dir": str(candidate_processed_dir),
            "images_dir": str(candidate_images_dir),
            "manifest": str(candidate_manifest_path),
            "data_version_hash": manifest.get("data_version_hash", ""),
            "chunk_count": loaded_chunks,
            "activated_at": assessment.result.get("generated_at", ""),
            "candidate_gate_report": gate_artifacts["gate_report"],
            "migration": "embedding-model",
        }
        write_manifest(MANIFEST_PATH, manifest)
        write_active_db(pointer_payload, ACTIVE_DB_PATH)
        result["activated"] = True
        return result
    except Exception:
        shutil.rmtree(version_dir, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="使用现有解析产物迁移向量模型")
    parser.add_argument("--processed-dir", type=Path, default=None)
    parser.add_argument("--images-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--activate", action="store_true", help="候选门禁通过后切换活动版本")
    args = parser.parse_args()
    try:
        result = migrate_embedding_model(
            processed_dir=args.processed_dir,
            images_dir=args.images_dir,
            output_dir=args.output_dir,
            activate=args.activate,
        )
    except (EmbeddingMigrationError, PipelineError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
