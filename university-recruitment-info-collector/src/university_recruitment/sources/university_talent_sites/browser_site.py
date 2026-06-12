from datetime import datetime

from bs4 import BeautifulSoup

from university_recruitment.models import RecruitmentJob, SourceType
from university_recruitment.sources.field_extractor import (
    extract_address,
    extract_department,
    extract_discipline,
    extract_education_requirement,
    extract_job_type,
)
from university_recruitment.sources.university_talent_sites.static_site import StaticTalentSiteAdapter


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
        jobs = self._extract_jobs_from_soup(soup)
        if jobs:
            return jobs
        return self._extract_text_jobs_from_soup(soup)

    def _extract_text_jobs_from_soup(self, soup: BeautifulSoup) -> list[RecruitmentJob]:
        jobs: list[RecruitmentJob] = []
        for index, line in enumerate(soup.get_text("\n", strip=True).splitlines(), start=1):
            title = self._normalize_title(line)
            if not self._looks_like_recruitment(title):
                continue
            description = title
            location = extract_address(description) or self.location
            jobs.append(
                RecruitmentJob(
                    id=f"{self.source_name}-text-{index}",
                    school=self.school,
                    position=title,
                    department=extract_department(title, description, self.school),
                    discipline=extract_discipline(description),
                    location=location,
                    longitude=self.longitude,
                    latitude=self.latitude,
                    education_requirement=extract_education_requirement(description),
                    job_type=extract_job_type(title, description),
                    deadline=None,
                    source_type=SourceType.UNIVERSITY_TALENT_SITE,
                    source_name=self.source_name,
                    source_url=f"{self.list_url.rstrip('/')}#text-{index}",
                    published_at=None,
                    collected_at=datetime.utcnow(),
                    description=description,
                )
            )
        return self._deduplicate(jobs)
