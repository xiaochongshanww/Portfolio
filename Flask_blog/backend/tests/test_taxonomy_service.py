"""分类/标签业务逻辑测试 — 覆盖 taxonomy/service.py。"""

from app import db
from app.models import Article, ArticleTag, Tag, User
from app.taxonomy import service as tax


def _user():
    u = User(email="t@test.com", password_hash="x", role="author")
    db.session.add(u)
    db.session.commit()
    return u


def _article(author_id, **kw):
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


class TestSlug:
    def test_valid_slug(self):
        assert tax.is_valid_slug("hello-world") is True
        assert tax.is_valid_slug("Bad Slug") is False
        assert tax.is_valid_slug("") is False
        assert tax.is_valid_slug(None) is False

    def test_make_slug(self):
        assert tax.make_slug("Hello World") == "hello-world"
        assert tax.make_slug("  VUE 3  ") == "vue-3"
        assert tax.make_slug("") == ""


class TestCategory:
    def test_create_category(self):
        c = tax.create_category("Frontend Dev")
        assert c.slug == "frontend-dev"
        assert c.name == "Frontend Dev"

    def test_create_category_slug_exists(self):
        tax.create_category("测试", slug="dup")
        try:
            tax.create_category("其他", slug="dup")
            assert False
        except tax.TaxonomyError as e:
            assert e.code == 4090

    def test_create_category_parent_not_found(self):
        try:
            tax.create_category("x", parent_id=9999)
            assert False
        except tax.TaxonomyError as e:
            assert e.code == 4040

    def test_list_categories(self):
        tax.create_category("a", slug="ca")
        assert len(tax.list_categories()) >= 1

    def test_update_category(self):
        c = tax.create_category("old", slug="co")
        tax.update_category(c, name="new", slug="cn")
        assert c.name == "new"
        assert c.slug == "cn"

    def test_update_category_self_parent(self):
        c = tax.create_category("x", slug="cx")
        try:
            tax.update_category(c, parent_id=c.id)
            assert False
        except tax.TaxonomyError:
            pass

    def test_delete_category(self):
        u = _user()
        c = tax.create_category("del", slug="cd")
        a = _article(u.id, category_id=c.id)
        affected = tax.delete_category(c)
        assert affected == 1
        assert a.category_id is None


class TestTag:
    def test_create_tag(self):
        t = tax.create_tag("Vue")
        assert t.name == "Vue"
        assert t.slug == "vue"

    def test_create_tag_slug_exists(self):
        tax.create_tag("one", slug="dup")
        try:
            tax.create_tag("two", slug="dup")
            assert False
        except tax.TaxonomyError as e:
            assert e.code == 4090

    def test_list_tags(self):
        tax.create_tag("t1", slug="t1")
        assert len(tax.list_tags()) >= 1

    def test_update_tag(self):
        t = tax.create_tag("a", slug="ta")
        tax.update_tag(t, name="b", slug="tb")
        assert t.name == "b"
        assert t.slug == "tb"

    def test_delete_tag_in_use(self):
        u = _user()
        a = _article(u.id)
        t = tax.create_tag("used", slug="tused")
        db.session.add(ArticleTag(article_id=a.id, tag_id=t.id))
        db.session.commit()
        try:
            tax.delete_tag(t)
            assert False
        except tax.TaxonomyError as e:
            assert e.code == 4002

    def test_delete_tag_unused(self):
        t = tax.create_tag("free", slug="tfree")
        tax.delete_tag(t)
        assert Tag.query.filter_by(id=t.id).first() is None


class TestPublicAndStats:
    def test_list_categories_public(self):
        u = _user()
        c = tax.create_category("pub", slug="cpub")
        _article(u.id, category_id=c.id)
        result = tax.list_categories_public()
        assert any(x["slug"] == "cpub" and x["article_count"] >= 1 for x in result)

    def test_list_tags_public(self):
        u = _user()
        a = _article(u.id)
        t = tax.create_tag("pubtag", slug="tpub")
        db.session.add(ArticleTag(article_id=a.id, tag_id=t.id))
        db.session.commit()
        result = tax.list_tags_public()
        assert any(x["slug"] == "tpub" and x["article_count"] >= 1 for x in result)

    def test_get_stats(self):
        u = _user()
        c = tax.create_category("stats", slug="cstat")
        a = _article(u.id, category_id=c.id)
        t = tax.create_tag("statst", slug="tstat")
        db.session.add(ArticleTag(article_id=a.id, tag_id=t.id))
        db.session.commit()
        stats = tax.get_stats()
        assert stats["summary"]["total_categories"] >= 1
        assert stats["summary"]["total_tags"] >= 1
