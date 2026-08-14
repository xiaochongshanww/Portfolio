"""用户业务逻辑层 — 供 routes.py 编排调用"""

import json

from .. import (
    CACHE_HIT_TOTAL,
    CACHE_MISS_TOTAL,
    METRICS_ENABLED,
    PUBLIC_AUTHOR_ARTICLES_REQUESTS_TOTAL,
    PUBLIC_AUTHOR_ARTICLES_ZERO_RESULT_TOTAL,
    PUBLIC_AUTHOR_PROFILE_REQUESTS_TOTAL,
    db,
    redis_client,
)
from ..models import Article, ArticleLike, User
from ..utils import compute_etag


class UserServiceError(Exception):
    """用户业务异常，携带 HTTP 状态码与错误码。"""

    def __init__(self, message, code=4001, status=400, data=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.data = data


def serialize_user(u: User, include_email=False):
    data = {
        "id": u.id,
        "role": u.role,
        "nickname": u.nickname,
        "bio": u.bio,
        "avatar": u.avatar,
    }
    if u.social_links:
        try:
            data["social_links"] = json.loads(u.social_links)
        except Exception:
            data["social_links"] = None
    if include_email:
        data["email"] = u.email
    return data


def update_profile(user, nickname=None, bio=None, avatar=None, social_links=None):
    """更新用户资料字段，返回更新后的用户。"""
    if nickname is not None:
        user.nickname = nickname
    if bio is not None:
        user.bio = bio
    if avatar is not None:
        user.avatar = avatar
    if social_links is not None:
        if not isinstance(social_links, dict):
            raise UserServiceError("social_links must be a dictionary")
        try:
            user.social_links = json.dumps(social_links, ensure_ascii=False)
        except Exception as e:
            raise UserServiceError("invalid social_links format", data=e)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise UserServiceError("database error", code=5001, status=500, data=e)
    return user


def list_users(page, size):
    """分页列出用户。"""
    q = User.query
    total = q.count()
    users = q.order_by(User.id.asc()).offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "page": page,
        "page_size": size,
        "has_next": page * size < total,
        "list": [serialize_user(u, include_email=True) for u in users],
    }


def change_role(user, role, operator_id=0):
    """修改用户角色并记录审计日志。"""
    old = user.role
    user.role = role
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise UserServiceError("database error", code=5001, status=500, data=e)
    from ..utils import audit_log

    audit_log(
        "user:role_change",
        operator_id,
        f"用户 {user.id} 角色变更: {old} → {user.role}",
    )
    return old


def _cache_get(cache_key, metric_label):
    """尝试读取缓存；命中时返回数据，未命中返回 None。"""
    if not redis_client:
        return None
    try:
        cached = redis_client.get(cache_key)
        if cached:
            data = json.loads(cached)
            if CACHE_HIT_TOTAL:
                try:
                    CACHE_HIT_TOTAL.labels(metric_label).inc()
                except Exception:
                    pass
            return data
        if CACHE_MISS_TOTAL:
            try:
                CACHE_MISS_TOTAL.labels(metric_label).inc()
            except Exception:
                pass
    except Exception:
        pass
    return None


def _cache_set(cache_key, data, ttl):
    if not redis_client:
        return
    try:
        redis_client.setex(cache_key, ttl, json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


def etag_response(data):
    """构造带 ETag 的响应；若 If-None-Match 命中返回 304。"""
    from flask import jsonify, request

    etag = compute_etag(data)
    if request.headers.get("If-None-Match") == etag:
        return ("", 304, {"ETag": etag})
    resp = jsonify({"code": 0, "message": "ok", "data": data})
    resp.headers["ETag"] = etag
    return resp


def public_author_profile(user_id):
    """公开作者资料：非敏感字段 + 已发布文章统计（带缓存）。"""
    if METRICS_ENABLED and PUBLIC_AUTHOR_PROFILE_REQUESTS_TOTAL:
        try:
            PUBLIC_AUTHOR_PROFILE_REQUESTS_TOTAL.inc()
        except Exception:
            pass
    cache_key = f"public:author:{user_id}"
    cached = _cache_get(cache_key, "public_author_profile")
    if cached is not None:
        return etag_response(cached)
    u = User.query.get_or_404(user_id)
    pub_count = Article.query.filter_by(
        author_id=u.id, status="published", deleted=False
    ).count()
    data = serialize_user(u, include_email=False)
    data["published_articles"] = pub_count
    _cache_set(cache_key, data, 300)
    return etag_response(data)


def public_author_articles(user_id, page, size, sort):
    """公开作者已发布文章列表，支持分页与排序（带缓存）。"""
    if METRICS_ENABLED and PUBLIC_AUTHOR_ARTICLES_REQUESTS_TOTAL:
        try:
            PUBLIC_AUTHOR_ARTICLES_REQUESTS_TOTAL.inc()
        except Exception:
            pass
    sort_field, _, sort_dir = sort.partition(":")
    if sort_field not in ("published_at", "created_at"):
        sort_field = "published_at"
    desc = (sort_dir or "desc").lower() != "asc"
    cache_key = (
        f"public:author_articles:{user_id}:{page}:{size}:{sort_field}:"
        f"{'d' if desc else 'a'}"
    )
    cached = _cache_get(cache_key, "public_author_articles")
    if cached is not None:
        return etag_response(cached)
    q = Article.query.filter_by(author_id=user_id, status="published", deleted=False)
    total = q.count()
    if total == 0 and METRICS_ENABLED and PUBLIC_AUTHOR_ARTICLES_ZERO_RESULT_TOTAL:
        try:
            PUBLIC_AUTHOR_ARTICLES_ZERO_RESULT_TOTAL.inc()
        except Exception:
            pass
    col = Article.published_at if sort_field == "published_at" else Article.created_at
    if desc:
        col = col.desc()
    items = q.order_by(col).offset((page - 1) * size).limit(size).all()
    from ..articles.routes import serialize_article

    data_list = [serialize_article(a) for a in items]
    payload = {
        "total": total,
        "page": page,
        "page_size": size,
        "has_next": page * size < total,
        "list": data_list,
    }
    _cache_set(cache_key, payload, 120)
    return etag_response(payload)


def public_author_stats(user_id):
    """作者公开统计：文章数 / 总浏览 / 总点赞 / 最近发布（带缓存）。"""
    cache_key = f"public:author_stats:{user_id}"
    cached = _cache_get(cache_key, "public_author_stats")
    if cached is not None:
        return etag_response(cached)
    u = User.query.get_or_404(user_id)
    q = Article.query.filter_by(author_id=u.id, status="published", deleted=False)
    articles = q.with_entities(
        Article.id, Article.published_at, Article.views_count
    ).all()
    article_ids = [row.id for row in articles]
    likes_total = 0
    if article_ids:
        likes_total = ArticleLike.query.filter(
            ArticleLike.article_id.in_(article_ids)
        ).count()
    total_views = sum(row.views_count or 0 for row in articles)
    last_pub = None
    if articles:
        pubs = [row.published_at for row in articles if row.published_at]
        if pubs:
            last_pub = max(pubs)
    payload = {
        "articles_count": len(article_ids),
        "total_views": total_views,
        "total_likes": likes_total,
        "last_published_at": last_pub.isoformat() if last_pub else None,
    }
    _cache_set(cache_key, payload, 120)
    return etag_response(payload)
