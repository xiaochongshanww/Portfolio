"""LLM semantic reranker — batch processing of top rule-matched candidates."""

import json
import logging
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from university_recruitment.config import (
    LLM_API_KEY, LLM_BASE_URL, LLM_MAX_JOBS, LLM_MODEL, LLM_TIMEOUT_SECONDS,
)
from university_recruitment.models import MatchResult, UserProfile

logger = logging.getLogger(__name__)


class LlmJobScore(BaseModel):
    """Validated LLM response for a single job."""
    job_id: str
    semantic_score: int = Field(default=50, ge=0, le=100)
    match_reasons: list[str] = Field(default_factory=list)
    potential_risks: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    llm_summary: str = ""


BATCH_PROMPT = """你是一个高校求职顾问。用户提供了个人背景，系统已用规则筛选出若干候选岗位。请对每个岗位进行语义分析。

## 用户信息
- 最高学历：{education}
- 专业：{major}
- 研究方向：{research_direction}
- 个人关键词：{keywords}
- 期望地区：{target_locations}
- 期望学校类型：{target_school_types}
- 岗位偏好：{job_preferences}
- 限制条件：{constraints}

## 候选岗位
{candidates_json}

## 分析要求
请以 JSON 数组格式输出（只输出 JSON，不要其他内容），对每个岗位给出：

```json
[
  {{
    "job_id": "与输入一致的 job_id",
    "semantic_score": 0-100,
    "match_reasons": ["匹配理由..."],
    "potential_risks": ["潜在风险..."],
    "suggested_actions": ["建议..."],
    "llm_summary": "一段80-150字的综合评估摘要"
  }}
]
```

分析要点：
1. 用户研究方向与岗位学科方向的相关度
2. 地理位置匹配度、通勤与搬迁成本
3. 公告中隐含的额外要求（年龄、职称、论文等）
4. 用户条件与岗位要求的差距
5. 针对性申请建议
6. semantic_score: 50=中性, 70+=较匹配, 85+=高度匹配, <40=不太匹配
"""


class LlmMatcher:
    def __init__(self) -> None:
        self.api_key = LLM_API_KEY
        self.model = LLM_MODEL
        self.base_url = LLM_BASE_URL
        self.client: OpenAI | None = None
        if self.api_key:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=LLM_TIMEOUT_SECONDS,
                )
            except Exception as exc:
                logger.warning("LLM client init failed: %s", exc)

    @property
    def available(self) -> bool:
        return self.client is not None

    def enrich(
        self, user: UserProfile, results: list[MatchResult]
    ) -> list[MatchResult]:
        """Batch LLM enrichment of rule-matched candidates.

        Maximum LLM_MAX_JOBS candidates are sent in one batch request.
        """
        if not self.client or not results:
            for r in results:
                if not r.llm_summary:
                    r.llm_summary = "LLM 未启用或无可分析岗位"
            return results

        candidates = results[:LLM_MAX_JOBS]
        try:
            llm_scores = self._batch_analyze(user, candidates)
        except Exception as exc:
            logger.warning("LLM batch analysis failed: %s", exc)
            for r in results:
                if not r.llm_summary:
                    r.llm_summary = "AI 分析暂不可用，当前结果来自规则匹配"
            return results

        # Merge LLM results
        score_map: dict[str, LlmJobScore] = {s.job_id: s for s in llm_scores}
        for result in results:
            llm_score = score_map.get(result.job.id)
            if llm_score is None:
                if not result.llm_summary:
                    result.llm_summary = "LLM 未对该岗位返回分析"
                continue

            # Composite score: 70% rule + 30% semantic
            result.match_score = int(
                result.match_score * 0.7 + llm_score.semantic_score * 0.3
            )
            if llm_score.match_reasons:
                result.match_reasons = llm_score.match_reasons
            if llm_score.potential_risks:
                result.potential_risks = (
                    result.potential_risks + llm_score.potential_risks
                )
            if llm_score.suggested_actions:
                result.suggested_actions = llm_score.suggested_actions
            result.llm_summary = llm_score.llm_summary

        return results

    def _batch_analyze(
        self, user: UserProfile, candidates: list[MatchResult]
    ) -> list[LlmJobScore]:
        """Send all candidates in one LLM request."""
        candidates_data = []
        for r in candidates:
            j = r.job
            candidates_data.append({
                "job_id": j.id,
                "school": j.school,
                "position": j.position,
                "department": j.department or "未说明",
                "discipline": j.discipline or "未说明",
                "location": j.location or "未说明",
                "education_requirement": j.education_requirement or "未说明",
                "job_type": j.job_type or "未说明",
                "deadline": j.deadline.isoformat() if j.deadline else "未说明",
                "description": (j.description or "")[:1500],
            })

        prompt = BATCH_PROMPT.format(
            education=user.education,
            major=user.major,
            research_direction=user.research_direction,
            keywords="、".join(user.keywords) if user.keywords else "无",
            target_locations="、".join(user.target_locations) if user.target_locations else "不限",
            target_school_types="、".join(user.target_school_types) if user.target_school_types else "不限",
            job_preferences="、".join(user.job_preferences) if user.job_preferences else "不限",
            constraints="、".join(user.constraints) if user.constraints else "无",
            candidates_json=json.dumps(candidates_data, ensure_ascii=False, indent=2),
        )

        assert self.client is not None
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content or ""

        # Parse and validate
        try:
            items = self._parse_batch_response(content)
            validated = []
            for item in items:
                try:
                    validated.append(LlmJobScore(**item))
                except ValidationError as exc:
                    logger.warning("LLM response validation failed for job: %s", exc)
            return validated
        except Exception as exc:
            logger.warning("Failed to parse LLM batch response: %s", exc)
            return []

    @staticmethod
    def _parse_batch_response(content: str) -> list[dict[str, Any]]:
        text = content.strip()
        # Find the outermost JSON array bounds
        json_start = text.find("[")
        if json_start == -1:
            raise ValueError("No JSON array in LLM response")
        json_end = text.rfind("]")
        if json_end == -1 or json_end <= json_start:
            raise ValueError("Malformed JSON array in LLM response")
        text = text[json_start: json_end + 1]
        # Normalize curly/smart quotes that LLMs sometimes emit
        text = (
            text
            .replace("\u201c", '"').replace("\u201d", '"')  # "" → "
            .replace("\u2018", "'").replace("\u2019", "'")  # '' → '
            .replace("\uff02", '"')                          # ＂ → "
        )
        try:
            result = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON decode failed: {exc}") from exc
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
        raise ValueError(f"Unexpected LLM response type: {type(result)}")
