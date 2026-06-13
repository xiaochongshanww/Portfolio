"""LLM primary field extraction for recruitment job descriptions.

This module uses the DeepSeek API as the *primary* parser to extract
structured fields from job description text. Regex-based extraction
runs as a fast fallback when LLM is unavailable or errors out.
"""

import json
import logging
from datetime import date
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field, field_validator

from university_recruitment.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)

# Allowed enum values
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


class LlmExtractedFields(BaseModel):
    """Validated LLM extraction output."""
    clean_position: str | None = None
    department: str | None = None
    discipline: str | None = None
    education_requirement: str | None = None
    job_type: str | None = None
    location: str | None = None
    deadline: date | None = None
    published_at: date | None = None

    @field_validator("education_requirement", mode="before")
    @classmethod
    def validate_education(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        if v in VALID_EDUCATION_REQUIREMENTS:
            return v
        logger.debug("Rejected invalid education_requirement from LLM: %s", v)
        return None

    @field_validator("job_type", mode="before")
    @classmethod
    def validate_job_type(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        if v in VALID_JOB_TYPES:
            return v
        logger.debug("Rejected invalid job_type from LLM: %s", v)
        return None

    @field_validator("department", mode="before")
    @classmethod
    def validate_department(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        if v in REJECTED_DEPARTMENT_VALUES:
            logger.debug("Rejected blacklisted department from LLM: %s", v)
            return None
        if not any(v.endswith(suffix) for suffix in VALID_DEPARTMENT_SUFFIXES):
            logger.debug("Rejected department without valid suffix from LLM: %s", v)
            return None
        return v

EXTRACTION_PROMPT = """你是一个高校招聘信息解析专家。请从以下招聘公告原文中精准提取结构化字段。

## 公告原文
{description}

## 提取字段
请仔细阅读公告，提取以下信息以 JSON 格式输出（只输出 JSON，不要其他内容）：

```json
{{
    "clean_position": "核心岗位名称（去掉学校名、发布日期、"公开招聘"、"招聘公告"等冗余词，只保留如"专任教师"、"博士后"、"辅导员"等核心岗位描述）。如果公告只是一个通用招聘汇总页面而不是具体岗位，填 null",
    "department": "招聘的学院/系/研究院/实验室/部门名称。必须包含"学院"、"系"、"部"、"研究院"、"中心"、"实验室"之一，否则填 null。如果部门是"用人部门"、"招聘单位"、"各学院"这种模糊表述，也填 null",
    "discipline": "学科方向或专业要求，如：计算机科学与技术、人工智能、临床医学、经济学。如果没有明确说明填 null",
    "education_requirement": "学历要求，取值仅限：博士研究生 / 博士 / 硕士研究生及以上 / 硕士及以上 / 硕士 / 本科及以上 / 本科。如果只提到"原则上要求"也是有效要求",
    "job_type": "岗位类型，取值仅限：教学科研岗 / 科研岗 / 博士后 / 辅导员 / 行政教辅岗 / 实验技术岗 / 医疗卫生岗",
    "location": "工作地点，格式为 城市+区，如'广州天河区'、'珠海香洲区'。如无法确定具体区，至少给出城市名",
    "deadline": "报名/申请截止日期，格式 YYYY-MM-DD，如无法确定填 null",
    "published_at": "公告发布日期，格式 YYYY-MM-DD，如无法确定填 null"
}}
```

## 关键注意事项
1. ⚠️ **department 严格校验**：必须是包含 学院/系/部/研究院/中心/实验室 的具体名称。找不到就填 null，绝不编造！"用人部门"、"招聘单位"、"各学院"、"是直属教育部"这类不是部门名，必须填 null
2. ⚠️ **无信息则 null**：任何字段在公告中找不到明确信息时，填 null，不要猜测或编造
3. 仔细区分"报名时间"和"公告发布日期"，不要混淆
4. deadline 取最晚的那个截止日期（如果有多个时间段）
5. 学历要求如果写"原则上要求博士"，也应提取为"博士"
6. 如果公告描述的是多个完全不同类型的岗位，取第一个或最主要的"""



class LlmFieldExtractor:
    """Uses LLM as the primary parser for recruitment job fields."""

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

    def extract(self, description: str) -> dict[str, str | None]:
        """Primary extraction: use LLM to extract all fields from a job description.

        Args:
            description: The full text of the job posting (up to 4000 chars).

        Returns:
            Dict with keys: clean_position, department, discipline,
            education_requirement, job_type, location, deadline, published_at.
            Each value is a string or None.
        """
        if not self.client:
            return {}

        text = description[:4000]

        try:
            prompt = EXTRACTION_PROMPT.format(description=text)
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=800,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content or ""
            return self._parse_response(content)
        except Exception as exc:
            logger.warning("LLM extraction failed: %s", exc)
            return {}

    @staticmethod
    def _parse_response(content: str) -> dict[str, str | None]:
        """Parse LLM response, extracting JSON from Markdown if needed."""
        try:
            text = content.strip()

            # Try to extract JSON from Markdown code blocks
            json_str = text
            if "```" in text:
                # Find JSON inside code blocks
                import re
                blocks = re.findall(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
                if blocks:
                    json_str = blocks[0].strip()

            # Find JSON object boundaries
            json_start = json_str.find("{")
            if json_start == -1:
                return {}
            json_end = json_str.rfind("}")
            json_str = json_str[json_start: json_end + 1]
            json_str = json_str.replace(""", '"').replace(""", '"')
            json_str = json_str.replace("'", "'").replace("'", "'")

            result = json.loads(json_str)
            if not isinstance(result, dict):
                return {}

            # Handle date fields — convert string to date
            for date_field in ("deadline", "published_at"):
                val = result.get(date_field)
                if val and isinstance(val, str) and val.strip():
                    try:
                        result[date_field] = date.fromisoformat(val.strip())
                    except (ValueError, TypeError):
                        result[date_field] = None
                else:
                    result[date_field] = None

            # Validate through Pydantic model
            validated = LlmExtractedFields(**result)
            return {
                "clean_position": validated.clean_position,
                "department": validated.department,
                "discipline": validated.discipline,
                "education_requirement": validated.education_requirement,
                "job_type": validated.job_type,
                "location": validated.location,
                "deadline": validated.deadline.isoformat() if validated.deadline else None,
                "published_at": validated.published_at.isoformat() if validated.published_at else None,
            }
        except Exception as exc:
            logger.warning("Failed to parse/validate LLM response: %s", exc)
            return {}


# Singleton
_extractor: LlmFieldExtractor | None = None


def get_llm_extractor() -> LlmFieldExtractor:
    global _extractor
    if _extractor is None:
        _extractor = LlmFieldExtractor()
    return _extractor
