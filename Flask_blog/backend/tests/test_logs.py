"""日志管理 API 测试。"""

from .helpers import auth_header


class TestLogs:
    def test_query_logs(self, client):
        h = auth_header(client, role='admin')
        resp = client.post('/api/v1/admin/logs/query', json={
            'page': 1, 'size': 10,
        }, headers=h)
        assert resp.status_code in (200,)

    def test_logs_unauthorized(self, client):
        resp = client.get('/api/v1/admin/logs/')
        assert resp.status_code == 401

    def test_logs_forbidden_author(self, client):
        h = auth_header(client, role='author')
        resp = client.post('/api/v1/admin/logs/query', json={}, headers=h)
        assert resp.status_code in (401, 403)

    def test_get_log_sources(self, client):
        h = auth_header(client, role='admin')
        resp = client.get('/api/v1/admin/logs/sources', headers=h)
        assert resp.status_code in (200,)

    def test_get_log_stats(self, client):
        h = auth_header(client, role='admin')
        resp = client.get('/api/v1/admin/logs/stats', headers=h)
        assert resp.status_code in (200,)

    def test_log_config(self, client):
        h = auth_header(client, role='admin')
        resp = client.get('/api/v1/admin/logs/config', headers=h)
        assert resp.status_code in (200,)
