"""Field validators and quality scoring for recruitment jobs."""

import json
import re
from dataclasses import dataclass
from typing import Any

from university_recruitment.models import DocumentType, QualityStatus, RecruitmentJob


# ── Field candidates ───────────────────────────────────

@dataclass
class FieldCandidate:
    value: Any
    source: str  # html_table_cell, attachment_cell, labeled_section, llm, regex, config_default
    confidence: float
    evidence_quote: str | None = None

    SOURCE_PRIORITY = {
        "html_table_cell": 1.00,
        "attachment_cell": 1.00,
        "labeled_section": 0.90,
        "llm_with_evidence": 0.85,
        "title_rule": 0.70,
        "regex_body": 0.35,
        "config_default": 0.30,
    }


def choose_best_candidate(field_name: str, candidates: list[FieldCandidate]) -> FieldCandidate | None:
    """Select the best candidate by source priority then confidence."""
    if not candidates:
        return None
    scored = [(FieldCandidate.SOURCE_PRIORITY.get(c.source, 0.3) * c.confidence, c) for c in candidates]
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


# ── Position validator ─────────────────────────────────

_NOTICE_TITLE_PATTERNS = (
    re.compile(r"^.*(?:招聘公告|招聘启事|招聘简章|招聘计划|公开招聘|人才引进公告|招聘通知)$"),
    re.compile(r"^第[一二三四五六七八九十\d]+批.*(?:招聘|公开).*公告$"),
    re.compile(r"^\d{4}年.*(?:招聘|招贤|引进).*公告$"),
    re.compile(r"^(?:高层次|紧缺|急需|优秀|骨干)人才.*(?:引进|招聘).*公告$"),
    re.compile(r"^(?:诚聘|诚邀|招募)"),
    re.compile(r"博士后(?:招聘|招收|进站)公告"),
    re.compile(r"^202\d年.*公告$"),
)

_SPECIFIC_POSITION_KEYWORDS = (
    "专任教师", "教师", "副教授", "教授", "讲师", "助教",
    "辅导员", "行政", "实验", "科研", "研究", "技术", "工程",
    "医师", "护士", "医生", "药师",
    "博士后", "院长", "主任", "秘书", "会计", "出纳",
    "管理", "干事", "编辑", "翻译", "馆员",
)


def looks_like_specific_position(value: str) -> tuple[bool, str]:
    """Check if position value is a specific position vs a notice title."""
    if not value:
        return False, "empty"
    cleaned = value.strip()
    for pat in _NOTICE_TITLE_PATTERNS:
        if pat.match(cleaned):
            return False, f"notice_title_match: {pat.pattern[:40]}"
    # If it matches at least one specific position keyword, likely a real position
    if any(kw in cleaned for kw in _SPECIFIC_POSITION_KEYWORDS):
        return True, "has_specific_keyword"
    # Short titles are suspicious
    if len(cleaned) < 6:
        return False, "too_short"
    # Contains specific position patterns
    if re.search(r"[（(]岗[位]?[)）]|—|—|兼", cleaned):
        return True, "contains_position_markers"
    # Pure date-like or batch titles
    if re.match(r"^\d{4}", cleaned) and not any(kw in cleaned for kw in _SPECIFIC_POSITION_KEYWORDS):
        return False, "date_like_no_keyword"
    return True, "accepted"


# ── Department validator ───────────────────────────────

_DEPARTMENT_REJECT_CONTENT = (
    "报名", "出具", "应聘", "资格", "留学服务", "党组织",
    "邮件", "投稿", "下载", "个人中心",
)
_DEPARTMENT_REJECT_PREFIX = (
    "是", "为", "在", "由", "必须", "应聘", "国外留学人员", "以电子邮件",
)
_DEPARTMENT_VALID_SUFFIXES = (
    "学院", "学部", "系", "部", "研究院", "医院", "中心", "实验室", "课题组",
)
_DEPARTMENT_REJECT_EXACT = {
    "教育部", "农业农村部", "人力资源部", "人事部", "学校", "本校", "招聘单位",
    "用人单位", "用人部门", "各学院", "相关部门",
}


def validate_department_candidate(value: str | None, evidence_text: str | None = None) -> tuple[str | None, list[str]]:
    """Validate a department candidate. Returns (validated_value, warnings)."""
    warnings: list[str] = []
    if not value:
        return None, warnings
    v = value.strip()

    # Check exact rejects
    if v in _DEPARTMENT_REJECT_EXACT:
        warnings.append(f"department '{v}' is not an organization name")
        return None, warnings

    # Check content patterns
    for pat in _DEPARTMENT_REJECT_CONTENT:
        if pat in v:
            warnings.append(f"department contains '{pat}'")
            return None, warnings

    # Check prefix patterns
    for pre in _DEPARTMENT_REJECT_PREFIX:
        if v.startswith(pre):
            warnings.append(f"department starts with '{pre}'")
            return None, warnings

    # Check length
    if len(v) > 40:
        warnings.append(f"department too long ({len(v)} chars)")
        return None, warnings

    # Check suffix
    if not any(v.endswith(suf) for suf in _DEPARTMENT_VALID_SUFFIXES):
        warnings.append(f"department missing valid suffix")
        return None, warnings

    return v, warnings


# ── Discipline validator ────────────────────────────────

_DISCIPLINE_REJECT_EXACT = {
    "基本条件", "其他要求", "岗位要求", "招聘联系人", "需求人数",
    "任职要求", "招聘条件", "报名条件", "资格条件",
}
_DISCIPLINE_REJECT_CONTENT = (
    "学历", "硕士", "博士", "本科", "学位",
    "周岁", "岁以下", "年龄",
    "中共党员", "中国共产党",
    "工作经历", "工作年限",
)


def validate_discipline_value(value: str) -> tuple[str | None, list[str]]:
    """Validate a single discipline value. Returns (validated, warnings)."""
    warnings: list[str] = []
    if not value:
        return None, warnings
    v = value.strip()

    if v in _DISCIPLINE_REJECT_EXACT:
        warnings.append(f"discipline is generic label: '{v}'")
        return None, warnings

    if len(v) > 120:
        warnings.append(f"discipline too long ({len(v)} chars)")
        return None, warnings

    for pat in _DISCIPLINE_REJECT_CONTENT:
        if pat in v:
            warnings.append(f"discipline contains '{pat}' — likely not a discipline name")
            return None, warnings

    return v, warnings


# ── Education validator ─────────────────────────────────

_VALID_EDUCATIONS = frozenset({
    "博士研究生", "博士", "硕士研究生及以上", "硕士研究生",
    "硕士及以上", "硕士", "本科及以上", "本科",
})


def validate_education(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    # Sort by length descending so "硕士研究生及以上" matches first
    for valid in sorted(_VALID_EDUCATIONS, key=len, reverse=True):
        if v == valid or valid in v:
            return valid
    return None


# ── Location validator ──────────────────────────────────

_CITY_RE = re.compile(r"(广州|深圳|珠海|佛山|东莞|中山|惠州|汕头|湛江|肇庆|江门|茂名|梅州|韶关|清远|河源|揭阳|阳江|潮州|云浮|汕尾)")
_DISTRICT_RE = re.compile(r"(荔湾|越秀|海珠|天河|白云|黄埔|番禺|花都|南沙|从化|增城|福田|罗湖|南山|宝安|龙岗|盐田|坪山|龙华|光明|香洲|金湾|斗门|禅城|南海|顺德|高明|三水|莞城|东城|南城|万江|石龙|虎门|长安)")
_ADDRESS_CLEAN_RE = re.compile(r"广州市?|深圳市?|珠海市?|等地|附近")


def normalize_location(value: str | None) -> tuple[str | None, str | None, str | None, list[str]]:
    """Normalize location into (city, district, address, warnings)."""
    warnings: list[str] = []
    if not value:
        return None, None, None, warnings
    v = value.strip().replace(" ", "")

    city = None
    district = None
    address = None

    # Check for structured format: "广州-天河区" or "广州·海珠区"
    parts = re.split(r"[-—·/]", v)
    if len(parts) >= 2:
        city = parts[0]
        for p in parts[1:]:
            if _DISTRICT_RE.search(p):
                district = p
                break
        if len(parts) > 2:
            address = "".join(parts[2:])

    if not city:
        m = _CITY_RE.search(v)
        if m:
            city = m.group(1)
    if not district:
        m = _DISTRICT_RE.search(v)
        if m:
            district = m.group(1)
    if not address:
        clean = _ADDRESS_CLEAN_RE.sub("", v)
        if city:
            clean = clean.replace(city, "")
        if district:
            clean = clean.replace(district, "")
        if clean and clean not in ("", "-", "—", "/"):
            address = clean.strip("-—/ ")

    if not city:
        warnings.append(f"cannot extract city from: '{v}'")
        return None, None, None, warnings

    return city, district, address, warnings


# ── Quality scoring ─────────────────────────────────────

def calculate_job_quality(job: RecruitmentJob, doc_type: str | None = None) -> tuple[int, str, list[str]]:
    """Calculate quality score and status for a job. Returns (score, status, warnings)."""
    score = 0
    warnings: list[str] = []

    # Position quality
    is_specific, reason = looks_like_specific_position(job.position)
    if is_specific:
        score += 20
    else:
        score -= 30
        warnings.append(f"position looks like notice title: {reason}")

    # Normalized position
    if job.normalized_position:
        score += 5

    # Department
    if job.department:
        dept_val, dept_warnings = validate_department_candidate(job.department)
        if dept_val:
            score += 10
            if len(dept_warnings) == 0:
                score += 5  # bonus for clean dept
        else:
            score -= 25
            warnings.extend(dept_warnings)
    else:
        score -= 5

    # Discipline
    if job.discipline:
        disc_val, disc_warnings = validate_discipline_value(job.discipline)
        if disc_val:
            score += 10
        else:
            score -= 20
            warnings.extend(disc_warnings)
    else:
        score -= 5

    # Education
    if job.education_requirement:
        edu = validate_education(job.education_requirement)
        if edu:
            score += 10
        else:
            score -= 5
            warnings.append(f"invalid education: {job.education_requirement}")

    # Job type
    if job.job_type:
        score += 10

    # Location
    if job.location:
        city, district, addr, loc_warnings = normalize_location(job.location)
        if city:
            score += 5
        if district:
            score += 3
        if loc_warnings:
            warnings.extend(loc_warnings)

    # Deadline
    if job.deadline:
        score += 5

    # Published at
    if job.published_at:
        score += 3

    # Evidence
    if job.evidence_json:
        score += 5

    # Doc type
    if doc_type == "single_position":
        score += 5
    elif doc_type == "multi_position_notice":
        score += 3

    # Final score
    final = max(0, min(score, 100))

    if final >= 75:
        status = QualityStatus.NORMAL.value
    elif final >= 45:
        status = QualityStatus.NEEDS_REVIEW.value
    else:
        status = QualityStatus.HIDDEN.value
        warnings.append(f"low quality score ({final})")

    return final, status, warnings


# ── Helper for building quality metadata ────────────────

def build_extraction_warnings_json(warnings: list[str]) -> str | None:
    if not warnings:
        return None
    return json.dumps(warnings, ensure_ascii=False)
