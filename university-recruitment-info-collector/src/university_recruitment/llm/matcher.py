from university_recruitment.models import MatchResult, UserProfile


class LlmMatcher:
    """Placeholder for future LLM-based semantic analysis."""

    def enrich(self, user: UserProfile, results: list[MatchResult]) -> list[MatchResult]:
        for result in results:
            result.llm_summary = (
                "LLM 分析尚未接入；当前结果来自规则匹配。"
                "后续可在这里补充语义匹配、风险解释和申请建议。"
            )
        return results
