from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class ParserUnavailableError(RuntimeError):
    pass


@dataclass
class ParseResult:
    elements: list[dict[str, Any]]
    artifact_dir: Path | None = None
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    media_files: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class PdfParser(Protocol):
    name: str

    def parse(self, pdf_path: Path, image_dir: Path) -> ParseResult:
        ...
