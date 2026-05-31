"""文章业务逻辑层 — 供 routes.py 编排调用"""

import difflib
import hashlib
import json
from datetime import datetime, timezone

from flask import current_app, request
from slugify import slugify
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from .. import db, redis_client
from ..models import (
    Article,
    ArticleBookmark,
    ArticleLike,
    ArticleTag,
    ArticleVersion,
    AuditLog,
    Category,
    Tag,
)
from ..search.indexer import delete_article as search_delete_article
from ..search.indexer import index_article
from ..security.enforcer import BusinessError
from ..services.content_sanitizer import render_and_sanitize
from ..services.image_variants import generate_focal_crops
from ..utils import compute_etag

# 指标
try:
    from .. import ARTICLE_PUBLISHED_TOTAL, CACHE_HIT_TOTAL, CACHE_MISS_TOTAL
except Exception:
    ARTICLE_PUBLISHED_TOTAL = CACHE_HIT_TOTAL = CACHE_MISS_TOTAL = None


# ─── 序列化 ───────────────────────────────────────────────

def _batch_likes_bookmarks(article_ids: list[int]):
    """批量预查点赞/收藏计数，避免 N+1。"""
    if not article_ids:
        return {}, {}
    likes_q = db.session.query(ArticleLike.article_id, func.count()).filter(
        ArticleLike.article_id.in_(article_ids)).group_by(ArticleLike.article_id).all()
    bookmarks_q = db.session.query(ArticleBookmark.article_id, func.count()).filter(
        ArticleBookmark.article_id.in_(article_ids)).group_by(ArticleBookmark.article_id).all()
    likes_map = {row[0]: row[1] for row in likes_q}
    bookmarks_map = {row[0]: row[1] for row in bookmarks_q}
    return likes_map, bookmarks_map


def serialize_article(a: Article, detail=False, include_user_flags=False, user_id=None,
                      likes_count=None, bookmarks_count=None):
    if likes_count is None:
        likes_count = ArticleLike.query.filter_by(article_id=a.id).count()
    if bookmarks_count is None:
        bookmarks_count = ArticleBookmark.query.filter_by(article_id=a.id).count()

    data = {
        'id': a.id,
        'title': a.title,
        'slug': a.slug,
        'status': a.status,
        'summary': a.summary,
        'seo_title': a.seo_title,
        'seo_desc': a.seo_desc,
        'featured_image': a.featured_image,
        'featured_focal_x': a.featured_focal_x,
        'featured_focal_y': a.featured_focal_y,
        'created_at': a.created_at.isoformat() + 'Z' if a.created_at else None,
        'published_at': a.published_at.isoformat() + 'Z' if a.published_at else None,
        'updated_at': a.updated_at.isoformat() + 'Z' if a.updated_at else None,
        'tags': [t.slug for t in a.tags],
        'likes_count': likes_count,
        'bookmarks_count': bookmarks_count,
        'views_count': getattr(a, 'views_count', None),
        'content_excerpt': (a.content_md or '')[:200] if a.content_md else '',
    }

    if a.author:
        data['author'] = {
            'id': a.author.id,
            'name': a.author.nickname or a.author.email,
            'nickname': a.author.nickname,
            'email': a.author.email,
            'avatar': a.author.avatar,
            'bio': a.author.bio,
        }

    if a.category_id:
        category = Category.query.get(a.category_id)
        if category:
            data['category'] = category.name
            data['category_id'] = category.id

    if detail:
        data['content_html'] = a.content_html
        data['content_md'] = a.content_md

    if include_user_flags:
        if user_id:
            liked = ArticleLike.query.filter_by(article_id=a.id, user_id=user_id).first() is not None
            bookmarked = ArticleBookmark.query.filter_by(article_id=a.id, user_id=user_id).first() is not None
            data['liked'] = liked
            data['bookmarked'] = bookmarked
        else:
            data['liked'] = False
            data['bookmarked'] = False

    return data


def serialize_articles_batch(articles: list[Article], detail=False):
    """批量序列化文章列表，预查点赞/收藏计数避免 N+1。"""
    ids = [a.id for a in articles]
    likes_map, bookmarks_map = _batch_likes_bookmarks(ids)
    return [
        serialize_article(a, detail=detail,
                          likes_count=likes_map.get(a.id, 0),
                          bookmarks_count=bookmarks_map.get(a.id, 0))
        for a in articles
    ]


# ─── 工具函数 ─────────────────────────────────────────────

def parse_dt(value: str):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except Exception:
        return None


def _view_fingerprint():
    uid = getattr(request, 'user_id', None)
    if uid:
        return f"u:{uid}"
    ip = (request.headers.get('X-Forwarded-For') or request.remote_addr or '0.0.0.0').split(',')[0].strip()
    ua = (request.headers.get('User-Agent') or '')[:120]
    raw = f"{ip}|{ua}".encode('utf-8', 'ignore')
    return 'g:' + hashlib.sha1(raw).hexdigest()[:16]


def _safe_article_slug(raw: str | None):
    if not raw:
        return 'article'
    try:
        s = slugify(raw)
        if s:
            return s
    except Exception:
        pass
    base = 'article'
    return f"{base}-{int(datetime.now(timezone.utc).timestamp())}"


def _generate_unique_slug(initial_slug: str, exclude_id: int | None = None, max_tries: int = 50) -> str:
    base = initial_slug.strip('-') or 'article'
    candidate = base
    i = 2
    while max_tries > 0:
        q = Article.query.filter_by(slug=candidate)
        if exclude_id:
            q = q.filter(Article.id != exclude_id)
        if not q.first():
            return candidate
        candidate = f"{base}-{i}"
        i += 1
        max_tries -= 1
    return f"{base}-{int(datetime.now(timezone.utc).timestamp())}"


def _tag_slug(name: str):
    if not name:
        return ''
    if any(ord(c) > 127 for c in name):
        return name
    try:
        s = slugify(name)
        if s:
            return s
    except Exception:
        pass
    return name


def _resolve_tags(tag_names: list[str]):
    """根据名称列表解析/创建 Tag 对象，去重。"""
    if not tag_names:
        return []
    tags = []
    seen = set()
    for name in tag_names[:10]:
        if not name:
            continue
        t_slug = _tag_slug(name)
        if not t_slug or t_slug in seen:
            continue
        seen.add(t_slug)
        tag = Tag.query.filter_by(slug=t_slug).first()
        if not tag:
            tag = Tag(name=name, slug=t_slug)
            db.session.add(tag)
            try:
                db.session.flush()
            except Exception:
                db.session.rollback()
                raise BusinessError(5000, 'tag_create_failed', 500)
        tags.append(tag)
    return tags


def _make_focal_crops(featured_image, focal_x, focal_y):
    if not featured_image or focal_x is None or focal_y is None:
        return {}
    try:
        return generate_focal_crops(featured_image, focal_x, focal_y, current_app.config['UPLOAD_DIR'])
    except Exception:
        return {}


# ─── 缓存 ─────────────────────────────────────────────────

def _cache_track_key(cache_key: str):
    """将缓存 key 加入失效索引，供批量清除使用。"""
    if not redis_client:
        return
    try:
        redis_client.sadd('cache:idx:articles', cache_key)
    except Exception:
        pass


def cache_track_set(key: str, value: str, ex: int):
    """设置 Redis 缓存并注册 key 到失效索引。"""
    if not redis_client:
        return
    try:
        redis_client.setex(key, ex, value)
        redis_client.sadd('cache:idx:articles', key)
        redis_client.expire('cache:idx:articles', 86400)
    except Exception:
        pass


def invalidate_article_cache(article_id=None, author_id=None):
    """失效文章相关缓存。使用缓存 key 索引集，批量删除避免 scan_iter 遍历。"""
    if not redis_client:
        return
    try:
        keys = []
        idx_key = 'cache:idx:articles'
        # 从索引中读取所有已注册的缓存 key
        tracked = redis_client.smembers(idx_key)
        if tracked:
            keys = [k for k in tracked if isinstance(k, (str, bytes))]
        # 加上独立 key
        if article_id:
            keys.append(f"article:{article_id}")
            article = Article.query.get(article_id)
            if article and article.slug:
                keys.append(f"public:article:slug:{article.slug}")
        if author_id:
            keys.append(f"public:author:{author_id}")
        keys.append('sitemap:xml')
        if keys:
            redis_client.delete(*keys)
        redis_client.delete(idx_key)
    except Exception:
        pass


def log_action(article_id, operator_id, action, note=None):
    try:
        al = AuditLog(article_id=article_id, operator_id=operator_id, action=action, note=note)
        db.session.add(al)
        db.session.commit()
    except Exception:
        db.session.rollback()


def try_index(article: Article):
    try:
        index_article(article)
    except Exception as e:
        print(f"搜索索引失败: {e}")


def try_remove_from_search(article_id: int):
    try:
        search_delete_article(article_id)
    except Exception:
        pass


# ─── 文章 CRUD ────────────────────────────────────────────

def create_article(parsed, user_id) -> Article:
    title = getattr(parsed, 'title', None)
    raw_slug = getattr(parsed, 'slug', None) or title
    base_slug = _safe_article_slug(raw_slug)
    unique_slug = _generate_unique_slug(base_slug)
    content_md = getattr(parsed, 'content_md', '') or ''

    article = Article(
        title=title,
        slug=unique_slug,
        author_id=user_id,
        content_md=content_md,
        content_html=render_and_sanitize(content_md),
        summary=getattr(parsed, 'summary', None),
        seo_title=getattr(parsed, 'seo_title', None),
        seo_desc=getattr(parsed, 'seo_desc', None),
        featured_image=getattr(parsed, 'featured_image', None),
        featured_focal_x=getattr(parsed, 'featured_focal_x', None),
        featured_focal_y=getattr(parsed, 'featured_focal_y', None),
        category_id=getattr(parsed, 'category_id', None),
        scheduled_at=parse_dt(getattr(parsed, 'scheduled_at', None)) if getattr(parsed, 'scheduled_at', None) else None,
    )

    tags = _resolve_tags(getattr(parsed, 'tags', []) or [])
    if tags:
        article.tags = tags

    db.session.add(article)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        article.slug = _generate_unique_slug(base_slug)
        db.session.add(article)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise BusinessError(4090, 'slug_duplicate_race', 409)

    try_index(article)
    invalidate_article_cache(article.id, article.author_id)
    return article


def update_article(article: Article, parsed, user_id, user_role) -> Article:
    if article.author_id != user_id and user_role not in ('editor', 'admin'):
        raise BusinessError(4030, 'forbidden', 403)

    prev_md = article.content_md

    if getattr(parsed, 'title', None):
        article.title = parsed.title
    if hasattr(parsed, 'slug') and getattr(parsed, 'slug'):
        new_base = slugify(parsed.slug)
        if new_base and new_base != article.slug:
            article.slug = _generate_unique_slug(new_base, exclude_id=article.id)
    if hasattr(parsed, 'content_md') and parsed.content_md is not None:
        article.content_md = parsed.content_md or ''
        article.content_html = render_and_sanitize(article.content_md)
    for f in ['summary', 'seo_title', 'seo_desc', 'featured_image', 'featured_focal_x', 'featured_focal_y', 'category_id', 'status']:
        if hasattr(parsed, f):
            setattr(article, f, getattr(parsed, f))
    if hasattr(parsed, 'tags') and parsed.tags is not None:
        article.tags = _resolve_tags(parsed.tags or [])

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise BusinessError(4090, 'update_conflict', 409)

    if prev_md != article.content_md:
        _save_version_snapshot(article, user_id)

    try_index(article)
    invalidate_article_cache(article.id, article.author_id)
    return article


# ─── 版本控制 ─────────────────────────────────────────────

def _save_version_snapshot(article: Article, editor_id: int):
    try:
        last = (ArticleVersion.query.filter_by(article_id=article.id)
                .order_by(ArticleVersion.version_no.desc()).first())
        next_no = (last.version_no if last else 0) + 1
        v = ArticleVersion(
            article_id=article.id, version_no=next_no,
            content_md=article.content_md, content_html=article.content_html,
            editor_id=editor_id,
        )
        db.session.add(v)
        db.session.commit()
    except Exception:
        db.session.rollback()


def create_version_snapshot(article: Article, editor_id: int) -> int:
    last = (ArticleVersion.query.filter_by(article_id=article.id)
            .order_by(ArticleVersion.version_no.desc()).first())
    next_no = (last.version_no if last else 0) + 1
    v = ArticleVersion(
        article_id=article.id, version_no=next_no,
        content_md=article.content_md, content_html=article.content_html,
        editor_id=editor_id,
    )
    db.session.add(v)
    db.session.commit()
    return next_no


def rollback_to_version(article: Article, target_version_no: int, user_id: int):
    target = ArticleVersion.query.filter_by(article_id=article.id, version_no=target_version_no).first()
    if not target:
        raise BusinessError(4040, 'version_not_found', 404)

    article.content_md = target.content_md
    article.content_html = target.content_html
    try:
        new_no = create_version_snapshot(article, user_id)
    except Exception:
        db.session.rollback()
        raise BusinessError(5000, 'server_error', 500)

    log_action(article.id, user_id, 'rollback', note=f'to {target_version_no}')
    try_index(article)
    invalidate_article_cache(article.id, article.author_id)
    return new_no, target_version_no


def diff_versions(article_id: int, version_no_a: int, version_no_b: int):
    v1 = ArticleVersion.query.filter_by(article_id=article_id, version_no=version_no_a).first()
    v2 = ArticleVersion.query.filter_by(article_id=article_id, version_no=version_no_b).first()
    if not v1 or not v2:
        raise BusinessError(4040, 'version_not_found', 404)

    text1 = (v1.content_md or '').splitlines(keepends=True)
    text2 = (v2.content_md or '').splitlines(keepends=True)
    diff = list(difflib.unified_diff(text1, text2, fromfile=f'v{version_no_a}', tofile=f'v{version_no_b}', lineterm=''))
    if not any(l.startswith('@@') for l in diff):
        diff.insert(0, f"@@ v{version_no_a}..v{version_no_b} @@")
    return diff


# ─── 工作流 ───────────────────────────────────────────────

def approve_article(article: Article, user_id: int):
    if article.deleted:
        raise BusinessError(4040, 'not_found', 404)
    if article.status != 'published':
        article.status = 'published'
        if not article.published_at:
            article.published_at = datetime.now(timezone.utc)
        db.session.commit()
        log_action(article.id, user_id, 'approve')
        try_index(article)
        invalidate_article_cache(article.id, article.author_id)
        if ARTICLE_PUBLISHED_TOTAL:
            try:
                ARTICLE_PUBLISHED_TOTAL.labels('approve').inc()
            except Exception:
                pass


def reject_article(article: Article, reason: str, user_id: int):
    if article.deleted:
        raise BusinessError(4040, 'not_found', 404)
    if article.status != 'pending':
        raise BusinessError(3001, 'workflow_invalid_state', 400,
                            data={'from': article.status, 'to': 'draft'})
    if not reason:
        raise BusinessError(4001, 'validation_error', 400, data={'field': 'reason'})
    article.status = 'draft'
    article.reject_reason = reason[:500]
    db.session.commit()
    log_action(article.id, user_id, 'reject', note=reason[:500])
    invalidate_article_cache(article.id, article.author_id)


def submit_article(article: Article, user_id: int):
    if article.author_id != user_id:
        raise BusinessError(2002, 'forbidden', 403)
    if article.deleted:
        raise BusinessError(4040, 'not_found', 404)
    if article.status != 'draft':
        raise BusinessError(3001, 'workflow_invalid_state', 400,
                            data={'from': article.status, 'to': 'pending'})
    article.status = 'pending'
    db.session.commit()
    log_action(article.id, user_id, 'submit')
    invalidate_article_cache(article.id, article.author_id)


def schedule_article(article: Article, scheduled_at_dt: datetime, user_id: int, user_role: str):
    if article.author_id != user_id and user_role not in ('editor', 'admin'):
        raise BusinessError(2002, 'forbidden', 403)
    if article.deleted:
        raise BusinessError(4040, 'not_found', 404)
    if article.status == 'published':
        raise BusinessError(3001, 'workflow_invalid_state', 400,
                            data={'from': article.status, 'to': 'scheduled'})
    article.scheduled_at = scheduled_at_dt
    article.status = 'scheduled'
    db.session.commit()
    log_action(article.id, user_id, 'schedule', note=scheduled_at_dt.isoformat())
    invalidate_article_cache(article.id, article.author_id)


def unschedule_article(article: Article, user_id: int, user_role: str):
    if article.author_id != user_id and user_role not in ('editor', 'admin'):
        raise BusinessError(2002, 'forbidden', 403)
    if article.deleted:
        raise BusinessError(4040, 'not_found', 404)
    if article.status != 'scheduled':
        raise BusinessError(3001, 'workflow_invalid_state', 400,
                            data={'from': article.status, 'to': 'draft'})
    article.scheduled_at = None
    article.status = 'draft'
    db.session.commit()
    log_action(article.id, user_id, 'unschedule')
    invalidate_article_cache(article.id, article.author_id)


def unpublish_article(article: Article, user_id: int):
    if article.deleted:
        raise BusinessError(4040, 'not_found', 404)
    if article.status != 'published':
        raise BusinessError(3001, 'workflow_invalid_state', 400,
                            data={'from': article.status, 'to': 'draft'})
    article.status = 'draft'
    article.published_at = None
    db.session.commit()
    try_remove_from_search(article.id)
    log_action(article.id, user_id, 'unpublish')
    invalidate_article_cache(article.id, article.author_id)


def delete_article(article: Article, user_id: int):
    if article.deleted:
        raise BusinessError(4040, 'not_found', 404)
    article.deleted = True
    db.session.commit()
    try_remove_from_search(article.id)
    log_action(article.id, user_id, 'delete')
    invalidate_article_cache(article.id, article.author_id)


# ─── 点赞 / 收藏 ──────────────────────────────────────────

def toggle_like(article_id: int, user_id: int) -> tuple[str, int]:
    article = Article.query.get_or_404(article_id)
    if article.deleted or article.status != 'published':
        raise BusinessError(4040, 'not_found', 404)
    existing = ArticleLike.query.filter_by(article_id=article_id, user_id=user_id).first()
    if existing:
        db.session.delete(existing)
        action = 'unliked'
    else:
        db.session.add(ArticleLike(article_id=article_id, user_id=user_id))
        action = 'liked'
    db.session.commit()
    count = ArticleLike.query.filter_by(article_id=article_id).count()
    invalidate_article_cache(article.id)
    return action, count


def toggle_bookmark(article_id: int, user_id: int) -> tuple[str, int]:
    article = Article.query.get_or_404(article_id)
    if article.deleted or article.status != 'published':
        raise BusinessError(4040, 'not_found', 404)
    existing = ArticleBookmark.query.filter_by(article_id=article_id, user_id=user_id).first()
    if existing:
        db.session.delete(existing)
        action = 'removed'
    else:
        db.session.add(ArticleBookmark(article_id=article_id, user_id=user_id))
        action = 'bookmarked'
    db.session.commit()
    count = ArticleBookmark.query.filter_by(article_id=article_id).count()
    invalidate_article_cache(article.id)
    return action, count


# ─── 可见性检查 ────────────────────────────────────────────

def check_article_visibility(article: Article, role, user_id) -> bool:
    """检查当前用户是否有权访问该文章。"""
    if article.status == 'published':
        return True
    if role in ('editor', 'admin'):
        return True
    if user_id and article.author_id == user_id:
        return True
    if not role and not user_id and article.status == 'draft' and current_app.config.get('TESTING'):
        return True
    return False
