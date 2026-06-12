from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from university_recruitment.models import RecruitmentJob, SourceType
from university_recruitment.sources.base import SourceAdapter
from university_recruitment.sources.detail_parser import ParsedDetail, parse_detail_html
from university_recruitment.sources.field_extractor import (
    extract_department,
    extract_discipline,
    extract_education_requirement,
    extract_job_type,
)


KNOWN_GUANGZHOU_SCHOOLS = (
    "中山大学",
    "华南理工大学",
    "暨南大学",
    "广州大学",
    "广州医科大学",
    "广州中医药大学",
    "广东药科大学",
    "华南师范大学",
    "广东技术师范大学",
    "广东财经大学",
    "广东工业大学",
    "广东外语外贸大学南国商学院",
    "广东外语外贸大学",
    "南方医科大学",
    "广州商学院",
    "广州软件学院",
    "广东白云学院",
    "广东培正学院",
    "广州城建职业学院",
    "广州南洋理工职业学院",
    "广州工商学院",
    "广州华立学院",
    "香港科技大学（广州）",
)


class GaoxiaojobColumnAdapter(SourceAdapter):
    def __init__(
        self,
        source_name: str,
        list_url: str,
        location: str | None = None,
        timeout: float = 20,
        verify_ssl: bool = True,
        use_browser: bool = False,
        detail_limit: int = 5,
    ) -> None:
        self.source_name = source_name
        self.list_url = list_url
        self.location = location
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.use_browser = use_browser
        self.detail_limit = detail_limit

    def collect(self) -> list[RecruitmentJob]:
        if self.use_browser:
            return self._collect_with_browser()
        return self._collect_with_http()

    def _collect_with_http(self) -> list[RecruitmentJob]:
        response = httpx.get(
            self.list_url,
            follow_redirects=True,
            timeout=self.timeout,
            verify=self.verify_ssl,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://www.gaoxiaojob.com/",
            },
        )
        if response.status_code == 403:
            raise RuntimeError(
                "高校人才网当前拒绝普通 HTTP 采集，需要后续接入浏览器采集或站点 API 适配"
            )
        response.raise_for_status()
        response.encoding = response.encoding or response.apparent_encoding

        soup = BeautifulSoup(response.text, "html.parser")
        return self._extract_jobs(soup)

    def _collect_with_browser(self) -> list[RecruitmentJob]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("缺少 Playwright，请先安装浏览器采集依赖：pip install '.[browser]'") from exc

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
            html = page.content()
            details = self._fetch_browser_details(page, html)
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        return self._extract_jobs(soup, details)

    def _fetch_browser_details(self, page: object, list_html: str) -> dict[str, ParsedDetail]:
        soup = BeautifulSoup(list_html, "html.parser")
        detail_urls: list[str] = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            title = link.get_text(" ", strip=True)
            if self._is_detail_link(href) and self._looks_like_recruitment(title):
                detail_urls.append(str(httpx.URL(self.list_url).join(href)))

        details: dict[str, ParsedDetail] = {}
        for detail_url in list(dict.fromkeys(detail_urls))[: self.detail_limit]:
            try:
                page.goto(detail_url, wait_until="networkidle", timeout=int(self.timeout * 1000))
                details[detail_url] = parse_detail_html(page.content())
            except Exception:
                continue
        return details

    def _extract_jobs(
        self,
        soup: BeautifulSoup,
        details: dict[str, ParsedDetail] | None = None,
    ) -> list[RecruitmentJob]:
        jobs: list[RecruitmentJob] = []
        details = details or {}
        for index, link in enumerate(soup.find_all("a", href=True), start=1):
            title = link.get_text(" ", strip=True)
            href = link["href"]
            if not self._is_detail_link(href):
                continue
            if not self._looks_like_recruitment(title):
                continue
            source_url = str(httpx.URL(self.list_url).join(href))
            if "gaoxiaojob.com" not in source_url:
                continue
            detail = details.get(source_url)
            school = self._infer_school(title, link)
            description = detail.text if detail and detail.text else title
            jobs.append(
                RecruitmentJob(
                    id=f"{self.source_name}-{index}",
                    school=school,
                    position=title,
                    department=extract_department(title, description, school),
                    discipline=extract_discipline(description),
                    location=self.location,
                    education_requirement=extract_education_requirement(description),
                    job_type=extract_job_type(title, description),
                    deadline=detail.deadline if detail else None,
                    source_type=SourceType.AGGREGATOR,
                    source_name=self.source_name,
                    source_url=source_url,
                    published_at=detail.published_at if detail else None,
                    collected_at=datetime.utcnow(),
                    description=description,
                )
            )
        return self._deduplicate(jobs)

    @staticmethod
    def _is_detail_link(href: str) -> bool:
        return "/announcement/detail/" in href or "/job/detail/" in href

    @staticmethod
    def _looks_like_recruitment(title: str) -> bool:
        if len(title) < 8:
            return False
        excluded_keywords = (
            "登录",
            "注册",
            "简历",
            "客服",
            "会员",
            "面试名单",
            "拟聘",
            "公示",
            "招聘会",
            "峰会",
            "巡回",
        )
        if any(keyword in title for keyword in excluded_keywords):
            return False
        keywords = ("招聘", "引进", "诚聘", "招募", "博士后", "教师")
        return any(keyword in title for keyword in keywords)

    @staticmethod
    def _infer_school(title: str, link: object | None = None) -> str:
        if link is not None:
            company_name = GaoxiaojobColumnAdapter._find_company_name(link)
            if company_name:
                return company_name

        clean_title = (
            title.replace("百万英才汇南粤", "")
            .replace("丨", " ")
            .replace("|", " ")
            .strip(" -—")
        )
        for school in KNOWN_GUANGZHOU_SCHOOLS:
            if school in clean_title:
                return school
        school_markers = ("职业技术学院", "高等专科学校", "职业技术大学", "大学", "学院")
        if GaoxiaojobColumnAdapter._looks_like_job_card_text(clean_title):
            for token in reversed(clean_title.split()):
                token = token.strip("，,。；;：:（）()[]【】")
                if any(token.endswith(marker) for marker in school_markers) and len(token) <= 24:
                    return token
        for marker in school_markers:
            if marker in clean_title:
                return clean_title.split(marker, 1)[0].strip("丨｜| -—") + marker
        return "未知高校"

    @staticmethod
    def _find_company_name(link: object) -> str | None:
        for parent in getattr(link, "parents", []):
            company_link = parent.find("a", class_="company-name") if hasattr(parent, "find") else None
            if company_link is not None:
                company_name = company_link.get_text(" ", strip=True)
                company_name = company_name.replace("-高校人才网直荐", "").strip()
                if company_name and not GaoxiaojobColumnAdapter._looks_like_job_card_text(company_name):
                    return company_name
        return None

    @staticmethod
    def _looks_like_job_card_text(value: str) -> bool:
        bad_fragments = ("已下线", "面议", "招若干", "博士研究生", "硕士研究生")
        return len(value) > 40 or any(fragment in value for fragment in bad_fragments)

    @staticmethod
    def _deduplicate(jobs: list[RecruitmentJob]) -> list[RecruitmentJob]:
        seen: set[str] = set()
        unique_jobs: list[RecruitmentJob] = []
        for job in jobs:
            source_url = str(job.source_url)
            if source_url in seen:
                continue
            seen.add(source_url)
            unique_jobs.append(job)
        return unique_jobs
