"""Tests for source configuration (source_config.py)."""

from pathlib import Path

import sys

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from university_recruitment.source_config import SourceConfig, load_sources
from university_recruitment.sources.factory import _build_location, build_source_adapter
from university_recruitment.sources.university_talent_sites import BrowserTalentSiteAdapter


@pytest.fixture
def valid_toml(tmp_path: Path) -> Path:
    path = tmp_path / "sources.toml"
    path.write_text("""
[[sources]]
school = "测试大学"
region = "广东"
city = "广州"
source_name = "测试大学人事处"
source_type = "university_talent_site"
list_url = "https://test.edu.cn/jobs"
parser = "static_list"
enabled = true
verify_ssl = true

[[sources]]
school = "示例大学"
region = "北京"
city = "北京"
source_name = "示例大学人才招聘网"
source_type = "university_talent_site"
list_url = "https://example.edu.cn/jobs"
parser = "static_list"
enabled = false
""")
    return path


class TestSourceConfig:
    def test_defaults(self) -> None:
        config = SourceConfig(
            source_name="测试",
            source_type="university_talent_site",
            list_url="https://example.edu.cn",
        )
        assert config.enabled is True
        assert config.verify_ssl is True
        assert config.parser == "static_list"
        assert config.request_timeout_seconds == 20
        assert config.detail_limit == 10
        assert config.school == "聚合源"
        assert config.district is None  # new field defaults to None

    def test_full_config(self) -> None:
        config = SourceConfig(
            school="测试大学",
            region="广东",
            city="广州",
            district="番禺区",
            source_name="测试大学人事处",
            source_type="university_talent_site",
            list_url="https://test.edu.cn/jobs",
            parser="static_list",
            enabled=True,
            verify_ssl=True,
            request_timeout_seconds=30,
            detail_limit=5,
        )
        assert config.school == "测试大学"
        assert config.detail_limit == 5
        assert config.district == "番禺区"


class TestBuildLocation:
    def test_city_and_district(self) -> None:
        config = SourceConfig(
            source_name="测试",
            source_type="university_talent_site",
            list_url="https://example.edu.cn",
            city="广州",
            district="番禺区",
        )
        assert _build_location(config) == "广州-番禺区"

    def test_city_without_district(self) -> None:
        config = SourceConfig(
            source_name="测试",
            source_type="university_talent_site",
            list_url="https://example.edu.cn",
            city="广州",
        )
        assert _build_location(config) == "广州"

    def test_no_city_falls_back_to_region(self) -> None:
        config = SourceConfig(
            source_name="测试",
            source_type="university_talent_site",
            list_url="https://example.edu.cn",
            region="广东",
        )
        assert _build_location(config) == "广东"

    def test_district_without_city(self) -> None:
        config = SourceConfig(
            source_name="测试",
            source_type="university_talent_site",
            list_url="https://example.edu.cn",
            district="番禺区",
        )
        assert _build_location(config) == "番禺区"


class TestBuildSourceAdapter:
    def test_builds_browser_list_adapter(self) -> None:
        config = SourceConfig(
            school="测试大学",
            city="广州",
            source_name="测试大学招聘系统",
            source_type="university_talent_site",
            list_url="https://example.edu.cn/recruit",
            parser="browser_list",
        )
        adapter = build_source_adapter(config)
        assert isinstance(adapter, BrowserTalentSiteAdapter)


class TestLoadSources:
    def test_loads_correctly(self, valid_toml: Path) -> None:
        sources = load_sources(valid_toml)
        assert len(sources) == 1  # only enabled
        assert sources[0].school == "测试大学"

    def test_include_disabled(self, valid_toml: Path) -> None:
        sources = load_sources(valid_toml, include_disabled=True)
        assert len(sources) == 2

    def test_missing_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_sources(Path("/nonexistent/sources.toml"))
