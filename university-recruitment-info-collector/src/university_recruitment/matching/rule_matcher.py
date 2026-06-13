"""Rule-based job matcher with hard/soft scoring."""

from datetime import date

from university_recruitment.models import (
    EducationLevel,
    MatchResult,
    RecruitmentJob,
    UserProfile,
    education_satisfies,
    parse_education_level,
)
from university_recruitment.school_metadata import school_matches_type


class RuleMatcher:
    def rank(
        self,
        user: UserProfile,
        jobs: list[RecruitmentJob],
        limit: int = 10,
        include_hard_failures: bool = False,
    ) -> list[MatchResult]:
        """Rank jobs, filtering hard constraint failures unless requested."""
        deduped = self._deduplicate_jobs(jobs)
        results = [self.match(user, job) for job in deduped]

        if not include_hard_failures:
            results = [r for r in results if r.hard_constraint_passed]

        results.sort(key=lambda r: (r.match_score, r.confidence_score), reverse=True)
        return results[:limit]

    def match(self, user: UserProfile, job: RecruitmentJob) -> MatchResult:
        score = 0
        reasons: list[str] = []
        risks: list[str] = []
        actions: list[str] = []
        hard_failures: list[str] = []
        confidence = 100  # starts at 100, reduced for missing data

        searchable = self._join_text(
            job.school, job.position, job.normalized_position, job.department,
            job.discipline, job.location, job.education_requirement,
            job.job_type, job.description,
        )

        # ── 1. Hard constraint: Deadline ──
        if job.deadline and job.deadline < date.today():
            hard_failures.append("报名截止时间已过")
        elif job.deadline:
            reasons.append(f"报名截止时间为 {job.deadline.isoformat()}")
            score += 5
        else:
            risks.append("公告未提取到明确截止时间")
            confidence -= 10

        # ── 2. Hard constraint: Education ──
        user_edu = parse_education_level(user.education)
        job_edu = parse_education_level(job.education_requirement)
        if user_edu != EducationLevel.UNKNOWN and job_edu != EducationLevel.UNKNOWN:
            satisfies = education_satisfies(user_edu, job_edu)
            if satisfies is True:
                score += 15
                reasons.append("学历条件满足岗位要求")
            elif satisfies is False:
                hard_failures.append(
                    f"学历不满足：需要{job.education_requirement}，用户为{user.education}"
                )
            else:
                risks.append("学历要求需要人工确认")
                confidence -= 5
        else:
            if not job.education_requirement:
                confidence -= 8
            risks.append("无法自动判断学历匹配")
            confidence -= 5

        # ── 3. Location ──
        if user.target_locations and job.location:
            if any(loc in (job.location or "") for loc in user.target_locations):
                score += 25
                reasons.append("工作地点符合用户偏好")
            else:
                score -= 5
                risks.append(f"工作地点({job.location})与用户偏好不完全一致")
        elif not job.location:
            confidence -= 5

        # ── 4. School type ──
        if user.target_school_types and job.school:
            type_hits = sum(
                1 for t in user.target_school_types
                if school_matches_type(job.school, t)
            )
            if type_hits:
                score += min(type_hits * 8, 16)
                reasons.append("学校类型符合用户偏好")
            else:
                score -= 5
                risks.append("学校类型与用户偏好不完全一致")
        elif user.target_school_types:
            risks.append("无法判断学校类型匹配")
            confidence -= 5

        # ── 5. Keywords ──
        keyword_hits = self._count_hits(
            [user.major, user.research_direction, *user.keywords], searchable
        )
        if keyword_hits:
            score += min(keyword_hits * 6, 18)
            reasons.append("专业、研究方向或关键词与公告内容存在交集")
        else:
            risks.append("未从公告中匹配到明显的专业或研究方向关键词")

        # ── 6. Job preferences ──
        pref_hits = self._count_hits(user.job_preferences, searchable)
        if pref_hits:
            score += min(pref_hits * 5, 10)
            reasons.append("岗位类型与用户偏好相关")

        # ── 7. Constraints with positive/negative/unknown ──
        for constraint in user.constraints:
            result = self._evaluate_constraint(constraint, searchable)
            if result == "satisfied":
                score += 5
                reasons.append(f"限制条件「{constraint}」在公告中体现")
            elif result == "not_satisfied":
                risks.append(f"限制条件「{constraint}」公告中未满足或明确排除")
            else:  # unknown
                risks.append(f"限制条件「{constraint}」需要人工核对公告原文")
                confidence -= 3

        # ── 8. Actions ──
        if risks:
            actions.append("打开原始公告确认风险项")
        actions.append("投递前根据岗位方向调整简历和研究成果表述")

        # ── Final score ──
        final_score = max(0, min(score, 100))

        return MatchResult(
            job=job,
            match_score=final_score,
            match_reasons=reasons,
            potential_risks=risks,
            suggested_actions=actions,
            confidence_score=max(0, confidence),
            hard_constraint_passed=len(hard_failures) == 0,
            hard_constraint_failures=hard_failures,
        )

    # ── Constraint evaluation ───────────────────────────

    @staticmethod
    def _evaluate_constraint(constraint: str, text: str) -> str:
        """Evaluate a constraint against job text.

        Returns: 'satisfied', 'not_satisfied', or 'unknown'
        """
        constraint_lower = constraint.strip().lower()
        text_lower = text.lower()

        # 编制 / 事业编制
        if constraint_lower in ("编制", "事业编制"):
            negative_patterns = (
                "不提供编制", "无编制", "非事业编制", "非事业编",
                "劳务派遣", "合同制", "编外", "不纳入事业编制",
            )
            if any(p in text_lower for p in negative_patterns):
                return "not_satisfied"
            positive_patterns = (
                "事业编制", "纳入编制", "提供编制", "入编",
                "办理入编", "编制内", "事业编",
            )
            if any(p in text_lower for p in positive_patterns):
                return "satisfied"
            return "unknown"

        # 年龄
        if "年龄" in constraint_lower:
            if "年龄" in text_lower or "周岁" in text_lower:
                return "satisfied"
            return "unknown"

        # 应届
        if "应届" in constraint_lower:
            if "应届" in text_lower:
                return "satisfied"
            if any(p in text_lower for p in ("往届", "非应届", "社会人员")):
                return "not_satisfied"
            return "unknown"

        # 职称
        if "职称" in constraint_lower:
            if any(p in text_lower for p in ("职称", "副高", "正高", "教授", "副教授", "讲师")):
                return "satisfied"
            return "unknown"

        # 工作经历
        if any(kw in constraint_lower for kw in ("工作经历", "工作经验")):
            if any(p in text_lower for p in ("工作经历", "工作经验", "工作年限", "从业")):
                return "satisfied"
            return "unknown"

        # 论文要求
        if "论文" in constraint_lower:
            if any(p in text_lower for p in ("论文", "SCI", "SSCI", "CSSCI", "发表")):
                return "satisfied"
            return "unknown"

        # Fallback: simple keyword match
        if constraint_lower in text_lower:
            return "satisfied"
        return "unknown"

    # ── Helpers ─────────────────────────────────────────

    @staticmethod
    def _join_text(*values: str | None) -> str:
        return " ".join(v for v in values if v).lower()

    @staticmethod
    def _count_hits(values: list[str], text: str) -> int:
        return sum(1 for v in values if v and v.lower() in text)

    @staticmethod
    def _deduplicate_jobs(jobs: list[RecruitmentJob]) -> list[RecruitmentJob]:
        seen: set[str] = set()
        unique: list[RecruitmentJob] = []
        for job in jobs:
            if job.id in seen:
                continue
            seen.add(job.id)
            unique.append(job)
        return unique
