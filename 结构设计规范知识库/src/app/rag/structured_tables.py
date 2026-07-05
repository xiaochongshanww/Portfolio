import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..retrieval.hybrid_search import evidence_contains
from ..retrieval.query import QueryInfo, analyze_query


STRUCTURED_TABLE_DIR = Path(__file__).resolve().parents[3] / "data" / "structured_tables"
RANGE_RE = re.compile(r"(\d+)\s*(?:到|至|~|-)\s*(\d+)")


@dataclass(frozen=True)
class StructuredTableMatch:
    table: dict[str, Any]
    row: dict[str, Any]
    score: float
    matched_terms: list[str]
    reason: str


@lru_cache(maxsize=1)
def load_structured_tables() -> list[dict[str, Any]]:
    if not STRUCTURED_TABLE_DIR.exists():
        return []
    tables: list[dict[str, Any]] = []
    for path in sorted(STRUCTURED_TABLE_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_path"] = str(path)
        tables.append(payload)
    return tables


def _source_matches(query_info: QueryInfo, source: dict[str, Any]) -> bool:
    if not query_info.spec_codes and not query_info.spec_names:
        return True
    source_text = " ".join(str(source.get(key, "")) for key in ("code", "name", "source_file"))
    if query_info.spec_codes and any(code in source_text for code in query_info.spec_codes):
        return True
    if query_info.spec_names and any(name in source_text for name in query_info.spec_names):
        return True
    return False


def _table_evidence(table: dict[str, Any]) -> str:
    source = table.get("source", {})
    parts = [
        source.get("code", ""),
        source.get("name", ""),
        source.get("table_id", ""),
        source.get("table_name", ""),
        source.get("clause_number", ""),
        " ".join(str(alias) for alias in table.get("table_aliases", [])),
    ]
    return "\n".join(str(part) for part in parts if part)


def _row_evidence(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for value in row.values():
        if isinstance(value, list):
            parts.append(" ".join(str(item) for item in value))
        elif value is not None:
            parts.append(str(value))
    return "\n".join(parts)


def _normalized_query_terms(text: str) -> list[str]:
    terms = [text]
    for start, end in RANGE_RE.findall(text):
        terms.extend(
            [
                f"{start}~{end}",
                f"{start}-{end}",
                f"{start}~{end}层",
                f"{start}-{end}层",
            ]
        )
    return list(dict.fromkeys(terms))


def _score_row(query_info: QueryInfo, table: dict[str, Any], row: dict[str, Any]) -> tuple[float, list[str]]:
    source = table.get("source", {})
    table_id = str(source.get("table_id") or "")
    table_evidence = _table_evidence(table)
    row_evidence = _row_evidence(row)
    combined_evidence = f"{table_evidence}\n{row_evidence}"
    matched_terms: list[str] = []
    score = 0.0

    if table_id and table_id in query_info.table_numbers:
        score += 10.0
        matched_terms.append(f"表{table_id}")

    for phrase in query_info.content_phrases:
        if evidence_contains(combined_evidence, phrase):
            score += 2.0
            matched_terms.append(phrase)

    for keyword in query_info.content_keywords:
        if evidence_contains(combined_evidence, keyword):
            score += 0.25

    normalized_query_terms = _normalized_query_terms(query_info.normalized)

    for alias in row.get("aliases", []):
        alias_text = str(alias)
        if any(evidence_contains(query_term, alias_text) for query_term in normalized_query_terms):
            score += 4.0 + min(len(alias_text), 8) * 0.15
            matched_terms.append(alias_text)

    for alias in table.get("table_aliases", []):
        alias_text = str(alias)
        if any(evidence_contains(query_term, alias_text) for query_term in normalized_query_terms):
            score += 3.0
            matched_terms.append(alias_text)

    if query_info.intent == "value_lookup":
        score += 1.0
    if query_info.wants_table:
        score += 0.8

    return score, list(dict.fromkeys(matched_terms))


def find_structured_table_matches(query: str, limit: int = 3) -> list[StructuredTableMatch]:
    query_info = analyze_query(query)
    if not query_info.wants_table and query_info.intent not in {"value_lookup", "classification", "formula"}:
        return []

    matches: list[StructuredTableMatch] = []
    for table in load_structured_tables():
        source = table.get("source", {})
        if not _source_matches(query_info, source):
            continue
        for row in table.get("rows", []):
            score, matched_terms = _score_row(query_info, table, row)
            if score <= 1.0:
                continue
            reason = "structured table match"
            if matched_terms:
                reason += ": " + ", ".join(matched_terms[:6])
            matches.append(
                StructuredTableMatch(
                    table=table,
                    row=row,
                    score=score,
                    matched_terms=matched_terms,
                    reason=reason,
                )
            )

    return sorted(matches, key=lambda item: item.score, reverse=True)[:limit]


def format_structured_table_context(match: StructuredTableMatch) -> str:
    source = match.table.get("source", {})
    row = match.row
    columns = {column.get("key"): column for column in match.table.get("columns", [])}
    pages = ", ".join(str(page) for page in source.get("pages", []))
    header = [
        "结构化表格命中：true",
        f"来源规范：{source.get('name', '')}",
        f"规范编号：{source.get('code', '')}",
        f"条文号：{source.get('clause_number', '')}",
        f"表号：{source.get('table_id', '')}",
        f"表名：{source.get('table_name', '')}",
        f"页码：{pages}",
        f"命中原因：{match.reason}",
    ]
    body_lines = []
    for key, value in row.items():
        if key == "aliases":
            continue
        column = columns.get(key, {})
        label = column.get("label") or key
        unit = column.get("unit")
        display_value = value
        if isinstance(value, list):
            display_value = "、".join(str(item) for item in value)
        if unit and value is not None:
            body_lines.append(f"- {label}：{display_value} {unit}")
        else:
            body_lines.append(f"- {label}：{display_value}")
    notes = "\n".join(f"- {note}" for note in match.table.get("notes", []))
    return "\n".join(header) + "\n结构化行数据：\n" + "\n".join(body_lines) + "\n表注：\n" + notes
