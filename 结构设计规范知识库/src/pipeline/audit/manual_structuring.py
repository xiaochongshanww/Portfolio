import json
import hashlib
import html
import re
import time
from pathlib import Path
from typing import Any

from src.pipeline.metadata import parse_spec_filename
from src.pipeline.paths import MANUAL_STRUCTURING_DIR, PROCESSED_DIR, STRUCTURED_TABLES_DIR


DEFAULT_RULES_PATH = MANUAL_STRUCTURING_DIR / "rules.json"
QUEUE_DIRNAME = "queue"
DRAFT_DIRNAME = "drafts"
VERSION_DIRNAME = "versions"
HTML_TABLE_RE = re.compile(r"<table[\s>]", re.I)
MERGED_CELL_RE = re.compile(r"\b(?:rowspan|colspan)\s*=", re.I)
IMAGE_REF_RE = re.compile(r"\[image\]|<img\b", re.I)
TABLE_ID_RE = re.compile(r"表\s*([A-Za-z]?\d+(?:\.\d+)*(?:-\d+)?)")
EXPLICIT_TABLE_TITLE_RE = re.compile(r"^\s*(续\s*)?表\s*([A-Za-z]?\d+(?:\.\d+)*(?:-\d+)?)")
TABLE_ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
HTML_TAG_RE = re.compile(r"<[^>]+>")
WINDOWS_UNSAFE_FILENAME_RE = re.compile(r'[<>:"/\\|?*]+')
NUMBER_TEXT_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")


def _candidate_stems(doc: str) -> list[str]:
    stems = [doc]
    if doc.endswith((".pdf", ".json")):
        stems.append(Path(doc).stem)
    return list(dict.fromkeys(stems))


def _doc_id(source_file: str, fallback: str) -> str:
    return Path(source_file).stem if source_file else Path(fallback).stem


def _safe_filename(value: str) -> str:
    return WINDOWS_UNSAFE_FILENAME_RE.sub("_", value).strip(" .") or "draft"


def _draft_path(doc: str, item_id: str, out_dir: Path = MANUAL_STRUCTURING_DIR) -> Path:
    return out_dir / DRAFT_DIRNAME / _safe_filename(doc) / f"{_safe_filename(item_id)}.json"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _business_content(payload: dict[str, Any]) -> dict[str, Any]:
    ignored = {"created_at", "updated_at", "draft_path", "draft_status", "validation", "publication"}
    return {key: value for key, value in payload.items() if key not in ignored}


def _upgrade_draft_schema(payload: dict[str, Any]) -> bool:
    changed = False
    rows = payload.get("rows", [])
    for column in payload.get("columns", []):
        if column.get("value_type"):
            continue
        key = str(column.get("key") or "")
        values = [row.get(key) for row in rows if isinstance(row, dict) and row.get(key) is not None]
        if key in {"aliases", "variables"} or any(isinstance(value, list) for value in values):
            value_type = "list"
        elif values and all(
            (isinstance(value, (int, float)) and not isinstance(value, bool))
            or (isinstance(value, str) and NUMBER_TEXT_RE.fullmatch(value.strip()))
            for value in values
        ):
            value_type = "number"
            for row in rows:
                value = row.get(key) if isinstance(row, dict) else None
                if isinstance(value, str) and NUMBER_TEXT_RE.fullmatch(value.strip()):
                    numeric = float(value)
                    row[key] = int(numeric) if numeric.is_integer() and "." not in value else numeric
        elif any(isinstance(value, dict) for value in values):
            value_type = "json"
        elif key == "value" and not values:
            value_type = "number"
        else:
            value_type = "text"
        column["value_type"] = value_type
        changed = True
    return changed


def _published_filename(draft: dict[str, Any], item_id: str) -> str:
    source = draft.get("source", {})
    code = re.sub(r"\W+", "_", str(source.get("code") or "spec"), flags=re.UNICODE).strip("_")
    table_id = re.sub(r"\W+", "_", str(source.get("table_id") or "table"), flags=re.UNICODE).strip("_")
    fingerprint = hashlib.sha1(item_id.encode("utf-8")).hexdigest()[:10]
    return _safe_filename(f"manual_{code}_{table_id}_{fingerprint}.json")


def _version_path(doc: str, item_id: str, version_id: str, out_dir: Path) -> Path:
    return (
        out_dir
        / VERSION_DIRNAME
        / _safe_filename(doc)
        / _safe_filename(item_id)
        / f"{_safe_filename(version_id)}.json"
    )


def _invalidate_structured_table_cache() -> None:
    try:
        from src.app.rag.structured_tables import load_structured_tables

        load_structured_tables.cache_clear()
    except ImportError:
        pass


def _publication_smoke_test(published: dict[str, Any], target_filename: str) -> dict[str, Any]:
    from src.app.rag.structured_tables import find_structured_table_matches

    source = published.get("source", {})
    table_id = str(source.get("table_id") or "")
    table_name = str(source.get("table_name") or "")
    aliases = [str(value) for value in published.get("table_aliases", []) if str(value)]
    queries = [f"表{table_id} {table_name} 取值"]
    queries.extend(f"表{table_id} {alias} 标准值" for alias in aliases[:2])
    results = []
    for query in list(dict.fromkeys(queries)):
        matches = find_structured_table_matches(query, limit=5)
        hit = any(Path(str(match.table.get("_path") or "")).name == target_filename for match in matches)
        results.append({"query": query, "hit": hit, "match_count": len(matches)})
    return {
        "passed": bool(results) and all(item["hit"] for item in results),
        "queries": results,
    }


def _find_queue_item(doc: str, item_id: str, out_dir: Path = MANUAL_STRUCTURING_DIR) -> dict[str, Any]:
    payload = read_manual_structuring_file(doc, out_dir)
    for item in payload.get("items", []):
        if str(item.get("id")) == item_id:
            return item
    raise KeyError(f"manual structuring item not found: {item_id}")


def _group_context(
    doc: str,
    item_id: str,
    out_dir: Path = MANUAL_STRUCTURING_DIR,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = read_manual_structuring_file(doc, out_dir)
    items = payload.get("items", [])
    selected = next((item for item in items if str(item.get("id")) == item_id), None)
    if not selected:
        raise KeyError(f"manual structuring item not found: {item_id}")
    member_ids = [str(value) for value in selected.get("group_item_ids", []) if str(value)]
    if not member_ids:
        return selected, [selected]
    by_id = {str(item.get("id")): item for item in items}
    members = [by_id[value] for value in member_ids if value in by_id]
    return selected, members or [selected]


def _draft_owner_id(doc: str, item_id: str, out_dir: Path = MANUAL_STRUCTURING_DIR) -> str:
    selected, members = _group_context(doc, item_id, out_dir)
    return str(selected.get("group_primary_item_id") or members[0].get("id") or item_id)


def _infer_table_id(title: str) -> str:
    match = TABLE_ID_RE.search(title)
    return match.group(1) if match else ""


def _infer_table_name(title: str, table_id: str) -> str:
    name = re.sub(r"<[^>]+>", " ", title)
    if table_id:
        name = re.sub(rf"^\s*表\s*{re.escape(table_id)}\s*", "", name)
    name = re.sub(r"\s+", " ", name).strip(" ：:-")
    return name or title[:80]


def _explicit_table_title(title: str) -> tuple[str, bool] | None:
    match = EXPLICIT_TABLE_TITLE_RE.search(title)
    if not match:
        return None
    return match.group(2), bool(match.group(1))


def _table_header_signature(text: str) -> str:
    rows = TABLE_ROW_RE.findall(text)
    if not rows:
        return ""
    header = " ".join(rows[:2])
    header = html.unescape(HTML_TAG_RE.sub(" ", header))
    return re.sub(r"\s+", "", header).lower()[:500]


def _page_clusters(items: list[dict[str, Any]], *, max_gap: int = 1) -> list[list[dict[str, Any]]]:
    ordered = sorted(items, key=lambda item: (int(item.get("page") or 0), int(item.get("element_index") or 0)))
    clusters: list[list[dict[str, Any]]] = []
    for item in ordered:
        page = int(item.get("page") or 0)
        if not clusters or page - int(clusters[-1][-1].get("page") or 0) > max_gap:
            clusters.append([item])
        else:
            clusters[-1].append(item)
    return [cluster for cluster in clusters if len(cluster) > 1]


def _annotate_cross_page_groups(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped_ids: set[str] = set()
    groups: list[tuple[list[dict[str, Any]], str, str]] = []
    explicit: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in candidates:
        parsed = _explicit_table_title(str(item.get("title") or ""))
        if parsed:
            table_id, _ = parsed
            explicit.setdefault((str(item.get("doc") or ""), table_id), []).append(item)
    for (_, table_id), items in explicit.items():
        for cluster in _page_clusters(items):
            groups.append((cluster, f"same_table_id:{table_id}", "high"))
            grouped_ids.update(str(item["id"]) for item in cluster)

    headers: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in candidates:
        if str(item["id"]) in grouped_ids:
            continue
        signature = _table_header_signature(str(item.get("current_text") or ""))
        if len(signature) >= 12:
            headers.setdefault((str(item.get("doc") or ""), signature), []).append(item)
    for (_, _), items in headers.items():
        for cluster in _page_clusters(items):
            groups.append((cluster, "adjacent_same_header", "medium"))
            grouped_ids.update(str(item["id"]) for item in cluster)

    for members, reason, confidence in groups:
        ordered = sorted(
            members,
            key=lambda item: (int(item.get("page") or 0), int(item.get("element_index") or 0)),
        )
        member_ids = [str(item["id"]) for item in ordered]
        pages = sorted({int(item.get("page") or 0) for item in ordered if int(item.get("page") or 0) > 0})
        fingerprint = hashlib.sha1("|".join(member_ids).encode("utf-8")).hexdigest()[:12]
        group_id = f"table_group_{fingerprint}"
        primary_id = member_ids[0]
        for item in ordered:
            item.update(
                {
                    "group_id": group_id,
                    "group_primary_item_id": primary_id,
                    "group_item_ids": member_ids,
                    "group_pages": pages,
                    "group_size": len(member_ids),
                    "group_reason": reason,
                    "group_confidence": confidence,
                }
            )
    return candidates


def load_manual_structuring_rules(rules_path: Path = DEFAULT_RULES_PATH) -> list[dict[str, Any]]:
    if not rules_path.exists():
        return []
    payload = json.loads(rules_path.read_text(encoding="utf-8"))
    rules = payload.get("rules", payload if isinstance(payload, list) else [])
    return [rule for rule in rules if isinstance(rule, dict)]


def _match_rules(text: str, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matched = []
    for rule in rules:
        terms = [str(term) for term in rule.get("terms", []) if str(term)]
        hits = [term for term in terms if term in text]
        if hits:
            matched.append({**rule, "matched_terms": hits})
    return matched


def _infer_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:120]
    return "复杂表格"


def _severity(matches: list[dict[str, Any]], generic_reasons: list[str]) -> str:
    if any(match.get("severity") == "high" for match in matches):
        return "high"
    if "image_reference" in generic_reasons and "merged_cells" in generic_reasons:
        return "high"
    return "medium"


def detect_manual_structuring_candidates(
    processed_dir: Path = PROCESSED_DIR,
    rules_path: Path = DEFAULT_RULES_PATH,
) -> list[dict[str, Any]]:
    rules = load_manual_structuring_rules(rules_path)
    candidates: list[dict[str, Any]] = []
    for path in sorted(processed_dir.glob("*.json")):
        if path.name.endswith("_chunks.json") or path.name == "build_quality.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        elements = payload.get("elements", payload if isinstance(payload, list) else [])
        source_file = payload.get("source_file", path.name) if isinstance(payload, dict) else path.name
        doc = _doc_id(source_file, path.name)
        for index, element in enumerate(elements):
            text = str(element.get("text") or "")
            if not HTML_TABLE_RE.search(text):
                continue
            matches = _match_rules(text, rules)
            generic_reasons = []
            if MERGED_CELL_RE.search(text):
                generic_reasons.append("merged_cells")
            if IMAGE_REF_RE.search(text):
                generic_reasons.append("image_reference")
            if "□" in text:
                generic_reasons.append("symbol_or_drawing_marker")
            if not matches and len(generic_reasons) < 2:
                continue
            page = int(element.get("page") or 0)
            issue_type = matches[0].get("id", "complex_table") if matches else "complex_table"
            candidates.append(
                {
                    "id": f"{doc}_p{page}_e{index}_{issue_type}",
                    "source_file": source_file,
                    "doc": doc,
                    "page": page,
                    "element_index": index,
                    "task_type": "manual_structuring",
                    "issue_type": issue_type,
                    "severity": _severity(matches, generic_reasons),
                    "review_status": "pending",
                    "title": _infer_title(text),
                    "current_text": text,
                    "image": element.get("img", ""),
                    "matched_rules": [
                        {
                            "id": match.get("id", ""),
                            "label": match.get("label", ""),
                            "reason": match.get("reason", ""),
                            "matched_terms": match.get("matched_terms", []),
                        }
                        for match in matches
                    ],
                    "generic_reasons": generic_reasons,
                    "recommended_action": "manual_structuring",
                    "target_schema": {
                        "source": "规范编号、规范名称、条文号、表号、表名、页码",
                        "columns": "字段 key、中文 label、单位 unit",
                        "rows": "逐行结构化数值、适用条件、检索别名 aliases",
                        "notes": "表注、插值规则、限制条件和与其他条文的联动关系",
                    },
                }
            )
    return _annotate_cross_page_groups(candidates)


def write_manual_structuring_queue(
    processed_dir: Path = PROCESSED_DIR,
    out_dir: Path = MANUAL_STRUCTURING_DIR,
    rules_path: Path = DEFAULT_RULES_PATH,
) -> dict[str, Any]:
    candidates = detect_manual_structuring_candidates(processed_dir, rules_path)
    queue_dir = out_dir / QUEUE_DIRNAME
    queue_dir.mkdir(parents=True, exist_ok=True)
    by_doc: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        by_doc.setdefault(str(candidate["doc"]), []).append(candidate)
    written = []
    for doc, items in by_doc.items():
        path = queue_dir / f"{doc}.json"
        existing_by_id: dict[str, dict[str, Any]] = {}
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            for item in payload.get("items", []):
                existing_by_id[str(item.get("id"))] = item
        merged = []
        for item in items:
            existing = existing_by_id.get(str(item["id"]), {})
            if existing.get("review_status"):
                item["review_status"] = existing["review_status"]
            if existing.get("notes"):
                item["notes"] = existing["notes"]
            merged.append(item)
        payload = {"doc": doc, "updated_at": int(time.time()), "items": merged}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append({"doc": doc, "path": str(path), "item_count": len(merged)})
    for path in sorted(queue_dir.glob("*.json")):
        if path.stem not in by_doc:
            path.unlink()
    return {"document_count": len(written), "candidate_count": len(candidates), "documents": written}


def list_manual_structuring_files(out_dir: Path = MANUAL_STRUCTURING_DIR) -> list[dict[str, Any]]:
    queue_dir = out_dir / QUEUE_DIRNAME
    if not queue_dir.exists():
        return []
    documents = []
    for path in sorted(queue_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload.get("items", [])
        task_keys = {
            str(item.get("group_id") or item.get("id")): item.get("review_status", "pending")
            for item in items
        }
        task_owners = {
            str(item.get("group_primary_item_id") or item.get("id"))
            for item in items
        }
        suggestion_dir = out_dir / "suggestions" / _safe_filename(str(payload.get("doc", path.stem)))
        suggestion_count = sum(
            1 for owner_id in task_owners if (suggestion_dir / f"{_safe_filename(owner_id)}.json").exists()
        )
        documents.append(
            {
                "doc": payload.get("doc", path.stem),
                "path": str(path),
                "item_count": len(items),
                "task_count": len(task_keys),
                "pending_count": sum(1 for item in items if item.get("review_status", "pending") == "pending"),
                "approved_count": sum(1 for item in items if item.get("review_status") == "approved"),
                "rejected_count": sum(1 for item in items if item.get("review_status") == "rejected"),
                "pending_task_count": sum(1 for status in task_keys.values() if status == "pending"),
                "approved_task_count": sum(1 for status in task_keys.values() if status == "approved"),
                "rejected_task_count": sum(1 for status in task_keys.values() if status == "rejected"),
                "suggestion_count": suggestion_count,
                "suggestion_missing_count": max(len(task_keys) - suggestion_count, 0),
            }
        )
    return documents


def read_manual_structuring_file(doc: str, out_dir: Path = MANUAL_STRUCTURING_DIR) -> dict[str, Any]:
    queue_dir = out_dir / QUEUE_DIRNAME
    for stem in _candidate_stems(doc):
        path = queue_dir / f"{stem}.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload.setdefault("doc", path.stem)
            payload.setdefault("items", [])
            return payload
    return {"doc": doc, "items": []}


def update_manual_structuring_status(
    doc: str,
    item_id: str,
    status: str,
    out_dir: Path = MANUAL_STRUCTURING_DIR,
    notes: str = "",
) -> dict[str, Any]:
    if status not in {"pending", "approved", "rejected"}:
        raise ValueError("status must be pending, approved, or rejected")
    queue_dir = out_dir / QUEUE_DIRNAME
    path = None
    for stem in _candidate_stems(doc):
        candidate = queue_dir / f"{stem}.json"
        if candidate.exists():
            path = candidate
            break
    if not path:
        raise FileNotFoundError(f"manual structuring queue not found: {doc}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    for item in items:
        if str(item.get("id")) == item_id:
            item["review_status"] = status
            if notes:
                item["notes"] = notes
            payload["items"] = items
            payload["updated_at"] = int(time.time())
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"doc": path.stem, "item_id": item_id, "review_status": status}
    raise KeyError(f"manual structuring item not found: {item_id}")


def _update_group_status(
    doc: str,
    item_id: str,
    status: str,
    out_dir: Path,
    notes: str,
) -> None:
    _, members = _group_context(doc, item_id, out_dir)
    for member in members:
        update_manual_structuring_status(doc, str(member["id"]), status, out_dir, notes=notes)


def _review_context_for_group(
    doc: str,
    owner_id: str,
    item: dict[str, Any],
    title: str,
    pages: list[int],
    members: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "manual_item_id": owner_id,
        "manual_item_ids": [str(member.get("id")) for member in members],
        "doc": doc,
        "page": pages[0] if pages else 0,
        "pages": pages,
        "element_index": item.get("element_index"),
        "issue_type": item.get("issue_type", ""),
        "severity": item.get("severity", ""),
        "title": title,
        "group_id": item.get("group_id", ""),
        "group_reason": item.get("group_reason", ""),
        "group_confidence": item.get("group_confidence", ""),
        "matched_rules": [rule for member in members for rule in member.get("matched_rules", [])],
        "generic_reasons": list(
            dict.fromkeys(reason for member in members for reason in member.get("generic_reasons", []))
        ),
        "current_text": "\n\n".join(
            f"--- page {member.get('page')} · element {member.get('element_index')} ---\n"
            f"{member.get('current_text', '')}"
            for member in members
        ),
        "elements": [
            {
                "item_id": member.get("id"),
                "page": member.get("page"),
                "element_index": member.get("element_index"),
                "title": member.get("title", ""),
                "current_text": member.get("current_text", ""),
                "image": member.get("image", ""),
            }
            for member in members
        ],
    }


def build_manual_structuring_draft(
    doc: str,
    item_id: str,
    out_dir: Path = MANUAL_STRUCTURING_DIR,
    *,
    force: bool = False,
) -> dict[str, Any]:
    owner_id = _draft_owner_id(doc, item_id, out_dir)
    path = _draft_path(doc, owner_id, out_dir)
    _, members = _group_context(doc, owner_id, out_dir)
    item = next((member for member in members if str(member.get("id")) == owner_id), members[0])
    source_file = str(item.get("source_file") or f"{doc}.pdf")
    spec = parse_spec_filename(source_file)
    title_item = next(
        (
            member
            for member in members
            if (parsed := _explicit_table_title(str(member.get("title") or ""))) and not parsed[1]
        ),
        item,
    )
    title = str(title_item.get("title") or "复杂表格")
    table_id = _infer_table_id(title)
    table_name = _infer_table_name(title, table_id)
    pages = sorted({int(member.get("page") or 0) for member in members if int(member.get("page") or 0) > 0})
    review_context = _review_context_for_group(doc, owner_id, item, title, pages, members)
    if path.exists() and not force:
        payload = json.loads(path.read_text(encoding="utf-8"))
        existing_ids = payload.get("review_context", {}).get("manual_item_ids", [])
        changed = _upgrade_draft_schema(payload)
        if existing_ids != review_context["manual_item_ids"]:
            payload.setdefault("source", {})["pages"] = pages
            payload["review_context"] = review_context
            payload["draft_status"] = "needs_review"
            payload.pop("validation", None)
            changed = True
        if changed:
            payload["updated_at"] = int(time.time())
            _atomic_write_json(path, payload)
        payload["draft_path"] = str(path)
        return payload

    now = int(time.time())
    payload = {
        "schema_version": "0.1",
        "draft_status": "needs_review",
        "created_at": now,
        "updated_at": now,
        "source": {
            "code": spec.code,
            "name": spec.name,
            "source_file": source_file,
            "clause_number": table_id if table_id and table_id[0].isdigit() else "",
            "table_id": table_id,
            "table_name": table_name,
            "pages": pages,
        },
        "columns": [
            {"key": "item", "label": "项目", "value_type": "text"},
            {"key": "condition", "label": "适用条件", "value_type": "text"},
            {"key": "value", "label": "取值", "value_type": "number"},
            {"key": "aliases", "label": "检索别名", "value_type": "list"},
        ],
        "rows": [],
        "table_aliases": [alias for alias in [f"表{table_id}" if table_id else "", table_name] if alias],
        "notes": [],
        "review_context": review_context,
    }
    _atomic_write_json(path, payload)
    payload["draft_path"] = str(path)
    return payload


def read_manual_structuring_draft(
    doc: str,
    item_id: str,
    out_dir: Path = MANUAL_STRUCTURING_DIR,
) -> dict[str, Any]:
    owner_id = _draft_owner_id(doc, item_id, out_dir)
    path = _draft_path(doc, owner_id, out_dir)
    if not path.exists():
        raise FileNotFoundError(f"manual structuring draft not found: {item_id}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if _upgrade_draft_schema(payload):
        payload["updated_at"] = int(time.time())
        _atomic_write_json(path, payload)
    payload["draft_path"] = str(path)
    return payload


def save_manual_structuring_draft(
    doc: str,
    item_id: str,
    draft: dict[str, Any],
    out_dir: Path = MANUAL_STRUCTURING_DIR,
) -> dict[str, Any]:
    _find_queue_item(doc, item_id, out_dir)
    owner_id = _draft_owner_id(doc, item_id, out_dir)
    path = _draft_path(doc, owner_id, out_dir)
    payload = dict(draft)
    payload.pop("draft_path", None)
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if existing and _business_content(existing) != _business_content(payload):
        payload["draft_status"] = "needs_review"
        payload.pop("validation", None)
    payload["updated_at"] = int(time.time())
    payload.setdefault("schema_version", "0.1")
    payload.setdefault("draft_status", "needs_review")
    payload.setdefault("created_at", existing.get("created_at", int(time.time())))
    _atomic_write_json(path, payload)
    payload["draft_path"] = str(path)
    return payload


def validate_manual_structuring_draft(
    doc: str,
    item_id: str,
    out_dir: Path = MANUAL_STRUCTURING_DIR,
) -> dict[str, Any]:
    owner_id = _draft_owner_id(doc, item_id, out_dir)
    path = _draft_path(doc, owner_id, out_dir)
    draft = read_manual_structuring_draft(doc, item_id, out_dir)
    draft.pop("draft_path", None)
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    def error(code: str, field: str, message: str) -> None:
        errors.append({"code": code, "path": field, "message": message})

    def warning(code: str, field: str, message: str) -> None:
        warnings.append({"code": code, "path": field, "message": message})

    source = draft.get("source")
    if not isinstance(source, dict):
        error("source_invalid", "source", "source 必须是对象")
        source = {}
    for key in ("code", "name", "source_file", "table_id", "table_name"):
        if not str(source.get(key) or "").strip():
            error("source_required", f"source.{key}", f"{key} 不能为空")
    pages = source.get("pages")
    if not isinstance(pages, list) or not pages:
        error("pages_required", "source.pages", "pages 必须是非空数组")
    elif any(not isinstance(page, int) or page <= 0 for page in pages):
        error("pages_invalid", "source.pages", "页码必须是正整数")

    columns = draft.get("columns")
    column_keys: list[str] = []
    column_types: dict[str, str] = {}
    if not isinstance(columns, list) or not columns:
        error("columns_required", "columns", "columns 必须是非空数组")
        columns = []
    for index, column in enumerate(columns):
        if not isinstance(column, dict):
            error("column_invalid", f"columns[{index}]", "列定义必须是对象")
            continue
        key = str(column.get("key") or "").strip()
        label = str(column.get("label") or "").strip()
        if not key:
            error("column_key_required", f"columns[{index}].key", "列 key 不能为空")
        elif key in column_keys:
            error("column_key_duplicate", f"columns[{index}].key", f"列 key 重复：{key}")
        else:
            column_keys.append(key)
            value_type = str(column.get("value_type") or "").strip()
            if value_type and value_type not in {"text", "number", "list", "json"}:
                error(
                    "column_type_invalid",
                    f"columns[{index}].value_type",
                    "value_type 必须是 text、number、list 或 json",
                )
            column_types[key] = value_type
        if not label:
            error("column_label_required", f"columns[{index}].label", "列 label 不能为空")

    rows = draft.get("rows")
    if not isinstance(rows, list) or not rows:
        error("rows_required", "rows", "rows 必须至少包含一行数据")
        rows = []
    fingerprints: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            error("row_invalid", f"rows[{index}]", "行数据必须是对象")
            continue
        unknown = sorted(set(row) - set(column_keys))
        if unknown:
            error("row_unknown_fields", f"rows[{index}]", f"存在未定义列：{', '.join(unknown)}")
        aliases = row.get("aliases", [])
        if "aliases" in row and (
            not isinstance(aliases, list) or any(not isinstance(alias, str) or not alias.strip() for alias in aliases)
        ):
            error("aliases_invalid", f"rows[{index}].aliases", "aliases 必须是非空字符串数组")
        for key, value in row.items():
            if value is None or key not in column_types:
                continue
            value_type = column_types[key]
            if value_type == "number" and (
                not isinstance(value, (int, float)) or isinstance(value, bool)
            ):
                error("cell_type_invalid", f"rows[{index}].{key}", "该单元格必须是数字")
            elif value_type == "list" and not isinstance(value, list):
                error("cell_type_invalid", f"rows[{index}].{key}", "该单元格必须是数组")
            elif value_type == "text" and not isinstance(value, str):
                error("cell_type_invalid", f"rows[{index}].{key}", "该单元格必须是文本")
        content = {key: value for key, value in row.items() if key != "aliases" and value not in (None, "", [])}
        if not content:
            error("row_empty", f"rows[{index}]", "每行至少需要一个非 aliases 的有效值")
        fingerprint = json.dumps(content, ensure_ascii=False, sort_keys=True)
        if fingerprint in fingerprints:
            warning("row_duplicate", f"rows[{index}]", "该行与前面的行内容重复")
        fingerprints.add(fingerprint)

    for field in ("table_aliases", "notes"):
        value = draft.get(field, [])
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            error(f"{field}_invalid", field, f"{field} 必须是非空字符串数组")
    if not draft.get("table_aliases"):
        warning("table_aliases_empty", "table_aliases", "建议填写表名、表号和常见问法别名")

    now = int(time.time())
    result = {
        "valid": not errors,
        "validated_at": now,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }
    draft["validation"] = result
    draft["draft_status"] = "validated" if result["valid"] else "needs_review"
    draft["updated_at"] = now
    _atomic_write_json(path, draft)
    return {**result, "draft_status": draft["draft_status"]}


def publish_manual_structuring_draft(
    doc: str,
    item_id: str,
    out_dir: Path = MANUAL_STRUCTURING_DIR,
    structured_dir: Path = STRUCTURED_TABLES_DIR,
) -> dict[str, Any]:
    owner_id = _draft_owner_id(doc, item_id, out_dir)
    draft_path = _draft_path(doc, owner_id, out_dir)
    draft = read_manual_structuring_draft(doc, item_id, out_dir)
    draft.pop("draft_path", None)
    if draft.get("draft_status") != "validated":
        raise ValueError("draft must be validated before publishing")

    filename = _published_filename(draft, owner_id)
    target = structured_dir / filename
    version_id = str(time.time_ns())
    previous = json.loads(target.read_text(encoding="utf-8")) if target.exists() else None
    published_at = int(time.time())
    published = {
        "schema_version": str(draft.get("schema_version") or "0.1"),
        "source": draft["source"],
        "columns": draft["columns"],
        "rows": draft["rows"],
        "table_aliases": draft.get("table_aliases", []),
        "notes": draft.get("notes", []),
        "publication": {
            "published_at": published_at,
            "source_doc": doc,
            "manual_item_id": owner_id,
            "version_id": version_id,
        },
    }
    version = {
        "version_id": version_id,
        "created_at": published_at,
        "action": "publish",
        "target_filename": filename,
        "previous_content": previous,
        "published_content": published,
        "rolled_back_at": None,
    }
    _atomic_write_json(_version_path(doc, owner_id, version_id, out_dir), version)
    _atomic_write_json(target, published)
    _invalidate_structured_table_cache()
    smoke_test = _publication_smoke_test(published, filename)
    version["smoke_test"] = smoke_test
    if not smoke_test["passed"]:
        if previous is None:
            if target.exists():
                target.unlink()
            rollback_action = "removed"
        else:
            _atomic_write_json(target, previous)
            rollback_action = "restored"
        version["rolled_back_at"] = int(time.time())
        version["automatic_rollback"] = {
            "reason": "structured retrieval smoke test failed",
            "action": rollback_action,
        }
        _atomic_write_json(_version_path(doc, owner_id, version_id, out_dir), version)
        _invalidate_structured_table_cache()
        raise RuntimeError("structured retrieval smoke test failed; publication was rolled back")
    _atomic_write_json(_version_path(doc, owner_id, version_id, out_dir), version)

    draft["draft_status"] = "published"
    draft["updated_at"] = published_at
    draft["publication"] = {
        "target_filename": filename,
        "published_at": published_at,
        "version_id": version_id,
    }
    _atomic_write_json(draft_path, draft)
    _update_group_status(doc, owner_id, "approved", out_dir, notes="结构化草稿已发布")
    return {
        "draft_status": "published",
        "target_path": str(target),
        "target_filename": filename,
        "version_id": version_id,
        "replaced_existing": previous is not None,
        "smoke_test": smoke_test,
    }


def list_manual_structuring_versions(
    doc: str,
    item_id: str,
    out_dir: Path = MANUAL_STRUCTURING_DIR,
) -> list[dict[str, Any]]:
    owner_id = _draft_owner_id(doc, item_id, out_dir)
    directory = out_dir / VERSION_DIRNAME / _safe_filename(doc) / _safe_filename(owner_id)
    versions = []
    for path in sorted(directory.glob("*.json"), reverse=True) if directory.exists() else []:
        payload = json.loads(path.read_text(encoding="utf-8"))
        versions.append(
            {
                "version_id": payload.get("version_id", path.stem),
                "created_at": payload.get("created_at"),
                "target_filename": payload.get("target_filename", ""),
                "replaced_existing": payload.get("previous_content") is not None,
                "rolled_back_at": payload.get("rolled_back_at"),
                "smoke_test": payload.get("smoke_test"),
                "automatic_rollback": payload.get("automatic_rollback"),
            }
        )
    return versions


def rollback_manual_structuring_publication(
    doc: str,
    item_id: str,
    out_dir: Path = MANUAL_STRUCTURING_DIR,
    structured_dir: Path = STRUCTURED_TABLES_DIR,
) -> dict[str, Any]:
    owner_id = _draft_owner_id(doc, item_id, out_dir)
    draft_path = _draft_path(doc, owner_id, out_dir)
    draft = read_manual_structuring_draft(doc, item_id, out_dir)
    draft.pop("draft_path", None)
    publication = draft.get("publication", {})
    version_id = str(publication.get("version_id") or "")
    if not version_id:
        raise ValueError("draft has no published version to roll back")
    version_path = _version_path(doc, owner_id, version_id, out_dir)
    if not version_path.exists():
        raise FileNotFoundError(f"publication version not found: {version_id}")
    version = json.loads(version_path.read_text(encoding="utf-8"))
    if version.get("rolled_back_at"):
        raise ValueError("publication version has already been rolled back")

    filename = str(version.get("target_filename") or "")
    target = structured_dir / filename
    if target.parent.resolve() != structured_dir.resolve():
        raise ValueError("invalid publication target")
    previous = version.get("previous_content")
    if previous is None:
        if target.exists():
            target.unlink()
        action = "removed"
        next_status = "validated"
    else:
        _atomic_write_json(target, previous)
        action = "restored"
        next_status = "published"

    rolled_back_at = int(time.time())
    version["rolled_back_at"] = rolled_back_at
    _atomic_write_json(version_path, version)
    if previous is not None:
        for field in ("schema_version", "source", "columns", "rows", "table_aliases", "notes"):
            if field in previous:
                draft[field] = previous[field]
    draft["draft_status"] = next_status
    draft["updated_at"] = rolled_back_at
    draft["publication"] = {
        **publication,
        "version_id": (
            previous.get("publication", {}).get("version_id", version_id) if previous is not None else version_id
        ),
        "published_at": (
            previous.get("publication", {}).get("published_at") if previous is not None else publication.get("published_at")
        ),
        "rolled_back_at": rolled_back_at,
        "rollback_action": action,
    }
    _atomic_write_json(draft_path, draft)
    queue_status = "approved" if previous is not None else "pending"
    _update_group_status(doc, owner_id, queue_status, out_dir, notes="结构化发布已回滚")
    _invalidate_structured_table_cache()
    return {
        "draft_status": next_status,
        "target_path": str(target),
        "version_id": version_id,
        "rollback_action": action,
    }
