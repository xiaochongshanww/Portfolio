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
    "硕士",
    "本科及以上",
    "本科",
)
DISCIPLINE_LABELS = ("需求学科", "学科专业", "专业要求", "招聘专业", "相关专业", "专业方向")
DEPARTMENT_PATTERN = re.compile(
    r"([\u4e00-\u9fa5A-Za-z0-9（）()·]+(?:学院|学部|研究院|医院|中心|实验室|课题组|系|部))"
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
    for match in DEPARTMENT_PATTERN.finditer(title):
        value = _clean_department(match.group(1), school)
        if value:
            return value
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
