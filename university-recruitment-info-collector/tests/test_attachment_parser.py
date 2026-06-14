from university_recruitment.sources.attachment_parser import (
    build_attachment_augmented_text,
    extract_attachment_urls_from_html,
    looks_like_attachment_notice,
    parse_attachment_bytes,
    prepare_llm_input_text,
)


def test_looks_like_attachment_notice() -> None:
    assert looks_like_attachment_notice("详见附件1") is True
    assert looks_like_attachment_notice("招聘专任教师若干，含岗位职责和要求") is False


def test_extract_attachment_urls_from_html_supports_relative_urls() -> None:
    html = """
    <html><body>
      <a href="/files/positions.xlsx">附件1：岗位表</a>
      <a href="https://example.edu.cn/files/notice.pdf">下载PDF</a>
      <a href="/article/123">正文</a>
    </body></html>
    """
    result = extract_attachment_urls_from_html(html, "https://example.edu.cn/jobs/2026/notice.html")
    assert len(result) == 2
    urls = [u for _, u in result]
    assert "https://example.edu.cn/files/positions.xlsx" in urls
    assert "https://example.edu.cn/files/notice.pdf" in urls


def test_parse_attachment_bytes_csv() -> None:
    csv_bytes = "岗位,部门,学历\n专任教师,计算机学院,博士\n".encode("utf-8")
    text = parse_attachment_bytes("岗位需求.csv", csv_bytes)
    assert "专任教师" in text
    assert "计算机学院" in text


def test_build_attachment_augmented_text(monkeypatch) -> None:
    class _Resp:
        def __init__(self, text: str = "", content: bytes = b"") -> None:
            self.text = text
            self.content = content

        def raise_for_status(self) -> None:
            return None

    notice_html = '<a href="/files/jobs.csv">附件1：岗位表</a>'
    csv_bytes = "岗位,部门\n专任教师,计算机学院\n".encode("utf-8")

    def _fake_get(url, follow_redirects=True, timeout=20.0):
        if str(url).endswith("notice.html"):
            return _Resp(text=notice_html)
        if str(url).endswith("jobs.csv"):
            return _Resp(content=csv_bytes)
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("university_recruitment.sources.attachment_parser.httpx.get", _fake_get)
    merged, warnings = build_attachment_augmented_text(
        body_text="见附件1",
        notice_url="https://example.edu.cn/notice.html",
    )
    assert "附件1" in merged
    assert "专任教师" in merged
    assert warnings == []


def test_prepare_llm_input_text_uses_attachment_for_short_notice(monkeypatch) -> None:
    def _fake_build(body_text, notice_url, max_attachments=3, timeout=20.0, max_chars=12000):
        return body_text + "\n\n[附件1]\n专任教师 | 计算机学院 | 博士 | 广州 | 事业编 | 多个岗位信息字段", []

    monkeypatch.setattr(
        "university_recruitment.sources.attachment_parser.build_attachment_augmented_text",
        _fake_build,
    )
    text, used_attachment_text, warnings = prepare_llm_input_text(
        body_text="见附件1",
        notice_url="https://example.edu.cn/notice.html",
        min_chars=10,
    )
    assert used_attachment_text is True
    assert "专任教师" in text
    assert warnings == []
