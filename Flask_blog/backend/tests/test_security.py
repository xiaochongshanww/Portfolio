"""安全监控 API 测试。"""

from .helpers import auth_header, create_user


class TestSecurity:
    def test_get_stats(self, client):
        h = auth_header(client, role='admin')
        resp = client.get('/api/v1/security/stats', headers=h)
        assert resp.status_code in (200,)

    def test_system_health(self, client):
        h = auth_header(client, role='admin')
        resp = client.get('/api/v1/security/system-health', headers=h)
        assert resp.status_code in (200,)

    def test_get_events_recent(self, client):
        h = auth_header(client, role='editor')
        resp = client.get('/api/v1/security/events/recent', headers=h)
        assert resp.status_code in (200,)

    def test_get_threat_trends(self, client):
        h = auth_header(client, role='admin')
        resp = client.get('/api/v1/security/threat-trends', headers=h)
        assert resp.status_code in (200,)

    def test_security_unauthorized(self, client):
        resp = client.get('/api/v1/security/stats')
        assert resp.status_code == 401

    def test_block_ip(self, client):
        h = auth_header(client, role='admin')
        resp = client.post('/api/v1/security/block-ip', json={
            'ip': '10.0.0.99', 'reason': 'test',
        }, headers=h)
        assert resp.status_code in (200,)
