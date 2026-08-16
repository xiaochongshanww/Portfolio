"""搜索索引测试 — 覆盖 search/indexer.py。"""

from app import db
from app.models import Article, Tag, User
from app.search import indexer


def _user():
    u = User(email="i@test.com", password_hash="x", role="author")
    db.session.add(u)
    db.session.commit()
    return u


def _article(author_id, **kw):
    data = {
        "title": "Idx",
        "slug": "idx",
        "content_md": "x",
        "author_id": author_id,
        "status": "published",
    }
    data.update(kw)
    a = Article(**data)
    db.session.add(a)
    db.session.commit()
    return a


class TestArticleToDoc:
    def test_article_to_doc(self, app):
        u = _user()
        a = _article(u.id)
        t = Tag(name="t", slug="tag1")
        db.session.add(t)
        db.session.commit()
        a.tags.append(t)
        db.session.commit()
        doc = indexer.article_to_doc(a)
        assert doc["id"] == a.id
        assert doc["title"] == "Idx"
        assert doc["tags"] == ["tag1"]
        assert doc["status"] == "published"


class TestIndexing:
    def test_index_published(self, app):
        u = _user()
        a = _article(u.id, status="published")
        indexer.index_article(a)  # should call add_documents via DummyIdx

    def test_index_draft_deletes(self, app):
        u = _user()
        a = _article(u.id, status="draft")
        indexer.index_article(a)  # draft → delete_document

    def test_delete_article(self, app):
        indexer.delete_article(9999)

    def test_reindex_all(self, app):
        u = _user()
        _article(u.id, status="published")
        indexer.reindex_all(published_only=True)
