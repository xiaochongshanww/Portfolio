"""Multi-stage LLM document analyzer for recruitment notices.

Stages:
  A — Document classification (what kind of notice?)
  B — Full position extraction with evidence
  C — Quality review and correction

Regex-based extraction remains as a low-confidence fallback.
"""

import json
import logging
import re
from datetime import date
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field, field_validator

from university_recruitment.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────
VALID_EDUCATION_REQUIREMENTS = frozenset({
    "博士研究生", "博士", "硕士研究生及以上", "硕士研究生",
    "硕士及以上", "硕士", "本科及以上", "本科",
})
VALID_JOB_TYPES = frozenset({
    "教学科研岗", "科研岗", "博士后", "辅导员",
    "行政教辅岗", "实验技术岗", "医疗卫生岗",
})
VALID_DEPARTMENT_SUFFIXES = (
    "学院", "学部", "系", "部", "研究院", "医院", "中心", "实验室", "课题组",
)
REJECTED_DEPARTMENT_VALUES = frozenset({
    "用人部门", "招聘单位", "各学院", "相关部门", "学校", "本校",
    "用人部", "是直属教育部", "区）教师发展中心",
})
RECRUITMENT_DOC_TYPES = frozenset({
    "single_position", "multi_position_notice", "general_talent_notice",
    "postdoc_notice", "result_announcement", "interview_notice",
    "publicity_notice", "non_recruitment", "unknown",
})


# ── Pydantic Models ────────────────────────────────────

class Evidence(BaseModel):
    """Source evidence for a field value."""
    source_id: str = ""        # e.g. "html_table_1.row_3" or "paragraph_5"
    quote: str = ""            # the original text snippet
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ExtractedPosition(BaseModel):
    """A single position extracted from a recruitment notice."""
    position_raw: str
    position_normalized: str | None = None
    department: str | None = None
    discipline: list[str] = Field(default_factory=list)
    education_requirement: str | None = None
    job_type: str | None = None
    location: str | None = None
    deadline: date | None = None
    headcount: int | None = None
    requirements: list[str] = Field(default_factory=list)
    evidence: dict[str, Evidence] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("education_requirement", mode="before")
    @classmethod
    def validate_education(cls, v: str | None) -> str | None:
        if v is None: return None
        v = str(v).strip()
        return v if v in VALID_EDUCATION_REQUIREMENTS else None

    @field_validator("job_type", mode="before")
    @classmethod
    def validate_job_type(cls, v: str | None) -> str | None:
        if v is None: return None
        v = str(v).strip()
        return v if v in VALID_JOB_TYPES else None

    @field_validator("department", mode="before")
    @classmethod
    def validate_department(cls, v: str | None) -> str | None:
        if v is None: return None
        v = str(v).strip()
        if v in REJECTED_DEPARTMENT_VALUES: return None
        if not any(v.endswith(s) for s in VALID_DEPARTMENT_SUFFIXES): return None
        return v


class DocumentAnalysis(BaseModel):
    """Full analysis result for a recruitment document."""
    document_type: str = "unknown"
    contains_specific_positions: bool = False
    position_count_estimate: int = 0
    has_position_table: bool = False
    global_deadline: date | None = None
    published_at: date | None = None
    school: str | None = None
    positions: list[ExtractedPosition] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("document_type", mode="before")
    @classmethod
    def validate_doc_type(cls, v: str | None) -> str:
        if v is None: return "unknown"
        v = str(v).strip()
        return v if v in RECRUITMENT_DOC_TYPES else "unknown"


# ── Prompts ─────────────────────────────────────────────

STAGE_A_PROMPT = """你是高校招聘公告分类器。分析以下文档，判断其类型。

## 文档
{input_text}

## 要求
输出 JSON（不要 Markdown）:

{{
    "document_type": "single_position | multi_position_notice | general_talent_notice | postdoc_notice | result_announcement | interview_notice | publicity_notice | non_recruitment | unknown",
    "contains_specific_positions": true/false,
    "position_count_estimate": 数量,
    "has_position_table": true/false,
    "primary_position_source": "body_text | html_table | attachment | none",
    "confidence": 0.0-1.0,
    "reason": "简短判断依据"
}}

注意:
- result_announcement/interview_notice/publicity_notice 不是岗位公告
- non_recruitment: 不是招聘相关内容
- general_talent_notice: 通用人才引进，没有具体岗位
- single_position: 仅1个明确岗位
- multi_position_notice: 多个岗位"""

STAGE_B_PROMPT = """你是高校招聘岗位拆分和字段抽取器。

## 文档
{input_text}

## 公共信息
{global_context}

## 要求
提取**所有**岗位，不得只取第一个。输出 JSON 数组:

[
  {{
    "position_raw": "公告中的原始岗位名称",
    "position_normalized": "标准化岗位名(专任教师/博士后/辅导员/实验员/行政人员)",
    "department": "学院/系/部/研究院/中心/实验室(必须包含这些后缀，找不到填null)",
    "discipline": ["专业1", "专业2"],
    "education_requirement": "博士研究生|博士|硕士研究生及以上|硕士及以上|硕士|本科及以上|本科",
    "job_type": "教学科研岗|科研岗|博士后|辅导员|行政教辅岗|实验技术岗|医疗卫生岗",
    "location": "城市+区 如'广州白云区'",
    "deadline": "YYYY-MM-DD",
    "headcount": 人数,
    "requirements": ["条件1", "条件2"],
    "evidence": {{
      "position": {{"source_id": "...", "quote": "原文", "confidence": 1.0}},
      "department": {{"source_id": "...", "quote": "原文", "confidence": 1.0}},
      "education_requirement": {{"source_id": "...", "quote": "原文", "confidence": 1.0}}
    }},
    "confidence": 0.0-1.0
  }}
]

关键规则:
1. ⚠️ 提取所有岗位，不是只取第一个
2. ⚠️ 每个字段必须有原文证据(evidence.quote)
3. ⚠️ 找不到明确证据的字段填 null
4. 不要把公告标题当岗位名
5. 不要把完整句子当部门名
6. 不要把学校简介中的学历词当岗位要求
7. 公共条件(如统一截止日期)应用到每个岗位"""

STAGE_C_PROMPT = """你是高校招聘数据质量审查器。检查已提取的岗位数据。

## 原文
{input_text}

## 已提取岗位
{positions_json}

## 要求
检查以下问题并输出纠正后的结果:

{{
    "accepted": true/false,
    "issues": ["问题描述"],
    "corrected_positions": [
      {{
        "index": 原有序号,
        "corrected_fields": {{"department": "修正值", ...}},
        "reason": "修正原因"
      }}
    ],
    "missing_positions_warning": true/false,
    "overall_quality": "good | acceptable | poor"
}}

检查项:
1. 是否漏了岗位
2. 是否把非岗位当成岗位
3. department与position是否错位
4. 学历是否来自该岗位行而非别处
5. deadline是否取错
6. 是否把地址当成部门
7. 是否存在无原文依据的编造字段
8. position_normalized 是否与 position_raw 语义一致"""


# ── Extractor ───────────────────────────────────────────

class LlmFieldExtractor:
    """Multi-stage LLM document analyzer for recruitment notices."""

    def __init__(self) -> None:
        self.api_key = LLM_API_KEY
        self.model = LLM_MODEL
        self.base_url = LLM_BASE_URL
        self.client: OpenAI | None = None
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception as exc:
                logger.warning("Failed to init LLM client: %s", exc)

    @property
    def available(self) -> bool:
        return self.client is not None

    def _call_llm(self, prompt: str, max_tokens: int = 1500) -> str:
        assert self.client is not None
        resp = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""

    def _parse_json(self, content: str) -> dict | list | None:
        """Parse JSON from LLM response, handling Markdown wrappers."""
        text = content.strip()
        if "```" in text:
            blocks = re.findall(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
            if blocks: text = blocks[0].strip()
        # Find outermost JSON structure
        if text.startswith("{"):
            end = text.rfind("}")
            if end >= 0: text = text[:end + 1]
        elif text.startswith("["):
            end = text.rfind("]")
            if end >= 0: text = text[:end + 1]
        text = text.replace(""", '"').replace(""", '"')
        text = text.replace("'", "'").replace("'", "'")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("JSON parse failed: %s", exc)
            return None

    # ── Stage A: Document Classification ─────────────

    def classify_document(self, text: str, metadata: dict | None = None) -> dict:
        """Stage A: determine what kind of document this is."""
        if not self.client: return {"document_type": "unknown"}
        input_text = _build_structured_input(text, metadata)
        try:
            prompt = STAGE_A_PROMPT.format(input_text=input_text[:8000])
            content = self._call_llm(prompt, max_tokens=300)
            result = self._parse_json(content)
            if isinstance(result, dict): return result
        except Exception as exc:
            logger.warning("Stage A failed: %s", exc)
        return {"document_type": "unknown"}

    # ── Stage B: Full Position Extraction ─────────────

    def extract_positions(self, text: str, metadata: dict | None = None,
                          global_context: str = "") -> list[dict]:
        """Stage B: extract all positions with evidence."""
        if not self.client: return []
        input_text = _build_structured_input(text, metadata)
        try:
            prompt = STAGE_B_PROMPT.format(
                input_text=input_text[:12000],
                global_context=global_context or "无特殊公共条件",
            )
            content = self._call_llm(prompt, max_tokens=3000)
            result = self._parse_json(content)
            if isinstance(result, list):
                return [self._validate_position(p) for p in result if isinstance(p, dict)]
            if isinstance(result, dict) and "positions" in result:
                return [self._validate_position(p) for p in result["positions"] if isinstance(p, dict)]
        except Exception as exc:
            logger.warning("Stage B failed: %s", exc)
        return []

    def _validate_position(self, raw: dict) -> dict:
        """Validate and clean a single position dict from LLM."""
        try:
            pos = ExtractedPosition(**raw)
            return {
                "position_raw": pos.position_raw,
                "position_normalized": pos.position_normalized,
                "department": pos.department,
                "discipline": pos.discipline if pos.discipline else (
                    [raw.get("discipline")] if isinstance(raw.get("discipline"), str) else []
                ),
                "education_requirement": pos.education_requirement,
                "job_type": pos.job_type,
                "location": pos.location,
                "deadline": pos.deadline.isoformat() if pos.deadline else None,
                "headcount": pos.headcount,
                "requirements": pos.requirements,
                "confidence": pos.confidence,
            }
        except Exception as exc:
            logger.debug("Position validation failed: %s", exc)
            # Return raw with defaults
            return {
                "position_raw": str(raw.get("position_raw", "")),
                "position_normalized": None,
                "department": None,
                "discipline": [],
                "education_requirement": None,
                "job_type": None,
                "location": None,
                "deadline": None,
                "headcount": None,
                "requirements": [],
                "confidence": 0.3,
            }

    # ── Stage C: Quality Review ───────────────────────

    def review_extraction(self, text: str, positions: list[dict],
                          metadata: dict | None = None) -> dict:
        """Stage C: review extracted positions against source text."""
        if not self.client or not positions: return {"accepted": True, "issues": []}
        input_text = _build_structured_input(text, metadata)
        try:
            prompt = STAGE_C_PROMPT.format(
                input_text=input_text[:8000],
                positions_json=json.dumps(positions, ensure_ascii=False, indent=2),
            )
            content = self._call_llm(prompt, max_tokens=1500)
            result = self._parse_json(content)
            if isinstance(result, dict): return result
        except Exception as exc:
            logger.warning("Stage C failed: %s", exc)
        return {"accepted": True, "issues": []}

    # ── Full Pipeline ─────────────────────────────────

    def analyze_document(self, text: str, metadata: dict | None = None) -> dict:
        """Run the full 3-stage analysis pipeline.

        Returns a dict compatible with the old extract() output
        PLUS a 'positions' list for multi-position notices.
        """
        if not self.client:
            return {"positions": [], "warnings": ["LLM not available"]}

        # Stage A: Classification
        doc_type = self.classify_document(text, metadata)
        doc_type_str = doc_type.get("document_type", "unknown")

        # Skip non-recruitment docs early
        non_recruit = {"result_announcement", "interview_notice", "publicity_notice", "non_recruitment"}
        if doc_type_str in non_recruit:
            return {
                "clean_position": None, "department": None,
                "discipline": None, "education_requirement": None,
                "job_type": None, "location": None,
                "deadline": None, "published_at": None,
                "positions": [], "warnings": [f"Document classified as {doc_type_str}, skipping extraction"],
                "document_type": doc_type_str,
            }

        # Stage B: Full extraction
        global_ctx = json.dumps({
            "school": (metadata or {}).get("school", ""),
            "published_at_hint": (metadata or {}).get("published_at_hint", ""),
            "source_url": (metadata or {}).get("source_url", ""),
        }, ensure_ascii=False)
        positions = self.extract_positions(text, metadata, global_ctx)

        # Stage C: Review
        review = self.review_extraction(text, positions, metadata)
        warnings = review.get("issues", [])
        warnings.extend(doc_type.get("reason", "").split("; "))

        # Build backward-compatible single-position output
        single = positions[0] if positions else {}
        return {
            "clean_position": single.get("position_normalized"),
            "department": single.get("department"),
            "discipline": (
                single["discipline"][0] if single.get("discipline") and len(single["discipline"]) > 0 else None
            ),
            "education_requirement": single.get("education_requirement"),
            "job_type": single.get("job_type"),
            "location": single.get("location"),
            "deadline": single.get("deadline"),
            "published_at": doc_type.get("published_at"),
            "positions": positions,
            "warnings": warnings,
            "document_type": doc_type_str,
            "review_accepted": review.get("accepted", True),
        }

    # ── Legacy API ─────────────────────────────────────

    def extract(self, description: str) -> dict[str, str | None]:
        """Legacy single-call extraction. Delegates to analyze_document."""
        result = self.analyze_document(description)
        return {
            "clean_position": result.get("clean_position"),
            "department": result.get("department"),
            "discipline": result.get("discipline"),
            "education_requirement": result.get("education_requirement"),
            "job_type": result.get("job_type"),
            "location": result.get("location"),
            "deadline": result.get("deadline"),
            "published_at": result.get("published_at"),
        }


# ── Helpers ─────────────────────────────────────────────

def _build_structured_input(text: str, metadata: dict | None = None) -> str:
    """Build structured input from flat text + optional metadata.

    If metadata contains 'tables' or 'sections', format them.
    Otherwise wrap the text with page-level metadata.
    """
    parts = []
    if metadata:
        parts.append(f"## 页面信息")
        parts.append(f"- 标题: {metadata.get('title', '')}")
        parts.append(f"- URL: {metadata.get('source_url', '')}")
        parts.append(f"- 学校: {metadata.get('school', '')}")
        parts.append(f"- 发布时间提示: {metadata.get('published_at_hint', '')}")
        parts.append("")

    # Sections from HTML parsing
    sections = metadata.get("sections") if metadata else None
    if sections:
        parts.append("## 文档结构")
        for sec in sections:
            heading = sec.get("heading", "")
            content = sec.get("text", "")[:3000]
            parts.append(f"### {heading}")
            parts.append(content)
            parts.append("")
    else:
        parts.append("## 正文")
        parts.append(text[:12000])

    # Tables from HTML
    tables = metadata.get("tables") if metadata else None
    if tables:
        parts.append("## HTML表格")
        for i, tbl in enumerate(tables):
            hdrs = tbl.get("headers", [])
            rows = tbl.get("rows", [])[:50]
            parts.append(f"### 表格{i+1}: {' | '.join(hdrs)}")
            for row in rows[:50]:
                parts.append(" | ".join(str(c) for c in row))
            parts.append("")

    return "\n".join(parts)


# Singleton
_extractor: LlmFieldExtractor | None = None


def get_llm_extractor() -> LlmFieldExtractor:
    global _extractor
    if _extractor is None:
        _extractor = LlmFieldExtractor()
    return _extractor
