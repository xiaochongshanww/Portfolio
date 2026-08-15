"""访客统计服务与中间件测试。"""

import hashlib

from app.models import DailyStats, VisitorStats
from app.services.visitor_tracker import VisitorTracker


class TestGetClientIp:
    def test_x_forwarded_for(self, app):
        with app.test_request_context(headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}):
            assert VisitorTracker.get_client_ip() == "1.2.3.4"

    def test_x_real_ip(self, app):
        with app.test_request_context(headers={"X-Real-IP": "9.9.9.9"}):
            assert VisitorTracker.get_client_ip() == "9.9.9.9"

    def test_x_client_ip(self, app):
        with app.test_request_context(headers={"X-Client-IP": "8.8.8.8"}):
            assert VisitorTracker.get_client_ip() == "8.8.8.8"

    def test_remote_addr_fallback(self, app):
        with app.test_request_context():
            ip = VisitorTracker.get_client_ip()
            assert ip


class TestUserAgentHash:
    def test_hash(self, app):
        with app.test_request_context(headers={"User-Agent": "Mozilla/5.0"}):
            expected = hashlib.sha256(b"Mozilla/5.0").hexdigest()
            assert VisitorTracker.get_user_agent_hash() == expected


class TestTrackVisit:
    def test_new_visitor(self, app):
        with app.test_request_context(headers={"User-Agent": "UA-1"}):
            is_new = VisitorTracker.track_visit()
            assert is_new is True
            assert VisitorStats.query.count() == 1
            stats = DailyStats.query.first()
            assert stats is not None
            assert stats.unique_visitors == 1
            assert stats.total_page_views == 1

    def test_existing_visitor_increments(self, app):
        with app.test_request_context(headers={"User-Agent": "UA-2"}):
            assert VisitorTracker.track_visit() is True
            assert VisitorTracker.track_visit() is False  # existing → not new
            assert VisitorStats.query.count() == 1
            assert VisitorStats.query.first().page_views == 2
            assert DailyStats.query.first().total_page_views == 2

    def test_retry_path(self, app):
        # _retry_track_visit with no existing record → returns False safely
        with app.test_request_context(headers={"User-Agent": "UA-3"}):
            res = VisitorTracker._retry_track_visit()
            assert res is False


class TestDailyStats:
    def test_update_new(self, app):
        from datetime import date

        VisitorTracker.update_daily_stats(date(2026, 1, 1), True)
        s = DailyStats.query.filter_by(stat_date=date(2026, 1, 1)).first()
        assert s is not None
        assert s.unique_visitors == 1
        assert s.total_page_views == 1

    def test_update_existing(self, app):
        from datetime import date

        VisitorTracker.update_daily_stats(date(2026, 1, 2), True)
        VisitorTracker.update_daily_stats(date(2026, 1, 2), False)
        s = DailyStats.query.filter_by(stat_date=date(2026, 1, 2)).first()
        assert s.unique_visitors == 1
        assert s.total_page_views == 2


class TestGetStats:
    def test_today_stats_empty(self, app):
        assert VisitorTracker.get_today_stats() == {
            "today_visitors": 0,
            "today_page_views": 0,
        }

    def test_today_stats_with_data(self, app):
        with app.test_request_context(headers={"User-Agent": "UA-4"}):
            VisitorTracker.track_visit()
        s = VisitorTracker.get_today_stats()
        assert s["today_visitors"] >= 1

    def test_total_stats(self, app):
        with app.test_request_context(headers={"User-Agent": "UA-5"}):
            VisitorTracker.track_visit()
        t = VisitorTracker.get_total_stats()
        assert t["total_visitors"] >= 1
        assert t["total_page_views"] >= 1

    def test_get_visitor_stats(self, app):
        s = VisitorTracker.get_visitor_stats()
        assert set(s) == {
            "today_visitors",
            "today_page_views",
            "total_visitors",
            "total_page_views",
        }


class TestMiddleware:
    def test_skip_patterns(self, app):
        from app.middlewares.visitor_tracker import VisitorTrackingMiddleware

        inst = VisitorTrackingMiddleware()
        cases = [
            "/api/v1/articles",
            "/admin/x",
            "/metrics/x",
            "/static/x.css",
            "/uploads/a.png",
            "/favicon.ico",
            "/robots.txt",
            "/sitemap.xml",
            "/style.css",
            "/app.js",
            "/img/logo.svg",
        ]
        for path in cases:
            with app.test_request_context(path=path, headers={"User-Agent": "UA-6"}):
                assert inst._should_skip_tracking() is True, path

    def test_does_not_skip_article_page(self, app):
        from app.middlewares.visitor_tracker import VisitorTrackingMiddleware

        inst = VisitorTrackingMiddleware()
        with app.test_request_context(
            path="/article/my-post", headers={"User-Agent": "UA-7"}
        ):
            assert inst._should_skip_tracking() is False

    def test_skip_bot_ua(self, app):
        from app.middlewares.visitor_tracker import VisitorTrackingMiddleware

        inst = VisitorTrackingMiddleware()
        with app.test_request_context(
            path="/article/x", headers={"User-Agent": "Googlebot"}
        ):
            assert inst._should_skip_tracking() is True

    def test_track_visitor_post_skipped(self, app):
        from app.middlewares.visitor_tracker import VisitorTrackingMiddleware

        inst = VisitorTrackingMiddleware()
        with app.test_request_context(
            path="/article/x", method="POST", headers={"User-Agent": "UA-8"}
        ):
            inst.track_visitor()  # should no-op for non-GET

    def test_track_visitor_get_records(self, app):
        from app.middlewares.visitor_tracker import VisitorTrackingMiddleware

        inst = VisitorTrackingMiddleware()
        with app.test_request_context(
            path="/article/x", headers={"User-Agent": "UA-9"}
        ):
            inst.track_visitor()
            assert VisitorStats.query.count() >= 1

    def test_init_app_registers_before_request(self, app, client):
        from app.middlewares.visitor_tracker import VisitorTrackingMiddleware

        inst = VisitorTrackingMiddleware()
        inst.init_app(app)
        client.get("/some-page", headers={"User-Agent": "UA-10"})
        assert VisitorStats.query.count() >= 1
