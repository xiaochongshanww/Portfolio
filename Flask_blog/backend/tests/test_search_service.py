"""搜索业务逻辑测试 — 覆盖 search/service.py。"""

from app import db
from app.models import Article, Tag, User
from app.search import service as search_svc


def _user():
    u = User(email="s@test.com", password_hash="x", role="author")
    db.session.add(u)
    db.session.commit()
    return u


def _article(author_id, **kw):
    data = {
        "title": "Searchable",
        "slug": "s",
        "content_md": "x",
        "author_id": author_id,
        "status": "published",
    }
    data.update(kw)
    a = Article(**data)
    db.session.add(a)
    db.session.commit()
    return a


class TestBuildSearchParams:
    def test_base_params(self):
        p = search_svc.build_search_params(1, 10, [], None, None)
        assert p["limit"] == 10
        assert p["offset"] == 0
        assert "filter" not in p
        assert "facets" not in p

    def test_with_filter_facets_sort(self):
        p = search_svc.build_search_params(
            2, 20, ["status = 'published'"], ["tags"], "published_at:desc"
        )
        assert p["offset"] == 20
        assert p["filter"] == ["status = 'published'"]
        assert p["facets"] == ["tags"]
        assert p["sort"] == ["published_at:desc"]


class TestParseFilters:
    def test_status_and_dates(self):
        clauses, sort = search_svc.parse_filters(
            "published", None, "and", None, None, "2026-01-01", "2026-02-01", None
        )
        assert any("status = 'published'" in c for c in clauses)
        assert any("published_at >= 2026-01-01" in c for c in clauses)

    def test_tags_and_mode(self):
        clauses, _ = search_svc.parse_filters(
            None, ["vue", "react"], "and", None, None, None, None, None
        )
        assert "tags = 'vue'" in clauses

    def test_tags_or_mode(self):
        clauses, _ = search_svc.parse_filters(
            None, ["vue", "react"], "or", None, None, None, None, None
        )
        assert any("vue" in c and "react" in c for c in clauses)

    def test_category_author(self):
        clauses, _ = search_svc.parse_filters(
            None, None, "and", "3", "7", None, None, None
        )
        assert "category_id = 3" in clauses
        assert "author_id = 7" in clauses

    def test_sort_validation(self):
        _, sort = search_svc.parse_filters(
            None, None, "and", None, None, None, None, "views_count:desc"
        )
        assert sort == "views_count:desc"
        _, bad = search_svc.parse_filters(
            None, None, "and", None, None, None, None, "hacked:desc"
        )
        assert bad is None


class TestDbFallback:
    def test_search_by_keyword(self, app):
        u = _user()
        _article(u.id, title="Special Keyword Article")
        total, hits, _facets = search_svc._db_fallback(
            "Special", [], "and", None, None, None, None, None, 1, 10, None
        )
        assert total >= 1
        assert len(hits) >= 1

    def test_search_by_tag(self, app):
        u = _user()
        a = _article(u.id)
        t = Tag(name="t", slug="fallback-tag")
        db.session.add(t)
        db.session.commit()
        a.tags.append(t)
        db.session.commit()
        total, hits, _facets = search_svc._db_fallback(
            "", ["fallback-tag"], "and", None, None, None, None, None, 1, 10, None
        )
        assert total >= 1
        assert len(hits) >= 1

    def test_category_filter(self, app):
        u = _user()
        from app.models import Category

        c = Category(name="c", slug="fallback-cat")
        db.session.add(c)
        db.session.commit()
        _article(u.id, category_id=c.id)
        total, hits, _facets = search_svc._db_fallback(
            "", [], "and", str(c.id), None, None, None, None, 1, 10, None
        )
        assert total >= 1
        assert len(hits) >= 1
