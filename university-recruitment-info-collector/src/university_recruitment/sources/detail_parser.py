import re
from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ParsedDetail:
    text: str
    published_at: date | None = None
    deadline: date | None = None


DATE_PATTERNS = (
    re.compile(r"(?P<year>20\d{2})[-/.](?P<month>1[0-2]|0?[1-9])[-/.](?P<day>3[01]|[12]\d|0?[1-9])"),
    re.compile(r"(?P<year>20\d{2})\s*年\s*(?P<month>1[0-2]|0?[1-9])\s*月\s*(?P<day>3[01]|[12]\d|0?[1-9])\s*日?"),
)
DEADLINE_KEYWORDS = ("截止", "报名时间", "报名截止", "申请截止", "接收报名", "截至")


def parse_detail_html(html: str) -> ParsedDetail:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = _extract_main_text(soup)
    published_at = _extract_published_at(text)
    deadline = _extract_deadline(text)
    if published_at and deadline and deadline < published_at:
        deadline = None
    return ParsedDetail(
        text=text,
        published_at=published_at,
        deadline=deadline,
    )


def _normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def _extract_main_text(soup: BeautifulSoup) -> str:
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    raw_text = _normalize_text(soup.get_text("\n", strip=True))
    lines = [line for line in raw_text.splitlines() if line.strip()]
    lines = _trim_head(lines, title)
    lines = _trim_tail(lines)
    lines = _drop_noise_lines(lines)
    return "\n".join(lines)


def _trim_head(lines: list[str], title: str) -> list[str]:
    if not lines:
        return lines

    title_core = title.split("-高校人才网", 1)[0].split("|", 1)[0].strip()
    if title_core:
        matching_indexes = [idx for idx, line in enumerate(lines) if title_core and title_core in line]
        if len(matching_indexes) >= 2:
            return lines[matching_indexes[1] :]
        if matching_indexes:
            start = matching_indexes[0]
            if start > 0:
                return lines[start:]

    anchors = ("基本信息", "发布日期", "发布时间", "一、", "一.")
    for idx, line in enumerate(lines):
        if any(anchor in line for anchor in anchors):
            return lines[max(0, idx - 1) :]
    return lines


def _trim_tail(lines: list[str]) -> list[str]:
    tail_anchors = (
        "登录高校人才网",
        "立即登录",
        "求职者登录",
        "相关公告",
        "相关推荐",
        "友情链接",
        "版权所有",
    )
    for idx, line in enumerate(lines):
        if any(anchor in line for anchor in tail_anchors):
            return lines[:idx]
    return lines


def _drop_noise_lines(lines: list[str]) -> list[str]:
    noise_exact = {
        "首页",
        "栏目导航",
        "省区导航",
        "城市导航",
        "学科导航",
        "找职位",
        "找单位",
        "求职VIP",
        "注册",
        "分享",
        "收藏",
        "微信扫一扫",
        "分享给你的朋友吧",
        "公告热度",
        "已下线",
        "查看此公告的职位列表",
        "展开",
    }
    noise_contains = ("导航痕迹", "扫描此二维码分享", "高才优聘小程序")
    cleaned: list[str] = []
    for line in lines:
        value = line.strip()
        if not value:
            continue
        if value in noise_exact:
            continue
        if any(fragment in value for fragment in noise_contains):
            continue
        cleaned.append(value)
    return cleaned


def _extract_published_at(text: str) -> date | None:
    labeled_date = _extract_labeled_date(text, ("发布时间", "发布日期", "发布于"))
    if labeled_date:
        return labeled_date
    dates = _extract_dates(text[:1200])
    return min(dates) if dates else None


def _extract_deadline(text: str) -> date | None:
    labeled_date = _extract_labeled_date(text, ("截止日期", "报名截止", "申请截止", "截止时间"))
    if labeled_date:
        return labeled_date
    candidates: list[date] = []
    for keyword in DEADLINE_KEYWORDS:
        for match in re.finditer(keyword, text):
            window = text[match.start() : match.start() + 160]
            candidates.extend(_extract_dates(window))
    if candidates:
        return max(candidates)
    return None


def _extract_dates(text: str) -> list[date]:
    dates: list[date] = []
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            try:
                dates.append(
                    date(
                        int(match.group("year")),
                        int(match.group("month")),
                        int(match.group("day")),
                    )
                )
            except ValueError:
                continue
    return dates


def _extract_labeled_date(text: str, labels: tuple[str, ...]) -> date | None:
    for label in labels:
        for match in re.finditer(label, text):
            window = text[match.start() : match.start() + 80]
            dates = _extract_dates(window)
            if dates:
                return dates[0]
    return None
