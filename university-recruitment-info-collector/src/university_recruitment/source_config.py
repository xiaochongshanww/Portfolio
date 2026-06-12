import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from pydantic import BaseModel, Field, HttpUrl

from university_recruitment.config import PROJECT_ROOT
from university_recruitment.models import SourceType


DEFAULT_SOURCES_PATH = PROJECT_ROOT / "config" / "sources.toml"


class SourceConfig(BaseModel):
    school: str = "聚合源"
    region: str | None = None
    city: str | None = None
    district: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    source_name: str
    source_type: SourceType
    list_url: HttpUrl | str
    parser: str = "static_list"
    enabled: bool = True
    verify_ssl: bool = True
    request_timeout_seconds: float = Field(default=20, gt=0)
    detail_limit: int = Field(default=10, ge=0)


def load_sources(path: Path = DEFAULT_SOURCES_PATH, include_disabled: bool = False) -> list[SourceConfig]:
    with path.open("rb") as file:
        data = tomllib.load(file)
    sources = [SourceConfig(**item) for item in data.get("sources", [])]
    if include_disabled:
        return sources
    return [source for source in sources if source.enabled]
