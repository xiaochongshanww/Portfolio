from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
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
EMBEDDINGS = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
]
DEFAULT_VARIANT = "baseline"
VARIANT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_variant(variant: str) -> str:
    normalized = variant.strip()
    if not VARIANT_RE.fullmatch(normalized):
        raise ValueError("variant 必须是 1-64 位 ASCII 字母、数字、点、下划线或连字符")
    return normalized


def _variant_documents(variant: str) -> list[str]:
    return [
        "5.1.1 办公室楼面均布活荷载标准值为 2.0 kN/m²。",
        "5.1.2 楼面梁设计时应按规定考虑活荷载折减。",
        f"附录 A 跨平台知识包运行探针样本，内容变体 {variant}。",
    ]


def _variant_data_version_hash(variant: str) -> str:
    return hashlib.sha256(f"knowledge-package-portability-v2:{variant}".encode()).hexdigest()


def _build_source_runtime(root: Path, *, variant: str = DEFAULT_VARIANT) -> dict[str, Path]:
    variant = _normalize_variant(variant)
    documents = _variant_documents(variant)
    data_version_hash = _variant_data_version_hash(variant)
    data = root / "data"
    version = data / "db_versions" / "portability-source"
    database = version / "db"
    database.mkdir(parents=True)

    client = chromadb.PersistentClient(path=str(database))
    collection = client.get_or_create_collection(settings.collection_name)
    collection.add(
        ids=["compat-1", "compat-2", "compat-3"],
        embeddings=EMBEDDINGS,
        documents=documents,
        metadatas=[
            {"source_file": SOURCE_FILE, "clause_number": "5.1.1", "page": 1},
            {"source_file": SOURCE_FILE, "clause_number": "5.1.2", "page": 1},
            {"source_file": SOURCE_FILE, "clause_number": "A", "page": 2},
        ],
    )
    if collection.count() != len(documents):
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
                "name": f"跨平台兼容测试规范（{variant}）",
                "chunk_count": len(documents),
            }
        ],
        "document_count": 1,
        "chunk_count": len(documents),
        "image_count": 1,
        "embedding_model": settings.embedding_model,
        "embedding_dimensions": settings.embedding_dimensions,
        "collection_name": settings.collection_name,
        "data_version_hash": data_version_hash,
    }
    manifest_path = version / "manifest.json"
    _write_json(manifest_path, manifest)
    _write_json(
        data / "active_db.json",
        {
            "active_db_dir": str(database.resolve()),
            "manifest": str(manifest_path.resolve()),
            "data_version_hash": data_version_hash,
        },
    )
    structured = data / "structured_tables"
    _write_json(
        structured / "表5.1.1-活荷载.json",
        {
            "schema_version": "0.1",
            "package_variant": variant,
            "rows": [{"用途": "办公室", "标准值": 2.0}],
        },
    )
    images = data / "images"
    images.mkdir()
    (images / "第1页-示意图.png").write_bytes(f"portability-image:{variant}".encode())
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


def create_portability_package(
    output_path: Path,
    *,
    variant: str = DEFAULT_VARIANT,
) -> dict[str, Any]:
    variant = _normalize_variant(variant)
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="knowledge-package-source-") as temporary_name:
        source_root = Path(temporary_name)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.create_portability_package",
                "--prepare-source",
                str(source_root),
                "--variant",
                variant,
            ],
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
        "variant": variant,
        "warnings": validation["warnings"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="生成真实 Chroma 跨平台兼容测试知识包")
    parser.add_argument("--output", type=Path, help="输出知识包 ZIP")
    parser.add_argument("--prepare-source", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--variant", default=DEFAULT_VARIANT, help="确定性合成内容变体")
    args = parser.parse_args()
    if args.prepare_source:
        _build_source_runtime(args.prepare_source, variant=args.variant)
        return 0
    if not args.output:
        parser.error("--output 是必需参数")
    result = create_portability_package(args.output, variant=args.variant)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
