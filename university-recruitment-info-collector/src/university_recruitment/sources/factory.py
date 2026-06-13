from university_recruitment.models import SourceType
from university_recruitment.source_config import SourceConfig
from university_recruitment.sources.aggregators import GaoxiaojobColumnAdapter
from university_recruitment.sources.base import SourceAdapter
from university_recruitment.sources.university_talent_sites import (
    BrowserTalentSiteAdapter,
    HkustGzCareerAdapter,
    StaticTalentSiteAdapter,
)


def _build_location(config: SourceConfig) -> str | None:
    if config.district:
        return f"{config.city}-{config.district}" if config.city else config.district
    return config.city or config.region


def build_source_adapter(config: SourceConfig, use_llm: bool = False) -> SourceAdapter:
    location = _build_location(config)
    if config.source_type == SourceType.UNIVERSITY_TALENT_SITE and config.parser == "static_list":
        return StaticTalentSiteAdapter(
            source_name=config.source_name,
            list_url=str(config.list_url),
            school=config.school,
            location=location,
            longitude=config.longitude,
            latitude=config.latitude,
            timeout=config.request_timeout_seconds,
            verify_ssl=config.verify_ssl,
            detail_limit=config.detail_limit,
            use_llm=use_llm,
        )
    if config.source_type == SourceType.UNIVERSITY_TALENT_SITE and config.parser == "browser_list":
        return BrowserTalentSiteAdapter(
            source_name=config.source_name,
            list_url=str(config.list_url),
            school=config.school,
            location=location,
            longitude=config.longitude,
            latitude=config.latitude,
            timeout=config.request_timeout_seconds,
            verify_ssl=config.verify_ssl,
            detail_limit=config.detail_limit,
            use_llm=use_llm,
        )
    if config.source_type == SourceType.UNIVERSITY_TALENT_SITE and config.parser == "hkust_gz_career":
        return HkustGzCareerAdapter(
            source_name=config.source_name,
            list_url=str(config.list_url),
            school=config.school,
            location=location,
            longitude=config.longitude,
            latitude=config.latitude,
            timeout=config.request_timeout_seconds,
            detail_limit=config.detail_limit,
            use_llm=use_llm,
        )
    if config.source_type == SourceType.AGGREGATOR and config.parser in {
        "gaoxiaojob_column",
        "gaoxiaojob_browser",
    }:
        return GaoxiaojobColumnAdapter(
            source_name=config.source_name,
            list_url=str(config.list_url),
            school=config.school,
            location=location,
            longitude=config.longitude,
            latitude=config.latitude,
            timeout=config.request_timeout_seconds,
            verify_ssl=config.verify_ssl,
            use_browser=config.parser == "gaoxiaojob_browser",
            detail_limit=config.detail_limit,
            use_llm=use_llm,
        )
    raise ValueError(f"Unsupported source parser: {config.source_type}/{config.parser}")
