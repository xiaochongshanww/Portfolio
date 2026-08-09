import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SPEC_CODE_RE = re.compile(r"^(?P<prefix>[A-Z]{1,4})\s*(?P<number>\d{4,6}(?:-\d{4})?)")
VALID_ASSET_ACCESS_SCOPES = {"public", "authenticated", "disabled"}


@dataclass(frozen=True)
class SpecMetadata:
    source_file: str
    code: str
    name: str
    version: str = ""
    effective_date: str = ""
    status: str = "active"
    aliases: list[str] = field(default_factory=list)
    notes: str = ""
    metadata_status: str = "complete"
    image_access: str = "authenticated"
    page_image_access: str = "authenticated"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "code": self.code,
            "name": self.name,
            "version": self.version,
            "effective_date": self.effective_date,
            "status": self.status,
            "aliases": self.aliases,
            "notes": self.notes,
            "metadata_status": self.metadata_status,
            "image_access": self.image_access,
            "page_image_access": self.page_image_access,
        }


def parse_spec_filename(filename: str) -> SpecMetadata:
    path = Path(filename)
    stem = path.stem
    parts = [part.strip() for part in stem.split("_")]
    code_part = parts[0] if parts else ""
    name = parts[1].strip(" .") if len(parts) > 1 else ""
    version = parts[2].strip() if len(parts) > 2 else ""

    match = SPEC_CODE_RE.match(code_part)
    code = ""
    matched_standard_code = bool(match)
    if match:
        code = f"{match.group('prefix')} {match.group('number')}"
    elif code_part:
        code = code_part

    if not name:
        name = stem

    metadata_status = "complete" if matched_standard_code and name else "partial"
    return SpecMetadata(
        source_file=path.name,
        code=code,
        name=name,
        version=version,
        metadata_status=metadata_status,
    )


def parse_metadata_overrides(data: Any) -> dict[str, dict[str, Any]]:
    if isinstance(data, dict) and "documents" in data:
        documents = data["documents"]
    elif isinstance(data, list):
        documents = data
    elif isinstance(data, dict):
        documents = list(data.values())
    else:
        raise ValueError("来源元数据必须是 documents 数组、数组或对象")
    if not isinstance(documents, list):
        raise ValueError("来源元数据 documents 必须是数组")

    overrides: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(documents):
        if not isinstance(item, dict):
            raise ValueError(f"来源元数据 documents[{index}] 必须是对象")
        source_file = str(item.get("source_file") or "").strip()
        if not source_file:
            raise ValueError(f"来源元数据 documents[{index}] 缺少 source_file")
        if source_file in overrides:
            raise ValueError(f"来源元数据包含重复 source_file: {source_file}")
        for key in ("image_access", "page_image_access"):
            if key in item and item[key] not in VALID_ASSET_ACCESS_SCOPES:
                allowed = ", ".join(sorted(VALID_ASSET_ACCESS_SCOPES))
                raise ValueError(f"{source_file} 的 {key} 必须是 {allowed} 之一")
        overrides[source_file] = item
    return overrides


def load_metadata_overrides(metadata_path: Path) -> dict[str, dict[str, Any]]:
    if not metadata_path.exists():
        return {}
    return parse_metadata_overrides(json.loads(metadata_path.read_text(encoding="utf-8")))


def apply_metadata_override(base: SpecMetadata, override: dict[str, Any] | None) -> SpecMetadata:
    if not override:
        return base

    data = base.to_dict()
    for key in [
        "code",
        "name",
        "version",
        "effective_date",
        "status",
        "aliases",
        "notes",
        "image_access",
        "page_image_access",
    ]:
        if key in override and override[key] not in (None, ""):
            data[key] = override[key]

    for key in ("image_access", "page_image_access"):
        if data[key] not in VALID_ASSET_ACCESS_SCOPES:
            allowed = ", ".join(sorted(VALID_ASSET_ACCESS_SCOPES))
            raise ValueError(f"{base.source_file} 的 {key} 必须是 {allowed} 之一")

    data["metadata_status"] = "complete" if data.get("code") and data.get("name") else "partial"
    if not isinstance(data.get("aliases"), list):
        data["aliases"] = [str(data["aliases"])]
    return SpecMetadata(**data)


def load_spec_metadata(pdf_files: list[Path], metadata_path: Path) -> dict[str, SpecMetadata]:
    overrides = load_metadata_overrides(metadata_path)
    metadata: dict[str, SpecMetadata] = {}
    for pdf in pdf_files:
        parsed = parse_spec_filename(pdf.name)
        metadata[pdf.name] = apply_metadata_override(parsed, overrides.get(pdf.name))
    return metadata
