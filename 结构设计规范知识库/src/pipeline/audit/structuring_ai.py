import json
import os
import re
import time
from pathlib import Path
from typing import Any

from src.app.core.config import settings
from src.pipeline.paths import AUDIT_DIR, MANUAL_STRUCTURING_DIR, RAW_DIR

from .manual_structuring import read_manual_structuring_draft
from .multimodal import _data_url, _extract_json_object, find_source_pdf, render_pdf_pages


SUGGESTION_DIRNAME = "suggestions"
UNSAFE_FILENAME_RE = re.compile(r'[<>:"/\\|?*]+')


def _safe_filename(value: str) -> str:
    return UNSAFE_FILENAME_RE.sub("_", value).strip(" .") or "suggestion"


def _suggestion_identity(
    doc: str,
    item_id: str,
    out_dir: Path,
) -> tuple[str, Path, dict[str, Any]]:
    draft = read_manual_structuring_draft(doc, item_id, out_dir)
    owner_id = str(draft.get("review_context", {}).get("manual_item_id") or item_id)
    path = out_dir / SUGGESTION_DIRNAME / _safe_filename(doc) / f"{_safe_filename(owner_id)}.json"
    return owner_id, path, draft


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _prompt(draft: dict[str, Any]) -> str:
    review = draft.get("review_context", {})
    elements = [
        {
            "page": item.get("page"),
            "element_index": item.get("element_index"),
            "title": item.get("title", ""),
            "current_text": str(item.get("current_text", ""))[:8000],
        }
        for item in review.get("elements", [])
    ]
    schema = {
        "source": draft.get("source", {}),
        "columns": draft.get("columns", []),
        "current_rows": draft.get("rows", []),
        "table_aliases": draft.get("table_aliases", []),
        "notes": draft.get("notes", []),
    }
    return (
        "你是结构设计规范复杂表格的数据录入助手。请严格对照所有页面截图和 OCR/HTML 源码，"
        "生成供人工审核的结构化 JSON 建议。禁止根据工程常识、其他规范或上下文猜测截图中不可见的数据；"
        "无法确认的单元格填 null，并在 assumptions 中说明。不允许省略可见的表格行、表头层级、单位、"
        "适用条件和表注。跨页续表必须合并为一张表。数值使用 JSON number，别名和变量使用字符串数组。"
        "只输出 JSON，不要 Markdown。输出结构必须是："
        '{"columns":[{"key":"...","label":"...","unit":"","value_type":"text|number|list|json"}],'
        '"rows":[{"字段key":"值"}],"table_aliases":["..."],"notes":["..."],'
        '"confidence":0.0,"assumptions":["..."]}。'
        "可以改进 columns，但不得修改规范编号、表号、表名、来源文件或页码。"
        f"\n当前结构模式={json.dumps(schema, ensure_ascii=False)}"
        f"\n跨页解析元素={json.dumps(elements, ensure_ascii=False)}"
    )


def normalize_structuring_suggestion(
    draft: dict[str, Any],
    parsed: dict[str, Any],
) -> dict[str, Any]:
    raw_columns = parsed.get("columns", [])
    columns: list[dict[str, Any]] = []
    keys: set[str] = set()
    for item in raw_columns if isinstance(raw_columns, list) else []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        label = str(item.get("label") or "").strip()
        if not key or not label or key in keys:
            continue
        value_type = str(item.get("value_type") or "text")
        if value_type not in {"text", "number", "list", "json"}:
            value_type = "text"
        column = {"key": key, "label": label, "value_type": value_type}
        unit = str(item.get("unit") or "").strip()
        if unit:
            column["unit"] = unit
        columns.append(column)
        keys.add(key)
    if not columns:
        columns = [dict(column) for column in draft.get("columns", []) if isinstance(column, dict)]
        keys = {str(column.get("key") or "") for column in columns}

    types = {str(column.get("key")): str(column.get("value_type") or "text") for column in columns}
    rows: list[dict[str, Any]] = []
    raw_rows = parsed.get("rows", [])
    for raw_row in raw_rows[:500] if isinstance(raw_rows, list) else []:
        if not isinstance(raw_row, dict):
            continue
        row: dict[str, Any] = {}
        for key in keys:
            value = raw_row.get(key)
            value_type = types.get(key, "text")
            if value_type == "number" and isinstance(value, str):
                try:
                    value = float(value)
                    if value.is_integer() and "." not in str(raw_row.get(key)):
                        value = int(value)
                except ValueError:
                    pass
            elif value_type == "list":
                if isinstance(value, str):
                    value = [part.strip() for part in re.split(r"[,，;\n]", value) if part.strip()]
                elif value is None:
                    value = []
            row[key] = value
        if any(value not in (None, "", []) for value in row.values()):
            rows.append(row)

    def string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))

    try:
        model_confidence = float(parsed.get("confidence", 0))
    except (TypeError, ValueError):
        model_confidence = 0.0
    model_confidence = max(0.0, min(model_confidence, 1.0))
    proposal = {
        "source": draft.get("source", {}),
        "columns": columns,
        "rows": rows,
        "table_aliases": string_list(parsed.get("table_aliases")),
        "notes": string_list(parsed.get("notes")),
        "confidence": model_confidence,
        "model_confidence": model_confidence,
        "assumptions": string_list(parsed.get("assumptions")),
    }
    _apply_quality_gate(draft, proposal)
    return proposal


def _apply_quality_gate(draft: dict[str, Any], proposal: dict[str, Any]) -> bool:
    original = json.dumps(proposal, ensure_ascii=False, sort_keys=True)
    assumptions = [str(item) for item in proposal.get("assumptions", []) if str(item)]
    rows = proposal.get("rows", [])
    null_count = sum(value is None for row in rows if isinstance(row, dict) for value in row.values())
    evidence = str(draft.get("review_context", {}).get("current_text") or "")
    numeric_values = {
        str(value)
        for row in rows
        if isinstance(row, dict)
        for value in row.values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    missing_numbers = sorted(value for value in numeric_values if value not in evidence)
    warnings: list[str] = []
    blocking_errors: list[str] = []
    columns = proposal.get("columns", [])
    if not columns:
        blocking_errors.append("建议没有列定义")
    if not rows:
        blocking_errors.append("建议没有可用行数据")
    column_types = {
        str(column.get("key")): str(column.get("value_type") or "text")
        for column in columns
        if isinstance(column, dict) and column.get("key")
    }
    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            blocking_errors.append(f"第 {row_index + 1} 行不是对象")
            continue
        for key, value in row.items():
            value_type = column_types.get(key)
            if value is None:
                continue
            if value_type == "number" and (
                not isinstance(value, (int, float)) or isinstance(value, bool)
            ):
                blocking_errors.append(f"第 {row_index + 1} 行 {key} 不是数字")
            if value_type == "list" and not isinstance(value, list):
                blocking_errors.append(f"第 {row_index + 1} 行 {key} 不是列表")
    confidence = float(proposal.get("model_confidence", proposal.get("confidence", 0)) or 0)
    proposal["model_confidence"] = max(0.0, min(confidence, 1.0))
    if assumptions:
        confidence = min(confidence, 0.85)
        warnings.append(f"模型声明了 {len(assumptions)} 条不确定项")
    if null_count:
        confidence = min(confidence, 0.8)
        warnings.append(f"建议中包含 {null_count} 个空单元格")
    if missing_numbers:
        confidence = min(confidence, 0.6)
        warnings.append(f"{len(missing_numbers)} 个数值未在解析文本中直接核验")
    proposal["confidence"] = max(0.0, min(confidence, 1.0))
    proposal["quality"] = {
        "needs_careful_review": bool(warnings),
        "applicable": not blocking_errors,
        "blocking_errors": list(dict.fromkeys(blocking_errors)),
        "null_cell_count": null_count,
        "unverified_numeric_values": missing_numbers,
        "warnings": warnings,
    }
    return original != json.dumps(proposal, ensure_ascii=False, sort_keys=True)


def generate_structuring_suggestion(
    doc: str,
    item_id: str,
    *,
    out_dir: Path = MANUAL_STRUCTURING_DIR,
    source_dir: Path = RAW_DIR,
    audit_dir: Path = AUDIT_DIR,
) -> dict[str, Any]:
    if not settings.mimo_api_key:
        raise RuntimeError("MIMO_API_KEY 未设置，无法生成结构化建议")

    owner_id, path, draft = _suggestion_identity(doc, item_id, out_dir)
    source_file = str(draft.get("source", {}).get("source_file") or doc)
    pdf_path = find_source_pdf(source_file, source_dir) or find_source_pdf(doc, source_dir)
    if not pdf_path:
        raise FileNotFoundError(f"source pdf not found: {source_file}")
    pages = [int(page) for page in draft.get("source", {}).get("pages", []) if int(page) > 0]
    if not pages:
        raise ValueError("draft source.pages is empty")
    rendered = render_pdf_pages(pdf_path, pages, audit_dir / "structuring_images")
    missing_pages = [page for page in pages if page not in rendered]
    if missing_pages:
        raise RuntimeError(f"failed to render pages: {missing_pages}")

    import httpx

    content: list[dict[str, Any]] = [{"type": "text", "text": _prompt(draft)}]
    for page in pages:
        content.append({"type": "image_url", "image_url": {"url": _data_url(rendered[page])}})
    request_payload = {
        "model": os.environ.get("AI_STRUCTURING_MODEL", settings.mimo_model),
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "stream": False,
    }
    response = httpx.post(
        f"{settings.mimo_base_url}/chat/completions",
        json=request_payload,
        headers={"Authorization": f"Bearer {settings.mimo_api_key}", "Content-Type": "application/json"},
        timeout=settings.llm_timeout_seconds,
    )
    response.raise_for_status()
    raw_content = response.json()["choices"][0]["message"]["content"]
    parsed = _extract_json_object(raw_content)
    proposal = normalize_structuring_suggestion(draft, parsed)
    payload = {
        "suggestion_status": "ready",
        "generated_at": int(time.time()),
        "model": request_payload["model"],
        "doc": doc,
        "manual_item_id": owner_id,
        "draft_updated_at": draft.get("updated_at"),
        "baseline": {
            "column_count": len(draft.get("columns", [])),
            "row_count": len(draft.get("rows", [])),
        },
        "proposal": proposal,
        "raw_response": raw_content,
    }
    _atomic_write(path, payload)
    return {
        "suggestion_path": str(path),
        "model": payload["model"],
        "confidence": proposal["confidence"],
        "column_count": len(proposal["columns"]),
        "row_count": len(proposal["rows"]),
        "assumption_count": len(proposal["assumptions"]),
    }


def read_structuring_suggestion(
    doc: str,
    item_id: str,
    out_dir: Path = MANUAL_STRUCTURING_DIR,
) -> dict[str, Any]:
    _, path, draft = _suggestion_identity(doc, item_id, out_dir)
    if not path.exists():
        raise FileNotFoundError(f"structuring suggestion not found: {item_id}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    proposal = payload.get("proposal", {})
    if "model_confidence" not in proposal and payload.get("raw_response"):
        try:
            raw = _extract_json_object(str(payload["raw_response"]))
            proposal["model_confidence"] = float(raw.get("confidence", proposal.get("confidence", 0)) or 0)
        except (json.JSONDecodeError, TypeError, ValueError):
            proposal["model_confidence"] = float(proposal.get("confidence", 0) or 0)
    if _apply_quality_gate(draft, proposal):
        _atomic_write(path, payload)
    payload["stale"] = payload.get("draft_updated_at") != draft.get("updated_at")
    payload["suggestion_path"] = str(path)
    return payload
