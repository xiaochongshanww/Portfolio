from .client import ensure_index
from ..models import Article

def article_to_doc(article: Article):
    return {
        'id': article.id,
        'title': article.title,
        'content': (article.content_md or '')[:5000],
        'tags': [t.slug for t in article.tags],
        'status': article.status,
        'category_id': article.category_id,
        'author_id': article.author_id,
        'published_at': article.published_at.isoformat() if article.published_at else None,
        'created_at': article.created_at.isoformat() if article.created_at else None,
        'likes_count': article.likes.count() if hasattr(article, 'likes') else None,
        'views_count': getattr(article, 'views_count', None)
    }

def index_article(article: Article):
    """根据文章状态更新索引：仅保留已发布且未删除的文章。测试模式下同步等待任务完成."""
    idx = ensure_index()
    if article.status != 'published' or article.deleted:
        try:
            task = idx.delete_document(str(article.id))
            try:
                if task and hasattr(idx, 'wait_for_task'):
                    idx.wait_for_task(task.get('taskUid') or task.get('uid'))
            except Exception:
                pass
        except Exception:
            pass
        return
    task = idx.add_documents([article_to_doc(article)])
    try:
        if task and hasattr(idx, 'wait_for_task'):
            idx.wait_for_task(task.get('taskUid') or task.get('uid'))
    except Exception:
        pass


def delete_article(article_id: int):
    idx = ensure_index()
    try:
        task = idx.delete_document(str(article_id))
        try:
            if task and hasattr(idx, 'wait_for_task'):
                idx.wait_for_task(task.get('taskUid') or task.get('uid'))
        except Exception:
            pass
    except Exception:
        pass


def reindex_all(published_only: bool = True):
    """全量重建索引。适用于字段调整或批量修复。"""
    idx = ensure_index()
    query = Article.query.filter_by(deleted=False)
    if published_only:
        query = query.filter_by(status='published')
    articles = query.all()
    docs = [article_to_doc(a) for a in articles if a.status == 'published']
    # 清空索引再写入（MeiliSearch 暂无官方 truncate，可逐步替换）
    try:
        idx.delete_all_documents()
    except Exception:
        pass
    if docs:
        idx.add_documents(docs)
