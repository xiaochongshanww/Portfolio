"""安全监控路由 API 测试 — 覆盖 security/routes。"""

from .helpers import auth_header


class TestSecurityApi:
    def test_stats(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/security/stats", headers=h)
        assert resp.status_code == 200

    def test_system_health(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/security/system-health", headers=h)
        assert resp.status_code == 200

    def test_events_recent(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/security/events/recent", headers=h)
        assert resp.status_code == 200

    def test_access_stats_today(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/security/access-stats/today", headers=h)
        assert resp.status_code == 200

    def test_threat_trends(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/security/threat-trends", headers=h)
        assert resp.status_code == 200

    def test_block_ip(self, client):
        h = auth_header(client, role="admin")
        resp = client.post(
            "/api/v1/security/block-ip", json={"ip": "8.8.8.8"}, headers=h
        )
        assert resp.status_code in (200, 400, 409)

    def test_suspend_user(self, client):
        h = auth_header(client, role="admin")
        resp = client.post(
            "/api/v1/security/suspend-user", json={"user_id": 1}, headers=h
        )
        assert resp.status_code in (200, 400, 404)

    def test_forbidden_for_author(self, client):
        h = auth_header(client, role="author")
        resp = client.get("/api/v1/security/stats", headers=h)
        assert resp.status_code in (401, 403)
