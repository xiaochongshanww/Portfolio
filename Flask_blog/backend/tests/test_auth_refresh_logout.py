class FakeRedis:
    def __init__(self):
        self.store = {}
    def setex(self, key, ttl, value):
        self.store[key] = value
    def get(self, key):
        return self.store.get(key)


def test_refresh_revokes_old_token(client, monkeypatch):
    # 准备 fake redis 以启用 refresh 白名单/黑名单逻辑
    r = FakeRedis()
    monkeypatch.setattr('app.redis_client', r, raising=False)
    monkeypatch.setattr('app.auth.routes.redis_client', r, raising=False)

    # 注册+登录
    client.post('/api/v1/auth/register', json={'email':'rr@test.com','password':'pass123'})
    login_resp = client.post('/api/v1/auth/login', json={'email':'rr@test.com','password':'pass123'})
    assert login_resp.status_code == 200
    # 取得初始 refresh cookie
    cookies = login_resp.headers.getlist('Set-Cookie')
    old_refresh_cookie = [c for c in cookies if c.startswith('refresh_token=')][0]
    old_refresh_value = old_refresh_cookie.split('refresh_token=')[1].split(';',1)[0]

    # 第一次刷新 -> 生成新 refresh 并黑名单旧 jti
    first_refresh = client.post('/api/v1/auth/refresh')
    assert first_refresh.status_code == 200
    new_cookies = first_refresh.headers.getlist('Set-Cookie')
    assert any('refresh_token=' in c for c in new_cookies)

    # 强制使用旧 refresh，再次调用 refresh 应 401 (新版 Flask test_client.set_cookie 仅需 name,value)
    client.set_cookie('refresh_token', old_refresh_value)
    second_refresh = client.post('/api/v1/auth/refresh')
    assert second_refresh.status_code == 401


def test_logout_revokes_refresh(client, monkeypatch):
    r = FakeRedis()
    monkeypatch.setattr('app.redis_client', r, raising=False)
    monkeypatch.setattr('app.auth.routes.redis_client', r, raising=False)

    client.post('/api/v1/auth/register', json={'email':'lo@test.com','password':'pass123'})
    login_resp = client.post('/api/v1/auth/login', json={'email':'lo@test.com','password':'pass123'})
    assert login_resp.status_code == 200

    # 退出登录
    logout_resp = client.post('/api/v1/auth/logout')
    assert logout_resp.status_code == 200

    # 退出后再刷新应 401 (refresh token 已被加入黑名单)
    refresh_after_logout = client.post('/api/v1/auth/refresh')
    assert refresh_after_logout.status_code == 401
