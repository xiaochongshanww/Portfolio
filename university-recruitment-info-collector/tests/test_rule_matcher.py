"""Tests for rule matcher with education levels and constraint logic."""

from datetime import date

from university_recruitment.matching.rule_matcher import RuleMatcher
from university_recruitment.models import RecruitmentJob, SourceType, UserProfile


def make_job(**overrides) -> RecruitmentJob:
    defaults = {
        "id": str(overrides.get("id", "test-job")),
        "school": "测试大学",
        "position": "教师",
        "department": "计算机学院",
        "discipline": "计算机科学与技术",
        "location": "广州",
        "education_requirement": "博士",
        "job_type": "教学科研岗",
        "deadline": date(2027, 12, 31),
        "source_type": SourceType.UNIVERSITY_TALENT_SITE,
        "source_name": "测试源",
        "source_url": f"https://example.edu.cn/{overrides.get('id', 'test-job')}",
        "published_at": date(2026, 6, 1),
        "description": "招聘计算机方向教师，从事人工智能研究。",
    }
    defaults.update({k: v for k, v in overrides.items() if k != "id"})
    return RecruitmentJob(**defaults)


def make_user(**overrides) -> UserProfile:
    return UserProfile(
        education=overrides.get("education", "博士"),
        major=overrides.get("major", "计算机科学与技术"),
        research_direction=overrides.get("research_direction", "人工智能"),
        keywords=overrides.get("keywords", ["机器学习", "数据挖掘"]),
        target_locations=overrides.get("target_locations", ["广州"]),
        target_school_types=overrides.get("target_school_types", ["双一流"]),
        job_preferences=overrides.get("job_preferences", ["教学科研岗"]),
        constraints=overrides.get("constraints", ["编制"]),
    )


class TestRuleMatcher:
    def test_score_starts_from_zero(self):
        matcher = RuleMatcher()
        user = make_user()
        job = make_job()
        result = matcher.match(user, job)
        # Score should be positive (from education, location, keywords)
        assert result.match_score > 0

    def test_expired_job_hard_failure(self):
        matcher = RuleMatcher()
        user = make_user()
        job = make_job(deadline=date(2020, 1, 1))
        result = matcher.match(user, job)
        assert not result.hard_constraint_passed
        assert any("截止时间已过" in f for f in result.hard_constraint_failures)

    def test_no_deadline_not_expired(self):
        matcher = RuleMatcher()
        user = make_user()
        job = make_job(deadline=None)
        result = matcher.match(user, job)
        assert result.hard_constraint_passed

    def test_education_satisfies(self):
        matcher = RuleMatcher()
        user = make_user(education="博士")
        job = make_job(education_requirement="硕士及以上")
        result = matcher.match(user, job)
        assert result.hard_constraint_passed

    def test_education_mismatch_hard_failure(self):
        matcher = RuleMatcher()
        user = make_user(education="硕士")
        job = make_job(education_requirement="博士")
        result = matcher.match(user, job)
        assert not result.hard_constraint_passed
        assert any("学历不满足" in f for f in result.hard_constraint_failures)

    def test_location_mismatch(self):
        matcher = RuleMatcher()
        user = make_user(target_locations=["北京"])
        job = make_job(location="广州")
        result = matcher.match(user, job)
        assert any("不完全一致" in r for r in result.potential_risks)

    def test_score_clamped_max(self):
        matcher = RuleMatcher()
        user = make_user()
        job = make_job()
        result = matcher.match(user, job)
        assert 0 <= result.match_score <= 100

    def test_score_clamped_min(self):
        matcher = RuleMatcher()
        user = make_user(target_locations=["北京"])
        job = make_job(location="上海", deadline=date(2020, 1, 1))
        result = matcher.match(user, job)
        # With hard failure, score can be low
        assert result.match_score >= 0

    def test_no_keyword_hits(self):
        matcher = RuleMatcher()
        user = make_user(major="考古学", keywords=["古代史"], research_direction="考古")
        job = make_job()
        result = matcher.match(user, job)
        assert any("未从公告中匹配" in r for r in result.potential_risks)

    def test_deadline_reason(self):
        matcher = RuleMatcher()
        user = make_user()
        job = make_job(deadline=date(2027, 6, 15))
        result = matcher.match(user, job)
        assert any("2027-06-15" in r for r in result.match_reasons)

    def test_constraint_positive(self):
        """编制 should be satisfied when 纳入事业编制 appears."""
        matcher = RuleMatcher()
        user = make_user(constraints=["编制"])
        job = make_job(description="纳入事业编制管理，提供编制")
        result = matcher.match(user, job)
        assert any("编制" in r for r in result.match_reasons)

    def test_constraint_negative(self):
        """编制 should NOT be satisfied when 劳务派遣 appears."""
        matcher = RuleMatcher()
        user = make_user(constraints=["编制"])
        job = make_job(description="本次招聘为劳务派遣，不提供编制")
        result = matcher.match(user, job)
        assert any("编制" in r for r in result.potential_risks)

    def test_constraint_unknown(self):
        """编制 unknown when no mention in text."""
        matcher = RuleMatcher()
        user = make_user(constraints=["编制"])
        job = make_job(description="招聘计算机方向教师")
        result = matcher.match(user, job)
        assert any("编制" in r for r in result.potential_risks)

    def test_school_type_matching(self):
        matcher = RuleMatcher()
        user = make_user(target_school_types=["双一流"])
        job = make_job(school="中山大学")  # 中山大学 is double-first-class
        result = matcher.match(user, job)
        assert any("学校类型" in r for r in result.match_reasons)

    def test_confidence_score_present(self):
        matcher = RuleMatcher()
        user = make_user()
        job = make_job()
        result = matcher.match(user, job)
        assert 0 <= result.confidence_score <= 100

    def test_hard_constraint_failures_filtered(self):
        matcher = RuleMatcher()
        user = make_user(education="本科")
        jobs = [
            make_job(id="j1", education_requirement="博士", source_url="https://x.com/1"),
            make_job(id="j2", education_requirement="本科及以上", source_url="https://x.com/2"),
        ]
        results = matcher.rank(user, jobs, include_hard_failures=False)
        assert len(results) == 1
        assert results[0].job.id == "j2"


class TestRank:
    def test_orders_by_score_desc(self):
        matcher = RuleMatcher()
        user = make_user()
        j1 = make_job(id="a", source_url="https://x.com/a", location="广州")
        j2 = make_job(id="b", source_url="https://x.com/b", location="北京")
        results = matcher.rank(user, [j1, j2])
        assert results[0].match_score >= results[-1].match_score

    def test_limit(self):
        matcher = RuleMatcher()
        user = make_user()
        jobs = [make_job(id=f"j{i}", source_url=f"https://x.com/{i}") for i in range(10)]
        results = matcher.rank(user, jobs, limit=3)
        assert len(results) <= 3

    def test_deduplicate(self):
        matcher = RuleMatcher()
        user = make_user()
        j1 = make_job(id="a", source_url="https://x.com/a")
        # Second job from different source but same ID won't happen with stable IDs
        # Test: same job (same ID) appears twice — should be deduplicated
        results = matcher.rank(user, [j1, j1])
        assert len(results) == 1

    def test_empty_jobs(self):
        matcher = RuleMatcher()
        user = make_user()
        results = matcher.rank(user, [])
        assert len(results) == 0
