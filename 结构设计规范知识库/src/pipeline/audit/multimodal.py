import base64
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from src.app.core.config import settings
from src.pipeline.paths import AUDIT_DIR, CORRECTIONS_DIR, PROCESSED_DIR, RAW_DIR


def parse_pages(value: str) -> list[int]:
    pages: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            if start.strip().isdigit() and end.strip().isdigit():
                pages.update(range(int(start), int(end) + 1))
            continue
        if part.isdigit():
            pages.add(int(part))
    return sorted(page for page in pages if page > 0)


def find_source_pdf(doc: str, source_dir: Path = RAW_DIR) -> Path | None:
    candidates = sorted(path for path in source_dir.glob("*.pdf") if path.is_file())
    for pdf in candidates:
        if doc in {pdf.name, pdf.stem}:
            return pdf
    for pdf in candidates:
        if doc in pdf.name or doc in pdf.stem:
            return pdf
    return None


def load_processed_elements(source_file: str, processed_dir: Path = PROCESSED_DIR) -> list[dict[str, Any]]:
    path = processed_dir / f"{Path(source_file).stem}.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("elements", payload if isinstance(payload, list) else [])


def render_pdf_pages(pdf_path: Path, pages: list[int], out_dir: Path) -> dict[int, Path]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("缺少 PyMuPDF，无法为 AI 校对渲染 PDF 页图") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    rendered: dict[int, Path] = {}
    doc = fitz.open(pdf_path)
    try:
        for page in pages:
            if page < 1 or page > len(doc):
                continue
            page_obj = doc[page - 1]
            target = out_dir / f"{pdf_path.stem}_p{page:04d}.png"
            pix = page_obj.get_pixmap(matrix=fitz.Matrix(2, 2))
            pix.save(target)
            rendered[page] = target
    finally:
        doc.close()
    return rendered


def _data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def _review_prompt(source_file: str, page: int, elements: list[dict[str, Any]]) -> str:
    compact_elements = [
        {
            "element_index": element.get("_element_index"),
            "type": element.get("type"),
            "chunk_type": element.get("chunk_type", "text"),
            "text": str(element.get("text", ""))[:2500],
            "img": element.get("img", ""),
        }
        for element in elements
    ]
    return (
        "你是结构设计规范 PDF 解析校对助手。请对照页面截图和 MinerU elements，"
        "只找出有明确证据的解析错误，不要根据常识补全文字。"
        "表格数值、公式、强制性条文只能给出 needs_review 候选。"
        "输出严格 JSON，不要 Markdown。JSON 结构："
        "{\"candidates\":[{\"id\":\"...\",\"source_file\":\"...\",\"page\":1,"
        "\"issue_type\":\"ocr_error|table_misaligned|formula_error|title_level|split_merge|image_mapping|other\","
        "\"severity\":\"low|medium|high\",\"confidence\":0.0,"
        "\"target\":{\"element_index\":0,\"field\":\"text\"},"
        "\"suggested_patch\":{\"action\":\"replace_text|set_field|delete_element|insert_after|merge_next\",\"value\":\"...\"},"
        "\"review_status\":\"pending\",\"evidence\":{\"reason\":\"...\"}}]}"
        f"\nsource_file={source_file}\npage={page}\nelements="
        f"{json.dumps(compact_elements, ensure_ascii=False)}"
    )


def call_mimo_review(source_file: str, page: int, image_path: Path, elements: list[dict[str, Any]]) -> dict[str, Any]:
    if not settings.mimo_api_key:
        return {
            "source_file": source_file,
            "page": page,
            "status": "not_configured",
            "candidates": [],
            "message": "MIMO_API_KEY 未设置，未调用多模态模型。",
        }

    import httpx

    payload = {
        "model": os.environ.get("AI_REVIEW_MODEL", settings.mimo_model),
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _review_prompt(source_file, page, elements)},
                    {"type": "image_url", "image_url": {"url": _data_url(image_path)}},
                ],
            }
        ],
        "temperature": 0,
        "stream": False,
    }
    response = httpx.post(
        f"{settings.mimo_base_url}/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {settings.mimo_api_key}", "Content-Type": "application/json"},
        timeout=settings.llm_timeout_seconds,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    parsed = _extract_json_object(content)
    return {"source_file": source_file, "page": page, "status": "ok", "candidates": parsed.get("candidates", [])}


def write_review_report(report: dict[str, Any], out_dir: Path = AUDIT_DIR) -> Path:
    report_dir = out_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{Path(report['source_file']).stem}_ai_review.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_candidate_file(source_file: str, candidates: list[dict[str, Any]], corrections_dir: Path = CORRECTIONS_DIR) -> Path:
    candidates_dir = corrections_dir / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    path = candidates_dir / f"{Path(source_file).stem}.json"
    payload = {"source_file": source_file, "generated_at": int(time.time()), "corrections": candidates}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run_multimodal_review(
    doc: str,
    pages: str = "",
    *,
    source_dir: Path = RAW_DIR,
    processed_dir: Path = PROCESSED_DIR,
    out_dir: Path = AUDIT_DIR,
) -> dict[str, Any]:
    pdf_path = find_source_pdf(doc, source_dir)
    if not pdf_path:
        return {"source_file": doc, "pages": pages, "status": "not_found", "candidates": [], "message": "未找到匹配 PDF"}

    requested_pages = parse_pages(pages)
    if not requested_pages:
        requested_pages = [1]

    elements = load_processed_elements(pdf_path.name, processed_dir)
    indexed_elements = [{**element, "_element_index": index} for index, element in enumerate(elements)]
    try:
        rendered = render_pdf_pages(pdf_path, requested_pages, out_dir / "page_images")
    except RuntimeError as exc:
        report = {
            "source_file": pdf_path.name,
            "pages": pages,
            "status": "dependency_missing",
            "message": str(exc),
            "candidate_count": 0,
            "candidate_path": "",
            "pages_reviewed": [],
            "candidates": [],
        }
        report_path = write_review_report(report, out_dir)
        return {**report, "report_path": str(report_path)}

    page_reports = []
    all_candidates: list[dict[str, Any]] = []
    for page in requested_pages:
        page_elements = [element for element in indexed_elements if int(element.get("page") or 0) == page]
        image_path = rendered.get(page)
        if not image_path:
            page_reports.append({"source_file": pdf_path.name, "page": page, "status": "page_not_rendered", "candidates": []})
            continue
        page_report = call_mimo_review(pdf_path.name, page, image_path, page_elements)
        page_reports.append(page_report)
        for candidate in page_report.get("candidates", []):
            candidate.setdefault("source_file", pdf_path.name)
            candidate.setdefault("page", page)
            candidate.setdefault("review_status", "pending")
            all_candidates.append(candidate)

    candidate_path = write_candidate_file(pdf_path.name, all_candidates) if all_candidates else ""
    status = "ok" if any(report.get("status") == "ok" for report in page_reports) else page_reports[0].get("status", "not_configured")
    report = {
        "source_file": pdf_path.name,
        "pages": pages,
        "status": status,
        "model": os.environ.get("AI_REVIEW_MODEL", settings.mimo_model) if settings.mimo_api_key else "",
        "candidate_count": len(all_candidates),
        "candidate_path": str(candidate_path),
        "pages_reviewed": page_reports,
        "candidates": all_candidates,
    }
    report_path = write_review_report(report, out_dir)
    return {**report, "report_path": str(report_path)}
