import json
import os
import shutil
import subprocess
import re
from pathlib import Path
from typing import Any

from src.pipeline.artifacts import find_artifact, require_artifacts, scan_mineru_artifacts, write_artifact_index

from .base import ParseResult, ParserUnavailableError


MINERU_TEXT_TYPES = {"text", "equation"}
MINERU_MEDIA_TYPES = {"image", "table"}


def doc_id_for_pdf(pdf_path: Path) -> str:
    safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "_", pdf_path.stem).strip("._")
    return safe or "document"


def _find_content_list(output_dir: Path, pdf_stem: str) -> Path | None:
    candidates = sorted(output_dir.rglob("*content_list*.json"))
    if not candidates:
        return None
    preferred = [path for path in candidates if pdf_stem in path.name or pdf_stem in str(path.parent)]
    return (preferred or candidates)[0]


def _find_markdown(output_dir: Path, pdf_stem: str) -> Path | None:
    candidates = sorted(output_dir.rglob("*.md"))
    if not candidates:
        return None
    preferred = [path for path in candidates if path.name == f"{pdf_stem}.md" or path.name == "full.md"]
    return (preferred or candidates)[0]


def _copy_mineru_image(item: dict[str, Any], artifact_dir: Path, image_dir: Path, pdf_stem: str, index: int) -> tuple[str, str]:
    img_path = str(item.get("img_path") or "")
    if not img_path:
        return "", ""
    source = (artifact_dir / img_path).resolve()
    if not source.exists():
        matches = list(artifact_dir.rglob(Path(img_path).name))
        if not matches:
            return "", img_path
        source = matches[0]
    suffix = source.suffix or ".jpg"
    target_name = f"{pdf_stem}_mineru_{index:04d}{suffix}"
    image_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, image_dir / target_name)
    return target_name, img_path


def mineru_item_to_element(item: dict[str, Any], artifact_dir: Path, image_dir: Path, pdf_stem: str, index: int) -> dict[str, Any] | None:
    item_type = str(item.get("type") or "").lower()
    page = int(item.get("page_idx", 0)) + 1 if str(item.get("page_idx", "")).lstrip("-").isdigit() else 0
    text_level = item.get("text_level")
    image, original_image = _copy_mineru_image(item, artifact_dir, image_dir, pdf_stem, index)

    if item_type in MINERU_TEXT_TYPES:
        text = str(item.get("text") or "").strip()
        if not text:
            return None
        element_type = "Title" if isinstance(text_level, int) and text_level <= 2 else "Text"
        return {
            "type": element_type,
            "text": text,
            "page": page,
            "img": image,
            "original_img_path": original_image,
            "chunk_type": "formula" if item_type == "equation" else "text",
            "bbox": item.get("bbox", []),
            "parser": "mineru",
        }

    if item_type in MINERU_MEDIA_TYPES:
        caption_key = "table_caption" if item_type == "table" else "image_caption"
        footnote_key = "table_footnote" if item_type == "table" else "image_footnote"
        parts = [str(part).strip() for part in item.get(caption_key, []) if str(part).strip()]
        parts.extend(str(part).strip() for part in item.get(footnote_key, []) if str(part).strip())
        body = str(item.get("table_body") or item.get("text") or "").strip()
        if body:
            parts.append(body)
        text = "\n".join(parts).strip() or f"[{item_type}] {image}"
        return {
            "type": "Title" if item_type == "table" else "Text",
            "text": text,
            "page": page,
            "img": image,
            "original_img_path": original_image,
            "chunk_type": "table" if item_type == "table" else "figure",
            "bbox": item.get("bbox", []),
            "html": item.get("table_body", "") if item_type == "table" else "",
            "parser": "mineru",
        }

    return None


def content_list_to_elements(content_list: list[dict[str, Any]], artifact_dir: Path, image_dir: Path, pdf_stem: str) -> list[dict[str, Any]]:
    elements = []
    for index, item in enumerate(content_list):
        element = mineru_item_to_element(item, artifact_dir, image_dir, pdf_stem, index)
        if element:
            elements.append(element)
    return elements


class MineruParser:
    name = "mineru"

    def __init__(self, output_dir: Path, binary: str | None = None, extra_args: list[str] | None = None):
        self.output_dir = output_dir
        self.binary = binary or os.environ.get("MINERU_BIN", "mineru")
        self.extra_args = extra_args or os.environ.get("MINERU_ARGS", "").split()

    def parse(self, pdf_path: Path, image_dir: Path) -> ParseResult:
        if shutil.which(self.binary) is None:
            raise ParserUnavailableError(
                f"未找到 MinerU CLI：{self.binary}。请先安装 MinerU，或使用 --parser-backend pymupdf。"
            )

        doc_dir = self.output_dir / doc_id_for_pdf(pdf_path)
        raw_dir = doc_dir / "raw"
        if doc_dir.exists():
            shutil.rmtree(doc_dir)
        raw_dir.mkdir(parents=True, exist_ok=True)

        command = [self.binary, "-p", str(pdf_path), "-o", str(raw_dir), *self.extra_args]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(f"MinerU 解析失败: {detail}")

        version = subprocess.run([self.binary, "--version"], text=True, capture_output=True, check=False)
        cli_version = (version.stdout or version.stderr).strip() if version.returncode == 0 else ""
        artifacts = scan_mineru_artifacts(doc_dir)
        require_artifacts(artifacts)
        write_artifact_index(
            doc_dir / "artifacts.json",
            pdf_path.name,
            artifacts,
            {"command": command, "mineru_version": cli_version},
        )

        content_list_path = find_artifact(artifacts, "content_list")
        markdown_path = find_artifact(artifacts, "markdown")
        if not content_list_path:
            raise RuntimeError(f"MinerU 未生成 content_list JSON：{pdf_path.name}")
        content_list = json.loads(content_list_path.read_text(encoding="utf-8"))
        artifact_dir = content_list_path.parent
        elements = content_list_to_elements(content_list, artifact_dir, image_dir, pdf_path.stem)
        return ParseResult(
            elements=elements,
            artifact_dir=doc_dir,
            artifacts=artifacts,
            media_files=sorted(path.name for path in image_dir.glob(f"{pdf_path.stem}_mineru_*") if path.is_file()),
            metadata={
                "parser_backend": self.name,
                "mineru_output_dir": str(doc_dir),
                "mineru_raw_dir": str(raw_dir),
                "mineru_content_list": str(content_list_path),
                "mineru_markdown": str(markdown_path) if markdown_path else "",
                "mineru_artifact_index": str(doc_dir / "artifacts.json"),
                "mineru_version": cli_version,
                "mineru_command": command,
            },
        )
