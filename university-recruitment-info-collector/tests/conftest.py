from datetime import date, datetime
from pathlib import Path

import pytest

from university_recruitment.models import RecruitmentJob, SourceType, UserProfile


def make_job(**overrides: object) -> RecruitmentJob:
    defaults: dict[str, object] = {
        "id": "test-job-001",
        "school": "测试大学",
        "position": "计算机科学方向教师",
        "department": "计算机学院",
        "discipline": "计算机科学与技术",
        "location": "广州",
        "education_requirement": "博士",
        "job_type": "教学科研岗",
        "deadline": date(2027, 12, 31),
        "source_type": SourceType.UNIVERSITY_TALENT_SITE,
        "source_name": "测试大学人才招聘网",
        "source_url": "https://example.edu.cn/jobs/test",
        "published_at": date(2026, 6, 1),
        "collected_at": datetime(2026, 6, 12, 10, 0, 0),
        "description": "招聘计算机科学方向教师，要求博士学历。",
    }
    defaults.update(overrides)
    return RecruitmentJob(**defaults)


@pytest.fixture
def sample_job() -> RecruitmentJob:
    return make_job()


@pytest.fixture
def sample_user_profile() -> UserProfile:
    return UserProfile(
        education="博士",
        major="计算机科学与技术",
        research_direction="人工智能",
        keywords=["机器学习", "数据挖掘"],
        target_locations=["广州"],
        target_school_types=["双一流"],
        job_preferences=["教学科研岗"],
        constraints=["编制"],
    )


@pytest.fixture
def sample_jobs() -> list[RecruitmentJob]:
    return [
        make_job(
            id="job-1",
            school="中山大学",
            position="人工智能方向教师",
            location="广州",
            education_requirement="博士",
            deadline=date(2027, 6, 30),
        ),
        make_job(
            id="job-2",
            school="华南理工大学",
            position="计算机科学副教授",
            location="广州",
            education_requirement="博士",
            deadline=date(2027, 8, 31),
        ),
        make_job(
            id="job-3",
            school="暨南大学",
            position="数学讲师",
            location="广州",
            education_requirement="硕士及以上",
            deadline=date(2026, 6, 1),
        ),
    ]


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_recruitment.sqlite"
