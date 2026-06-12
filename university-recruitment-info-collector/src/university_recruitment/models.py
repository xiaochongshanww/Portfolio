from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class SourceType(StrEnum):
    UNIVERSITY_TALENT_SITE = "university_talent_site"
    AGGREGATOR = "aggregator"
    WECHAT_ARTICLE = "wechat_article"


class RecruitmentJob(BaseModel):
    id: str
    school: str
    position: str
    department: str | None = None
    discipline: str | None = None
    location: str | None = None
    education_requirement: str | None = None
    job_type: str | None = None
    deadline: date | None = None
    source_type: SourceType
    source_name: str
    source_url: HttpUrl | str
    published_at: date | None = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    description: str = ""


class UserProfile(BaseModel):
    education: str
    major: str
    research_direction: str
    keywords: list[str] = Field(default_factory=list)
    target_locations: list[str] = Field(default_factory=list)
    target_school_types: list[str] = Field(default_factory=list)
    job_preferences: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    job: RecruitmentJob
    match_score: int = Field(ge=0, le=100)
    match_reasons: list[str] = Field(default_factory=list)
    potential_risks: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    llm_summary: str | None = None


class MatchRequest(BaseModel):
    user: UserProfile
    limit: int = Field(default=10, ge=1, le=50)
    use_llm: bool = False


class MatchResponse(BaseModel):
    results: list[MatchResult]
