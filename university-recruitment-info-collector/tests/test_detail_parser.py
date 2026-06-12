"""Tests for HTML detail parser (detail_parser.py)."""

from datetime import date

from university_recruitment.sources.detail_parser import (
    DATE_PATTERNS,
    DEADLINE_KEYWORDS,
    parse_detail_html,
    _extract_dates,
    _extract_deadline,
    _extract_labeled_date,
    _extract_published_at,
)


class TestExtractDates:
    def test_iso_format(self) -> None:
        text = "报名时间：2026-06-15 至 2026-07-30"
        dates = _extract_dates(text)
        assert date(2026, 6, 15) in dates
        assert date(2026, 7, 30) in dates

    def test_slash_format(self) -> None:
        text = "截止 2026/08/15"
        dates = _extract_dates(text)
        assert date(2026, 8, 15) in dates

    def test_chinese_format(self) -> None:
        text = "2026年6月15日"
        dates = _extract_dates(text)
        assert date(2026, 6, 15) in dates

    def test_dot_format(self) -> None:
        text = "2026.09.01"
        dates = _extract_dates(text)
        assert date(2026, 9, 1) in dates

    def test_invalid_date_ignored(self) -> None:
        text = "2026-02-30 至 2026-03-01"
        dates = _extract_dates(text)
        assert date(2026, 3, 1) in dates
        assert len(dates) == 1

    def test_no_dates(self) -> None:
        text = "本公告长期有效，招满为止"
        dates = _extract_dates(text)
        assert dates == []


class TestExtractDeadline:
    def test_exact_label(self) -> None:
        text = "截止日期：2026-12-31。其他说明..."
        deadline = _extract_deadline(text)
        assert deadline == date(2026, 12, 31)

    def test_keyword_in_text(self) -> None:
        text = "简历投递截至 2026-10-15，面试另行通知"
        deadline = _extract_deadline(text)
        assert deadline == date(2026, 10, 15)

    def test_multiple_candidates_takes_max(self) -> None:
        text = "报名时间：2026-06-01 至 2026-08-30，截止日期 2026-09-15"
        deadline = _extract_deadline(text)
        assert deadline == date(2026, 9, 15)

    @staticmethod
    def test_no_deadline() -> None:
        text = "本公告没有截止日期，长期招聘"
        deadline = _extract_deadline(text)
        assert deadline is None


class TestExtractPublishedAt:
    def test_labeled_date(self) -> None:
        text = "发布时间：2026-05-20。招聘岗位如下..."
        pub = _extract_published_at(text)
        assert pub == date(2026, 5, 20)

    def test_fallback_to_earliest_date(self) -> None:
        text = "相关信息发布于 2026-04-10，报名截止 2026-06-01。"
        pub = _extract_published_at(text)
        assert pub == date(2026, 4, 10)

    def test_no_publish_date(self) -> None:
        text = "招聘教师若干名"
        pub = _extract_published_at(text)
        assert pub is None


class TestParseDetailHtml:
    def test_strips_script_style(self) -> None:
        html = """
        <html>
        <head><title>招聘公告</title></head>
        <body>
        <script>alert('test')</script>
        <style>.hidden{display:none}</style>
        <p>发布时间：2026-06-01</p>
        <p>截止日期：2026-12-31</p>
        </body>
        </html>
        """
        result = parse_detail_html(html)
        assert "alert" not in result.text
        assert ".hidden" not in result.text
        assert "发布时间" in result.text
        assert result.published_at == date(2026, 6, 1)
        assert result.deadline == date(2026, 12, 31)

    def test_trim_noise_lines(self) -> None:
        html = """
        <html><head><title>公告</title></head>
        <body>
        <p>首页</p>
        <p>导航痕迹 > 招聘</p>
        <p>招聘教师公告</p>
        <p>版权所有 © 2026</p>
        </body>
        </html>
        """
        result = parse_detail_html(html)
        assert "首页" not in result.text
        assert "版权所有" not in result.text
        assert "招聘教师公告" in result.text

    def test_deadline_before_published_ignored(self) -> None:
        html = """
        <html><head><title>公告</title></head>
        <body>
        <p>发布时间：2026-06-01</p>
        <p>截止日期：2025-12-31</p>
        </body>
        </html>
        """
        result = parse_detail_html(html)
        assert result.deadline is None

    def test_empty_html(self) -> None:
        result = parse_detail_html("<html></html>")
        assert result.text == ""
        assert result.published_at is None
        assert result.deadline is None
