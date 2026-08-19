from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.active_db import resolve_pointer_path  # noqa: E402

DEFAULT_ACTIVE_DB_PATH = PROJECT_ROOT / "data" / "active_db.json"


class RuntimeManifestError(ValueError):
    def __init__(self, issues: list[str] | str):
        self.issues = [issues] if isinstance(issues, str) else list(issues)
        super().__init__("；".join(self.issues))


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeManifestError(f"{label}不存在：{path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeManifestError(f"{label}无法读取或不是有效 UTF-8 JSON：{path}") from exc
    if not isinstance(value, dict):
        raise RuntimeManifestError(f"{label}根节点必须是对象：{path}")
    return value


def _resolve_manifest_path(active_db_path: Path, active_db: dict[str, Any]) -> Path:
    reference = str(active_db.get("manifest") or "").strip()
    if not reference:
        raise RuntimeManifestError("活动数据库指针缺少 manifest")
    return resolve_pointer_path(reference, active_db_path, active_db_path.parent / "manifest.json")


def validate_runtime_manifest(
    active_db_path: Path = DEFAULT_ACTIVE_DB_PATH,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    active_db_path = active_db_path.resolve()
    active_db = _load_json(active_db_path, "活动数据库指针")
    resolved_manifest_path = (
        manifest_path.resolve()
        if manifest_path is not None
        else _resolve_manifest_path(active_db_path, active_db)
    )
    manifest = _load_json(resolved_manifest_path, "活动运行 manifest")
    issues: list[str] = []
    documents = manifest.get("documents")
    if not isinstance(documents, list):
        issues.append("manifest.documents必须是数组")
        documents = []

    source_files: list[str] = []
    chunk_sum = 0
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            issues.append(f"manifest.documents[{index}]必须是对象")
            continue
        source_file = str(document.get("source_file") or "").strip()
        if not source_file:
            issues.append(f"manifest.documents[{index}]缺少 source_file")
        elif source_file in source_files:
            issues.append(f"manifest.documents包含重复 source_file：{source_file}")
        else:
            source_files.append(source_file)
        chunk_count = document.get("chunk_count")
        if not isinstance(chunk_count, int) or isinstance(chunk_count, bool) or chunk_count < 0:
            issues.append(f"manifest.documents[{index}].chunk_count必须是非负整数")
        else:
            chunk_sum += chunk_count

    document_count = manifest.get("document_count")
    if document_count != len(documents):
        issues.append(
            f"manifest.document_count不一致：声明={document_count}，实际={len(documents)}"
        )
    manifest_chunk_count = manifest.get("chunk_count")
    if manifest_chunk_count != chunk_sum:
        issues.append(
            f"manifest.chunk_count不一致：声明={manifest_chunk_count}，文档合计={chunk_sum}"
        )

    active_chunk_count = active_db.get("chunk_count")
    if active_chunk_count != manifest_chunk_count:
        issues.append(
            f"活动指针 chunk_count 不一致：指针={active_chunk_count}，manifest={manifest_chunk_count}"
        )
    active_version = str(active_db.get("data_version_hash") or "")
    manifest_version = str(manifest.get("data_version_hash") or "")
    if active_version != manifest_version:
        issues.append("活动指针与 manifest 的 data_version_hash 不一致")

    return {
        "ok": not issues,
        "active_db_path": str(active_db_path),
        "manifest_path": str(resolved_manifest_path),
        "document_count": len(documents),
        "declared_document_count": document_count,
        "chunk_sum": chunk_sum,
        "declared_chunk_count": manifest_chunk_count,
        "active_chunk_count": active_chunk_count,
        "data_version_hash": manifest_version,
        "issues": issues,
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="校验活动运行 manifest 与活动指针的一致性")
    parser.add_argument("--active-db", type=Path, default=DEFAULT_ACTIVE_DB_PATH)
    parser.add_argument("--manifest", type=Path, help="显式指定 manifest；默认读取活动指针")
    args = parser.parse_args()
    try:
        result = validate_runtime_manifest(args.active_db, args.manifest)
    except RuntimeManifestError as exc:
        result = {"ok": False, "error": "runtime_manifest_invalid", "issues": exc.issues}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
