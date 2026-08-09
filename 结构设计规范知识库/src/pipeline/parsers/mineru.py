import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.pipeline.artifacts import (
    find_artifact,
    require_artifacts,
    scan_mineru_artifacts,
    write_artifact_index,
)

from .base import ParseResult, ParserUnavailableError

MINERU_TEXT_TYPES = {"text", "equation"}
MINERU_MEDIA_TYPES = {"image", "table"}
DEFAULT_MINERU_BINARY = "magic-pdf"
DEFAULT_MINERU_COMPATIBILITY_POLICY = "strict"
MINERU_COMPATIBILITY_POLICIES = {"strict", "allow-unverified"}
VERIFIED_MINERU_IMPLEMENTATIONS = {("magic-pdf", "1.3.12")}
MINERU_VERSION_TIMEOUT_SECONDS = 10
MINERU_VERSION_PATTERN = re.compile(
    r"\b(?P<implementation>magic-pdf|mineru)\b\s*,?\s*(?:version\s*)?v?"
    r"(?P<version>\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)",
    re.IGNORECASE,
)


class ParserCompatibilityError(ParserUnavailableError):
    pass


@dataclass(frozen=True)
class MineruCliProbe:
    binary: str
    resolved_binary: str
    implementation: str
    version: str
    raw_version: str
    policy: str
    compatibility: str
    verified: bool
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _compatibility_policy(value: str | None = None) -> str:
    policy = (
        (
            value
            or os.environ.get("MINERU_COMPATIBILITY_POLICY")
            or DEFAULT_MINERU_COMPATIBILITY_POLICY
        )
        .strip()
        .lower()
    )
    if policy not in MINERU_COMPATIBILITY_POLICIES:
        choices = ", ".join(sorted(MINERU_COMPATIBILITY_POLICIES))
        raise ParserCompatibilityError(f"MINERU_COMPATIBILITY_POLICY 必须是以下值之一: {choices}")
    return policy


def probe_mineru_cli(
    binary: str | None = None,
    *,
    policy: str | None = None,
    timeout_seconds: int = MINERU_VERSION_TIMEOUT_SECONDS,
) -> MineruCliProbe:
    requested_binary = binary or os.environ.get("MINERU_BIN") or DEFAULT_MINERU_BINARY
    compatibility_policy = _compatibility_policy(policy)
    resolved_binary = shutil.which(requested_binary)
    if resolved_binary is None:
        raise ParserUnavailableError(
            f"未找到 PDF 解析 CLI：{requested_binary}。"
            "请安装 requirements-parser.txt，或将 MINERU_BIN 指向 magic-pdf 1.3.12。"
        )

    try:
        completed = subprocess.run(
            [resolved_binary, "--version"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise ParserUnavailableError(
            f"PDF 解析 CLI 版本探测超时（{timeout_seconds} 秒）：{requested_binary}"
        ) from exc
    except OSError as exc:
        raise ParserUnavailableError(f"无法执行 PDF 解析 CLI：{requested_binary}：{exc}") from exc

    raw_version = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part and part.strip()
    )[:2000]
    if completed.returncode != 0:
        detail = raw_version or f"exit code {completed.returncode}"
        raise ParserUnavailableError(f"PDF 解析 CLI 版本探测失败：{detail}")

    matched = MINERU_VERSION_PATTERN.search(raw_version)
    if matched is None:
        rendered = raw_version or "<empty>"
        raise ParserCompatibilityError(f"无法识别 PDF 解析 CLI 的实现和版本：{rendered}")

    implementation = matched.group("implementation").lower()
    version = matched.group("version")
    verified = (implementation, version) in VERIFIED_MINERU_IMPLEMENTATIONS
    if verified:
        return MineruCliProbe(
            binary=requested_binary,
            resolved_binary=str(Path(resolved_binary).resolve()),
            implementation=implementation,
            version=version,
            raw_version=raw_version,
            policy=compatibility_policy,
            compatibility="verified",
            verified=True,
        )

    supported = ", ".join(
        f"{name} {item_version}" for name, item_version in sorted(VERIFIED_MINERU_IMPLEMENTATIONS)
    )
    warning = (
        f"检测到未验证的 PDF 解析器 {implementation} {version}；当前兼容矩阵仅包含 {supported}。"
    )
    if compatibility_policy == "strict":
        raise ParserCompatibilityError(
            f"{warning} 如需隔离迁移试验，显式设置 "
            "MINERU_COMPATIBILITY_POLICY=allow-unverified；不得将试验结果视为生产兼容。"
        )
    return MineruCliProbe(
        binary=requested_binary,
        resolved_binary=str(Path(resolved_binary).resolve()),
        implementation=implementation,
        version=version,
        raw_version=raw_version,
        policy=compatibility_policy,
        compatibility="unverified",
        verified=False,
        warning=warning,
    )


def doc_id_for_pdf(pdf_path: Path) -> str:
    safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "_", pdf_path.stem).strip("._")
    return safe or "document"


def _find_content_list(output_dir: Path, pdf_stem: str) -> Path | None:
    candidates = sorted(output_dir.rglob("*content_list*.json"))
    if not candidates:
        return None
    preferred = [
        path for path in candidates if pdf_stem in path.name or pdf_stem in str(path.parent)
    ]
    return (preferred or candidates)[0]


def _find_markdown(output_dir: Path, pdf_stem: str) -> Path | None:
    candidates = sorted(output_dir.rglob("*.md"))
    if not candidates:
        return None
    preferred = [
        path for path in candidates if path.name == f"{pdf_stem}.md" or path.name == "full.md"
    ]
    return (preferred or candidates)[0]


def _copy_mineru_image(
    item: dict[str, Any], artifact_dir: Path, image_dir: Path, pdf_stem: str, index: int
) -> tuple[str, str]:
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


def mineru_item_to_element(
    item: dict[str, Any], artifact_dir: Path, image_dir: Path, pdf_stem: str, index: int
) -> dict[str, Any] | None:
    item_type = str(item.get("type") or "").lower()
    page = (
        int(item.get("page_idx", 0)) + 1
        if str(item.get("page_idx", "")).lstrip("-").isdigit()
        else 0
    )
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


def content_list_to_elements(
    content_list: list[dict[str, Any]], artifact_dir: Path, image_dir: Path, pdf_stem: str
) -> list[dict[str, Any]]:
    elements = []
    for index, item in enumerate(content_list):
        element = mineru_item_to_element(item, artifact_dir, image_dir, pdf_stem, index)
        if element:
            elements.append(element)
    return elements


class MineruParser:
    name = "mineru"

    def __init__(
        self,
        output_dir: Path,
        binary: str | None = None,
        extra_args: list[str] | None = None,
        compatibility_policy: str | None = None,
    ):
        self.output_dir = output_dir
        self.binary = binary or os.environ.get("MINERU_BIN") or DEFAULT_MINERU_BINARY
        self.extra_args = (
            extra_args if extra_args is not None else os.environ.get("MINERU_ARGS", "").split()
        )
        self.compatibility_policy = compatibility_policy
        self._cli_probe: MineruCliProbe | None = None

    def probe(self) -> MineruCliProbe:
        if self._cli_probe is None:
            self._cli_probe = probe_mineru_cli(self.binary, policy=self.compatibility_policy)
        return self._cli_probe

    def parse(self, pdf_path: Path, image_dir: Path) -> ParseResult:
        cli_probe = self.probe()

        doc_dir = self.output_dir / doc_id_for_pdf(pdf_path)
        raw_dir = doc_dir / "raw"
        if doc_dir.exists():
            shutil.rmtree(doc_dir)
        raw_dir.mkdir(parents=True, exist_ok=True)

        command = [
            cli_probe.resolved_binary,
            "-p",
            str(pdf_path),
            "-o",
            str(raw_dir),
            *self.extra_args,
        ]
        completed = subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(f"MinerU 解析失败: {detail}")

        artifacts = scan_mineru_artifacts(doc_dir)
        require_artifacts(artifacts)
        write_artifact_index(
            doc_dir / "artifacts.json",
            pdf_path.name,
            artifacts,
            {
                "command": command,
                "mineru_version": cli_probe.raw_version,
                "parser_cli": cli_probe.to_dict(),
            },
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
            media_files=sorted(
                path.name for path in image_dir.glob(f"{pdf_path.stem}_mineru_*") if path.is_file()
            ),
            metadata={
                "parser_backend": self.name,
                "mineru_output_dir": str(doc_dir),
                "mineru_raw_dir": str(raw_dir),
                "mineru_content_list": str(content_list_path),
                "mineru_markdown": str(markdown_path) if markdown_path else "",
                "mineru_artifact_index": str(doc_dir / "artifacts.json"),
                "mineru_version": cli_probe.raw_version,
                "mineru_command": command,
                "parser_cli": cli_probe.to_dict(),
            },
        )
