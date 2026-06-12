"""Tests for storage layer (storage.py)."""

from datetime import date
from pathlib import Path

from university_recruitment.models import RecruitmentJob, SourceType
from university_recruitment.storage import JobStore


def make_job(**overrides: object) -> RecruitmentJob:
    job_id = str(overrides.get("id", "test-job"))
    defaults: dict[str, object] = {
        "id": job_id,
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
        "source_url": f"https://example.edu.cn/jobs/{job_id}",
        "published_at": date(2026, 6, 1),
        "collected_at": date(2026, 6, 12),
        "description": "招聘教师。",
    }
    defaults.update(overrides)
    return RecruitmentJob(**defaults)


class TestJobStore:
    def test_init_db_creates_table(self, db_path: Path) -> None:
        store = JobStore(db_path)
        store.init_db()
        conn = store.connect()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        assert any(row["name"] == "recruitment_jobs" for row in tables)
        conn.close()

    def test_init_db_idempotent(self, db_path: Path) -> None:
        store = JobStore(db_path)
        store.init_db()
        store.init_db()  # should not raise

    def test_upsert_inserts_new(self, db_path: Path) -> None:
        store = JobStore(db_path)
        store.init_db()
        job = make_job()
        count = store.upsert_jobs([job])
        assert count == 1
        jobs = store.list_jobs(include_expired=True)
        assert len(jobs) == 1

    def test_upsert_updates_existing(self, db_path: Path) -> None:
        store = JobStore(db_path)
        store.init_db()
        store.upsert_jobs([make_job(position="旧岗位")])
        store.upsert_jobs([make_job(position="新岗位")])
        jobs = store.list_jobs(include_expired=True)
        assert len(jobs) == 1
        assert jobs[0].position == "新岗位"

    def test_upsert_empty(self, db_path: Path) -> None:
        store = JobStore(db_path)
        store.init_db()
        count = store.upsert_jobs([])
        assert count == 0

    def test_list_filters_expired(self, db_path: Path) -> None:
        store = JobStore(db_path)
        store.init_db()
        store.upsert_jobs([
            make_job(id="active", deadline=date(2099, 12, 31)),
            make_job(id="expired", deadline=date(2020, 1, 1)),
        ])
        active = store.list_jobs(include_expired=False)
        expired = store.list_jobs(include_expired=True)
        assert len(active) == 1
        assert active[0].id == "active"
        assert len(expired) == 2

    def test_list_ordering(self, db_path: Path) -> None:
        store = JobStore(db_path)
        store.init_db()
        store.upsert_jobs([
            make_job(id="a", deadline=date(2027, 6, 30), position="岗位A"),
            make_job(id="b", deadline=date(2027, 1, 1), position="岗位B"),
            make_job(id="c", deadline=None, position="岗位C"),
        ])
        jobs = store.list_jobs(include_expired=False)
        # Non-null deadlines first, then null deadlines; within each, ASC
        non_null = [j for j in jobs if j.deadline is not None]
        null_dl = [j for j in jobs if j.deadline is None]
        assert len(non_null) == 2
        assert len(null_dl) == 1
        if len(non_null) >= 2:
            assert non_null[0].id == "b"  # earlier deadline
            assert non_null[1].id == "a"

    def test_round_trip(self, db_path: Path) -> None:
        store = JobStore(db_path)
        store.init_db()
        original = make_job()
        store.upsert_jobs([original])
        jobs = store.list_jobs(include_expired=True)
        assert len(jobs) == 1
        retrieved = jobs[0]
        assert retrieved.id == original.id
        assert retrieved.school == original.school
        assert retrieved.position == original.position
        assert retrieved.deadline == original.deadline
        assert retrieved.source_type == original.source_type
        assert retrieved.source_url == str(original.source_url)
