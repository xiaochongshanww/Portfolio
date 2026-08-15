"""Markdown 渲染与 HTML 清洗测试。"""

from app.services.content_sanitizer import (
    render_and_sanitize,
    render_and_sanitize_simple,
    render_markdown,
    sanitize_html,
)


class TestRenderMarkdown:
    def test_none(self):
        assert render_markdown(None) == ""
        assert render_markdown("") == ""

    def test_basic(self):
        html = render_markdown("# Title\n\nsome **bold**")
        assert "<h1" in html and "Title" in html
        assert "<strong>bold</strong>" in html

    def test_table_extension(self):
        html = render_markdown("| a | b |\n|---|---|\n| 1 | 2 |")
        assert "<table>" in html


class TestSanitize:
    def test_none(self):
        assert sanitize_html(None) == ""
        assert sanitize_html("") == ""

    def test_strips_scripts(self):
        out = sanitize_html("<p>hello</p><script>alert(1)</script>")
        assert "hello" in out
        assert "<script" not in out

    def test_allows_safe_tags(self):
        out = sanitize_html('<p><a href="https://x.com" title="t">link</a></p>')
        assert "<a href=" in out
        assert "https://x.com" in out

    def test_strips_unsafe_attrs(self):
        out = sanitize_html('<img src="x" onerror="alert(1)">')
        assert "onerror" not in out

    def test_iframe_whitelist_keeps_youtube(self):
        html = (
            '<div class="video-embed"><iframe src="https://www.youtube.com/embed/abc" '
            'loading="lazy" allowfullscreen frameborder="0"></iframe></div>'
        )
        out = sanitize_html(html)
        assert "youtube.com/embed/abc" in out

    def test_iframe_non_whitelist_removed(self):
        html = '<iframe src="https://evil.com/x"></iframe>'
        out = sanitize_html(html)
        assert "<iframe" not in out


class TestVideoIframeBuilder:
    def test_youtube_watch(self):
        from app.services.content_sanitizer import _build_video_iframe

        out = _build_video_iframe("https://www.youtube.com/watch?v=VID123")
        assert "https://www.youtube.com/embed/VID123" in out

    def test_youtube_short(self):
        from app.services.content_sanitizer import _build_video_iframe

        out = _build_video_iframe("https://youtu.be/SHORTID")
        assert "/embed/SHORTID" in out

    def test_bilibili(self):
        from app.services.content_sanitizer import _build_video_iframe

        out = _build_video_iframe("https://www.bilibili.com/video/BV1xx411c7mD")
        assert "player.bilibili.com/player.html?bvid=BV1xx411c7mD" in out

    def test_vimeo(self):
        from app.services.content_sanitizer import _build_video_iframe

        out = _build_video_iframe("https://vimeo.com/12345678")
        assert "player.vimeo.com/video/12345678" in out

    def test_unknown_host(self):
        from app.services.content_sanitizer import _build_video_iframe

        assert _build_video_iframe("https://example.com/x") == ""


class TestShortcodes:
    def test_video_shortcode(self):
        from app.services.content_sanitizer import _preprocess_shortcodes

        out = _preprocess_shortcodes(":::video https://www.youtube.com/watch?v=VVV :::")
        assert "youtube.com/embed/VVV" in out

    def test_gist_shortcode(self):
        from app.services.content_sanitizer import _preprocess_shortcodes

        out = _preprocess_shortcodes(":::gist https://gist.github.com/u/abc :::")
        assert 'class="embed-gist"' in out
        assert 'data-gist="https://gist.github.com/u/abc"' in out

    def test_bad_video_falls_back(self):
        from app.services.content_sanitizer import _preprocess_shortcodes

        out = _preprocess_shortcodes(":::video https://example.com/x :::")
        assert ":::video" in out  # kept as raw line


class TestRenderAndSanitize:
    def test_full_pipeline(self):
        out = render_and_sanitize("# hi\n\n<script>x</script>")
        assert "<h1>hi</h1>" in out
        assert "<script" not in out

    def test_none(self):
        assert render_and_sanitize(None) == ""
        assert render_and_sanitize_simple(None) == ""
        assert render_and_sanitize_simple("") == ""

    def test_simple(self):
        out = render_and_sanitize_simple("**bold**")
        assert "<strong>bold</strong>" in out
