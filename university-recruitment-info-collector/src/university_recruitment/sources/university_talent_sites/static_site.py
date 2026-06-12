from datetime import datetime
import re

import httpx
from bs4 import BeautifulSoup

from university_recruitment.models import RecruitmentJob, SourceType
from university_recruitment.sources.base import SourceAdapter
from university_recruitment.sources.detail_parser import parse_detail_html
from university_recruitment.sources.field_extractor import (
    extract_department,
    extract_discipline,
    extract_education_requirement,
    extract_job_type,
)


class StaticTalentSiteAdapter(SourceAdapter):
    def __init__(
        self,
        source_name: str,
        list_url: str,
        school: str,
        location: str | None = None,
        timeout: float = 20,
        verify_ssl: bool = True,
        detail_limit: int = 10,
    ) -> None:
        self.source_name = source_name
        self.list_url = list_url
        self.school = school
        self.location = location
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.detail_limit = detail_limit

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
        jobs: list[RecruitmentJob] = []
        for index, link in enumerate(soup.find_all("a", href=True), start=1):
            title = self._normalize_title(link.get_text(" ", strip=True))
            if not self._looks_like_recruitment(title):
                continue
            source_url = str(httpx.URL(self.list_url).join(link["href"]))
            if not source_url.startswith(("http://", "https://")):
                continue
            if source_url.lower().endswith(".pdf"):
                continue
            detail = self._fetch_detail(source_url) if len(jobs) < self.detail_limit else None
            description = detail.text if detail and detail.text else title
            jobs.append(
                RecruitmentJob(
                    id=f"{self.source_name}-{index}",
                    school=self.school,
                    position=title,
                    department=extract_department(title, description, self.school),
                    discipline=extract_discipline(description),
                    location=self.location,
                    education_requirement=extract_education_requirement(description),
                    job_type=extract_job_type(title, description),
                    deadline=detail.deadline if detail else None,
                    source_type=SourceType.UNIVERSITY_TALENT_SITE,
                    source_name=self.source_name,
                    source_url=source_url,
                    published_at=detail.published_at if detail else None,
                    collected_at=datetime.utcnow(),
                    description=description,
                )
            )
        return self._deduplicate(jobs)

    def _fetch_detail(self, source_url: str):
        try:
            response = httpx.get(
                source_url,
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
        except Exception:
            return None
        return parse_detail_html(response.text)

    @staticmethod
    def _looks_like_recruitment(title: str) -> bool:
        if len(title) < 6:
            return False
        excluded_titles = {
            "人才招聘",
            "人员招聘",
            "人才招聘办公室",
            "博士后工作",
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
        }
        if title in excluded_titles:
            return False
        if title.startswith("首页") or title.startswith("您所在的位置") or title.endswith("办公室"):
            return False
        if title.endswith("招聘信息"):
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
