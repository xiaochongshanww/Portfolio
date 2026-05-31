import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_MINERU_KINDS = {"content_list", "markdown"}
OPTIONAL_MINERU_KINDS = {"middle", "model", "media"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_record(kind: str, path: Path, root: Path, *, required: bool) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": str(path),
        "relative_path": str(path.relative_to(root)) if path.is_relative_to(root) else path.name,
        "sha256": file_sha256(path),
        "size_bytes": path.stat().st_size,
        "required": required,
        "status": "ok",
    }


def missing_artifact(kind: str, *, required: bool) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": "",
        "relative_path": "",
        "sha256": "",
        "size_bytes": 0,
        "required": required,
        "status": "missing",
    }


def classify_mineru_artifact(path: Path) -> str | None:
    name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "markdown"
    if "content_list" in name and suffix == ".json":
        return "content_list"
    if "middle" in name and suffix == ".json":
        return "middle"
    if "model" in name and suffix == ".json":
        return "model"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        return "media"
    return None


def scan_mineru_artifacts(doc_dir: Path) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    present = set()
    for path in sorted(p for p in doc_dir.rglob("*") if p.is_file()):
        kind = classify_mineru_artifact(path)
        if not kind:
            continue
        present.add(kind)
        found.append(artifact_record(kind, path, doc_dir, required=kind in REQUIRED_MINERU_KINDS))

    for kind in sorted(REQUIRED_MINERU_KINDS | OPTIONAL_MINERU_KINDS):
        if kind not in present:
            found.append(missing_artifact(kind, required=kind in REQUIRED_MINERU_KINDS))
    return sorted(found, key=lambda item: (item["kind"], item["relative_path"]))


def write_artifact_index(path: Path, source_file: str, artifacts: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
    payload = {
        "source_file": source_file,
        "artifacts": artifacts,
        "metadata": metadata,
        "missing_required": [item["kind"] for item in artifacts if item["required"] and item["status"] != "ok"],
        "missing_optional": [item["kind"] for item in artifacts if not item["required"] and item["status"] != "ok"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def require_artifacts(artifacts: list[dict[str, Any]]) -> None:
    missing = [item["kind"] for item in artifacts if item["required"] and item["status"] != "ok"]
    if missing:
        raise RuntimeError(f"MinerU 必需产物缺失: {', '.join(sorted(set(missing)))}")


def find_artifact(artifacts: list[dict[str, Any]], kind: str) -> Path | None:
    for item in artifacts:
        if item["kind"] == kind and item["status"] == "ok":
            return Path(item["path"])
    return None
