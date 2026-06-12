from datetime import date

from university_recruitment.models import MatchResult, RecruitmentJob, UserProfile


class RuleMatcher:
    def rank(self, user: UserProfile, jobs: list[RecruitmentJob], limit: int = 10) -> list[MatchResult]:
        results = [self.match(user, job) for job in self._deduplicate_jobs(jobs)]
        results.sort(key=lambda item: item.match_score, reverse=True)
        return results[:limit]

    def match(self, user: UserProfile, job: RecruitmentJob) -> MatchResult:
        score = 40
        reasons: list[str] = []
        risks: list[str] = []
        actions: list[str] = []

        searchable_text = self._join_text(
            job.school,
            job.position,
            job.department,
            job.discipline,
            job.location,
            job.education_requirement,
            job.job_type,
            job.description,
        )

        if job.deadline and job.deadline < date.today():
            score -= 60
            risks.append("报名截止时间已过")
        elif job.deadline:
            reasons.append(f"报名截止时间为 {job.deadline.isoformat()}")
        else:
            risks.append("公告未提取到明确截止时间")

        if user.education and job.education_requirement:
            if user.education in job.education_requirement or job.education_requirement in user.education:
                score += 15
                reasons.append("学历条件与岗位要求匹配")
            else:
                risks.append("学历要求需要人工确认")

        if user.target_locations and job.location:
            if any(location in job.location for location in user.target_locations):
                score += 25
                reasons.append("工作地点符合用户偏好")
            else:
                score -= 35
                risks.append("工作地点与用户偏好不完全一致")

        keyword_hits = self._count_hits([user.major, user.research_direction, *user.keywords], searchable_text)
        if keyword_hits:
            score += min(keyword_hits * 8, 24)
            reasons.append("专业、研究方向或关键词与公告内容存在交集")
        else:
            risks.append("未从公告中匹配到明显的专业或研究方向关键词")

        preference_hits = self._count_hits(user.job_preferences, searchable_text)
        if preference_hits:
            score += min(preference_hits * 6, 12)
            reasons.append("岗位类型与用户偏好相关")

        constraint_hits = self._count_hits(user.constraints, searchable_text)
        if constraint_hits:
            score += min(constraint_hits * 4, 8)
            reasons.append("公告中出现了用户关注的限制条件关键词")
        elif user.constraints:
            risks.append("用户限制条件需要进一步核对公告原文")

        if risks:
            actions.append("打开原始公告确认风险项")
        actions.append("投递前根据岗位方向调整简历和研究成果表述")

        return MatchResult(
            job=job,
            match_score=max(0, min(score, 100)),
            match_reasons=reasons,
            potential_risks=risks,
            suggested_actions=actions,
        )

    @staticmethod
    def _join_text(*values: str | None) -> str:
        return " ".join(value for value in values if value).lower()

    @staticmethod
    def _count_hits(values: list[str], text: str) -> int:
        return sum(1 for value in values if value and value.lower() in text)

    @staticmethod
    def _deduplicate_jobs(jobs: list[RecruitmentJob]) -> list[RecruitmentJob]:
        seen: set[tuple[str, str]] = set()
        unique_jobs: list[RecruitmentJob] = []
        for job in jobs:
            key = (job.school.strip(), job.position.strip())
            if key in seen:
                continue
            seen.add(key)
            unique_jobs.append(job)
        return unique_jobs
