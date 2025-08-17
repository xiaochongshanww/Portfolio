import os
from datetime import datetime, timezone
from celery import Celery
from . import create_app, db, redis_client
from .models import Article
from .search.indexer import index_article
# 指标
try:
    from . import ARTICLE_PUBLISHED_TOTAL
except Exception:
    ARTICLE_PUBLISHED_TOTAL = None

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)

celery_app = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

# 将 Flask 配置传入 Celery（如需要）
flask_app = create_app()

def _invalidate_article_cache(article_id=None):
    if not redis_client:
        return
    try:
        if article_id:
            redis_client.delete(f"article:{article_id}")
        for k in redis_client.scan_iter(match="articles:list:*"):
            redis_client.delete(k)
    except Exception:
        pass

@celery_app.task
def publish_scheduled_articles():
    """扫描 scheduled 状态且时间已到的文章并发布。"""
    with flask_app.app_context():
        now = datetime.now(timezone.utc)
        q = Article.query.filter(Article.status=='scheduled', Article.scheduled_at!=None, Article.scheduled_at <= now, Article.deleted==False)
        updated = []
        for art in q.all():
            art.status = 'published'
            art.published_at = now
            updated.append(art)
        if updated:
            db.session.commit()
            for art in updated:
                try:
                    index_article(art)
                except Exception:
                    pass
                _invalidate_article_cache(art.id)
                if ARTICLE_PUBLISHED_TOTAL:
                    try: ARTICLE_PUBLISHED_TOTAL.labels('schedule').inc()
                    except Exception: pass
        return len(updated)
