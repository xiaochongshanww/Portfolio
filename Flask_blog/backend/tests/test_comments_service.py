"""评论业务逻辑测试 — 覆盖 comments/service.py。"""

from app import db
from app.comments import service as comment_svc
from app.models import Article, Comment, User


def _user(**kw):
    u = User(
        email=kw.pop("email", "c@test.com"), password_hash="x", role="author", **kw
    )
    db.session.add(u)
    db.session.commit()
    return u


def _article(author_id=None, **kw):
    if author_id is None:
        author_id = _user().id
    data = {
        "title": "A",
        "slug": "a",
        "content_md": "x",
        "author_id": author_id,
        "status": "published",
    }
    data.update(kw)
    a = Article(**data)
    db.session.add(a)
    db.session.commit()
    return a


def _comment(article_id, user_id, **kw):
    data = {
        "article_id": article_id,
        "user_id": user_id,
        "content": "hello",
        "status": "pending",
    }
    data.update(kw)
    c = Comment(**data)
    db.session.add(c)
    db.session.commit()
    return c


class TestCreateComment:
    def test_create_root_comment(self, app):
        u = _user()
        a = _article(author_id=u.id)
        c = comment_svc.create_comment(u.id, a.id, "nice post")
        assert c.parent_id is None
        assert c.status == "pending"

    def test_article_not_found(self, app):
        u = _user()
        try:
            comment_svc.create_comment(u.id, 9999, "x")
            assert False
        except comment_svc.CommentServiceError as e:
            assert e.code == 4040

    def test_unpublished_article_rejected(self, app):
        u = _user()
        a = _article(author_id=u.id, status="draft")
        try:
            comment_svc.create_comment(u.id, a.id, "x")
            assert False
        except comment_svc.CommentServiceError as e:
            assert e.code == 4040

    def test_invalid_parent(self, app):
        u = _user()
        a = _article(author_id=u.id)
        try:
            comment_svc.create_comment(u.id, a.id, "x", parent_id=9999)
            assert False
        except comment_svc.CommentServiceError as e:
            assert e.status == 400

    def test_max_depth(self, app):
        u = _user()
        a = _article(author_id=u.id)
        c1 = _comment(a.id, u.id, status="approved")
        c2 = _comment(a.id, u.id, status="approved", parent_id=c1.id)
        c3 = _comment(a.id, u.id, status="approved", parent_id=c2.id)
        try:
            comment_svc.create_comment(u.id, a.id, "x", parent_id=c3.id)
            assert False
        except comment_svc.CommentServiceError as e:
            assert "max depth" in e.message


class TestSerializationAndTree:
    def test_serialize_comment(self, app):
        u = _user()
        a = _article(author_id=u.id)
        c = _comment(a.id, u.id, status="approved")
        d = comment_svc.serialize_comment(c)
        assert d["content"] == "hello"
        assert "status" not in d
        d2 = comment_svc.serialize_comment(c, include_status=True)
        assert d2["status"] == "approved"

    def test_build_tree(self, app):
        u = _user()
        a = _article(author_id=u.id)
        parent = _comment(a.id, u.id, status="approved")
        child = _comment(a.id, u.id, status="approved", parent_id=parent.id)
        tree = comment_svc.build_comment_tree([parent, child])
        assert len(tree) == 1
        assert len(tree[0]["children"]) == 1


class TestQueries:
    def test_list_approved(self, app):
        u = _user()
        a = _article(author_id=u.id)
        _comment(a.id, u.id, status="approved")
        _comment(a.id, u.id, status="pending")
        assert len(comment_svc.list_approved(a.id)) == 1

    def test_list_pending(self, app):
        u = _user()
        a = _article(author_id=u.id)
        _comment(a.id, u.id, status="pending")
        result = comment_svc.list_pending(1, 10)
        assert result["total"] == 1
        assert result["has_next"] is False

    def test_admin_list_filters(self, app):
        u = _user()
        a = _article(author_id=u.id)
        _comment(a.id, u.id, status="approved", content="unique text")
        _comment(a.id, u.id, status="pending", content="other")
        result = comment_svc.admin_list(1, 10, status="approved")
        assert result["total"] == 1
        result2 = comment_svc.admin_list(1, 10, content="unique")
        assert result2["total"] == 1

    def test_get_stats(self, app):
        u = _user()
        a = _article(author_id=u.id)
        _comment(a.id, u.id, status="pending")
        stats = comment_svc.get_stats()
        assert stats["pending"] >= 1
        assert stats["total"] >= 1


class TestModeration:
    def test_moderate_approve(self, app):
        u = _user()
        a = _article(author_id=u.id)
        c = _comment(a.id, u.id)
        comment_svc.moderate_comment(c, "approve")
        assert c.status == "approved"

    def test_moderate_reject(self, app):
        u = _user()
        a = _article(author_id=u.id)
        c = _comment(a.id, u.id)
        comment_svc.moderate_comment(c, "reject")
        assert c.status == "rejected"

    def test_moderate_invalid(self, app):
        u = _user()
        a = _article(author_id=u.id)
        c = _comment(a.id, u.id)
        try:
            comment_svc.moderate_comment(c, "bogus")
            assert False
        except comment_svc.CommentServiceError:
            pass

    def test_moderate_batch(self, app):
        u = _user()
        a = _article(author_id=u.id)
        c1 = _comment(a.id, u.id)
        c2 = _comment(a.id, u.id)
        status, count = comment_svc.moderate_batch([c1, c2], "approve")
        assert status == "approved"
        assert count == 2
        assert c1.status == "approved"
        assert c2.status == "approved"
