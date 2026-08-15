"""系统设置路由 API 测试 — 覆盖 settings/routes。"""

from .helpers import auth_header


class TestSettingsApi:
    def test_get_all(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/settings/all", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["code"] == 0

    def test_get_general(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/settings/general", headers=h)
        assert resp.status_code == 200

    def test_put_general(self, client):
        h = auth_header(client, role="admin")
        resp = client.put(
            "/api/v1/settings/general", json={"siteName": "New Name"}, headers=h
        )
        assert resp.status_code == 200

    def test_get_content(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/settings/content", headers=h)
        assert resp.status_code == 200

    def test_put_security(self, client):
        h = auth_header(client, role="admin")
        resp = client.put(
            "/api/v1/settings/security", json={"maxLoginAttempts": 5}, headers=h
        )
        assert resp.status_code == 200

    def test_system_info(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/settings/system/info", headers=h)
        assert resp.status_code == 200

    def test_optimize_database(self, client):
        h = auth_header(client, role="admin")
        resp = client.post("/api/v1/settings/system/optimize-database", headers=h)
        assert resp.status_code == 200

    def test_clear_cache(self, client):
        h = auth_header(client, role="admin")
        resp = client.post("/api/v1/settings/system/clear-cache", headers=h)
        assert resp.status_code == 200

    def test_forbidden_for_author(self, client):
        h = auth_header(client, role="author")
        resp = client.get("/api/v1/settings/all", headers=h)
        assert resp.status_code in (401, 403)
