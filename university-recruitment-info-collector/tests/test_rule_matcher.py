"""Tests for rule matcher (matching/rule_matcher.py)."""

from datetime import date

from university_recruitment.matching.rule_matcher import RuleMatcher
from university_recruitment.models import RecruitmentJob, SourceType, UserProfile


def make_job(**overrides: object) -> RecruitmentJob:
    defaults: dict[str, object] = {
        "id": "test-job",
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
        "source_url": "https://example.edu.cn",
        "published_at": date(2026, 6, 1),
        "collected_at": date(2026, 6, 12),
        "description": "招聘计算机方向教师，从事人工智能研究。",
    }
    defaults.update(overrides)
    return RecruitmentJob(**defaults)


def make_user(**overrides: str | list[str]) -> UserProfile:
    defaults: dict[str, str | list[str]] = {
        "education": "博士",
        "major": "计算机科学与技术",
        "research_direction": "人工智能",
        "keywords": ["机器学习", "数据挖掘"],
        "target_locations": ["广州"],
        "target_school_types": ["双一流"],
        "job_preferences": ["教学科研岗"],
        "constraints": ["编制"],
    }
    defaults.update(overrides)
    return UserProfile(**defaults)


matcher = RuleMatcher()


class TestRuleMatcher:
    def test_baseline_score(self) -> None:
        result = matcher.match(make_user(), make_job())
        # 40 (base) + 15 (education) + 25 (location) + 16 (2 keywords * 8) + 6 (preference) + 4 (constraint)
        assert result.match_score == 100

    def test_expired_job(self) -> None:
        result = matcher.match(make_user(), make_job(deadline=date(2020, 1, 1)))
        # base 40 - 60 expired + 15 education + 25 location + 16 keywords + 6 preference = 42
        assert result.match_score == 42
        assert any("截止" in r for r in result.potential_risks)

    def test_no_deadline_not_expired(self) -> None:
        result = matcher.match(make_user(), make_job(deadline=None))
        assert result.match_score > 0
        assert any("截止时间" in r for r in result.potential_risks)

    def test_education_mismatch(self) -> None:
        result = matcher.match(
            make_user(education="本科"),
            make_job(education_requirement="博士"),
        )
        assert any("学历" in r for r in result.potential_risks)

    def test_location_mismatch(self) -> None:
        result = matcher.match(
            make_user(target_locations=["北京"]),
            make_job(location="广州"),
        )
        assert any("工作地点" in r for r in result.potential_risks)

    def test_score_clamped_max(self) -> None:
        result = matcher.match(make_user(), make_job())
        assert result.match_score <= 100

    def test_score_clamped_min(self) -> None:
        result = matcher.match(
            make_user(),
            make_job(deadline=date(2020, 1, 1), location="拉萨", education_requirement="硕士"),
        )
        assert result.match_score >= 0

    def test_no_keyword_hits(self) -> None:
        result = matcher.match(
            make_user(keywords=["核物理", "天体物理"], major="生物学", research_direction="遗传学"),
            make_job(description="招聘计算机方向教师"),
        )
        assert any("关键词" in r for r in result.potential_risks)

    def test_deadline_reason(self) -> None:
        result = matcher.match(make_user(), make_job(deadline=date(2027, 6, 30)))
        assert any("截止时间" in r for r in result.match_reasons)


class TestRank:
    def test_orders_by_score_desc(self) -> None:
        jobs = [
            make_job(id="low", position="岗位A"),
            make_job(id="high", position="岗位B"),
        ]
        # Second job is identical, so scores should be equal
        results = matcher.rank(make_user(), jobs, limit=5)
        for i in range(len(results) - 1):
            assert results[i].match_score >= results[i + 1].match_score

    def test_limit(self) -> None:
        jobs = [make_job(id=f"job-{i}", position=f"岗位{i}") for i in range(20)]
        results = matcher.rank(make_user(), jobs, limit=5)
        assert len(results) == 5

    def test_deduplicate(self) -> None:
        jobs = [
            make_job(id="a", school="测试大学", position="教师"),
            make_job(id="b", school="测试大学", position="教师"),
        ]
        results = matcher.rank(make_user(), jobs)
        assert len(results) == 1

    def test_empty_jobs(self) -> None:
        results = matcher.rank(make_user(), [])
        assert results == []
