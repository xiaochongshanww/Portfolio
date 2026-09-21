from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote

from src.pipeline.metadata import VALID_ASSET_ACCESS_SCOPES, load_metadata_overrides
from src.pipeline.source_catalog import SourceCatalogStore

from .config import settings

DEFAULT_ASSET_ACCESS = "authenticated"


@lru_cache(maxsize=8)
def _cached_document_records(path: str, modified_ns: int, size: int) -> tuple[dict, ...]:
    del modified_ns, size
    return tuple(load_metadata_overrides(Path(path)).values())


def _document_records() -> list[dict] | None:
    try:
        path = settings.source_metadata_path.resolve()
        stat = path.stat()
        return list(_cached_document_records(str(path), stat.st_mtime_ns, stat.st_size))
    except (OSError, ValueError):
        return None


def _catalog_document_records() -> list[dict]:
    data_dir = getattr(settings, "data_dir", None)
    if not data_dir:
        return []
    try:
        catalog = SourceCatalogStore(Path(data_dir)).read()
    except (OSError, ValueError, TypeError):
        return []

    records = []
    for source in catalog.get("sources", []):
        if not source.get("active_asset_version_id"):
            continue
        metadata = source.get("active_metadata") or source.get("metadata")
        if isinstance(metadata, dict) and metadata.get("source_file"):
            records.append(dict(metadata))
    return records


def _all_document_records() -> list[dict] | None:
    records = _document_records()
    if records is None:
        return None
    by_source = {
        Path(str(record.get("source_file") or "")).name.casefold(): record for record in records
    }
    for record in _catalog_document_records():
        source_file = Path(str(record.get("source_file") or "")).name.casefold()
        if source_file:
            by_source[source_file] = record
    return list(by_source.values())


def _record_for_source(source: str) -> dict | None:
    decoded = Path(unquote(source)).name.casefold()
    decoded_stem = Path(decoded).stem
    records = _all_document_records()
    if records is None:
        raise RuntimeError("来源访问策略不可用")
    for record in records:
        source_file = Path(str(record.get("source_file") or "")).name.casefold()
        if (
            decoded in {source_file, Path(source_file).stem}
            or decoded_stem == Path(source_file).stem
        ):
            return record
    return None


def _record_for_image(filename: str) -> dict | None:
    image_stem = Path(unquote(filename)).name.casefold()
    matches: list[tuple[int, dict]] = []
    records = _all_document_records()
    if records is None:
        raise RuntimeError("来源访问策略不可用")
    for record in records:
        source_stem = Path(str(record.get("source_file") or "")).stem.casefold()
        if source_stem and source_stem in image_stem:
            matches.append((len(source_stem), record))
    return max(matches, key=lambda item: item[0])[1] if matches else None


def asset_access_scope(kind: str, identifier: str) -> str:
    try:
        if kind == "image":
            record = _record_for_image(identifier)
            field = "image_access"
        elif kind == "page_image":
            record = _record_for_source(identifier)
            field = "page_image_access"
        else:
            raise ValueError(f"不支持的资源类型: {kind}")
    except RuntimeError:
        return "disabled"

    value = str((record or {}).get(field) or DEFAULT_ASSET_ACCESS)
    return value if value in VALID_ASSET_ACCESS_SCOPES else "disabled"


def asset_scope_from_path(path: str) -> str | None:
    decoded = unquote(path)
    if decoded.startswith("/images/"):
        return asset_access_scope("image", decoded.removeprefix("/images/"))
    if decoded.startswith("/page-images/"):
        remainder = decoded.removeprefix("/page-images/")
        doc, separator, page = remainder.rpartition("/")
        if separator and page.isdigit():
            return asset_access_scope("page_image", doc)
        return "disabled"
    return None
