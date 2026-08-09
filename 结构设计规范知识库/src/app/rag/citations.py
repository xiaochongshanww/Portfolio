import re
from urllib.parse import unquote, urlparse

IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
CODE_PATTERN = re.compile(r"\bGB\s*\d{5}(?:[-—]\d{4})?\b", re.I)
CLAUSE_PATTERN = re.compile(r"第\s*(\d+(?:\.\d+){2})\s*条")
TABLE_PATTERN = re.compile(r"表\s*(\d+(?:\.\d+){1,2})")


def _url_identity(url: str) -> str:
    parsed = urlparse(url)
    return unquote(parsed.path) + (f"?{parsed.query}" if parsed.query else "")


def _normalize_code(value: str) -> str:
    return re.sub(r"\s+", "", value).upper().replace("—", "-")


def _code_supported(answer_code: str, trace_codes: set[str]) -> bool:
    normalized = _normalize_code(answer_code)
    answer_match = re.fullmatch(r"(GB\d{5})(?:-(\d{4}))?", normalized)
    if not answer_match:
        return False
    base, year = answer_match.groups()
    for trace_code in trace_codes:
        trace_match = re.fullmatch(r"(GB\d{5})(?:-(\d{4}))?", trace_code)
        if not trace_match or trace_match.group(1) != base:
            continue
        if year is None or trace_match.group(2) == year:
            return True
    return False


def validate_trace_citations(answer: str, trace: dict) -> tuple[bool, dict[str, list[str]]]:
    sources = trace.get("sources", [])
    trace_codes = {
        _normalize_code(str(source.get("code", ""))) for source in sources if source.get("code")
    }
    trace_codes.update(
        _normalize_code(str(value)) for value in trace.get("mentioned_codes", []) if value
    )
    trace_clauses = {
        str(value)
        for source in sources
        for value in (source.get("clause_number"), source.get("matched_clause_number"))
        if value
    }
    trace_tables = {str(source.get("table_id")) for source in sources if source.get("table_id")}
    trace_clauses.update(str(value) for value in trace.get("mentioned_clauses", []))
    trace_tables.update(str(value) for value in trace.get("mentioned_tables", []))
    answer_codes = {_normalize_code(value) for value in CODE_PATTERN.findall(answer)}
    answer_clauses = set(CLAUSE_PATTERN.findall(answer))
    answer_tables = set(TABLE_PATTERN.findall(answer))
    unsupported = {
        "codes": sorted(code for code in answer_codes if not _code_supported(code, trace_codes)),
        "clauses": sorted(answer_clauses - trace_clauses),
        "tables": sorted(answer_tables - trace_tables),
    }
    return not any(unsupported.values()), unsupported


def remove_unsupported_precise_citations(content: str, trace: dict) -> str:
    _, unsupported = validate_trace_citations(content, trace)
    sanitized = content
    for table_id in unsupported["tables"]:
        sanitized = re.sub(rf"表\s*{re.escape(table_id)}", "相关表格", sanitized)
    for clause_id in unsupported["clauses"]:
        sanitized = re.sub(rf"第\s*{re.escape(clause_id)}\s*条", "相关条文", sanitized)
    for code in unsupported["codes"]:
        sanitized = re.sub(re.escape(code), "相关规范", sanitized, flags=re.I)
    return sanitized


def normalize_answer_citations(content: str, trace: dict) -> str:
    offered_urls = [str(url) for url in trace.get("image_urls", []) if url]
    offered_by_identity = {_url_identity(url): url for url in offered_urls}

    def normalize_image(match: re.Match) -> str:
        identity = _url_identity(match.group(2))
        offered = offered_by_identity.get(identity)
        return f"![{match.group(1)}]({offered})" if offered else ""

    normalized = remove_unsupported_precise_citations(content, trace)
    normalized = IMAGE_PATTERN.sub(normalize_image, normalized)
    normalized = re.sub(r"`(!\[[^\]]*\]\([^)]+\))`", r"\1", normalized)

    if offered_urls and not IMAGE_PATTERN.search(normalized):
        normalized = normalized.rstrip() + f"\n\n![来源页面]({offered_urls[0]})"

    source_codes = []
    for source in trace.get("sources", []):
        code = str(source.get("code") or "").strip()
        if code and code not in source_codes:
            source_codes.append(code)
    if source_codes and not any(code in normalized for code in source_codes):
        normalized = (
            normalized.rstrip() + "\n\n【来源引用】\n- 规范编号：" + "、".join(source_codes[:3])
        )
    return normalized
