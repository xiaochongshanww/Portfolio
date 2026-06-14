from datetime import datetime, timezone
from time import perf_counter

from bs4 import BeautifulSoup

from university_recruitment.models import JobStatus, RecruitmentJob, SourceType
from university_recruitment.sources.base import SourceAdapter
from university_recruitment.sources.field_extractor import (
    extract_discipline,
    extract_education_requirement,
    extract_job_type,
)
from university_recruitment.sources.title_cleaner import clean_position_title
from university_recruitment.llm.extractor import get_llm_extractor
from university_recruitment.quality.validators import (
    build_extraction_warnings_json, calculate_job_quality,
)
from university_recruitment.url_utils import content_hash, generate_job_id, normalize_url


class HkustGzCareerAdapter(SourceAdapter):
    def __init__(
        self,
        source_name: str,
        list_url: str,
        school: str,
        location: str | None = None,
        longitude: float | None = None,
        latitude: float | None = None,
        timeout: float = 20,
        detail_limit: int = 0,
        use_llm: bool = False,
    ) -> None:
        self.source_name = source_name
        self.list_url = list_url
        self.school = school
        self.location = location
        self.longitude = longitude
        self.latitude = latitude
        self.timeout = timeout
        self.detail_limit = detail_limit  # 0 = unlimited
        self.use_llm = use_llm
        self._init_profile_stats()
        self._set_profile("detail_limit", detail_limit)

    def collect(self) -> list[RecruitmentJob]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("缺少 Playwright，请先安装浏览器采集依赖：playwright install chromium") from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(locale="zh-CN")
            self._record_profile("list_requests", 1)
            started_at = perf_counter()
            page.goto(self.list_url, wait_until="networkidle", timeout=int(self.timeout * 1000))
            soup = BeautifulSoup(page.content(), "html.parser")
            self._record_profile("list_seconds", perf_counter() - started_at)
            browser.close()
        return self._extract_jobs(soup)

    def _extract_jobs(self, soup: BeautifulSoup) -> list[RecruitmentJob]:
        jobs: list[RecruitmentJob] = []
        llm = get_llm_extractor() if self.use_llm else None
        limit = self.detail_limit if self.detail_limit > 0 else float("inf")
        rows = soup.select("table.el-table__body tr.jobs-table-row")
        self._set_profile("candidates_seen", len(rows))
        self._set_profile("detail_limit", limit)

        for row in rows:
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td .cell")]
            if len(cells) < 3:
                continue
            job_id, raw_position, department = cells[:3]
            if not job_id or not raw_position:
                continue

            position = clean_position_title(raw_position, self.school)
            normalized_position = None
            description = f"{position} | {department} | Job ID: {job_id}"

            discipline = extract_discipline(description)
            education_requirement = extract_education_requirement(description)
            job_type = extract_job_type(position, description)
            extraction_method = "regex"

            if llm and llm.available and len(description) >= 30:
                # Use analyze_document for consistent extraction pipeline
                metadata = {
                    "title": position,
                    "source_url": f"{self.list_url.rstrip('/')}/job-{job_id}",
                    "school": self.school,
                }
                try:
                    analysis = llm.analyze_document(description, metadata)
                    llm_positions = analysis.get("positions", [])
                    if llm_positions:
                        extracted = llm_positions[0]
                        disc = extracted.get("discipline")
                        if isinstance(disc, list):
                            disc = disc[0] if disc else None
                        discipline = disc or discipline
                        education_requirement = extracted.get("education_requirement") or education_requirement
                        job_type = extracted.get("job_type") or job_type
                        if extracted.get("position_normalized") and len(extracted["position_normalized"]) > 3:
                            normalized_position = extracted["position_normalized"]
                        extraction_method = "llm_analyze_document"
                except Exception:
                    pass  # Fall back to regex results already computed

            source_url = f"{self.list_url.rstrip('/')}/job-{job_id}"
            canonical_url = normalize_url(source_url)
            stable_id = generate_job_id(canonical_url)
            ch = content_hash(description)
            now = datetime.now(timezone.utc)

            job_obj = RecruitmentJob(
                id=stable_id,
                school=self.school,
                position=position,
                normalized_position=normalized_position,
                department=department,
                discipline=discipline,
                location=self.location,
                longitude=self.longitude,
                latitude=self.latitude,
                education_requirement=education_requirement,
                job_type=job_type,
                deadline=None,
                source_type=SourceType.UNIVERSITY_TALENT_SITE,
                source_name=self.source_name,
                source_url=canonical_url,
                published_at=None,
                collected_at=now,
                description=description,
                status=JobStatus.ACTIVE,
                content_hash=ch,
                extraction_method=extraction_method,
            )
            qscore, qstatus, qwarnings = calculate_job_quality(job_obj)
            job_obj.quality_score = qscore
            job_obj.quality_status = qstatus
            job_obj.extraction_warnings = build_extraction_warnings_json(qwarnings)

            jobs.append(job_obj)
            if len(jobs) >= limit:
                break
        return jobs
