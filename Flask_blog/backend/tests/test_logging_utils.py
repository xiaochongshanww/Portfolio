"""日志工具测试 — 覆盖 utils/logging_utils.py。"""

from datetime import datetime, timedelta

from app import db
from app.models import LogConfig, LogEntry
from app.utils import logging_utils as lu


class TestCreateLogEntry:
    def test_creates_entry(self, app):
        with app.test_request_context("/"):
            entry = lu.create_log_entry("INFO", "SYSTEM", "hello log")
            assert entry is not None
            assert entry.message == "hello log"
            assert entry.source == "SYSTEM"

    def test_creates_with_user_id(self, app):
        from app.models import User

        u = User(email="l@test.com", password_hash="x", role="author")
        db.session.add(u)
        db.session.commit()
        with app.test_request_context("/"):
            entry = lu.create_log_entry("INFO", "SYSTEM", "by user", user_id=u.id)
            assert entry.user_id == u.id


class TestGetLogConfig:
    def test_missing_returns_default(self, app):
        assert lu.get_log_config("nope", 42) == 42

    def test_bool(self, app):
        db.session.add(LogConfig(config_key="flag", config_value="true"))
        db.session.commit()
        assert lu.get_log_config("flag") is True

    def test_int_and_float(self, app):
        db.session.add(LogConfig(config_key="num", config_value="123"))
        db.session.add(LogConfig(config_key="ratio", config_value="1.5"))
        db.session.commit()
        assert lu.get_log_config("num") == 123
        assert lu.get_log_config("ratio") == 1.5

    def test_is_logging_enabled(self, app):
        assert lu.is_logging_enabled("user_logs") in (True, False)


class TestEventLogging:
    def test_log_security_event(self, app):
        with app.test_request_context("/"):
            lu.log_security_event(
                "login_attempt", severity="WARNING", details={"ip": "x"}
            )
        assert LogEntry.query.filter_by(source="SECURITY").count() >= 1

    def test_log_system_event(self, app):
        with app.test_request_context("/"):
            lu.log_system_event("system ok", component="TEST")
        assert LogEntry.query.filter_by(source="SYSTEM_TEST").count() >= 1


class TestDecorators:
    def test_log_user_action(self, app):
        @lu.log_user_action("test_action")
        def handler():
            return "ok"

        with app.test_request_context("/test"):
            result = handler()
            assert result == "ok"
        assert LogEntry.query.filter_by(source="USER_ACTION").count() >= 1

    def test_log_api_request(self, app):
        @lu.log_api_request()
        def handler():
            return "resp"

        with app.test_request_context("/api/test"):
            result = handler()
            assert result == "resp"
        assert LogEntry.query.filter_by(source="API_REQUEST").count() >= 1


class TestCleanup:
    def test_cleanup_old_logs(self, app):
        old = datetime.utcnow() - timedelta(days=100)
        db.session.add(
            LogEntry(
                level="INFO", source="S", message="old", timestamp=old, created_at=old
            )
        )
        db.session.commit()
        with app.test_request_context("/"):
            count = lu.cleanup_old_logs(days=30)
        assert count >= 1

    def test_get_request_info(self, app):
        with app.test_request_context("/path", method="GET"):
            info = lu.get_request_info()
            assert "endpoint" in info
            assert "method" in info
