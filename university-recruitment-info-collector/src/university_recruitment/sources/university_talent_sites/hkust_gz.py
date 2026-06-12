from datetime import datetime

from bs4 import BeautifulSoup

from university_recruitment.models import RecruitmentJob, SourceType
from university_recruitment.sources.base import SourceAdapter
from university_recruitment.sources.field_extractor import (
    extract_discipline,
    extract_education_requirement,
    extract_job_type,
)


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
        detail_limit: int = 10,
    ) -> None:
        self.source_name = source_name
        self.list_url = list_url
        self.school = school
        self.location = location
        self.longitude = longitude
        self.latitude = latitude
        self.timeout = timeout
        self.detail_limit = detail_limit

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
        for row in soup.select("table.el-table__body tr.jobs-table-row"):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td .cell")]
            if len(cells) < 3:
                continue
            job_id, position, department = cells[:3]
            if not job_id or not position:
                continue
            description = f"{position} | {department} | Job ID: {job_id}"
            jobs.append(
                RecruitmentJob(
                    id=f"{self.source_name}-{job_id}",
                    school=self.school,
                    position=position,
                    department=department,
                    discipline=extract_discipline(description),
                    location=self.location,
                    longitude=self.longitude,
                    latitude=self.latitude,
                    education_requirement=extract_education_requirement(description),
                    job_type=extract_job_type(position, description),
                    deadline=None,
                    source_type=SourceType.UNIVERSITY_TALENT_SITE,
                    source_name=self.source_name,
                    source_url=f"{self.list_url.rstrip('/')}#job-{job_id}",
                    published_at=None,
                    collected_at=datetime.utcnow(),
                    description=description,
                )
            )
            if len(jobs) >= self.detail_limit:
                break
        return jobs
