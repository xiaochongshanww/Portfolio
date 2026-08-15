"""用户 service 层与路由测试。"""

import pytest
from app.models import User

from .helpers import auth_header, create_article, create_user


@pytest.fixture(autouse=True)
def _clear_users_cache(app):
    # users/service 在模块 import 时捕获 redis_client;多 app 测试下固定指向
    # 首次 create_app 的 FakeRedis,导致跨测试缓存污染。这里显式清空它。
    from app.users import service as usvc

    rc = usvc.redis_client
    if rc and hasattr(rc, "store"):
        rc.store.clear()
    yield


class TestSerialize:
    def test_serialize_user(self, app):
        from app.models import User
        from app.users.service import serialize_user

        uid = create_user(nickname="N", bio="B", avatar="/a.png")
        u = User.query.get(uid)
        data = serialize_user(u)
        assert data["nickname"] == "N"
        assert "email" not in data
        data2 = serialize_user(u, include_email=True)
        assert "email" in data2

    def test_serialize_social_links(self, app):
        from app.models import User
        from app.users.service import serialize_user

        uid = create_user(social_links='{"github": "x"}')
        data = serialize_user(User.query.get(uid))
        assert data["social_links"] == {"github": "x"}

    def test_serialize_bad_social(self, app):
        from app.models import User
        from app.users.service import serialize_user

        uid = create_user(social_links="{bad")
        data = serialize_user(User.query.get(uid))
        assert data["social_links"] is None


class TestUpdateProfile:
    def test_update_fields(self, app):
        from app.users.service import update_profile

        uid = create_user()
        from app.models import User

        u = User.query.get(uid)
        update_profile(u, nickname="NewNick", bio="NewBio")
        assert u.nickname == "NewNick"
        assert u.bio == "NewBio"

    def test_update_social_links(self, app):
        from app.users.service import update_profile

        uid = create_user()
        u = User.query.get(uid)
        update_profile(u, social_links={"twitter": "t"})
        assert '"twitter"' in u.social_links

    def test_update_social_links_not_dict(self, app):
        import pytest
        from app.users.service import UserServiceError, update_profile

        uid = create_user()
        from app.models import User

        u = User.query.get(uid)
        with pytest.raises(UserServiceError):
            update_profile(u, social_links="not-a-dict")


class TestListUsers:
    def test_list(self, app):
        from app.users.service import list_users

        create_user()
        create_user()
        res = list_users(1, 10)
        assert res["total"] >= 2
        assert res["has_next"] is False


class TestChangeRole:
    def test_change_role(self, app):
        from app.models import User
        from app.users.service import change_role

        uid = create_user(role="author")
        u = User.query.get(uid)
        old = change_role(u, "editor", operator_id=uid)
        assert old == "author"
        assert u.role == "editor"


class TestRoutes:
    def test_me(self, client):
        h = auth_header(client, role="author")
        r = client.get("/api/v1/users/me", headers=h)
        assert r.status_code == 200
        assert r.get_json()["data"]["email"]

    def test_update_me(self, client):
        h = auth_header(client, role="author")
        r = client.patch("/api/v1/users/me", json={"nickname": "X"}, headers=h)
        assert r.status_code == 200
        assert r.get_json()["data"]["nickname"] == "X"

    def test_update_me_validation_error(self, client):
        h = auth_header(client, role="author")
        r = client.patch("/api/v1/users/me", json={"nickname": "x" * 100}, headers=h)
        assert r.status_code == 400

    def test_list_users_admin(self, client):
        h = auth_header(client, role="admin")
        r = client.get("/api/v1/users/", headers=h)
        assert r.status_code == 200
        assert "list" in r.get_json()["data"]

    def test_change_role_route(self, client):
        h = auth_header(client, role="admin")
        target = create_user(role="author")
        r = client.patch(
            f"/api/v1/users/{target}/role", json={"role": "editor"}, headers=h
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["new_role"] == "editor"

    def test_change_role_invalid(self, client):
        h = auth_header(client, role="admin")
        target = create_user()
        r = client.patch(
            f"/api/v1/users/{target}/role", json={"role": "superuser"}, headers=h
        )
        assert r.status_code == 400

    def test_public_profile(self, client):
        uid = create_user(nickname="Author")
        create_article(author_id=uid, status="published")
        r = client.get(f"/api/v1/users/public/{uid}")
        assert r.status_code == 200
        assert r.get_json()["data"]["published_articles"] == 1

    def test_public_articles(self, client):
        uid = create_user()
        create_article(author_id=uid, status="published")
        r = client.get(f"/api/v1/users/public/{uid}/articles?page=1&page_size=10")
        assert r.status_code == 200
        assert r.get_json()["data"]["total"] == 1

    def test_public_articles_sort_created(self, client):
        uid = create_user()
        create_article(author_id=uid, status="published")
        r = client.get(f"/api/v1/users/public/{uid}/articles?sort=created_at:asc")
        assert r.status_code == 200

    def test_public_stats(self, client):
        uid = create_user()
        create_article(author_id=uid, status="published")
        r = client.get(f"/api/v1/users/public/{uid}/stats")
        assert r.status_code == 200
        assert r.get_json()["data"]["articles_count"] == 1

    def test_public_stats_empty(self, client):
        uid = create_user()
        r = client.get(f"/api/v1/users/public/{uid}/stats")
        assert r.status_code == 200
        assert r.get_json()["data"]["articles_count"] == 0

    def test_public_profile_etag(self, client):
        uid = create_user()
        r1 = client.get(f"/api/v1/users/public/{uid}")
        etag = r1.headers.get("ETag")
        r2 = client.get(f"/api/v1/users/public/{uid}", headers={"If-None-Match": etag})
        assert r2.status_code == 304
