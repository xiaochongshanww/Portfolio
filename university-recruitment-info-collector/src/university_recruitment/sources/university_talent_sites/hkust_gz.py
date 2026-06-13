from datetime import datetime, timezone

from bs4 import BeautifulSoup

from university_recruitment.models import RecruitmentJob, SourceType
from university_recruitment.sources.base import SourceAdapter
from university_recruitment.sources.field_extractor import (
    extract_discipline,
    extract_education_requirement,
    extract_job_type,
)
from university_recruitment.sources.title_cleaner import clean_position_title
from university_recruitment.llm.extractor import get_llm_extractor


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

    def collect(self) -> list[RecruitmentJob]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("缺少 Playwright，请先安装浏览器采集依赖：playwright install chromium") from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(locale="zh-CN")
            page.goto(self.list_url, wait_until="networkidle", timeout=int(self.timeout * 1000))
            soup = BeautifulSoup(page.content(), "html.parser")
            browser.close()
        return self._extract_jobs(soup)

    def _extract_jobs(self, soup: BeautifulSoup) -> list[RecruitmentJob]:
        jobs: list[RecruitmentJob] = []
        llm = get_llm_extractor() if self.use_llm else None
        limit = self.detail_limit if self.detail_limit > 0 else float("inf")

        for row in soup.select("table.el-table__body tr.jobs-table-row"):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td .cell")]
            if len(cells) < 3:
                continue
            job_id, raw_position, department = cells[:3]
            if not job_id or not raw_position:
                continue

            position = clean_position_title(raw_position, self.school)
            description = f"{position} | {department} | Job ID: {job_id}"

            if llm and llm.available:
                # ── LLM PRIMARY EXTRACTION ──
                try:
                    llm_result = llm.extract(description)
                except Exception:
                    llm_result = {}

                discipline = (
                    llm_result.get("discipline")
                    or extract_discipline(description)
                )
                education_requirement = (
                    llm_result.get("education_requirement")
                    or extract_education_requirement(description)
                )
                job_type = (
                    llm_result.get("job_type")
                    or extract_job_type(position, description)
                )
                # LLM may suggest a better position title
                llm_position = llm_result.get("clean_position")
                if llm_position and len(llm_position) > 3:
                    position = llm_position
            else:
                # ── REGEX-ONLY ──
                discipline = extract_discipline(description)
                education_requirement = extract_education_requirement(description)
                job_type = extract_job_type(position, description)

            jobs.append(
                RecruitmentJob(
                    id=f"{self.source_name}-{job_id}",
                    school=self.school,
                    position=position,
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
                    source_url=f"{self.list_url.rstrip('/')}#job-{job_id}",
                    published_at=None,
                    collected_at=datetime.now(timezone.utc),
                    description=description,
                )
            )
            if len(jobs) >= limit:
                break
        return jobs
