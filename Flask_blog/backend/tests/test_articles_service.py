"""文章业务逻辑测试 — 覆盖 articles/service.py。"""

from datetime import datetime, timedelta, timezone

from app import db
from app.articles import service as svc
from app.models import Article, ArticleVersion, User


def _user(**kw):
    data = {"email": "a@test.com", "password_hash": "x", "role": "author"}
    data.update(kw)
    u = User(**data)
    db.session.add(u)
    db.session.commit()
    return u


def _article(author_id=None, **kw):
    if author_id is None:
        author_id = _user().id
    import uuid

    data = {
        "title": "T",
        "slug": f"t-{uuid.uuid4().hex[:8]}",
        "content_md": "x",
        "author_id": author_id,
        "status": "draft",
    }
    data.update(kw)
    a = Article(**data)
    db.session.add(a)
    db.session.commit()
    return a


class TestHelpers:
    def test_parse_dt(self):
        assert svc.parse_dt("2026-01-01T10:00:00") is not None
        assert svc.parse_dt("bogus") is None
        assert svc.parse_dt(None) is None

    def test_slug_helpers(self):
        assert svc._safe_article_slug("Hello World") == "hello-world"
        assert svc._tag_slug("Vue JS") == "vue-js"

    def test_make_focal_crops_none(self):
        assert not svc._make_focal_crops(None, None, None)

    def test_serialize_article_detail(self, app):
        u = _user()
        a = _article(author_id=u.id, status="published")
        d = svc.serialize_article(a, detail=True, include_user_flags=True, user_id=u.id)
        assert d["id"] == a.id
        assert d["status"] == "published"
        assert "content_md" in d

    def test_check_visibility(self, app):
        u = _user()
        a = _article(author_id=u.id, status="draft")
        # 作者可见
        assert svc.check_article_visibility(a, "author", u.id) is True
        # 无角色不可见
        assert svc.check_article_visibility(a, None, None) is False
        pub = _article(author_id=u.id, status="published")
        assert svc.check_article_visibility(pub, None, None) is True


class TestVersions:
    def test_create_version_snapshot(self, app):
        u = _user()
        a = _article(author_id=u.id)
        vno = svc.create_version_snapshot(a, u.id)
        assert vno >= 1
        assert ArticleVersion.query.filter_by(article_id=a.id).count() >= 1

    def test_diff_versions(self, app):
        u = _user()
        a = _article(author_id=u.id)
        svc.create_version_snapshot(a, u.id)
        a.title = "Changed"
        db.session.commit()
        svc.create_version_snapshot(a, u.id)
        diff = svc.diff_versions(a.id, 1, 2)
        assert isinstance(diff, list)

    def test_rollback_to_version(self, app):
        u = _user()
        a = _article(author_id=u.id, title="Original")
        svc.create_version_snapshot(a, u.id)
        a.title = "Modified"
        db.session.commit()
        svc.create_version_snapshot(a, u.id)
        result = svc.rollback_to_version(a, 1, u.id)
        assert result is not None
        assert ArticleVersion.query.filter_by(article_id=a.id).count() >= 2


class TestInteractions:
    def test_toggle_like(self, app):
        u = _user()
        a = _article(author_id=u.id, status="published")
        action, count = svc.toggle_like(a.id, u.id)
        assert action == "liked"
        assert count == 1
        action2, count2 = svc.toggle_like(a.id, u.id)
        assert action2 == "unliked"
        assert count2 == 0

    def test_toggle_bookmark(self, app):
        u = _user()
        a = _article(author_id=u.id, status="published")
        action, count = svc.toggle_bookmark(a.id, u.id)
        assert action == "bookmarked"
        assert count == 1


class TestWorkflow:
    def test_submit(self, app):
        u = _user()
        a = _article(author_id=u.id)
        svc.submit_article(a, u.id)
        assert a.status == "pending"

    def test_approve(self, app):
        u = _user()
        a = _article(author_id=u.id, status="pending")
        svc.approve_article(a, u.id)
        assert a.status == "published"
        assert a.published_at is not None

    def test_reject(self, app):
        u = _user()
        a = _article(author_id=u.id, status="pending")
        svc.reject_article(a, "needs work", u.id)
        assert a.status in ("rejected", "draft")

    def test_schedule(self, app):
        u = _user()
        a = _article(author_id=u.id, status="pending")
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        svc.schedule_article(a, future, u.id, "editor")
        assert a.status == "scheduled"
        assert a.scheduled_at is not None

    def test_unschedule(self, app):
        u = _user()
        a = _article(author_id=u.id, status="scheduled")
        svc.unschedule_article(a, u.id, "editor")
        assert a.status in ("pending", "draft")

    def test_unpublish(self, app):
        u = _user()
        a = _article(author_id=u.id, status="published")
        svc.unpublish_article(a, u.id)
        assert a.status == "draft"

    def test_delete(self, app):
        u = _user()
        a = _article(author_id=u.id)
        svc.delete_article(a, u.id)
        assert a.deleted is True
