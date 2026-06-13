import re


JOB_TYPE_RULES = (
    ("博士后", ("博士后",)),
    ("教学科研岗", ("教学科研", "教研岗", "专任教师", "教师招聘", "青年教师")),
    ("科研岗", ("科研岗", "专职科研", "科研人员")),
    ("实验技术岗", ("实验技术", "技术支撑", "实验岗")),
    ("辅导员", ("辅导员",)),
    ("行政教辅岗", ("行政教辅", "党政管理", "管理岗位", "合同制员工")),
    ("医疗卫生岗", ("附属医院", "卫生专业技术", "医师", "护士", "临床")),
)
EDUCATION_RULES = (
    "博士研究生",
    "博士",
    "硕士研究生及以上",
    "硕士研究生",
    "硕士及以上",
    "硕士",
    "本科及以上",
    "本科",
)
DISCIPLINE_LABELS = ("需求学科", "学科专业", "专业要求", "招聘专业", "相关专业", "专业方向")


def extract_address(text: str) -> str | None:
    """Extract a detailed street address from job description text."""
    match = ADDRESS_PATTERN.search(text)
    if match:
        return match.group(0)
    return None


ADDRESS_PATTERN = re.compile(
    r"广州市?\s*[一-龥]{1,8}(?:区)\s*[一-龥]{0,30}(?:路|街|大道|巷|号)"
)

DEPARTMENT_PATTERN = re.compile(
    r"([一-龥A-Za-z0-9（）()·]+(?:学院|学部|研究院|医院|中心|实验室|课题组|系|部))"
)


def extract_job_type(title: str, text: str) -> str | None:
    title_type = _extract_job_type_from_text(title)
    if title_type:
        return title_type
    labeled_match = re.search(r"(岗位类型|岗位类别|栏目分类)[：:\s|]+(.{2,40})", text)
    if labeled_match:
        return _extract_job_type_from_text(labeled_match.group(2))
    return None


def _extract_job_type_from_text(text: str) -> str | None:
    for job_type, keywords in JOB_TYPE_RULES:
        if any(keyword in text for keyword in keywords):
            return job_type
    return None


def extract_education_requirement(text: str) -> str | None:
    """Extract education requirement with priority ordering.

    Searches in priority order so that "博士研究生" is matched before "博士",
    and "硕士研究生及以上" before "硕士", etc.
    """
    for education in EDUCATION_RULES:
        if education in text:
            return education
    return None


def extract_discipline(text: str) -> str | None:
    for label in DISCIPLINE_LABELS:
        match = re.search(rf"{label}(?:（[^）]*）)?[：:\s|]+([^\n]{{2,180}})", text)
        if not match:
            continue
        value = _clean_inline_value(match.group(1))
        if value and not _looks_like_bad_discipline(value):
            return value
    return None


def extract_department(title: str, text: str, school: str) -> str | None:
    """Extract department name from title first, then from description body."""
    # First, try the title
    dept = _extract_department_from_text(title, school)
    if dept:
        return dept

    # Fallback: search the first 1500 chars of description body
    if text and text != title:
        dept = _extract_department_from_text(text[:1500], school)
        if dept:
            return dept

    return None


def _extract_department_from_text(text: str, school: str) -> str | None:
    """Search for department patterns in a text block."""
    for match in DEPARTMENT_PATTERN.finditer(text):
        value = _clean_department(match.group(1), school)
        if value:
            return value
    return None


def extract_date_from_url(url: str) -> str | None:
    """Try to infer published date from URL path patterns.

    Supports patterns like:
    - /2025/06/12/...
    - /article/20250612/...
    - ...content_20250612...
    """
    # Pattern: /YYYY/MM/DD/ or /YYYY-MM-DD/
    match = re.search(r"/(20\d{2})[-/](\d{1,2})[-/](\d{1,2})[/.]", url)
    if match:
        y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if 2020 <= y <= 2030 and 1 <= m <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{m:02d}-{d:02d}"

    # Pattern: YYYYMMDD
    match = re.search(r"(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])", url)
    if match:
        y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if 2020 <= y <= 2030 and 1 <= m <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{m:02d}-{d:02d}"

    return None


def _clean_inline_value(value: str) -> str | None:
    value = re.split(r"(报名方式|栏目分类|工作地点|发布时间|截止日期|招聘人数|岗位职责)", value, maxsplit=1)[0]
    value = value.replace("|", " ").replace("， ,", "，").strip(" ：:,，、\n\t")
    value = re.sub(r"\s+", " ", value)
    return value[:120] or None


def _clean_department(value: str, school: str) -> str | None:
    value = value.strip("丨｜| -—")
    if value == school or value.startswith("首页"):
        return None
    if school in value:
        value = value.split(school, 1)[-1].strip("丨｜| -—")
    if len(value) < 3:
        return None
    return value


def _looks_like_bad_discipline(value: str) -> bool:
    bad_values = {"其他说明", "管理学院", "15", "岗位职责", "任职要求"}
    if value in bad_values:
        return True
    return len(value) < 4 and not any(ch in value for ch in ("学", "工程", "医学", "经济", "管理"))
