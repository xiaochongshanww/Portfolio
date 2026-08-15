"""日志管理 service 层与路由补充测试。"""

from datetime import datetime, timezone

from app import db
from app.models import LogEntry

from .helpers import auth_header, create_user


def _log(level="INFO", source="app", message="msg", **kw):
    e = LogEntry(
        timestamp=datetime.now(timezone.utc),
        level=level,
        source=source,
        message=message,
        **kw,
    )
    db.session.add(e)
    db.session.commit()
    return e.id


class TestService:
    def test_query_filters(self, app):
        from app.logs.service import query_logs_common

        _log(level="ERROR", source="auth", message="denied", request_id="r1")
        _log(level="INFO", source="search", message="ok")
        total, logs = query_logs_common(
            1, 10, "ERROR", "auth", "denied", None, "r1", "", ""
        )
        assert total == 1
        assert logs[0]["level"] == "ERROR"

    def test_query_level_ignored_unknown(self, app):
        from app.logs.service import query_logs_common

        _log(level="INFO")
        total, _ = query_logs_common(1, 10, "NOPE", "", "", None, "", "", "")
        assert total == 1

    def test_query_user_and_time(self, app):
        from app.logs.service import query_logs_common

        uid = create_user()
        _log(user_id=uid)
        _log(user_id=None)
        total, _ = query_logs_common(1, 10, "", "", "", uid, "", "", "")
        assert total == 1
        # invalid start_time is ignored
        total2, _ = query_logs_common(1, 10, "", "", "", None, "", "not-a-date", "")
        assert total2 == 2

    def test_build_log_query(self, app):
        from app.logs.service import build_log_query

        _log(level="ERROR")
        q = build_log_query(
            "ERROR", "app", "msg", "2020-01-01T00:00:00Z", "2099-01-01T00:00:00Z"
        )
        assert q.count() == 1

    def test_stats(self, app):
        from app.logs.service import get_log_stats_data

        _log(level="ERROR")
        _log(level="WARNING")
        stats = get_log_stats_data()
        assert stats["total"] == 2
        assert stats["level_distribution"]["ERROR"] == 1
        assert len(stats["weekly_trend"]) == 7

    def test_detail(self, app):
        from app.logs.service import get_log_detail_data

        eid = _log(request_id="rx")
        data = get_log_detail_data(eid)
        assert data["log"]["id"] == eid

    def test_detail_related(self, app):
        from app.logs.service import get_log_detail_data

        e1 = _log(request_id="rr")
        _log(request_id="rr")
        data = get_log_detail_data(e1)
        assert len(data["related_logs"]) == 1

    def test_config_list_and_upsert(self, app):
        from app.logs.service import get_log_config_list_data, upsert_log_config

        upsert_log_config("max_log_days", "30", "days")
        upsert_log_config("max_log_days", "60")  # update path
        configs = get_log_config_list_data()
        assert len(configs) == 1
        assert configs[0]["config_value"] == "60"

    def test_sources_and_users(self, app):
        from app.logs.service import get_log_sources_data, get_log_users_data

        uid = create_user(nickname="LogUser")
        _log(source="auth", user_id=uid)
        assert get_log_sources_data() == ["auth"]
        users = get_log_users_data()
        assert users[0]["name"] == "LogUser"


class TestRoutes:
    def test_export(self, client):
        _log()
        h = auth_header(client, role="admin")
        r = client.get("/api/v1/admin/logs/export", headers=h)
        assert r.status_code == 200
        assert r.get_json()["data"]["total"] == 1

    def test_cleanup(self, client):
        from datetime import timedelta

        # cleanup_old_logs 按 created_at(而非 timestamp)过滤
        old = LogEntry(
            created_at=datetime.now(timezone.utc) - timedelta(days=60),
            timestamp=datetime.now(timezone.utc) - timedelta(days=60),
            level="INFO",
            source="old",
            message="stale",
        )
        db.session.add(old)
        db.session.commit()
        _log()
        h = auth_header(client, role="admin")
        r = client.post("/api/v1/admin/logs/cleanup", json={"days": 30}, headers=h)
        assert r.status_code == 200
        assert r.get_json()["data"]["deleted_count"] == 1

    def test_cleanup_invalid_days(self, client):
        h = auth_header(client, role="admin")
        r = client.post("/api/v1/admin/logs/cleanup", json={"days": 0}, headers=h)
        assert r.status_code == 400

    def test_detail_route(self, client):
        eid = _log()
        h = auth_header(client, role="admin")
        r = client.get(f"/api/v1/admin/logs/{eid}", headers=h)
        assert r.status_code == 200

    def test_config_post(self, client):
        h = auth_header(client, role="admin")
        r = client.post(
            "/api/v1/admin/logs/config",
            json={"config_key": "k", "config_value": "v"},
            headers=h,
        )
        assert r.status_code == 200

    def test_config_post_missing(self, client):
        h = auth_header(client, role="admin")
        r = client.post("/api/v1/admin/logs/config", json={}, headers=h)
        assert r.status_code == 400

    def test_users_route(self, client):
        uid = create_user(nickname="Who")
        _log(user_id=uid)
        h = auth_header(client, role="admin")
        r = client.get("/api/v1/admin/logs/users", headers=h)
        assert r.status_code == 200
        assert r.get_json()["data"][0]["name"] == "Who"

    def test_options_endpoints(self, client):
        h = auth_header(client, role="admin")
        for path in [
            "/api/v1/admin/logs/",
            "/api/v1/admin/logs/stats",
            "/api/v1/admin/logs/cleanup",
            "/api/v1/admin/logs/config",
            "/api/v1/admin/logs/sources",
        ]:
            r = client.options(path, headers=h)
            assert r.status_code in (200,)
