"""评论路由 API 测试 — 覆盖 comments/routes。"""

from .helpers import auth_header, create_article, create_comment, create_user


def _published_article():
    uid = create_user()
    return create_article(author_id=uid, status="published")


class TestCommentsApi:
    def test_create_comment(self, client):
        h = auth_header(client, role="author")
        article_id = _published_article()
        resp = client.post(
            "/api/v1/comments/",
            json={"article_id": article_id, "content": "nice post"},
            headers=h,
        )
        assert resp.status_code == 201

    def test_create_comment_unauthorized(self, client):
        resp = client.post("/api/v1/comments/", json={"article_id": 1, "content": "x"})
        assert resp.status_code == 401

    def test_list_approved(self, client):
        article_id = _published_article()
        uid = create_user()
        create_comment(article_id, user_id=uid, status="approved")
        resp = client.get(f"/api/v1/comments/article/{article_id}")
        assert resp.status_code == 200
        assert resp.get_json()["code"] == 0

    def test_comment_tree(self, client):
        article_id = _published_article()
        uid = create_user()
        parent = create_comment(article_id, user_id=uid, status="approved")
        create_comment(article_id, user_id=uid, status="approved", parent_id=parent)
        resp = client.get(f"/api/v1/comments/article/{article_id}/tree")
        assert resp.status_code == 200
        assert resp.get_json()["code"] == 0

    def test_pending_list(self, client):
        h = auth_header(client, role="editor")
        resp = client.get("/api/v1/comments/pending", headers=h)
        assert resp.status_code == 200

    def test_admin_list_and_stats(self, client):
        h = auth_header(client, role="editor")
        listing = client.get("/api/v1/comments/admin/list", headers=h)
        assert listing.status_code == 200
        stats = client.get("/api/v1/comments/admin/stats", headers=h)
        assert stats.status_code == 200

    def test_moderate(self, client):
        h = auth_header(client, role="editor")
        article_id = _published_article()
        uid = create_user()
        cid = create_comment(article_id, user_id=uid, status="pending")
        resp = client.post(
            f"/api/v1/comments/moderate/{cid}", json={"action": "approve"}, headers=h
        )
        assert resp.status_code == 200

    def test_moderate_batch(self, client):
        h = auth_header(client, role="editor")
        article_id = _published_article()
        uid = create_user()
        c1 = create_comment(article_id, user_id=uid, status="pending")
        c2 = create_comment(article_id, user_id=uid, status="pending")
        resp = client.post(
            "/api/v1/comments/moderate/batch",
            json={"ids": [c1, c2], "action": "reject"},
            headers=h,
        )
        assert resp.status_code == 200

    def test_moderate_forbidden_for_author(self, client):
        h = auth_header(client, role="author")
        resp = client.post(
            "/api/v1/comments/moderate/1", json={"action": "approve"}, headers=h
        )
        assert resp.status_code in (401, 403)
