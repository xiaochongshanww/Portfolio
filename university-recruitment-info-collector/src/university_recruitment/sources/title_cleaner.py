"""Title cleaning utilities for recruitment job positions.

Raw link text from Chinese university sites often contains noise:
- Date prefixes like "2025-04-18" or "2025年4月18日"
- School names duplicated from the source config
- Leading numbers, brackets, and separators
- Trailing bracket content like "（2025年4月）"

This module normalizes those into clean position titles.
"""

import re

# Patterns for date prefixes that should be stripped from position titles
_LEADING_DATE_PATTERNS = (
    # ISO-style: "2025-04-18" or "2025-04-18 "
    re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}\s*"),
    # Chinese-style: "2025年4月18日" or "2025年04月18日"
    re.compile(r"^\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日\s*"),
    # Short numeric prefix: "24 " or "18 " (year abbreviations)
    re.compile(r"^\d{2}\s+(?=[一-龥])"),
)

# Patterns for trailing bracket noise — only date/batch indicators
_TRAILING_BRACKET_PATTERNS = (
    # Full-width brackets with date: （2025年4月） （2025年） （第二批）
    re.compile(r"[（(]\s*(?:\d{4}\s*年\s*\d{1,2}\s*月?|第[一二三四五六七八九十\d]+批|二〇[二一二三四五六七八九〇]+年)\s*[）)]\s*$"),
    # Half-width brackets with date: (2025-04) (2025)
    re.compile(r"[(（]\s*\d{4}(?:[-/]\d{1,2})?\s*[)）]\s*$"),
    # Pure date suffix: " 2025年4月" or " 2025-04" at end
    re.compile(r"\s+\d{4}\s*年\s*\d{1,2}\s*月?\s*$"),
    re.compile(r"\s+\d{4}[-/]\d{1,2}\s*$"),
)

# Known noise prefixes
_NOISE_PREFIXES = (
    "当前位置：",
    "您所在的位置：",
    "首页 >",
    "首页>",
    "首页",
)

# Characters to strip from start/end
_STRIP_CHARS = "◆·•*-—>｜| \t\n\r"


def clean_position_title(title: str, school: str | None = None) -> str:
    """Clean a raw position title into a readable job title.

    Args:
        title: Raw link text from the list page.
        school: Optional school name to strip from the title.

    Returns:
        Cleaned position title.
    """
    if not title:
        return title

    title = title.strip()
    title = re.sub(r"\s+", " ", title)

    # Remove known noise prefixes
    for prefix in _NOISE_PREFIXES:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()

    # Remove leading date patterns
    for pattern in _LEADING_DATE_PATTERNS:
        title = pattern.sub("", title)

    # Remove trailing bracket noise (only date/batch indicators)
    for pattern in _TRAILING_BRACKET_PATTERNS:
        title = pattern.sub("", title)

    # Strip the school name if it appears at the beginning
    if school and title.startswith(school):
        title = title[len(school):].strip(_STRIP_CHARS)

    # Strip common separators at start
    title = title.lstrip(_STRIP_CHARS)

    # If title is now empty or too short, return original
    if len(title) < 3:
        return title

    return title.strip()
