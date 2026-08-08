from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.client import SharedSystemClient

from src.app.core.config import settings
from src.pipeline.knowledge_package import export_runtime_package, validate_runtime_package


SOURCE_FILE = "GB 50009-2012_跨平台兼容测试规范.pdf"
DOCUMENTS = [
    "5.1.1 办公室楼面均布活荷载标准值为 2.0 kN/m²。",
    "5.1.2 楼面梁设计时应按规定考虑活荷载折减。",
    "附录 A 跨平台知识包运行探针样本。",
]
EMBEDDINGS = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
]
DATA_VERSION_HASH = hashlib.sha256("knowledge-package-portability-v1".encode()).hexdigest()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_source_runtime(root: Path) -> dict[str, Path]:
    data = root / "data"
    version = data / "db_versions" / "portability-source"
    database = version / "db"
    database.mkdir(parents=True)

    client = chromadb.PersistentClient(path=str(database))
    collection = client.get_or_create_collection(settings.collection_name)
    collection.add(
        ids=["compat-1", "compat-2", "compat-3"],
        embeddings=EMBEDDINGS,
        documents=DOCUMENTS,
        metadatas=[
            {"source_file": SOURCE_FILE, "clause_number": "5.1.1", "page": 1},
            {"source_file": SOURCE_FILE, "clause_number": "5.1.2", "page": 1},
            {"source_file": SOURCE_FILE, "clause_number": "A", "page": 2},
        ],
    )
    if collection.count() != len(DOCUMENTS):
        raise RuntimeError("兼容样包 Chroma 集合写入数量不一致")
    collection = None
    client = None
    SharedSystemClient.clear_system_cache()

    manifest = {
        "schema_version": 1,
        "built_at": "2026-08-08T00:00:00+00:00",
        "documents": [
            {
                "source_file": SOURCE_FILE,
                "code": "GB 50009-2012",
                "name": "跨平台兼容测试规范",
                "chunk_count": len(DOCUMENTS),
            }
        ],
        "document_count": 1,
        "chunk_count": len(DOCUMENTS),
        "image_count": 1,
        "embedding_model": settings.embedding_model,
        "collection_name": settings.collection_name,
        "data_version_hash": DATA_VERSION_HASH,
    }
    manifest_path = version / "manifest.json"
    _write_json(manifest_path, manifest)
    _write_json(
        data / "active_db.json",
        {
            "active_db_dir": str(database.resolve()),
            "manifest": str(manifest_path.resolve()),
            "data_version_hash": DATA_VERSION_HASH,
        },
    )
    structured = data / "structured_tables"
    _write_json(
        structured / "表5.1.1-活荷载.json",
        {"schema_version": "0.1", "rows": [{"用途": "办公室", "标准值": 2.0}]},
    )
    images = data / "images"
    images.mkdir()
    (images / "第1页-示意图.png").write_bytes(b"portability-image")
    metadata = data / "metadata"
    _write_json(
        metadata / "specs.json",
        {
            "documents": [
                {
                    "source_file": SOURCE_FILE,
                    "image_access": "authenticated",
                    "page_image_access": "disabled",
                }
            ]
        },
    )
    raw = data / "raw"
    raw.mkdir()
    return {
        "data": data,
        "active": data / "active_db.json",
        "manifest": manifest_path,
        "structured": structured,
        "images": images,
        "metadata": metadata,
        "raw": raw,
    }


def _source_runtime_paths(root: Path) -> dict[str, Path]:
    data = root / "data"
    version = data / "db_versions" / "portability-source"
    return {
        "data": data,
        "active": data / "active_db.json",
        "manifest": version / "manifest.json",
        "structured": data / "structured_tables",
        "images": data / "images",
        "metadata": data / "metadata",
        "raw": data / "raw",
    }


def create_portability_package(output_path: Path) -> dict[str, Any]:
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="knowledge-package-source-") as temporary_name:
        source_root = Path(temporary_name)
        result = subprocess.run(
            [sys.executable, "-m", "scripts.create_portability_package", "--prepare-source", str(source_root)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=PROJECT_ROOT,
            timeout=120,
        )
        if result.returncode != 0:
            details = (result.stderr or result.stdout).strip() or f"exit={result.returncode}"
            raise RuntimeError(f"兼容样包源数据库创建失败: {details}")
        source = _source_runtime_paths(source_root)
        exported = export_runtime_package(
            output_path,
            active_db_path=source["active"],
            fallback_manifest_path=source["manifest"],
            structured_tables_dir=source["structured"],
            images_dir=source["images"],
            metadata_dir=source["metadata"],
            raw_dir=source["raw"],
            overwrite=True,
            quality_waiver_actor="ci-portability",
            quality_waiver_reason="CI 合成知识包跨平台兼容验证",
            export_actor="ci-portability",
            export_audit_dir=source["data"] / "audit" / "package_exports",
        )
    validation = validate_runtime_package(output_path)
    exported.pop("audit_record", None)
    return {
        **exported,
        "schema_version": validation["schema_version"],
        "platform": platform.system().lower(),
        "machine": validation["compatibility"].get("machine"),
        "chunk_count": validation["chunk_count"],
        "warnings": validation["warnings"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="生成真实 Chroma 跨平台兼容测试知识包")
    parser.add_argument("--output", type=Path, help="输出知识包 ZIP")
    parser.add_argument("--prepare-source", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.prepare_source:
        _build_source_runtime(args.prepare_source)
        return 0
    if not args.output:
        parser.error("--output 是必需参数")
    result = create_portability_package(args.output)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
