from datetime import date, datetime, timezone
import re

import httpx
from bs4 import BeautifulSoup

from university_recruitment.models import JobStatus, RecruitmentJob, SourceType
from university_recruitment.sources.base import SourceAdapter
from university_recruitment.sources.detail_parser import parse_detail_html
from university_recruitment.sources.field_extractor import (
    extract_address,
    extract_department,
    extract_discipline,
    extract_education_requirement,
    extract_job_type,
    extract_date_from_url,
)
from university_recruitment.sources.title_cleaner import clean_position_title
from university_recruitment.llm.extractor import get_llm_extractor
from university_recruitment.url_utils import content_hash, generate_job_id, normalize_url


def _parse_llm_date(value: str | None) -> date | None:
    """Safely parse a date string returned by LLM."""
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, TypeError):
        return None


class StaticTalentSiteAdapter(SourceAdapter):
    def __init__(
        self,
        source_name: str,
        list_url: str,
        school: str,
        location: str | None = None,
        longitude: float | None = None,
        latitude: float | None = None,
        timeout: float = 20,
        verify_ssl: bool = True,
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
        self.detail_limit = detail_limit  # 0 = unlimited
        self.use_llm = use_llm

    def collect(self) -> list[RecruitmentJob]:
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
                )
            },
        )
        response.raise_for_status()
        response.encoding = response.encoding or response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        return self._extract_jobs_from_soup(soup)

    def _extract_jobs_from_soup(self, soup: BeautifulSoup) -> list[RecruitmentJob]:
        jobs: list[RecruitmentJob] = []

        # Collect all candidate links first
        candidates: list[tuple[int, str, str]] = []
        for index, link in enumerate(soup.find_all("a", href=True), start=1):
            raw_title = self._normalize_title(link.get_text(" ", strip=True))
            if not self._looks_like_recruitment(raw_title):
                continue
            source_url = str(httpx.URL(self.list_url).join(link["href"]))
            if not source_url.startswith(("http://", "https://")):
                continue
            if source_url.lower().endswith(".pdf"):
                continue
            candidates.append((index, raw_title, source_url))

        # Determine detail fetch limit (0 = unlimited)
        detail_limit = self.detail_limit if self.detail_limit > 0 else len(candidates)

        # Initialize LLM extractor if enabled
        llm = get_llm_extractor() if self.use_llm else None

        for index, raw_title, source_url in candidates:
            should_fetch_detail = len(jobs) < detail_limit
            detail = self._fetch_detail(source_url) if should_fetch_detail else None
            description = detail.text if detail and detail.text else raw_title

            # Only use LLM when we have real detail content (>60 chars)
            has_real_content = detail and detail.text and len(detail.text) > 60
            if llm and llm.available and has_real_content:
                # ── LLM PRIMARY EXTRACTION ──
                try:
                    llm_result = llm.extract(description)
                except Exception:
                    llm_result = {}

                # Position: prefer LLM, fall back to regex cleaner
                llm_position = llm_result.get("clean_position")
                if llm_position and len(llm_position) > 2:
                    position = llm_position
                else:
                    position = clean_position_title(raw_title, self.school)

                # Department: LLM first, regex fallback
                department = (
                    llm_result.get("department")
                    or extract_department(position, description, self.school)
                )

                # Discipline: LLM first, regex fallback
                discipline = (
                    llm_result.get("discipline")
                    or extract_discipline(description)
                )

                # Education: LLM first, regex fallback
                education_requirement = (
                    llm_result.get("education_requirement")
                    or extract_education_requirement(description)
                )

                # Job type: LLM first, regex fallback
                job_type = (
                    llm_result.get("job_type")
                    or extract_job_type(position, description)
                )

                # Location: LLM first, regex + config fallback
                location = (
                    llm_result.get("location")
                    or extract_address(description)
                    or self.location
                )

                # Dates: LLM can parse varied Chinese formats better than regex
                deadline = (
                    _parse_llm_date(llm_result.get("deadline"))
                    or (detail.deadline if detail else None)
                )
                published_at = (
                    _parse_llm_date(llm_result.get("published_at"))
                    or (detail.published_at if detail else None)
                )
            else:
                # ── REGEX-ONLY EXTRACTION (fast path) ──
                position = clean_position_title(raw_title, self.school)
                department = extract_department(position, description, self.school)
                discipline = extract_discipline(description)
                education_requirement = extract_education_requirement(description)
                job_type = extract_job_type(position, description)
                deadline = detail.deadline if detail else None
                published_at = detail.published_at if detail else None
                location = extract_address(description) or self.location

            # Infer published_at from URL if still missing
            if not published_at:
                inferred = extract_date_from_url(source_url)
                if inferred:
                    published_at = date.fromisoformat(inferred)

            canonical_url = normalize_url(source_url)
            job_id = generate_job_id(canonical_url)
            ch = content_hash(description)
            now = datetime.now(timezone.utc)

            # Determine status
            job_status = JobStatus.ACTIVE
            if deadline and deadline < date.today():
                job_status = JobStatus.EXPIRED

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
                    deadline=deadline,
                    source_type=SourceType.UNIVERSITY_TALENT_SITE,
                    source_name=self.source_name,
                    source_url=canonical_url,
                    published_at=published_at,
                    collected_at=now,
                    description=description,
                    status=job_status,
                    content_hash=ch,
                )
            )

        return self._deduplicate(jobs)

    def _fetch_detail(self, source_url: str):
        """Fetch detail page with retry and fallback User-Agent."""
        user_agents = [
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            ),
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/118.0.0.0 Safari/537.36"
            ),
        ]
        last_error = None
        for attempt, ua in enumerate(user_agents):
            try:
                response = httpx.get(
                    source_url,
                    follow_redirects=True,
                    timeout=self.timeout + attempt * 10,
                    verify=self.verify_ssl,
                    headers={"User-Agent": ua},
                )
                response.raise_for_status()
                response.encoding = response.encoding or response.apparent_encoding
                return parse_detail_html(response.text)
            except Exception as exc:
                last_error = exc
                continue
        # All retries failed — log once at debug level
        return None

    @staticmethod
    def _looks_like_recruitment(title: str) -> bool:
        if len(title) < 6:
            return False
        excluded_titles = {
            # Generic navigation links (not real job postings)
            "人才招聘",
            "人才招聘系统",
            "人才招聘平台",
            "人员招聘",
            "人才招聘办公室",
            "诚聘英才",
            "招聘公告",
            "公开招聘",
            "人才引进",
            "博士后工作",
            "博士后招聘",
            "固定教师岗",
            "行政管理岗位",
            "技术支撑岗位",
            "专项招聘岗位",
            "事业编制招聘",
            "劳动合同招聘",
            "高层次人才招聘公告",
            "高层次人才招聘",
            "博士后招聘公告",
            "其他系列招聘公告",
            "教学科研人员招聘",
            "非教学科研人员招聘",
            "专业技术人员招聘",
            "教学科研人才招聘",
            "行政教辅、合同制员工招聘",
            "百人计划引进人才",
            "公开招聘 公开招聘",
            "校内招聘 校内招聘",
            "非事业编制招聘",
            "首页 > 人事管理 > 人才招聘",
            "广州体育学院公开招聘网",
            "高层次人才引进",
            "师资人才招聘",
            "管理教辅人员招聘",
            "专任教师招聘",
            "行政教辅招聘",
            "党政管理人员招聘",
            "教辅人员招聘",
            "后勤人员招聘",
            "其他人员招聘",
            "当前位置：首页>招聘公告",
            "招聘信息",
        }
        if title in excluded_titles:
            return False
        if title.startswith("首页") or title.startswith("您所在的位置") or title.endswith("办公室"):
            return False
        if title.endswith("招聘信息"):
            return False
        # Reject pure "XX年招聘公告/启事" with no specific position mentioned
        if re.match(r"^\d{4}\s*年?(招聘公告|招聘启事|公开招聘|公开招聘公告|招聘)$", title):
            return False
        excluded_keywords = (
            "公示",
            "公布",
            "面试",
            "拟聘",
            "名单",
            "初试",
            "笔试",
            "资格复审",
            "资格审核",
            "资格审",
            "综合成绩",
            "成绩表",
            "成绩公告",
            "考试成绩",
            "考试安排",
            "考试公告",
            "考核公告",
            "应聘确认",
            "笔试安排",
            "体检",
            "体检环节",
            "后续工作",
            "通知公告",
            "网站升级",
            "投递指南",
            "简历投递指南",
            "考核论证报告",
            "招聘会",
            "操作说明",
            "公开招聘专栏",
            "会议评审",
            "地点变更",
            "附件",
            "岗位需求表",
            "企业云招聘",
            "双选会",
            "揽才",
            "由谁组织",
            "不得报名",
            "公开招聘的程序",
            "宣讲会",
        )
        if any(keyword in title for keyword in excluded_keywords):
            return False
        keywords = ("招聘", "引进", "诚聘", "招募")
        return any(keyword in title for keyword in keywords)

    @staticmethod
    def _normalize_title(title: str) -> str:
        title = re.sub(r"\s+", " ", title).strip()
        return title.strip("◆·•*-—> ")

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
