"""Structured HTML detail parsing with sections, tables, and attachments."""

import re
from dataclasses import dataclass, field
from datetime import date

from bs4 import BeautifulSoup, Tag


@dataclass(frozen=True)
class ParsedSection:
    heading: str
    text: str
    index: int


@dataclass(frozen=True)
class ParsedTable:
    table_id: str
    headers: list[str]
    rows: list[list[str]]
    caption: str | None = None


@dataclass(frozen=True)
class ParsedAttachment:
    attachment_id: str
    filename: str
    url: str
    file_type: str


@dataclass(frozen=True)
class ParsedDetail:
    text: str
    title: str | None = None
    sections: list = field(default_factory=list)  # list[ParsedSection]
    tables: list = field(default_factory=list)    # list[ParsedTable]
    attachments: list = field(default_factory=list)  # list[ParsedAttachment]
    published_at: date | None = None
    deadline: date | None = None


# ── Constants ───────────────────────────────────────────

_HEADING_TAGS = ("h1", "h2", "h3", "h4")
_SECTION_ANCHOR_RE = re.compile(r"^[（(]?[一二三四五六七八九十百]+[、.).)）]|^\d+[、.）)]|^[（(]\d+[）)]")
_HEADER_KEYWORDS = ("岗位", "部门", "专业", "学历", "人数", "要求", "学院", "单位", "名称", "条件",
                    "招聘部门", "用人部门", "招聘专业", "学位要求", "工作地点")
_ATTACHMENT_EXTENSIONS = (".xlsx", ".xls", ".csv", ".pdf", ".docx", ".doc")
_ATTACHMENT_RE = re.compile(r"(附件\d*|附表\d*|附表)[：:\.\s]*([^\s<>]+)?", re.IGNORECASE)

DATE_PATTERNS = (
    re.compile(r"(?P<year>20\d{2})[-/.](?P<month>1[0-2]|0?[1-9])[-/.](?P<day>3[01]|[12]\d|0?[1-9])"),
    re.compile(r"(?P<year>20\d{2})\s*年\s*(?P<month>1[0-2]|0?[1-9])\s*月\s*(?P<day>3[01]|[12]\d|0?[1-9])\s*日?"),
)
DEADLINE_KEYWORDS = ("截止", "报名时间", "报名截止", "申请截止", "接收报名", "截至")


# ── Main parser ─────────────────────────────────────────

def parse_detail_html(html: str) -> ParsedDetail:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    text = _extract_main_text(soup)
    published_at = _extract_published_at(text)
    deadline = _extract_deadline(text)
    if published_at and deadline and deadline < published_at:
        deadline = None
    sections = _extract_sections(soup)
    tables = _extract_html_tables(soup)
    attachments = _extract_attachments(soup)
    return ParsedDetail(
        text=text,
        title=title,
        sections=sections,
        tables=tables,
        attachments=attachments,
        published_at=published_at,
        deadline=deadline,
    )


# ── Sections ────────────────────────────────────────────

def _extract_sections(soup: BeautifulSoup) -> list:
    """Extract structured sections with proper heading nesting."""
    sections: list[dict] = []
    current_heading = ""
    current_text: list[str] = []
    section_index = 0

    for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "div", "span", "li", "strong"]):
        if tag.name in ("h1", "h2", "h3", "h4"):
            _flush_section(sections, current_heading, current_text, section_index)
            current_heading = tag.get_text(" ", strip=True)[:120]
            current_text = []
            section_index += 1
        elif tag.name == "strong" and len(tag.get_text(strip=True)) > 3:
            # Some Chinese notices use <strong> as section headings
            text = tag.get_text(" ", strip=True)
            if _looks_like_section_heading(text):
                _flush_section(sections, current_heading, current_text, section_index)
                current_heading = text[:120]
                current_text = []
                section_index += 1
        else:
            t = tag.get_text(" ", strip=True)
            if t and len(t) > 3:
                current_text.append(t)

    _flush_section(sections, current_heading, current_text, section_index)
    return sections if sections else None


def _flush_section(sections: list, heading: str, text_lines: list, idx: int) -> None:
    if text_lines:
        sections.append(ParsedSection(
            heading=heading or "",
            text="\n".join(text_lines),
            index=idx,
        ))


def _looks_like_section_heading(text: str) -> bool:
    """Check if text looks like a structured section heading."""
    if len(text) < 4:
        return False
    if _SECTION_ANCHOR_RE.match(text):
        return True
    keywords = ("岗位", "招聘条件", "报名", "福利", "待遇", "招聘程序", "引进",
                "招聘计划", "用人计划", "岗位需求", "招聘岗位")
    return any(kw in text for kw in keywords)


# ── Tables ──────────────────────────────────────────────

def _extract_html_tables(soup: BeautifulSoup) -> list:
    """Extract all data tables with rowspan/colspan handling."""
    tables = []
    for idx, table in enumerate(soup.find_all("table"), start=1):
        # Skip navigation/breadcrumb tables
        if _is_nav_table(table):
            continue
        parsed = _parse_table(table)
        if parsed and parsed["rows"]:
            parsed["table_id"] = f"table_{idx}"
            tables.append(parsed)
    return tables if tables else None


def _is_nav_table(table: Tag) -> bool:
    """Check if a table is a navigation/layout table (not data)."""
    cells = [td.get_text(" ", strip=True) for td in table.find_all("td")]
    total = len(cells)
    if total == 0:
        return True
    nav_counts = sum(1 for c in cells if any(kw in c for kw in ("首页", "上一页", "下一页", "导航")))
    return nav_counts > total * 0.5


def _parse_table(table: Tag) -> dict | None:
    """Parse an HTML table into headers and rows with colspan/rowspan."""
    headers = []
    rows = []
    rowspan_tracker: dict[int, str] = {}

    tr_elements = table.find_all("tr")
    if not tr_elements:
        return None

    for tr_idx, tr in enumerate(tr_elements):
        cells = tr.find_all(["td", "th"])
        row = []
        col_idx = 0

        for cell in cells:
            # Handle rowspan inheritance
            while col_idx in rowspan_tracker and rowspan_tracker[col_idx] != "__skip__":
                row.append(rowspan_tracker[col_idx])
                col_idx += 1

            text = cell.get_text(" ", strip=True)
            colspan = int(cell.get("colspan", 1))
            rowspan = int(cell.get("rowspan", 1))

            # Fill colspan
            for _ in range(colspan):
                row.append(text)
                col_idx += 1

            # Track rowspan
            if rowspan > 1:
                for c in range(colspan):
                    tracker_idx = col_idx - colspan + c
                    if rowspan > 2:
                        rowspan_tracker[tracker_idx] = text
                    else:
                        rowspan_tracker[tracker_idx] = "__skip__"

        # Null out rowspan entries consumed this row
        rowspan_tracker = {k: v for k, v in rowspan_tracker.items() if v != "__skip__"}

        if tr_idx == 0 and (tr.find("th") or _looks_like_table_header(row)):
            headers = row
        else:
            rows.append(row)

    return {"headers": headers, "rows": rows} if rows else None


def _looks_like_table_header(cells: list[str]) -> bool:
    if not cells:
        return False
    return any(any(kw in c for kw in _HEADER_KEYWORDS) for c in cells)


# ── Attachments ─────────────────────────────────────────

def _extract_attachments(soup: BeautifulSoup) -> list:
    """Extract file attachment links from page content."""
    attachments = []
    for idx, link in enumerate(soup.find_all("a", href=True), start=1):
        href = link["href"]
        text = link.get_text(" ", strip=True)
        lower = href.lower()
        file_type = None
        for ext in _ATTACHMENT_EXTENSIONS:
            if ext in lower or ext in text.lower():
                file_type = ext.lstrip(".")
                break
        if not file_type:
            continue
        if href.startswith("http"):
            attachments.append(ParsedAttachment(
                attachment_id=f"att_{idx}",
                filename=text or href.split("/")[-1],
                url=href,
                file_type=file_type,
            ))
    return attachments if attachments else None


# ── Text extraction (kept for legacy compat) ────────────

def _normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _extract_main_text(soup: BeautifulSoup) -> str:
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    raw = _normalize_text(soup.get_text("\n", strip=True))
    lines = [line for line in raw.splitlines() if line.strip()]
    lines = _trim_head(lines, title)
    lines = _trim_tail(lines)
    lines = _drop_noise_lines(lines)
    return "\n".join(lines)


def _trim_head(lines: list[str], title: str) -> list[str]:
    if not lines:
        return lines
    core = title.split("-高校人才网", 1)[0].split("|", 1)[0].strip()
    if core:
        idxs = [i for i, l in enumerate(lines) if core in l]
        if len(idxs) >= 2:
            return lines[idxs[1]:]
        if idxs:
            return lines[idxs[0]:]
    anchors = ("基本信息", "发布日期", "发布时间", "一、", "一.")
    for i, l in enumerate(lines):
        if any(a in l for a in anchors):
            return lines[max(0, i - 1):]
    return lines


def _trim_tail(lines: list[str]) -> list[str]:
    anchors = ("登录高校人才网", "立即登录", "求职者登录", "相关公告", "相关推荐", "友情链接", "版权所有")
    for i, l in enumerate(lines):
        if any(a in l for a in anchors):
            return lines[:i]
    return lines


def _drop_noise_lines(lines: list[str]) -> list[str]:
    noise_exact = {
        "首页", "栏目导航", "省区导航", "城市导航", "学科导航",
        "找职位", "找单位", "求职VIP", "注册", "分享", "收藏",
        "微信扫一扫", "分享给你的朋友吧", "公告热度", "已下线",
        "查看此公告的职位列表", "展开",
    }
    noise_contains = ("导航痕迹", "扫描此二维码分享", "高才优聘小程序")
    result = []
    for line in lines:
        v = line.strip()
        if not v or v in noise_exact:
            continue
        if any(f in v for f in noise_contains):
            continue
        result.append(v)
    return result


# ── Date extraction ─────────────────────────────────────

def _extract_published_at(text: str) -> date | None:
    labeled = _extract_labeled_date(text, ("发布时间", "发布日期", "发布于"))
    return labeled or (min(_extract_dates(text[:1200])) if _extract_dates(text[:1200]) else None)


def _extract_deadline(text: str) -> date | None:
    labeled = _extract_labeled_date(text, ("截止日期", "报名截止", "申请截止", "截止时间"))
    if labeled:
        return labeled
    candidates: list[date] = []
    for keyword in DEADLINE_KEYWORDS:
        for match in re.finditer(keyword, text):
            candidates.extend(_extract_dates(text[match.start():match.start() + 160]))
    return max(candidates) if candidates else None


def _extract_dates(text: str) -> list[date]:
    dates = []
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            try:
                dates.append(date(
                    int(match.group("year")), int(match.group("month")), int(match.group("day")),
                ))
            except ValueError:
                continue
    return dates


def _extract_labeled_date(text: str, labels: tuple[str, ...]) -> date | None:
    for label in labels:
        for match in re.finditer(label, text):
            window = text[match.start():match.start() + 80]
            dates = _extract_dates(window)
            if dates:
                return dates[0]
    return None
