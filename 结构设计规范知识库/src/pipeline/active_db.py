import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .manifest import read_manifest
from .paths import ACTIVE_DB_PATH, DB_DIR, MANIFEST_PATH


def read_active_db(path: Path = ACTIVE_DB_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"active_db_dir": str(DB_DIR), "manifest": "data/manifest.json"}
    return json.loads(path.read_text(encoding="utf-8"))


def _project_root(pointer_path: Path) -> Path:
    return pointer_path.resolve().parents[1]


def _portable_pointer_value(value: Any, pointer_path: Path) -> Any:
    if not isinstance(value, str) or not value:
        return value
    candidate = Path(value)
    if not candidate.is_absolute():
        return value.replace("\\", "/")
    try:
        return candidate.resolve().relative_to(_project_root(pointer_path)).as_posix()
    except ValueError:
        return value


def resolve_pointer_path(value: str | None, pointer_path: Path, default: Path) -> Path:
    if not value:
        return default.resolve()

    candidate = Path(value)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        if resolved.exists():
            return resolved

    project_root = _project_root(pointer_path)
    foreign_candidates = (PureWindowsPath(value), PurePosixPath(value))
    for foreign_candidate in foreign_candidates:
        if not foreign_candidate.is_absolute():
            continue
        parts = list(foreign_candidate.parts)
        data_index = next(
            (index for index, part in enumerate(parts) if part.casefold() == "data"),
            None,
        )
        if data_index is not None:
            return project_root.joinpath(*parts[data_index:]).resolve()

    if candidate.is_absolute():
        return candidate.resolve()

    return (project_root / candidate).resolve()


def write_active_db(payload: dict[str, Any], path: Path = ACTIVE_DB_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    portable = dict(payload)
    for key in ("active_db_dir", "manifest"):
        portable[key] = _portable_pointer_value(portable.get(key), path)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(portable, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def active_db_dir(path: Path = ACTIVE_DB_PATH) -> Path:
    payload = read_active_db(path)
    return resolve_pointer_path(payload.get("active_db_dir"), path, DB_DIR)


def read_active_manifest(
    path: Path = ACTIVE_DB_PATH,
    fallback_manifest_path: Path = MANIFEST_PATH,
) -> dict[str, Any]:
    if not path.exists():
        return read_manifest(fallback_manifest_path) or {}
    payload = read_active_db(path)
    manifest_path = resolve_pointer_path(payload.get("manifest"), path, fallback_manifest_path)
    return read_manifest(manifest_path) or {}
