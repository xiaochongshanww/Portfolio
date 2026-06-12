import json
import logging
from typing import Any

from openai import OpenAI

from university_recruitment.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from university_recruitment.models import MatchResult, UserProfile

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """你是一个高校求职顾问，正在帮助一位用户分析招聘岗位与其背景的匹配度。

## 用户信息
- 最高学历：{education}
- 专业：{major}
- 研究方向：{research_direction}
- 个人关键词：{keywords}
- 期望地区：{target_locations}
- 期望学校类型：{target_school_types}
- 岗位偏好：{job_preferences}
- 限制条件：{constraints}

## 招聘岗位信息
- 学校：{school}
- 岗位：{position}
- 学院/部门：{department}
- 学科方向：{discipline}
- 工作地点：{location}
- 学历要求：{education_requirement}
- 岗位类型：{job_type}
- 截止日期：{deadline}
- 公告原文：{description}

## 分析要求
请从以下维度分析该岗位与用户的匹配情况，以 JSON 格式输出（不要输出其他内容）：

```json
{{
    "match_reasons": ["匹配理由1", "匹配理由2", ...],
    "potential_risks": ["潜在风险1", ...],
    "suggested_actions": ["建议操作1", ...],
    "llm_summary": "一段综合评估摘要（100-200字）"
}}
```

分析要点：
1. 用户研究方向与岗位学科方向的相关度
2. 学校地理位置与用户期望地区的匹配度：评估通勤可行性、是否需要跨城搬迁、该地区生活成本与薪资水平的匹配
3. 公告中隐含的额外要求（如年龄、职称、论文数量等）
4. 用户条件与岗位要求的差距
5. 针对性的申请建议和材料准备方向，**特别是基于地理位置的建议**（如：是否需要提前租房、该地区的交通便利程度、是否建议同时关注邻近城市的类似岗位等）
"""


class LlmMatcher:
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

    def enrich(self, user: UserProfile, results: list[MatchResult]) -> list[MatchResult]:
        if not self.client:
            for result in results:
                result.llm_summary = (
                    "LLM 分析未启用：未设置 LLM_API_KEY 环境变量。"
                    "当前结果来自规则匹配。"
                )
            return results

        for result in results:
            try:
                self._enrich_single(user, result)
            except Exception as exc:
                logger.warning("LLM analysis failed for job %s: %s", result.job.id, exc)
                result.llm_summary = "LLM 分析暂不可用，当前结果来自规则匹配。"
        return results

    def _enrich_single(self, user: UserProfile, result: MatchResult) -> None:
        assert self.client is not None
        prompt = self._build_prompt(user, result)
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content or ""
        parsed = self._parse_response(content)
        if parsed.get("match_reasons"):
            result.match_reasons = parsed["match_reasons"]
        if parsed.get("potential_risks"):
            result.potential_risks = parsed["potential_risks"]
        if parsed.get("suggested_actions"):
            result.suggested_actions = parsed["suggested_actions"]
        result.llm_summary = parsed.get("llm_summary")

    def _build_prompt(self, user: UserProfile, result: MatchResult) -> str:
        job = result.job
        return ANALYSIS_PROMPT.format(
            education=user.education,
            major=user.major,
            research_direction=user.research_direction,
            keywords="、".join(user.keywords) if user.keywords else "无",
            target_locations="、".join(user.target_locations) if user.target_locations else "不限",
            target_school_types="、".join(user.target_school_types) if user.target_school_types else "不限",
            job_preferences="、".join(user.job_preferences) if user.job_preferences else "不限",
            constraints="、".join(user.constraints) if user.constraints else "无",
            school=job.school,
            position=job.position,
            department=(job.department or "未说明"),
            discipline=(job.discipline or "未说明"),
            location=(job.location or "未说明"),
            education_requirement=(job.education_requirement or "未说明"),
            job_type=(job.job_type or "未说明"),
            deadline=job.deadline.isoformat() if job.deadline else "未说明",
            description=job.description[:2000] if job.description else "无",
        )

    @staticmethod
    def _parse_response(content: str) -> dict[str, Any]:
        try:
            text = content.strip()

            json_start = text.find("{")
            if json_start == -1:
                raise ValueError("No JSON object found in response")

            json_end = text.rfind("}")
            text = text[json_start : json_end + 1]

            text = text.replace("“", '"').replace("”", '"')
            text = text.replace("‘", "'").replace("’", "'")

            result = json.loads(text)
            if isinstance(result, dict):
                return {
                    "match_reasons": result.get("match_reasons", []),
                    "potential_risks": result.get("potential_risks", []),
                    "suggested_actions": result.get("suggested_actions", []),
                    "llm_summary": result.get("llm_summary", ""),
                }
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to parse LLM response: %s", exc)
        return {"llm_summary": content[:300]}
