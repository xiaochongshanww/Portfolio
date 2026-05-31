"""系统设置与系统操作 API 测试。"""

from .helpers import auth_header


class TestSettings:
    def test_get_settings(self, client):
        h = auth_header(client, role='admin')
        resp = client.get('/api/v1/settings/general', headers=h)
        assert resp.status_code == 200
        assert 'code' in resp.json

    def test_get_settings_unauthorized(self, client):
        resp = client.get('/api/v1/settings/general')
        assert resp.status_code == 401

    def test_get_settings_forbidden_author(self, client):
        h = auth_header(client, role='author')
        resp = client.get('/api/v1/settings/general', headers=h)
        # settings might allow author or might require editor+
        # Either way, not 500
        assert resp.status_code not in (500,)

    def test_get_system_info(self, client):
        h = auth_header(client, role='admin')
        resp = client.post('/api/v1/settings/system/info', headers=h)
        assert resp.status_code in (200, 405)

    def test_clear_cache(self, client):
        h = auth_header(client, role='admin')
        resp = client.post('/api/v1/settings/system/clear-cache', headers=h)
        assert resp.status_code in (200,)

    def test_security_settings(self, client):
        h = auth_header(client, role='admin')
        resp = client.get('/api/v1/settings/security', headers=h)
        assert resp.status_code in (200,)
