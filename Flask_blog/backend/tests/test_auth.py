"""认证流程测试 — 注册/登录/刷新/登出/改密/权限。

合并自原 test_auth / test_auth_comprehensive / test_auth_refresh_logout /
test_change_password_revokes_refresh，消除多文件重叠。
"""

from .helpers import auth_header


class FakeRedis:
    def __init__(self):
        self.store = {}

    def setex(self, key, ttl, value):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)


class FakeRedisAll:
    def __init__(self):
        self.store = {}

    def setex(self, key, ttl, value):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        if key in self.store:
            del self.store[key]

    def scan_iter(self, match=None):
        import fnmatch

        for k in list(self.store.keys()):
            if not match or fnmatch.fnmatch(k, match.replace("*", "*")):
                yield k


def _capture_xsrf(client, resp):
    """解析 login 响应的 Set-Cookie 头并记录 XSRF-TOKEN 供后续请求使用。"""
    tokens = []
    for cookie in resp.headers.getlist("Set-Cookie"):
        if cookie.startswith("XSRF-TOKEN="):
            tokens.append(cookie.split("XSRF-TOKEN=", 1)[1].split(";", 1)[0])
    if tokens:
        client._xsrf = tokens


def _xsrf_header(client):
    """从 login 响应 Set-Cookie 中取 XSRF-TOKEN 并构造请求头（双提交 CSRF）。"""
    xsrf = getattr(client, "_xsrf", None)
    assert xsrf, "XSRF-TOKEN not available (call _capture_xsrf after login)"
    return {"X-XSRF-TOKEN": xsrf[0]}


def _login(client, email="u1@test.com", password="pass123"):
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200
    _capture_xsrf(client, resp)
    return resp


def test_register_login(client, app):
    # register
    resp = client.post(
        "/api/v1/auth/register", json={"email": "u1@test.com", "password": "pass123"}
    )
    assert resp.status_code == 201
    # login
    resp = client.post(
        "/api/v1/auth/login", json={"email": "u1@test.com", "password": "pass123"}
    )
    if resp.status_code != 200:
        print("login fail payload:", resp.get_json())
    print("login Set-Cookie headers:", resp.headers.getlist("Set-Cookie"))
    assert resp.status_code == 200
    _capture_xsrf(client, resp)
    data = resp.get_json()
    assert data["code"] == 0
    # refresh (双提交 CSRF：需携带 XSRF cookie + 头)
    refresh_resp = client.post("/api/v1/auth/refresh", headers=_xsrf_header(client))
    print("refresh status:", refresh_resp.status_code, "body:", refresh_resp.get_json())
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.get_json()["data"]
    # logout (需要 Bearer token)
    access_token = refresh_resp.get_json()["data"]["access_token"]
    logout_resp = client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout_resp.status_code == 200


class TestAuthComprehensive:
    def test_register_duplicate_email(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@test.com",
                "password": "test123456",
            },
        )
        assert resp.status_code == 201
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@test.com",
                "password": "test123456",
            },
        )
        assert resp.status_code == 409

    def test_login_wrong_password(self, client):
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrong@test.com",
                "password": "test123456",
            },
        )
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrong@test.com",
                "password": "wrongpassword",
            },
        )
        assert resp.status_code == 401

    def test_login_invalid_email(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "test123456",
            },
        )
        assert resp.status_code == 401

    def test_access_protected_route_no_token(self, client):
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 401

    def test_access_protected_route_invalid_token(self, client):
        resp = client.get(
            "/api/v1/users/me", headers={"Authorization": "Bearer invalidtoken"}
        )
        assert resp.status_code == 401

    def test_refresh_token(self, client):
        # 登录获取 refresh token (cookie)
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh@test.com",
                "password": "test123456",
            },
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "refresh@test.com",
                "password": "test123456",
            },
        )
        refresh_token = login_resp.headers.get("Set-Cookie", "")
        assert refresh_token != "", "Expected refresh token cookie"

    def test_registration_password_too_short(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "short@test.com",
                "password": "12",
            },
        )
        assert resp.status_code == 400

    def test_role_endpoints(self, client):
        """验证不同角色访问权限正确的端点。"""
        # Author 不能访问管理后台统计
        h_author = auth_header(client, role="author")
        resp = client.get("/api/v1/metrics/summary", headers=h_author)
        assert resp.status_code == 403

        # Admin 可以访问
        h_admin = auth_header(client, role="admin")
        resp = client.get("/api/v1/metrics/summary", headers=h_admin)
        assert resp.status_code in (200,)


def test_refresh_revokes_old_token(client, monkeypatch):
    # 准备 fake redis 以启用 refresh 白名单/黑名单逻辑
    r = FakeRedis()
    monkeypatch.setattr("app.redis_client", r, raising=False)
    monkeypatch.setattr("app.auth.service.redis_client", r, raising=False)
    monkeypatch.setattr("app.auth.routes.redis_client", r, raising=False)

    # 注册+登录
    login_resp = _login(client, email="rr@test.com")
    # 取得初始 refresh cookie
    cookies = login_resp.headers.getlist("Set-Cookie")
    old_refresh_cookie = [c for c in cookies if c.startswith("refresh_token=")][0]
    old_refresh_value = old_refresh_cookie.split("refresh_token=")[1].split(";", 1)[0]

    # 第一次刷新 -> 生成新 refresh 并黑名单旧 jti
    first_refresh = client.post("/api/v1/auth/refresh", headers=_xsrf_header(client))
    assert first_refresh.status_code == 200
    new_cookies = first_refresh.headers.getlist("Set-Cookie")
    assert any("refresh_token=" in c for c in new_cookies)

    # 强制使用旧 refresh，再次调用 refresh 应 401
    client.set_cookie("refresh_token", old_refresh_value)
    second_refresh = client.post("/api/v1/auth/refresh", headers=_xsrf_header(client))
    assert second_refresh.status_code == 401


def test_logout_revokes_refresh(client, monkeypatch):
    r = FakeRedis()
    monkeypatch.setattr("app.redis_client", r, raising=False)
    monkeypatch.setattr("app.auth.service.redis_client", r, raising=False)
    monkeypatch.setattr("app.auth.routes.redis_client", r, raising=False)

    login_resp = _login(client, email="lo@test.com")

    # 退出登录 (需要 Bearer token)
    access_token = login_resp.get_json()["data"]["access_token"]
    logout_resp = client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout_resp.status_code == 200

    # 退出后再刷新应 401 (refresh token 已被加入黑名单)
    refresh_after_logout = client.post(
        "/api/v1/auth/refresh", headers=_xsrf_header(client)
    )
    assert refresh_after_logout.status_code == 401


def test_change_password_revokes_all_refresh(client, monkeypatch):
    r = FakeRedisAll()
    monkeypatch.setattr("app.redis_client", r, raising=False)
    monkeypatch.setattr("app.auth.service.redis_client", r, raising=False)

    # 注册并登录两次以产生多个 refresh
    _login(client, email="cp@test.com")
    login2 = client.post(
        "/api/v1/auth/login", json={"email": "cp@test.com", "password": "pass123"}
    )
    access_token = login2.get_json()["data"]["access_token"]

    # 解析 XSRF-TOKEN（双提交 CSRF）
    xsrf = None
    for cookie in login2.headers.getlist("Set-Cookie"):
        if cookie.startswith("XSRF-TOKEN="):
            xsrf = cookie.split("XSRF-TOKEN=", 1)[1].split(";", 1)[0]
            break
    assert xsrf, "XSRF-TOKEN not set after login"

    # 记录当前 refresh allow 键数量
    allow_keys_before = [k for k in r.store.keys() if k.startswith("refresh:allow:")]
    assert len(allow_keys_before) >= 2

    # 修改密码
    change = client.post(
        "/api/v1/auth/change_password",
        json={
            "email": "cp@test.com",
            "old_password": "pass123",
            "new_password": "newpass456",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert change.status_code == 200

    # 所有旧 refresh 应被加入黑名单或 allow 被删除
    for k in allow_keys_before:
        assert k not in r.store  # allow 键已移除

    # 尝试刷新（使用当前 cookie refresh）应该失败（因黑名单）
    refresh = client.post("/api/v1/auth/refresh", headers={"X-XSRF-TOKEN": xsrf})
    assert refresh.status_code == 401
