"""Tests for Pydantic models (models.py)."""

from datetime import date, datetime

import pydantic
import pytest

from university_recruitment.models import (
    MatchRequest,
    MatchResult,
    RecruitmentJob,
    SourceType,
    UserProfile,
)


class TestRecruitmentJob:
    def test_minimal_construction(self) -> None:
        job = RecruitmentJob(
            id="j1",
            school="测试大学",
            position="教师",
            source_type=SourceType.UNIVERSITY_TALENT_SITE,
            source_name="测试源",
            source_url="https://example.edu.cn",
        )
        assert job.id == "j1"
        assert job.school == "测试大学"
        assert job.department is None
        assert job.collected_at.date() == date.today()
        assert job.description == ""

    def test_full_construction(self, sample_job: RecruitmentJob) -> None:
        assert sample_job.id == "test-job-001"
        assert sample_job.deadline == date(2027, 12, 31)
        assert sample_job.source_type == SourceType.UNIVERSITY_TALENT_SITE

    def test_deadline_none(self) -> None:
        job = RecruitmentJob(
            id="j2",
            school="测试大学",
            position="教师",
            source_type=SourceType.UNIVERSITY_TALENT_SITE,
            source_name="测试源",
            source_url="https://example.edu.cn",
            deadline=None,
        )
        assert job.deadline is None

    def test_collected_at_default(self) -> None:
        before = datetime.utcnow()
        job = RecruitmentJob(
            id="j3",
            school="测试大学",
            position="教师",
            source_type=SourceType.UNIVERSITY_TALENT_SITE,
            source_name="测试源",
            source_url="https://example.edu.cn",
        )
        after = datetime.utcnow()
        assert before <= job.collected_at <= after

    def test_longitude_latitude(self) -> None:
        job = RecruitmentJob(
            id="j4",
            school="测试大学",
            position="教师",
            source_type=SourceType.UNIVERSITY_TALENT_SITE,
            source_name="测试源",
            source_url="https://example.edu.cn",
            longitude=113.35,
            latitude=23.15,
        )
        assert job.longitude == 113.35
        assert job.latitude == 23.15

    def test_invalid_score_raises(self) -> None:
        job = RecruitmentJob(
            id="j4",
            school="测试大学",
            position="教师",
            source_type=SourceType.UNIVERSITY_TALENT_SITE,
            source_name="测试源",
            source_url="https://example.edu.cn",
        )
        with pytest.raises(pydantic.ValidationError):
            MatchResult(job=job, match_score=101)

    def test_negative_score_raises(self) -> None:
        job = RecruitmentJob(
            id="j5",
            school="测试大学",
            position="教师",
            source_type=SourceType.UNIVERSITY_TALENT_SITE,
            source_name="测试源",
            source_url="https://example.edu.cn",
        )
        with pytest.raises(pydantic.ValidationError):
            MatchResult(job=job, match_score=-1)


class TestUserProfile:
    def test_defaults(self) -> None:
        profile = UserProfile(education="博士", major="计算机", research_direction="AI")
        assert profile.keywords == []
        assert profile.target_locations == []
        assert profile.constraints == []

    def test_full_profile(self, sample_user_profile: UserProfile) -> None:
        assert sample_user_profile.education == "博士"
        assert "机器学习" in sample_user_profile.keywords


class TestMatchRequest:
    def test_limit_default(self) -> None:
        user = UserProfile(education="博士", major="计算机", research_direction="AI")
        req = MatchRequest(user=user)
        assert req.limit == 10

    def test_limit_clamping(self) -> None:
        user = UserProfile(education="博士", major="计算机", research_direction="AI")
        with pytest.raises(pydantic.ValidationError):
            MatchRequest(user=user, limit=0)
        with pytest.raises(pydantic.ValidationError):
            MatchRequest(user=user, limit=51)
