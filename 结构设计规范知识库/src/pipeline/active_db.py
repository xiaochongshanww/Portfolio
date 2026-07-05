import json
from pathlib import Path
from typing import Any

from .paths import ACTIVE_DB_PATH, DB_DIR


def read_active_db(path: Path = ACTIVE_DB_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"active_db_dir": str(DB_DIR), "manifest": "data/manifest.json"}
    return json.loads(path.read_text(encoding="utf-8"))


def write_active_db(payload: dict[str, Any], path: Path = ACTIVE_DB_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def active_db_dir(path: Path = ACTIVE_DB_PATH) -> Path:
    payload = read_active_db(path)
    return Path(payload.get("active_db_dir") or DB_DIR)


def read_active_manifest(path: Path = ACTIVE_DB_PATH) -> dict[str, Any]:
    payload = read_active_db(path)
    manifest_path = Path(payload.get("manifest") or "data/manifest.json")
    if not manifest_path.is_absolute():
        manifest_path = path.resolve().parents[1] / manifest_path
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))
