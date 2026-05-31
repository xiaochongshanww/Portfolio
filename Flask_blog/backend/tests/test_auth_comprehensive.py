"""综合认证测试 — 补充现有 auth 测试未覆盖的路径。"""

from .helpers import auth_header


class TestAuthComprehensive:
    def test_register_duplicate_email(self, client):
        resp = client.post('/api/v1/auth/register', json={
            'email': 'dup@test.com', 'password': 'test123456',
        })
        assert resp.status_code == 201
        resp = client.post('/api/v1/auth/register', json={
            'email': 'dup@test.com', 'password': 'test123456',
        })
        assert resp.status_code == 409

    def test_login_wrong_password(self, client):
        client.post('/api/v1/auth/register', json={
            'email': 'wrong@test.com', 'password': 'test123456',
        })
        resp = client.post('/api/v1/auth/login', json={
            'email': 'wrong@test.com', 'password': 'wrongpassword',
        })
        assert resp.status_code == 401

    def test_login_invalid_email(self, client):
        resp = client.post('/api/v1/auth/login', json={
            'email': 'nonexistent@test.com', 'password': 'test123456',
        })
        assert resp.status_code == 401

    def test_access_protected_route_no_token(self, client):
        resp = client.get('/api/v1/users/me')
        assert resp.status_code == 401

    def test_access_protected_route_invalid_token(self, client):
        resp = client.get('/api/v1/users/me',
                          headers={'Authorization': 'Bearer invalidtoken'})
        assert resp.status_code == 401

    def test_refresh_token(self, client):
        # 登录获取 refresh token (cookie)
        client.post('/api/v1/auth/register', json={
            'email': 'refresh@test.com', 'password': 'test123456',
        })
        login_resp = client.post('/api/v1/auth/login', json={
            'email': 'refresh@test.com', 'password': 'test123456',
        })
        refresh_token = login_resp.headers.get('Set-Cookie', '')
        xsrf = login_resp.headers.get('Set-Cookie', '')
        assert refresh_token != '', 'Expected refresh token cookie'

    def test_registration_password_too_short(self, client):
        resp = client.post('/api/v1/auth/register', json={
            'email': 'short@test.com', 'password': '12',
        })
        assert resp.status_code == 400

    def test_role_endpoints(self, client):
        """验证不同角色访问权限正确的端点。"""
        # Author 不能访问管理后台统计
        h_author = auth_header(client, role='author')
        resp = client.get('/api/v1/metrics/summary', headers=h_author)
        assert resp.status_code == 403

        # Admin 可以访问
        h_admin = auth_header(client, role='admin')
        resp = client.get('/api/v1/metrics/summary', headers=h_admin)
        assert resp.status_code in (200,)
