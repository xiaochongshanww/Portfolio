"""工具函数测试 — 覆盖 utils/common.py。"""

from app.models import AuditLog
from app.utils import common as cu


class TestRenderMarkdown:
    def test_empty(self):
        assert cu.render_markdown("") == ""

    def test_markdown_to_safe_html(self):
        html = cu.render_markdown("# Title\n\n**bold** and <script>alert(1)</script>")
        assert "<h1" in html
        assert "<script>" not in html


class TestAuditLog:
    def test_creates_audit(self, app):
        cu.audit_log("approve", operator_id=1, note="ok", article_id=5)
        entry = AuditLog.query.filter_by(action="approve").first()
        assert entry is not None
        assert entry.operator_id == 1
        assert entry.article_id == 5


class TestComputeEtag:
    def test_dict_etag_stable(self):
        e1 = cu.compute_etag({"a": 1, "b": 2})
        e2 = cu.compute_etag({"b": 2, "a": 1})
        assert e1 == e2
        assert e1.startswith('W/"')

    def test_string_etag(self):
        e = cu.compute_etag("hello")
        assert e.startswith('W/"')

    def test_none_etag(self):
        assert cu.compute_etag(None).startswith('W/"')
