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


def test_change_password_revokes_all_refresh(client, monkeypatch):
    r = FakeRedisAll()
    monkeypatch.setattr("app.redis_client", r, raising=False)
    monkeypatch.setattr("app.auth.service.redis_client", r, raising=False)

    # 注册并登录两次以产生多个 refresh
    client.post(
        "/api/v1/auth/register", json={"email": "cp@test.com", "password": "pass123"}
    )
    client.post(
        "/api/v1/auth/login", json={"email": "cp@test.com", "password": "pass123"}
    )
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
