from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    UNIVERSITY_TALENT_SITE = "university_talent_site"
    AGGREGATOR = "aggregator"
    WECHAT_ARTICLE = "wechat_article"


class JobStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REMOVED = "removed"
    UNKNOWN = "unknown"


class RunStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class EducationLevel(int, Enum):
    """Structured education hierarchy for matching."""
    UNKNOWN = 0
    BACHELOR = 1        # 本科
    MASTER = 2           # 硕士
    DOCTOR = 3           # 博士
    POSTDOC = 4          # 博士后


EDUCATION_STRING_TO_LEVEL: dict[str, EducationLevel] = {
    "本科": EducationLevel.BACHELOR,
    "本科及以上": EducationLevel.BACHELOR,
    "硕士": EducationLevel.MASTER,
    "硕士研究生": EducationLevel.MASTER,
    "硕士及以上": EducationLevel.MASTER,
    "硕士研究生及以上": EducationLevel.MASTER,
    "博士": EducationLevel.DOCTOR,
    "博士研究生": EducationLevel.DOCTOR,
    "博士后": EducationLevel.POSTDOC,
}


def parse_education_level(text: str | None) -> EducationLevel:
    """Parse an education requirement string into a structured level."""
    if not text:
        return EducationLevel.UNKNOWN
    cleaned = text.strip()
    # Sort by length descending so "硕士研究生及以上" matches before "硕士"
    for key in sorted(EDUCATION_STRING_TO_LEVEL, key=len, reverse=True):
        if key in cleaned:
            return EDUCATION_STRING_TO_LEVEL[key]
    return EducationLevel.UNKNOWN


def education_satisfies(user_level: EducationLevel, required_level: EducationLevel) -> bool | None:
    """Check if user education satisfies the job requirement.

    Returns True if satisfied, False if not, None if unknown.
    """
    if user_level == EducationLevel.UNKNOWN or required_level == EducationLevel.UNKNOWN:
        return None
    # "本科及以上" means bachelor is the minimum, so bachelor >= bachelor
    # "硕士及以上" means master is the minimum
    return user_level >= required_level


class QualityStatus(str, Enum):
    NORMAL = "normal"
    NEEDS_REVIEW = "needs_review"
    HIDDEN = "hidden"


class DocumentType(str, Enum):
    SINGLE_POSITION = "single_position"
    MULTI_POSITION_NOTICE = "multi_position_notice"
    GENERAL_TALENT_NOTICE = "general_talent_notice"
    POSTDOC_NOTICE = "postdoc_notice"
    RESULT_ANNOUNCEMENT = "result_announcement"
    INTERVIEW_NOTICE = "interview_notice"
    PUBLICITY_NOTICE = "publicity_notice"
    NON_RECRUITMENT = "non_recruitment"
    UNKNOWN = "unknown"


SKIP_DOC_TYPES = frozenset({
    DocumentType.RESULT_ANNOUNCEMENT, DocumentType.INTERVIEW_NOTICE,
    DocumentType.PUBLICITY_NOTICE, DocumentType.NON_RECRUITMENT,
})


class RecruitmentJob(BaseModel):
    id: str
    school: str
    position: str
    normalized_position: str | None = None
    department: str | None = None
    discipline: str | None = None
    location: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    education_requirement: str | None = None
    job_type: str | None = None
    deadline: date | None = None
    source_type: SourceType
    source_name: str
    source_url: HttpUrl | str
    published_at: date | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""

    # Lifecycle fields
    status: JobStatus = JobStatus.ACTIVE
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    last_changed_at: datetime | None = None
    content_hash: str | None = None
    removed_at: datetime | None = None

    # Extraction quality fields
    document_type: str | None = None
    extraction_method: str | None = None
    extraction_confidence: float | None = None
    quality_score: int | None = None
    quality_status: str | None = None
    extraction_warnings: str | None = None  # JSON list
    evidence_json: str | None = None  # JSON dict
    notice_title: str | None = None
    notice_url: str | None = None


class UserProfile(BaseModel):
    education: str
    major: str
    research_direction: str
    keywords: list[str] = Field(default_factory=list)
    target_locations: list[str] = Field(default_factory=list)
    target_school_types: list[str] = Field(default_factory=list)
    job_preferences: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class UserProfileTemplate(BaseModel):
    id: str
    name: str
    education: str
    major: str
    research_direction: str
    keywords: list[str] = Field(default_factory=list)
    target_locations: list[str] = Field(default_factory=list)
    target_school_types: list[str] = Field(default_factory=list)
    job_preferences: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FavoriteJob(BaseModel):
    job_id: str
    school: str
    position: str
    department: str | None = None
    location: str | None = None
    source_url: str
    saved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""


class MatchResult(BaseModel):
    job: RecruitmentJob
    match_score: int = Field(ge=0, le=100)
    match_reasons: list[str] = Field(default_factory=list)
    potential_risks: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    llm_summary: str | None = None
    confidence_score: int = Field(default=100, ge=0, le=100)
    hard_constraint_passed: bool = True
    hard_constraint_failures: list[str] = Field(default_factory=list)


class MatchRequest(BaseModel):
    user: UserProfile
    limit: int = Field(default=10, ge=1, le=50)
    use_llm: bool = False
    include_hard_constraint_failures: bool = False
    candidate_limit: int = Field(default=50, ge=1, le=200)
    result_limit: int = Field(default=10, ge=1, le=50)


class MatchResponse(BaseModel):
    results: list[MatchResult]
    total_candidates: int = 0
    hard_filtered_out: int = 0


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class JobListResponse(BaseModel):
    jobs: list[RecruitmentJob]
    pagination: PaginationMeta


class CollectionRun(BaseModel):
    id: str
    started_at: datetime
    finished_at: datetime | None = None
    status: RunStatus = RunStatus.RUNNING
    selected_source: str | None = None
    total_sources: int = 0
    successful_sources: int = 0
    failed_sources: int = 0
    total_collected: int = 0
    total_inserted: int = 0
    total_updated: int = 0
    total_unchanged: int = 0
    total_removed: int = 0
    error_summary: str | None = None


class CollectionSourceRun(BaseModel):
    run_id: str
    source_name: str
    started_at: datetime
    finished_at: datetime | None = None
    status: RunStatus = RunStatus.RUNNING
    collected_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    removed_count: int = 0
    error_message: str | None = None
