"""Celery 定时发布任务测试。

注意:app.tasks 在导入时会调用 create_app(),其内部使用模块级 flask_app;
因此本测试在 flask_app 的 app_context 中构造数据,再调用任务本身。
"""

from datetime import datetime, timedelta, timezone


def _make_user(t_app):
    from app import db
    from app.models import User

    u = User(email="task_owner@example.com", password_hash="x", role="author")
    db.session.add(u)
    db.session.commit()
    return u


def _make_article(t_app, user, status, scheduled_at=None, title="Task Article"):
    from app import db
    from app.models import Article

    a = Article(
        title=title,
        slug=f"task-{title.lower().replace(' ', '-')}",
        content_md="body",
        author_id=user.id,
        status=status,
        scheduled_at=scheduled_at,
    )
    db.session.add(a)
    db.session.commit()
    return a


class TestPublishScheduled:
    def test_publishes_due_articles(self, app):
        from app import db
        from app.models import Article
        from app.tasks import flask_app as t_app
        from app.tasks import publish_scheduled_articles

        with t_app.app_context():
            db.drop_all()
            db.create_all()
            u = _make_user(t_app)
            past = datetime.now(timezone.utc) - timedelta(minutes=5)
            future = datetime.now(timezone.utc) + timedelta(hours=1)
            due = _make_article(t_app, u, "scheduled", past, "Due One")
            _make_article(t_app, u, "scheduled", future, "Future One")
            _make_article(t_app, u, "published", None, "Already Pub")

            n = publish_scheduled_articles()
            assert n == 1
            due_again = Article.query.get(due.id)
            assert due_again.status == "published"
            assert due_again.published_at is not None

    def test_no_due_articles(self, app):
        from app import db
        from app.models import Article
        from app.tasks import flask_app as t_app
        from app.tasks import publish_scheduled_articles

        with t_app.app_context():
            db.drop_all()
            db.create_all()
            u = _make_user(t_app)
            future = datetime.now(timezone.utc) + timedelta(hours=1)
            _make_article(t_app, u, "scheduled", future, "Not Due")
            n = publish_scheduled_articles()
            assert n == 0
            assert Article.query.count() == 1


class TestInvalidateCache:
    def test_invalidate_by_id(self, app):
        from app.tasks import _invalidate_article_cache
        from app.tasks import redis_client as tasks_redis

        tasks_redis.setex("article:7", 100, "v")
        tasks_redis.setex("articles:list:1", 100, "v")
        _invalidate_article_cache(7)
        assert tasks_redis.get("article:7") is None

    def test_invalidate_no_id(self, app):
        from app.tasks import _invalidate_article_cache

        # no-op path (FakeRedis scan_iter returns empty)
        _invalidate_article_cache()
