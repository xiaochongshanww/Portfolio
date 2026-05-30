import re
from dataclasses import dataclass


CLAUSE_RE = re.compile(r"(?<!\d)(\d+\.\d+(?:\.\d+)?(?:-\d+)?)(?!\d)")
SPEC_CODE_RE = re.compile(r"\b([A-Z]{1,4})\s*([0-9]{4,6}(?:-[0-9]{4})?)\b", re.I)

SPEC_ALIASES = {
    "混规": "混凝土结构设计规范",
    "混凝土规范": "混凝土结构设计规范",
    "抗规": "建筑抗震设计规范",
    "抗震规范": "建筑抗震设计规范",
    "荷载规范": "建筑结构荷载规范",
    "荷规": "建筑结构荷载规范",
    "可靠性统一标准": "建筑结构可靠性设计统一标准",
    "设防分类": "建筑工程抗震设防分类标准",
}


@dataclass(frozen=True)
class QueryInfo:
    original: str
    normalized: str
    clause_numbers: list[str]
    spec_codes: list[str]
    spec_aliases: list[str]
    spec_names: list[str]


def normalize_spec_code(prefix: str, number: str) -> str:
    return f"{prefix.upper()} {number}"


def analyze_query(query: str) -> QueryInfo:
    normalized = re.sub(r"\s+", " ", query.strip())
    clause_numbers = list(dict.fromkeys(CLAUSE_RE.findall(normalized)))
    spec_codes = [
        normalize_spec_code(prefix, number)
        for prefix, number in SPEC_CODE_RE.findall(normalized)
    ]
    spec_aliases = [alias for alias in SPEC_ALIASES if alias in normalized]
    spec_names = list(dict.fromkeys(SPEC_ALIASES[alias] for alias in spec_aliases))
    return QueryInfo(
        original=query,
        normalized=normalized,
        clause_numbers=clause_numbers,
        spec_codes=list(dict.fromkeys(spec_codes)),
        spec_aliases=spec_aliases,
        spec_names=spec_names,
    )

