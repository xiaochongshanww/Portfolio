"""Tests for collection runner fault tolerance."""

from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from university_recruitment.models import JobStatus, RecruitmentJob, RunStatus, SourceType
from university_recruitment.collect import _collect_source
from university_recruitment.source_config import SourceConfig
from university_recruitment.storage import JobStore


def _make_source_config(**overrides):
    defaults = {
        "school": "测试大学",
        "region": "广东",
        "city": "广州",
        "source_name": "测试来源",
        "source_type": SourceType.UNIVERSITY_TALENT_SITE,
        "list_url": "https://example.edu.cn/jobs",
        "parser": "static_list",
        "enabled": True,
        "verify_ssl": True,
        "request_timeout_seconds": 20,
        "detail_limit": 0,
    }
    defaults.update(overrides)
    return SourceConfig(**defaults)


class TestEmptyCollectionFailClosed:
    def test_empty_result_with_history_fails(self, tmp_path, monkeypatch):
        """When collection returns 0 but source has existing jobs, should fail."""
        db = tmp_path / "test.sqlite"
        config = _make_source_config()

        store = JobStore(db)
        store.init_db()
        job = RecruitmentJob(
            id="j1", school="T", position="P",
            source_type=SourceType.UNIVERSITY_TALENT_SITE,
            source_name=config.source_name,
            source_url="https://x.com/1", description="",
        )
        store.upsert_jobs([job])

        with patch("university_recruitment.collect.build_source_adapter") as mock_build:
            mock_adapter = MagicMock()
            mock_adapter.collect.return_value = []
            mock_build.return_value = mock_adapter
            monkeypatch.setattr(
                "university_recruitment.collect.JobStore",
                lambda: JobStore(db),
            )
            result = _collect_source(config, "run-test", False, False)

        assert result["status"] == "failed"
        assert "0 jobs" in result["error"]
        assert result["removed"] == 0

    def test_empty_safety_check_exception_fails(self, tmp_path, monkeypatch):
        """When count_jobs_by_source throws, source must fail closed."""
        config = _make_source_config()

        with patch("university_recruitment.collect.build_source_adapter") as mock_build:
            mock_adapter = MagicMock()
            mock_adapter.collect.return_value = []
            mock_build.return_value = mock_adapter
            mock_store = MagicMock()
            mock_store.count_jobs_by_source.side_effect = RuntimeError("db down")
            monkeypatch.setattr(
                "university_recruitment.collect.JobStore",
                lambda: mock_store,
            )
            result = _collect_source(config, "run-test", False, False)

        assert result["status"] == "failed"
        assert "safety check failed" in result["error"]
        mock_store.mark_removed.assert_not_called()

    def test_empty_source_with_no_history_is_ok(self, tmp_path, monkeypatch):
        """First-ever collection returning 0 for a source is not a failure."""
        config = _make_source_config(source_name="新来源")
        db = tmp_path / "test.sqlite"
        JobStore(db).init_db()

        with patch("university_recruitment.collect.build_source_adapter") as mock_build:
            mock_adapter = MagicMock()
            mock_adapter.collect.return_value = []
            mock_build.return_value = mock_adapter
            monkeypatch.setattr(
                "university_recruitment.collect.JobStore",
                lambda: JobStore(db),
            )
            result = _collect_source(config, "run-test", False, False)

        assert result["collected"] == 0


class TestMarkRemovedFailure:
    def test_mark_removed_exception_marks_failed(self, tmp_path, monkeypatch):
        """When mark_removed throws, source status must be failed."""
        config = _make_source_config()

        with patch("university_recruitment.collect.build_source_adapter") as mock_build:
            mock_adapter = MagicMock()
            job = RecruitmentJob(
                id="j1", school="T", position="P",
                source_type=SourceType.UNIVERSITY_TALENT_SITE,
                source_name=config.source_name,
                source_url="https://x.com/1", description="",
            )
            mock_adapter.collect.return_value = [job]
            mock_build.return_value = mock_adapter

            mock_store = MagicMock()
            mock_store.upsert_jobs.return_value = {"inserted": 1, "updated": 0, "unchanged": 0}
            mock_store.mark_removed.side_effect = RuntimeError("disk full")
            monkeypatch.setattr(
                "university_recruitment.collect.JobStore",
                lambda: mock_store,
            )
            result = _collect_source(config, "run-test", False, False)

        assert result["status"] == "failed"
        assert "mark_removed" in result["error"]


class TestSourceFailureIsolation:
    def test_one_source_failure_isolated(self):
        """One source failing should not affect another source."""
        config_ok = _make_source_config(source_name="ok_source")
        config_fail = _make_source_config(source_name="fail_source")

        def mock_collect(cfg, run_id, use_llm, dry_run):
            if cfg.source_name == "fail_source":
                return {
                    "source_name": cfg.source_name,
                    "started_at": datetime.now(timezone.utc),
                    "finished_at": datetime.now(timezone.utc),
                    "status": "failed",
                    "collected": 0, "inserted": 0, "updated": 0,
                    "unchanged": 0, "removed": 0,
                    "error": "adapter error",
                    "active_ids": set(),
                }
            return {
                "source_name": cfg.source_name,
                "started_at": datetime.now(timezone.utc),
                "finished_at": datetime.now(timezone.utc),
                "status": "ok",
                "collected": 3, "inserted": 3, "updated": 0,
                "unchanged": 0, "removed": 0,
                "error": None,
                "active_ids": {"j1", "j2", "j3"},
            }

        r_ok = mock_collect(config_ok, "run-1", False, False)
        r_fail = mock_collect(config_fail, "run-1", False, False)

        assert r_ok["status"] == "ok"
        assert r_fail["status"] == "failed"
        assert r_ok["collected"] == 3
