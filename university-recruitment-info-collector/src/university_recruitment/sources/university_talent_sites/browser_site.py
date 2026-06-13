import logging
from datetime import datetime, timezone

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

from university_recruitment.models import JobStatus, RecruitmentJob, SourceType
from university_recruitment.sources.field_extractor import (
    extract_address,
    extract_department,
    extract_discipline,
    extract_education_requirement,
    extract_job_type,
    extract_date_from_url,
)
from university_recruitment.sources.title_cleaner import clean_position_title
from university_recruitment.sources.university_talent_sites.static_site import StaticTalentSiteAdapter
from university_recruitment.llm.extractor import get_llm_extractor
from university_recruitment.url_utils import content_hash, generate_job_id, normalize_url


class BrowserTalentSiteAdapter(StaticTalentSiteAdapter):
    def collect(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("缺少 Playwright，请先安装浏览器采集依赖：playwright install chromium") from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                ),
                locale="zh-CN",
            )
            page.goto(self.list_url, wait_until="networkidle", timeout=int(self.timeout * 1000))
            soup = BeautifulSoup(page.content(), "html.parser")
            browser.close()

        # Try structured extraction first, fall back to text-only
        jobs = self._extract_jobs_from_soup(soup)
        if jobs:
            return jobs
        return self._extract_text_jobs_from_soup(soup)

    def _extract_text_jobs_from_soup(self, soup: BeautifulSoup) -> list[RecruitmentJob]:
        """Fallback: extract jobs from plain text lines when no &lt;a&gt; links found."""
        jobs: list[RecruitmentJob] = []
        llm = get_llm_extractor() if self.use_llm else None

        for index, line in enumerate(soup.get_text("\n", strip=True).splitlines(), start=1):
            raw_title = self._normalize_title(line)
            if not self._looks_like_recruitment(raw_title):
                continue

            position = clean_position_title(raw_title, self.school)
            description = raw_title
            department = extract_department(position, description, self.school)
            discipline = extract_discipline(description)
            education_requirement = extract_education_requirement(description)
            job_type = extract_job_type(position, description)
            location = extract_address(description) or self.location

            # LLM enhancement for text-only mode (very limited info)
            if llm and llm.available and len(description) >= 60:
                try:
                    enhanced = llm.extract(description)
                    if enhanced.get("clean_position") and len(enhanced["clean_position"]) > 3:
                        position = enhanced["clean_position"]
                    if not department and enhanced.get("department"):
                        department = enhanced["department"]
                    if not discipline and enhanced.get("discipline"):
                        discipline = enhanced["discipline"]
                    if not education_requirement and enhanced.get("education_requirement"):
                        education_requirement = enhanced["education_requirement"]
                    if not job_type and enhanced.get("job_type"):
                        job_type = enhanced["job_type"]
                except Exception as exc:
                    logger.warning(
                        "LLM extraction failed for text-only job %s/%s: %s",
                        self.source_name, position[:40], type(exc).__name__,
                    )

            source_url = f"{self.list_url.rstrip('/')}/text-{index}"
            canonical_url = normalize_url(source_url)
            job_id = generate_job_id(canonical_url)
            ch = content_hash(description)
            now = datetime.now(timezone.utc)

            jobs.append(
                RecruitmentJob(
                    id=job_id,
                    school=self.school,
                    position=position,
                    department=department,
                    discipline=discipline,
                    location=location,
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
                )
            )
        return self._deduplicate(jobs)
