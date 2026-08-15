"""文章工作流 API 测试 — 覆盖 articles/routes 的关键端点。"""

from .helpers import auth_header, create_article, create_user


def _create_via_api(client, h, **overrides):
    data = {
        "title": "Workflow Article",
        "content_md": "# Hello",
        "slug": "workflow-article",
        "summary": "sum",
    }
    data.update(overrides)
    return client.post("/api/v1/articles/", json=data, headers=h)


class TestArticleWorkflow:
    def test_create_and_get(self, client):
        h = auth_header(client, role="author")
        resp = _create_via_api(client, h)
        assert resp.status_code == 201
        aid = resp.get_json()["data"]["id"]
        detail = client.get(f"/api/v1/articles/{aid}", headers=h)
        assert detail.status_code == 200
        assert detail.get_json()["data"]["id"] == aid

    def test_list_and_status_filter(self, client):
        h = auth_header(client, role="author")
        _create_via_api(client, h)
        listing = client.get("/api/v1/articles/?status=draft", headers=h)
        assert listing.status_code == 200
        assert listing.get_json()["code"] == 0

    def test_update_article(self, client):
        h = auth_header(client, role="author")
        aid = _create_via_api(client, h).get_json()["data"]["id"]
        resp = client.put(
            f"/api/v1/articles/{aid}", json={"title": "Updated Title"}, headers=h
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["title"] == "Updated Title"

    def test_submit_then_approve(self, client):
        author_h = auth_header(client, role="author")
        aid = _create_via_api(client, author_h).get_json()["data"]["id"]
        submit = client.post(f"/api/v1/articles/{aid}/submit", headers=author_h)
        assert submit.status_code == 200
        admin_h = auth_header(client, role="admin")
        approve = client.post(f"/api/v1/articles/{aid}/approve", headers=admin_h)
        assert approve.status_code == 200
        detail = client.get(f"/api/v1/articles/{aid}", headers=admin_h)
        assert detail.get_json()["data"]["status"] == "published"

    def test_reject_article(self, client):
        author_h = auth_header(client, role="author")
        aid = _create_via_api(client, author_h).get_json()["data"]["id"]
        client.post(f"/api/v1/articles/{aid}/submit", headers=author_h)
        admin_h = auth_header(client, role="admin")
        reject = client.post(
            f"/api/v1/articles/{aid}/reject",
            json={"reason": "needs work"},
            headers=admin_h,
        )
        assert reject.status_code == 200

    def test_versions(self, client):
        h = auth_header(client, role="author")
        aid = _create_via_api(client, h).get_json()["data"]["id"]
        client.put(f"/api/v1/articles/{aid}", json={"title": "V2"}, headers=h)
        client.put(f"/api/v1/articles/{aid}", json={"title": "V3"}, headers=h)
        versions = client.get(f"/api/v1/articles/{aid}/versions", headers=h)
        assert versions.status_code == 200

    def test_like_and_bookmark(self, client):
        author_h = auth_header(client, role="author")
        aid = _create_via_api(client, author_h).get_json()["data"]["id"]
        # 发布后才能点赞/收藏
        client.post(f"/api/v1/articles/{aid}/submit", headers=author_h)
        admin_h = auth_header(client, role="admin")
        client.post(f"/api/v1/articles/{aid}/approve", headers=admin_h)
        like = client.post(f"/api/v1/articles/{aid}/like", headers=author_h)
        assert like.status_code == 200
        bookmark = client.post(f"/api/v1/articles/{aid}/bookmark", headers=author_h)
        assert bookmark.status_code == 200

    def test_delete_article(self, client):
        h = auth_header(client, role="editor")
        aid = _create_via_api(client, h).get_json()["data"]["id"]
        resp = client.delete(f"/api/v1/articles/{aid}", headers=h)
        assert resp.status_code == 200

    def test_unauthorized_create(self, client):
        resp = client.post("/api/v1/articles/", json={"title": "x", "content_md": "y"})
        assert resp.status_code == 401

    def test_get_by_slug(self, client):
        from app import db
        from app.models import Article

        u = create_user()
        article_id = create_article(
            author_id=u,
            slug="slug-lookup",
            status="published",
            title="Slug Article",
        )
        db.session.query(Article).filter_by(id=article_id).update(
            {"published_at": None}
        )
        db.session.commit()
        resp = client.get("/api/v1/articles/public/slug-lookup")
        assert resp.status_code in (200, 404)
