"""简化日志管理 API 测试。"""

from datetime import datetime, timezone

from app import db
from app.models import LogEntry

TOKEN = {"Authorization": "Bearer " + "x" * 30}
BAD = {"Authorization": "Bearer short"}


def _add_log(level="ERROR", source="auth", message="boom", **kw):
    log = LogEntry(
        timestamp=datetime.now(timezone.utc),
        level=level,
        source=source,
        message=message,
        **kw,
    )
    db.session.add(log)
    db.session.commit()
    return log.id


class TestSimpleLogs:
    def test_health(self, client):
        r = client.get("/api/v1/simple/health")
        assert r.status_code == 200
        assert r.get_json()["status"] == "ok"

    def test_list_no_token(self, client):
        r = client.get("/api/v1/simple/logs/list")
        assert r.status_code == 401

    def test_list_short_token(self, client):
        r = client.get("/api/v1/simple/logs/list", headers=BAD)
        assert r.status_code == 401

    def test_list(self, client):
        _add_log()
        r = client.get("/api/v1/simple/logs/list", headers=TOKEN)
        assert r.status_code == 200
        body = r.get_json()
        assert body["status"] == "success"
        assert body["data"]["total"] == 1
        assert body["data"]["logs"][0]["level"] == "ERROR"

    def test_list_filters(self, client):
        _add_log(level="ERROR", source="auth")
        _add_log(level="INFO", source="search")
        r = client.get(
            "/api/v1/simple/logs/list?level=info&source=sear&keyword=boom",
            headers=TOKEN,
        )
        assert r.get_json()["data"]["total"] == 1

    def test_list_invalid_level_ignored(self, client):
        _add_log(level="ERROR")
        r = client.get("/api/v1/simple/logs/list?level=NOT_A_LEVEL", headers=TOKEN)
        assert r.get_json()["data"]["total"] == 1

    def test_list_with_user(self, client):
        from .helpers import create_user

        uid = create_user(nickname="Logger")
        _add_log(user_id=uid)
        r = client.get("/api/v1/simple/logs/list", headers=TOKEN)
        assert r.get_json()["data"]["logs"][0]["user_name"] == "Logger"

    def test_stats(self, client):
        _add_log(level="ERROR")
        _add_log(level="WARNING")
        r = client.get("/api/v1/simple/logs/stats", headers=TOKEN)
        body = r.get_json()
        assert body["status"] == "success"
        assert body["data"]["total"] == 2
        assert body["data"]["level_distribution"]["ERROR"] == 1
        assert len(body["data"]["weekly_trend"]) == 7

    def test_sources(self, client):
        _add_log(source="auth")
        _add_log(source="search")
        r = client.get("/api/v1/simple/logs/sources", headers=TOKEN)
        assert r.get_json()["data"] == ["auth", "search"]

    def test_clear_logs(self, client):
        from datetime import timedelta

        old = LogEntry(
            timestamp=datetime.now(timezone.utc) - timedelta(days=40),
            level="INFO",
            source="old",
            message="stale",
        )
        db.session.add(old)
        db.session.commit()
        _add_log()  # fresh
        r = client.post("/api/v1/simple/logs/clear", json={"days": 30}, headers=TOKEN)
        assert r.status_code == 200
        assert r.get_json()["data"]["deleted_count"] == 1

    def test_clear_logs_invalid_days(self, client):
        r = client.post("/api/v1/simple/logs/clear", json={"days": 0}, headers=TOKEN)
        assert r.status_code == 400
