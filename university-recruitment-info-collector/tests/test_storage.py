"""Tests for storage layer with lifecycle and migration."""

from datetime import date, datetime, timezone

import pytest

from university_recruitment.models import (
    JobStatus, RecruitmentJob, RunStatus, SourceType,
)
from university_recruitment.storage import JobStore


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
        "source_url": f"https://example.edu.cn/jobs/{overrides.get('id', 'test-job')}",
        "published_at": date(2026, 6, 1),
        "collected_at": datetime.now(timezone.utc),
        "description": "招聘教师。",
        "content_hash": "abc123",
        "status": JobStatus.ACTIVE,
    }
    defaults.update({k: v for k, v in overrides.items() if k != "id"})
    return RecruitmentJob(**defaults)


class TestJobStore:
    def test_init_db_creates_table(self, tmp_path):
        db = tmp_path / "test.sqlite"
        store = JobStore(db)
        store.init_db()
        with store.connect() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            names = {r["name"] for r in tables}
            assert "recruitment_jobs" in names
            assert "collection_runs" in names
            assert "schema_version" in names

    def test_init_db_idempotent(self, tmp_path):
        db = tmp_path / "test.sqlite"
        store = JobStore(db)
        store.init_db()
        store.init_db()

    def test_upsert_inserts_new(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        job = make_job()
        counts = store.upsert_jobs([job])
        assert counts["inserted"] == 1

    def test_upsert_updates_existing(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        job = make_job()
        store.upsert_jobs([job])
        job.position = "新岗位"
        job.content_hash = "newhash"
        counts = store.upsert_jobs([job])
        assert counts["updated"] == 1
        jobs, _ = store.list_jobs(include_expired=True)
        assert jobs[0].position == "新岗位"

    def test_upsert_empty(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        counts = store.upsert_jobs([])
        assert counts == {"inserted": 0, "updated": 0, "unchanged": 0}

    def test_upsert_unchanged(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        job = make_job()
        store.upsert_jobs([job])
        counts = store.upsert_jobs([job])
        assert counts["unchanged"] == 1

    def test_list_filters_expired(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        expired = make_job(id="expired", source_url="https://e.com/e",
                           deadline=date(2020, 1, 1), status=JobStatus.EXPIRED)
        active = make_job(id="active", source_url="https://a.com/a",
                          deadline=date(2099, 12, 31), status=JobStatus.ACTIVE)
        store.upsert_jobs([expired, active])
        jobs, _ = store.list_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "active"
        jobs, _ = store.list_jobs(include_expired=True)
        assert len(jobs) == 2

    def test_list_ordering(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        j1 = make_job(id="j1", source_url="https://a.com/1", deadline=date(2027, 6, 1))
        j2 = make_job(id="j2", source_url="https://b.com/2", deadline=None)
        store.upsert_jobs([j1, j2])
        jobs, _ = store.list_jobs()
        deadlines = [j.deadline for j in jobs]
        assert deadlines[0] is not None  # jobs with deadline come first

    def test_round_trip(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        job = make_job()
        store.upsert_jobs([job])
        jobs, _ = store.list_jobs(include_expired=True)
        assert len(jobs) == 1
        assert jobs[0].id == job.id

    def test_lifecycle_first_seen(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        job = make_job()
        store.upsert_jobs([job])
        jobs, _ = store.list_jobs(include_expired=True)
        assert jobs[0].first_seen_at is not None

    def test_lifecycle_last_seen_updated(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        job = make_job()
        store.upsert_jobs([job])
        first = store.list_jobs(include_expired=True)[0][0].last_seen_at
        job.content_hash = job.content_hash  # unchanged
        store.upsert_jobs([job])
        second = store.list_jobs(include_expired=True)[0][0].last_seen_at
        assert second is not None and first is not None
        assert second >= first

    def test_mark_removed(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        job = make_job()
        store.upsert_jobs([job])
        removed = store.mark_removed("run-1", job.source_name, set())
        assert removed == 1

    def test_no_mark_removed_when_active(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        job = make_job()
        store.upsert_jobs([job])
        removed = store.mark_removed("run-1", job.source_name, {job.id})
        assert removed == 0

    def test_expired_status_update(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        job = make_job(id="exp", source_url="https://x.com/e",
                       deadline=date(2020, 1, 1), status=JobStatus.ACTIVE)
        store.upsert_jobs([job])
        count = store.update_expired_status()
        assert count == 1

    def test_collection_runs(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        store.create_run("run-1", None, 5)
        store.finish_run("run-1", RunStatus.SUCCESS,
                         successful_sources=5, total_collected=10,
                         total_inserted=5, total_updated=3,
                         total_unchanged=2, total_removed=1)
        run = store.get_collection_run("run-1")
        assert run is not None
        assert run.status == RunStatus.SUCCESS
        assert run.total_collected == 10

    def test_pagination(self, tmp_path):
        store = JobStore(tmp_path / "test.sqlite")
        store.init_db()
        for i in range(5):
            job = make_job(id=f"j{i}", source_url=f"https://x.com/{i}")
            store.upsert_jobs([job])
        jobs, total = store.list_jobs(limit=3)
        assert len(jobs) == 3
        assert total == 5

    def test_migration_v2_adds_lifecycle_columns(self, tmp_path):
        db = tmp_path / "test.sqlite"
        store = JobStore(db)
        store.init_db()
        with store.connect() as conn:
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(recruitment_jobs)")}
            for col in ("status", "first_seen_at", "last_seen_at",
                        "last_changed_at", "content_hash", "removed_at"):
                assert col in cols, f"Column {col} missing after migration"
