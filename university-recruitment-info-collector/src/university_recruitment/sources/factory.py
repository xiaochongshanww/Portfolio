from university_recruitment.models import SourceType
from university_recruitment.source_config import SourceConfig
from university_recruitment.sources.aggregators import GaoxiaojobColumnAdapter
from university_recruitment.sources.base import SourceAdapter
from university_recruitment.sources.university_talent_sites import StaticTalentSiteAdapter


def build_source_adapter(config: SourceConfig) -> SourceAdapter:
    if config.source_type == SourceType.UNIVERSITY_TALENT_SITE and config.parser == "static_list":
        return StaticTalentSiteAdapter(
            source_name=config.source_name,
            list_url=str(config.list_url),
            school=config.school,
            location=config.city or config.region,
            timeout=config.request_timeout_seconds,
            verify_ssl=config.verify_ssl,
            detail_limit=config.detail_limit,
        )
    if config.source_type == SourceType.AGGREGATOR and config.parser in {
        "gaoxiaojob_column",
        "gaoxiaojob_browser",
    }:
        return GaoxiaojobColumnAdapter(
            source_name=config.source_name,
            list_url=str(config.list_url),
            location=config.city or config.region,
            timeout=config.request_timeout_seconds,
            verify_ssl=config.verify_ssl,
            use_browser=config.parser == "gaoxiaojob_browser",
            detail_limit=config.detail_limit,
        )
    raise ValueError(f"Unsupported source parser: {config.source_type}/{config.parser}")
