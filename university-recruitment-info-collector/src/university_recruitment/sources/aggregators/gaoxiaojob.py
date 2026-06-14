import json
from datetime import date, datetime, timezone

import httpx
from bs4 import BeautifulSoup

from university_recruitment.models import JobStatus, RecruitmentJob, SourceType
from university_recruitment.sources.base import SourceAdapter
from university_recruitment.sources.detail_parser import ParsedDetail, parse_detail_html
from university_recruitment.sources.field_extractor import (
    extract_address,
    extract_department,
    extract_discipline,
    extract_education_requirement,
    extract_job_type,
    extract_date_from_url,
)
from university_recruitment.sources.attachment_parser import prepare_llm_input_text
from university_recruitment.sources.title_cleaner import clean_position_title
from university_recruitment.llm.extractor import get_llm_extractor
from university_recruitment.url_utils import (
    build_position_job_id, content_hash, generate_job_id, normalize_url,
)


def _parse_llm_date(value: str | None) -> date | None:
    """Safely parse a date string returned by LLM."""
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, TypeError):
        return None


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
        school: str | None = None,
        location: str | None = None,
        longitude: float | None = None,
        latitude: float | None = None,
        timeout: float = 20,
        verify_ssl: bool = True,
        use_browser: bool = False,
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
        self.verify_ssl = verify_ssl
        self.use_browser = use_browser
        self.detail_limit = detail_limit  # 0 = unlimited
        self.use_llm = use_llm
        self._init_profile_stats()
        self._set_profile("detail_limit", detail_limit)

    def collect(self) -> list[RecruitmentJob]:
        if self.use_browser:
            return self._collect_with_browser()
        return self._collect_with_http()

    def _collect_with_http(self) -> list[RecruitmentJob]:
        with self._timed_profile_block("list_requests", "list_seconds"):
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
        if self._is_detail_link(str(httpx.URL(self.list_url).path)):
            return [self._build_detail_job(soup, str(response.url), 1)]
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
            with self._timed_profile_block("list_requests", "list_seconds"):
                page.goto(self.list_url, wait_until="networkidle", timeout=int(self.timeout * 1000))
                html = page.content()
                current_url = page.url
            if self._is_detail_link(str(httpx.URL(current_url).path)):
                soup = BeautifulSoup(html, "html.parser")
                jobs = [self._build_detail_job(soup, current_url, 1)]
                browser.close()
                return jobs
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

        limit = self.detail_limit if self.detail_limit > 0 else len(detail_urls)
        self._set_profile("candidates_seen", len(detail_urls))
        self._set_profile("detail_limit", limit)
        details: dict[str, ParsedDetail] = {}
        for detail_url in list(dict.fromkeys(detail_urls))[:limit]:
            try:
                with self._timed_profile_block("detail_requests", "detail_seconds"):
                    page.goto(detail_url, wait_until="networkidle", timeout=int(self.timeout * 1000))
                    details[detail_url] = parse_detail_html(page.content())
                self._record_profile("detail_success", 1)
            except Exception:
                self._record_profile("detail_failures", 1)
                continue
        return details

    def _extract_jobs(
        self,
        soup: BeautifulSoup,
        details: dict[str, ParsedDetail] | None = None,
    ) -> list[RecruitmentJob]:
        jobs: list[RecruitmentJob] = []
        details = details or {}
        llm = get_llm_extractor() if self.use_llm else None

        for index, link in enumerate(soup.find_all("a", href=True), start=1):
            raw_title = link.get_text(" ", strip=True)
            href = link["href"]
            if not self._is_detail_link(href):
                continue
            if not self._looks_like_recruitment(raw_title):
                continue
            source_url = str(httpx.URL(self.list_url).join(href))
            if "gaoxiaojob.com" not in source_url:
                continue

            detail = details.get(source_url)
            school = self._configured_school() or self._infer_school(raw_title, link)
            description = detail.text if detail and detail.text else raw_title
            analysis_text, used_attachment_text, _ = prepare_llm_input_text(
                body_text=description,
                notice_url=str(source_url),
            )

            normalized_position = None
            has_real_content = len(analysis_text) > 60
            canonical_url = normalize_url(source_url)
            now = datetime.now(timezone.utc)

            if llm and llm.available and has_real_content:
                # ── LLM analyze_document ──
                metadata = {
                    "title": raw_title,
                    "source_url": str(canonical_url),
                    "school": school,
                    "published_at_hint": str(detail.published_at) if detail and detail.published_at else "",
                    "sections": detail.sections if detail else None,
                    "tables": detail.tables if detail else None,
                }
                try:
                    analysis = llm.analyze_document(analysis_text, metadata)
                except Exception:
                    analysis = {"document_type": "unknown", "positions": [], "warnings": [], "review_accepted": True}

                doc_type = analysis.get("document_type", "unknown")
                skippable = {"result_announcement", "interview_notice", "publicity_notice", "non_recruitment"}
                if doc_type in skippable:
                    continue

                llm_positions = analysis.get("positions", [])

                if llm_positions:
                    for extracted in llm_positions:
                        pos_id = build_position_job_id(canonical_url, extracted.get("position_raw", raw_title), extracted.get("department"))
                        position = clean_position_title(extracted.get("position_raw", raw_title), school)

                        dept = extracted.get("department")
                        disc = extracted.get("discipline")
                        if isinstance(disc, list):
                            disc = disc[0] if disc else None

                        edu = extracted.get("education_requirement")
                        jt = extracted.get("job_type")
                        loc = extracted.get("location") or self.location
                        dl = _parse_llm_date(extracted.get("deadline")) or (detail.deadline if detail else None)
                        pa = _parse_llm_date(analysis.get("published_at")) or (detail.published_at if detail else None) or extract_date_from_url(source_url)

                        evidence = extracted.get("evidence", {})
                        ev_json = json.dumps(evidence, ensure_ascii=False) if evidence else None

                        jobs.append(self._build_extracted_job(pos_id, school, position, extracted.get("position_normalized"),
                            dept, disc, edu, jt, loc, dl, pa, analysis_text, canonical_url, ("llm_analyze_document_attachment" if used_attachment_text else "llm_analyze_document"),
                            doc_type, analysis.get("confidence"), now))
                else:
                    # Fallback to legacy extract
                    legacy = llm.extract(analysis_text) if hasattr(llm, "extract") else {}
                    position = clean_position_title(raw_title, school)
                    jobs.append(self._build_extracted_job(generate_job_id(canonical_url), school, position,
                        legacy.get("clean_position"), legacy.get("department"), legacy.get("discipline"),
                        legacy.get("education_requirement"), legacy.get("job_type"), legacy.get("location") or self.location,
                        _parse_llm_date(legacy.get("deadline")) or (detail.deadline if detail else None) or extract_date_from_url(source_url) if not detail or not detail.published_at else detail.published_at,
                        _parse_llm_date(legacy.get("published_at")) or (detail.published_at if detail else None) or extract_date_from_url(source_url),
                        analysis_text, canonical_url, ("llm_legacy_attachment" if used_attachment_text else "llm_legacy"), None, None, now))
            else:
                # ── REGEX-ONLY EXTRACTION ──
                normalized_position = None
                position = clean_position_title(raw_title, school)
                department = extract_department(position, description, school)
                discipline = extract_discipline(description)
                education_requirement = extract_education_requirement(description)
                job_type = extract_job_type(position, description)
                deadline = detail.deadline if detail else None
                published_at = detail.published_at if detail else None
                location = extract_address(description) or self.location
                if not published_at:
                    published_at = extract_date_from_url(source_url)

                jobs.append(self._build_extracted_job(generate_job_id(canonical_url), school, position,
                    None, department, discipline, education_requirement, job_type, location,
                    deadline, published_at, description, canonical_url, "regex", None, None, now))
        return self._deduplicate(jobs)

    def _build_detail_job(self, soup: BeautifulSoup, source_url: str, index: int) -> RecruitmentJob:
        raw_title = self._extract_detail_title(soup)
        detail = parse_detail_html(str(soup))
        description = detail.text if detail and detail.text else raw_title
        school = self._configured_school() or self._infer_school(raw_title)

        position = clean_position_title(raw_title, school)
        department = extract_department(position, description, school)
        discipline = extract_discipline(description)
        education_requirement = extract_education_requirement(description)
        job_type = extract_job_type(position, description)
        location = extract_address(description) or self.location
        published_at = detail.published_at if detail else None

        if not published_at:
            published_at = extract_date_from_url(source_url)

        return RecruitmentJob(
            id=f"{self.source_name}-{index}",
            school=school,
            position=position,
            department=department,
            discipline=discipline,
            location=location,
            longitude=self.longitude,
            latitude=self.latitude,
            education_requirement=education_requirement,
            job_type=job_type,
            deadline=detail.deadline if detail else None,
            source_type=SourceType.AGGREGATOR,
            source_name=self.source_name,
            source_url=source_url,
            published_at=published_at,
            collected_at=datetime.now(timezone.utc),
            description=description,
        )

    @staticmethod
    def _extract_detail_title(soup: BeautifulSoup) -> str:
        for selector in ("h1", ".title", ".article-title"):
            node = soup.select_one(selector)
            if node is not None:
                title = node.get_text(" ", strip=True)
                if title:
                    return title
        return soup.title.get_text(" ", strip=True) if soup.title else "高校人才网招聘公告"

    def _build_extracted_job(self, job_id, school, position, normalized_position,
                             department, discipline, education_requirement, job_type,
                             location, deadline, published_at, description,
                             canonical_url, method, doc_type=None, confidence=None, now=None):
        from datetime import datetime, timezone
        from university_recruitment.models import JobStatus
        from university_recruitment.quality.validators import (
            build_extraction_warnings_json, calculate_job_quality,
        )
        now = now or datetime.now(timezone.utc)
        job_status = JobStatus.EXPIRED if (deadline and deadline < date.today()) else JobStatus.ACTIVE
        qscore = None
        qstatus = None
        try:
            qscore, qstatus, _ = calculate_job_quality(RecruitmentJob(
                id=job_id, school=school, position=position,
                normalized_position=normalized_position,
                department=department, discipline=discipline,
                location=location, education_requirement=education_requirement,
                job_type=job_type, deadline=deadline, published_at=published_at,
                source_type=SourceType.AGGREGATOR, source_name=self.source_name,
                source_url=canonical_url, description=description,
            ), doc_type=doc_type)
        except Exception:
            pass
        return RecruitmentJob(
            id=job_id, school=school, position=position,
            normalized_position=normalized_position,
            department=department, discipline=discipline,
            location=location, longitude=self.longitude, latitude=self.latitude,
            education_requirement=education_requirement, job_type=job_type,
            deadline=deadline, source_type=SourceType.AGGREGATOR,
            source_name=self.source_name, source_url=canonical_url,
            published_at=published_at, collected_at=now,
            description=description, status=job_status,
            content_hash=content_hash(description),
            document_type=doc_type, extraction_method=method,
            extraction_confidence=confidence,
            quality_score=qscore, quality_status=qstatus,
        )

    def _configured_school(self) -> str | None:
        if self.school and self.school != "聚合源":
            return self.school
        return None

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
            "已下线",
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
        # Reject pure "XX年招聘公告/启事" with no specific position
        import re
        if re.match(r"^\d{4}\s*年?(招聘公告|招聘启事|公开招聘|公开招聘公告)$", title):
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
                company_name = company_name.replace("-高校人才网直荐", "").strip(" #")
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
