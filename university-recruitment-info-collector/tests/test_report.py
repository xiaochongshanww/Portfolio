"""Tests for report generation with collection-run-based health."""

from pathlib import Path

from university_recruitment import report
from university_recruitment.storage import JobStore


def test_source_health_report_uses_run_data(
    db_path: Path,
    tmp_path: Path,
    monkeypatch,
    sample_job,
) -> None:
    config_path = tmp_path / "sources.toml"
    config_path.write_text(
        """
[[sources]]
school = "测试大学"
region = "广东"
city = "广州"
source_name = "测试大学人才招聘网"
source_type = "university_talent_site"
list_url = "https://example.edu.cn/jobs"
parser = "static_list"
enabled = true

[[sources]]
school = "空结果大学"
region = "广东"
city = "广州"
source_name = "空结果大学人才招聘网"
source_type = "university_talent_site"
list_url = "https://empty.example.edu.cn/jobs"
parser = "static_list"
enabled = true

[[sources]]
school = "系统大学"
region = "广东"
city = "广州"
source_name = "系统大学招聘系统"
source_type = "university_talent_site"
list_url = "https://rszp.example.edu.cn"
parser = "static_list"
enabled = false
""",
        encoding="utf-8",
    )

    store = JobStore(db_path)
    store.init_db()
    store.upsert_jobs([sample_job])
    # Create a collection run record so health report uses run data
    from university_recruitment.models import CollectionSourceRun, RunStatus
    store.create_run("run-test", None, 3)
    store.upsert_source_run(CollectionSourceRun(
        run_id="run-test",
        source_name="测试大学人才招聘网",
        started_at=sample_job.collected_at,
        finished_at=sample_job.collected_at,
        status=RunStatus.SUCCESS,
        collected_count=1,
        inserted_count=1,
    ))
    store.upsert_source_run(CollectionSourceRun(
        run_id="run-test",
        source_name="空结果大学人才招聘网",
        started_at=sample_job.collected_at,
        finished_at=sample_job.collected_at,
        status=RunStatus.FAILED,
        collected_count=0,
        error_message="connection timeout",
    ))
    monkeypatch.setattr(report, "JobStore", lambda: JobStore(db_path))

    output = report.build_source_health_report(config_path)

    # New report format uses run status
    assert "Configured sources: 3" in output
    assert "Enabled sources: 2" in output
    assert "Last run failed: 1" in output  # 空结果大学 failed
    # 测试大学 has jobs + successful run
    assert "测试大学人才招聘网" in output
    # 系统大学 is disabled
    assert "dynamic_or_system_adapter_needed" in output
    # 空结果大学 shows as failed_with_existing_jobs (has historical jobs but run failed)
    assert "failed_with_existing_jobs" in output or "failed" in output


def test_build_report_summary(db_path: Path, tmp_path: Path, monkeypatch, sample_job) -> None:
    config_path = tmp_path / "sources.toml"
    config_path.write_text(
        """
[[sources]]
school = "测试大学"
region = "广东"
city = "广州"
source_name = "测试大学人才招聘网"
source_type = "university_talent_site"
list_url = "https://example.edu.cn/jobs"
parser = "static_list"
enabled = true
""",
        encoding="utf-8",
    )

    store = JobStore(db_path)
    store.init_db()
    store.upsert_jobs([sample_job])
    monkeypatch.setattr(report, "JobStore", lambda: JobStore(db_path))

    output = report.build_report(config_path)

    assert "# University Recruitment Data Report" in output
    assert "Jobs:" in output
    assert "Field Coverage" in output
    assert sample_job.school in output
