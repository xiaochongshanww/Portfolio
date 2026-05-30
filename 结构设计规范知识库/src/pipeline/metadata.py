import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SPEC_CODE_RE = re.compile(r"^(?P<prefix>[A-Z]{1,4})\s*(?P<number>\d{4,6}(?:-\d{4})?)")


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


def load_metadata_overrides(metadata_path: Path) -> dict[str, dict[str, Any]]:
    if not metadata_path.exists():
        return {}

    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "documents" in data:
        documents = data["documents"]
    elif isinstance(data, list):
        documents = data
    elif isinstance(data, dict):
        documents = list(data.values())
    else:
        documents = []

    overrides: dict[str, dict[str, Any]] = {}
    for item in documents:
        if not isinstance(item, dict) or not item.get("source_file"):
            continue
        overrides[item["source_file"]] = item
    return overrides


def apply_metadata_override(base: SpecMetadata, override: dict[str, Any] | None) -> SpecMetadata:
    if not override:
        return base

    data = base.to_dict()
    for key in ["code", "name", "version", "effective_date", "status", "aliases", "notes"]:
        if key in override and override[key] not in (None, ""):
            data[key] = override[key]

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
