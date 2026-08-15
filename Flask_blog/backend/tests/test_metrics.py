"""Metrics API 测试。"""

from .helpers import (
    auth_header,
    create_article,
    create_category,
    create_tag,
    create_user,
)


class TestMetrics:
    def test_ping(self, client):
        r = client.get("/api/v1/metrics/test")
        assert r.status_code == 200

    def test_summary(self, client):
        h = auth_header(client, role="admin")
        r = client.get("/api/v1/metrics/summary", headers=h)
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert "users" in data
        assert "articles" in data
        assert "comments" in data

    def test_summary_with_data(self, client):
        h = auth_header(client, role="admin")
        author = create_user()
        create_article(author_id=author, status="published")
        create_article(author_id=author, status="draft")
        create_category()
        create_tag()
        r = client.get("/api/v1/metrics/summary", headers=h)
        data = r.get_json()["data"]
        assert data["articles"]["published"] == 1
        assert data["articles"]["draft"] == 1
        assert data["taxonomy"]["tags"] >= 1

    def test_summary_forbidden_author(self, client):
        h = auth_header(client, role="author")
        r = client.get("/api/v1/metrics/summary", headers=h)
        assert r.status_code in (401, 403)

    def test_visitors(self, client):
        r = client.get("/api/v1/metrics/visitors")
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert set(data) == {
            "today_visitors",
            "today_page_views",
            "total_visitors",
            "total_page_views",
        }

    def test_track(self, client):
        r = client.post("/api/v1/metrics/track", headers={"User-Agent": "MetricUA"})
        assert r.status_code == 200
        assert r.get_json()["data"]["tracked"] is True

    def test_track_twice(self, client):
        client.post("/api/v1/metrics/track", headers={"User-Agent": "MetricUA2"})
        r = client.post("/api/v1/metrics/track", headers={"User-Agent": "MetricUA2"})
        assert r.get_json()["data"]["is_new_visitor"] is False
