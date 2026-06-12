from pathlib import Path

from university_recruitment import report
from university_recruitment.storage import JobStore


def test_source_health_report_summarizes_enabled_disabled_sources(
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
    monkeypatch.setattr(report, "JobStore", lambda: JobStore(db_path))

    output = report.build_source_health_report(config_path)

    assert "- Configured sources: 3" in output
    assert "- Enabled sources: 2" in output
    assert "- Enabled sources with jobs: 1" in output
    assert "- Enabled sources without jobs: 1" in output
    assert "空结果大学人才招聘网 | 空结果大学 | static_list | status=no_jobs" in output
    assert "- dynamic_or_system_adapter_needed: 1" in output
    assert "next=build_dedicated_adapter" in output
