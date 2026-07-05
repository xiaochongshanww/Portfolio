import re
from dataclasses import dataclass


CLAUSE_RE = re.compile(r"(?<!\d)(\d+\.\d+(?:\.\d+)?(?:-\d+)?)(?!\d)")
TABLE_ID_RE = re.compile(r"表\s*(\d+(?:\.\d+)+(?:-\d+)?)")
SPEC_CODE_RE = re.compile(r"\b([A-Z]{1,4})\s*([0-9]{4,6}(?:-[0-9]{4})?)\b", re.I)

SPEC_ALIASES = {
    "混规": "混凝土结构设计规范",
    "混凝土规范": "混凝土结构设计规范",
    "抗规": "建筑抗震设计规范",
    "抗震规范": "建筑抗震设计规范",
    "荷载规范": "建筑结构荷载规范",
    "荷规": "建筑结构荷载规范",
    "楼面活荷载": "建筑结构荷载规范",
    "屋面活荷载": "建筑结构荷载规范",
    "偶然荷载": "建筑结构荷载规范",
    "永久荷载": "建筑结构荷载规范",
    "可变荷载": "建筑结构荷载规范",
    "可靠性统一标准": "建筑结构可靠性设计统一标准",
    "设防分类": "建筑工程抗震设防分类标准",
    "抗震设防类别": "建筑工程抗震设防分类标准",
    "设防类别": "建筑工程抗震设防分类标准",
    "施工质量验收统一标准": "建筑工程施工质量验收统一标准",
    "检验批": "建筑工程施工质量验收统一标准",
    "分项工程": "建筑工程施工质量验收统一标准",
    "分部工程": "建筑工程施工质量验收统一标准",
}

VALUE_INTENT_TERMS = ("取多少", "是多少", "限值", "系数", "取值", "数值", "荷载值", "怎么取", "如何取")
VALUE_REFERENCE_TERMS = ("标准值", "设计值")
DEFINITION_INTENT_TERMS = ("是什么", "什么是", "定义", "含义", "什么意思", "关系", "区别")
FORMULA_INTENT_TERMS = ("公式", "计算式", "表达式", "怎么算", "如何计算")
REQUIREMENT_INTENT_TERMS = ("要求", "规定", "构造", "应", "不应", "宜")
CLASSIFICATION_INTENT_TERMS = ("划分", "分为", "分成", "类别", "等级", "类型", "哪几类", "哪些类")
TABLE_TERMS = ("表", "表格", "查表", "按表")
QUESTION_TERMS = ("哪个", "哪些", "哪里", "在哪", "多少", "怎么", "如何", "有什么", "有哪些", "确定")
QUERY_STOP_TERMS = (
    VALUE_INTENT_TERMS
    + VALUE_REFERENCE_TERMS
    + DEFINITION_INTENT_TERMS
    + FORMULA_INTENT_TERMS
    + REQUIREMENT_INTENT_TERMS
    + TABLE_TERMS
    + QUESTION_TERMS
)
QUERY_PARTICLES_RE = re.compile(r"[的中里及和与对按为是在：:，,。；;、\s]+")


@dataclass(frozen=True)
class QueryInfo:
    original: str
    normalized: str
    clause_numbers: list[str]
    table_numbers: list[str]
    spec_codes: list[str]
    spec_aliases: list[str]
    spec_names: list[str]
    intent: str
    wants_table: bool
    content_phrases: list[str]
    content_keywords: list[str]


def normalize_spec_code(prefix: str, number: str) -> str:
    return f"{prefix.upper()} {number}"


def extract_content_phrases(normalized: str) -> list[str]:
    text = normalized
    for term in QUERY_STOP_TERMS:
        text = text.replace(term, " ")
    text = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]+", " ", text)
    phrases = [phrase for phrase in QUERY_PARTICLES_RE.split(text) if len(phrase) >= 2]
    return list(dict.fromkeys(phrases))


def extract_content_keywords(normalized: str) -> list[str]:
    phrases = extract_content_phrases(normalized)
    grams: list[str] = []
    for phrase in phrases:
        grams.extend(phrase[index : index + 2] for index in range(len(phrase) - 1))
        grams.extend(phrase[index : index + 3] for index in range(len(phrase) - 2))
    keywords = phrases + grams
    return list(dict.fromkeys(keyword for keyword in keywords if len(keyword) >= 2))


def analyze_query(query: str) -> QueryInfo:
    normalized = re.sub(r"\s+", " ", query.strip())
    table_numbers = list(dict.fromkeys(TABLE_ID_RE.findall(normalized)))
    clause_numbers = [
        clause_number
        for clause_number in dict.fromkeys(CLAUSE_RE.findall(normalized))
        if clause_number not in table_numbers
    ]
    spec_codes = [
        normalize_spec_code(prefix, number)
        for prefix, number in SPEC_CODE_RE.findall(normalized)
    ]
    spec_aliases = [alias for alias in SPEC_ALIASES if alias in normalized]
    spec_names = list(dict.fromkeys(SPEC_ALIASES[alias] for alias in spec_aliases))
    wants_table = any(term in normalized for term in TABLE_TERMS)
    has_value_reference = any(term in normalized for term in VALUE_REFERENCE_TERMS)
    has_definition_intent = any(term in normalized for term in DEFINITION_INTENT_TERMS)
    has_formula_intent = any(term in normalized for term in FORMULA_INTENT_TERMS)
    has_value_lookup = (
        any(term in normalized for term in VALUE_INTENT_TERMS)
        or (has_value_reference and wants_table)
        or (has_value_reference and not has_definition_intent and not has_formula_intent)
    )
    if clause_numbers:
        intent = "clause_requirement"
    elif has_formula_intent:
        intent = "formula"
    elif has_value_lookup:
        intent = "value_lookup"
        wants_table = True
    elif any(term in normalized for term in CLASSIFICATION_INTENT_TERMS):
        intent = "classification"
        wants_table = True
    elif has_definition_intent:
        intent = "definition"
    elif any(term in normalized for term in REQUIREMENT_INTENT_TERMS):
        intent = "clause_requirement"
    else:
        intent = "general"
    content_phrases = extract_content_phrases(normalized)
    return QueryInfo(
        original=query,
        normalized=normalized,
        clause_numbers=clause_numbers,
        table_numbers=table_numbers,
        spec_codes=list(dict.fromkeys(spec_codes)),
        spec_aliases=spec_aliases,
        spec_names=spec_names,
        intent=intent,
        wants_table=wants_table,
        content_phrases=content_phrases,
        content_keywords=extract_content_keywords(normalized),
    )

