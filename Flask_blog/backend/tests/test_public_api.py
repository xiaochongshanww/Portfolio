"""公开接口 /public/v1 测试。"""

from datetime import datetime, timezone

import pytest
from app import db
from app.models import Article, Tag

from .helpers import create_article, create_category, create_tag, create_user


@pytest.fixture(autouse=True)
def _clear_pub_cache(app):
    # public_api 在模块 import 时捕获 redis_client;多 app 测试下它固定指向
    # 首次 create_app 的 FakeRedis,导致跨测试缓存污染。这里显式清空它。
    from app import public_api

    rc = public_api.redis_client
    if rc and hasattr(rc, "store"):
        rc.store.clear()
    yield


def _make_published(title="Pub", author=None, **kw):
    if author is None:
        author = create_user(nickname="PubAuthor")
    kw.setdefault("status", "published")
    kw.setdefault("published_at", datetime.now(timezone.utc))
    return create_article(title=title, author_id=author, **kw)


class TestPublicArticles:
    def test_list_empty(self, client):
        r = client.get("/public/v1/articles")
        assert r.status_code == 200
        body = r.get_json()
        assert body["code"] == 0
        assert body["data"]["total"] == 0
        assert body["data"]["list"] == []

    def test_list_with_articles_and_filters(self, client):
        cat = create_category()
        tag = create_tag()
        _make_published(title="Hello One", category_id=cat)
        _make_published(title="Hello Two", category_id=cat)
        _make_published(title="Draft Hidden", status="draft")

        r = client.get("/public/v1/articles")
        assert r.get_json()["data"]["total"] == 2

        r2 = client.get(f"/public/v1/articles?category_id={cat}")
        assert r2.get_json()["data"]["total"] == 2

        r3 = client.get("/public/v1/articles?page_size=1")
        body3 = r3.get_json()["data"]
        assert body3["total"] == 2
        assert len(body3["list"]) == 1
        assert body3["has_next"] is True

        # tag filter(路由按 slug 过滤)
        art_id = _make_published(title="Tagged")
        tag_slug = f"spec-{tag}"
        db.session.get(Tag, tag).slug = tag_slug
        a = db.session.get(Article, art_id)
        a.tags.append(db.session.get(Tag, tag))
        db.session.commit()
        r4 = client.get(f"/public/v1/articles?tag={tag_slug}")
        assert r4.get_json()["data"]["total"] == 1

    def test_list_etag_304(self, client):
        _make_published()
        r1 = client.get("/public/v1/articles")
        etag = r1.headers.get("ETag")
        assert etag
        r2 = client.get("/public/v1/articles", headers={"If-None-Match": etag})
        assert r2.status_code == 304

    def test_serialize_author(self, client):
        uid = create_user(nickname="Nick", bio="bio", avatar="/a.png")
        _make_published(author=uid)
        body = client.get("/public/v1/articles").get_json()["data"]["list"][0]
        assert body["author"]["id"] == uid
        assert body["author"]["name"] == "Nick"
        assert body["liked"] is False
        assert body["bookmarked"] is False

    def test_author_without_nickname_uses_email(self, client):
        # 回归:public_api 曾访问不存在的 User.username 导致无昵称作者 500
        uid = create_user(email="anon@example.com")
        _make_published(author=uid)
        r = client.get("/public/v1/articles")
        assert r.status_code == 200
        assert r.get_json()["data"]["list"][0]["author"]["name"] == "anon@example.com"


class TestPublicArticleDetail:
    def test_by_id(self, client):
        _make_published(title="Detail")
        r = client.get("/public/v1/articles/1")
        assert r.status_code == 200
        assert r.get_json()["data"]["title"] == "Detail"
        assert "content_html" in r.get_json()["data"]

    def test_by_slug(self, client):
        _make_published(title="Slug One")
        a = Article.query.first()
        r = client.get(f"/public/v1/articles/{a.slug}")
        assert r.status_code == 200

    def test_draft_not_found(self, client):
        create_article(status="draft")
        r = client.get("/public/v1/articles/1")
        assert r.status_code == 404

    def test_not_found(self, client):
        r = client.get("/public/v1/articles/99999")
        assert r.status_code == 404

    def test_detail_etag_304(self, client):
        _make_published()
        r1 = client.get("/public/v1/articles/1")
        etag = r1.headers.get("ETag")
        r2 = client.get("/public/v1/articles/1", headers={"If-None-Match": etag})
        assert r2.status_code == 304


class TestPublicTaxonomy:
    def test_taxonomy(self, client):
        cat = create_category()
        create_tag()
        _make_published(category_id=cat)
        r = client.get("/public/v1/taxonomy")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert len(data["categories"]) >= 1
        assert len(data["tags"]) >= 1

    def test_taxonomy_etag(self, client):
        r1 = client.get("/public/v1/taxonomy")
        etag = r1.headers.get("ETag")
        r2 = client.get("/public/v1/taxonomy", headers={"If-None-Match": etag})
        assert r2.status_code == 304
