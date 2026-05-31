"""文章路由 — 仅负责 HTTP 编排，业务逻辑委托给 service.py"""

import json
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request

from .. import db, limiter, require_auth, require_roles
from ..models import Article, ArticleVersion, AuditLog, Category
from ..security.enforcer import BusinessError, permission_required, workflow_transition
from ..utils import compute_etag
from .schemas import ArticleCreateModel, ArticleUpdateModel
from .service import (
    _make_focal_crops,
    _resolve_tags,
    _safe_article_slug,
    _view_fingerprint,
)
from .service import approve_article as svc_approve
from .service import (
    cache_track_set,
    check_article_visibility,
    create_article,
    create_version_snapshot,
)
from .service import delete_article as svc_delete
from .service import (
    diff_versions,
    invalidate_article_cache,
    log_action,
    parse_dt,
)
from .service import reject_article as svc_reject
from .service import (
    rollback_to_version,
)
from .service import schedule_article as svc_schedule
from .service import (
    serialize_article,
    serialize_articles_batch,
)
from .service import submit_article as svc_submit
from .service import (
    toggle_bookmark,
    toggle_like,
    try_index,
    try_remove_from_search,
)
from .service import unpublish_article as svc_unpublish
from .service import unschedule_article as svc_unschedule
from .service import (
    update_article,
)

try:
    from .. import ARTICLE_PUBLISHED_TOTAL, CACHE_HIT_TOTAL, CACHE_MISS_TOTAL
except Exception:
    ARTICLE_PUBLISHED_TOTAL = CACHE_HIT_TOTAL = CACHE_MISS_TOTAL = None

articles_bp = Blueprint('articles', __name__)

HAS_PY = True  # pydantic is always installed


@articles_bp.after_request
def add_cache_headers(response):
    """为公开接口添加 CDN 缓存头。"""
    if response.status_code == 200 and request.path.startswith('/articles/public/'):
        if 'Cache-Control' not in response.headers:
            response.headers['Cache-Control'] = f"public, max-age={current_app.config['PUBLIC_CACHE_MAX_AGE']}"
    return response


# ─── 创建 ─────────────────────────────────────────────────

@articles_bp.route('/', methods=['POST'])
@require_auth
def create_article_route():
    try:
        data = request.get_json() or {}
        try:
            parsed = ArticleCreateModel(**data)
        except Exception as ve:
            return jsonify({'code': 4001, 'message': 'validation error', 'data': str(ve)}), 400

        article = create_article(parsed, request.user_id)
        focal_meta = _make_focal_crops(article.featured_image, article.featured_focal_x, article.featured_focal_y)
        payload = serialize_article(article, detail=True, include_user_flags=True, user_id=request.user_id)
        if focal_meta:
            payload['featured_image_variants'] = focal_meta
        return jsonify({'code': 0, 'data': payload, 'message': 'ok'}), 201
    except BusinessError as e:
        return jsonify({'code': e.code, 'message': e.message, 'data': e.data}), e.http_status
    except Exception as e:
        current_app.logger.exception("create_article failed")
        return jsonify({'code': 5000, 'message': 'internal_error', 'detail': str(e)}), 500


# ─── 更新 ─────────────────────────────────────────────────

@articles_bp.route('/<int:article_id>', methods=['PUT'])
@require_auth
def update_article_route(article_id):
    try:
        article = Article.query.get_or_404(article_id)
        data = request.get_json() or {}
        try:
            parsed = ArticleUpdateModel(**data)
        except Exception as ve:
            return jsonify({'code': 4001, 'message': 'validation error', 'data': str(ve)}), 400

        article = update_article(article, parsed, request.user_id, request.user_role)
        focal_meta = _make_focal_crops(article.featured_image, article.featured_focal_x, article.featured_focal_y)
        payload = serialize_article(article, detail=True, include_user_flags=True, user_id=request.user_id)
        if focal_meta:
            payload['featured_image_variants'] = focal_meta
        return jsonify({'code': 0, 'data': payload, 'message': 'ok'})
    except BusinessError as e:
        return jsonify({'code': e.code, 'message': e.message, 'data': e.data}), e.http_status
    except Exception as e:
        current_app.logger.exception("update_article failed")
        return jsonify({'code': 5000, 'message': 'internal_error', 'detail': str(e)}), 500


# ─── 获取单篇 ─────────────────────────────────────────────

@articles_bp.route('/<int:article_id>', methods=['GET'])
def get_article(article_id):
    cache_key = f"article:{article_id}"
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                if data.get('status') != 'published':
                    redis_client.delete(cache_key)
                else:
                    etag = compute_etag(data)
                    if request.headers.get('If-None-Match') == etag:
                        return ('', 304, {'ETag': etag})
                    resp = jsonify({'code': 0, 'data': data, 'message': 'ok'})
                    resp.headers['ETag'] = etag
                    return resp
            except Exception:
                pass

    article = Article.query.get_or_404(article_id)
    if article.deleted:
        return jsonify({'code': 4040, 'message': 'not found'}), 404

    role = getattr(request, 'user_role', None)
    user_id = getattr(request, 'user_id', None)

    if article.status != 'published':
        if not role:
            from .. import require_auth as _rq
            auth_resp = _rq(lambda: None)()
            if auth_resp is None:
                role = getattr(request, 'user_role', None)
                user_id = getattr(request, 'user_id', None)
        if not check_article_visibility(article, role, user_id):
            return jsonify({'code': 4040, 'message': 'not found'}), 404

    data = serialize_article(article, detail=True, include_user_flags=True, user_id=user_id)
    if redis_client and article.status == 'published':
        try:
            cache_track_set(cache_key, current_app.config['CACHE_ARTICLE_DETAIL_TTL'], json.dumps(data))
        except Exception:
            pass

    etag = compute_etag(data)
    if request.headers.get('If-None-Match') == etag:
        return ('', 304, {'ETag': etag})
    resp = jsonify({'code': 0, 'data': data, 'message': 'ok'})
    resp.headers['ETag'] = etag
    return resp


# ─── 列表 ─────────────────────────────────────────────────

@articles_bp.route('/', methods=['GET'])
def list_articles():
    page = int(request.args.get('page', 1))
    size = min(int(request.args.get('page_size', 10)), 50)
    status = request.args.get('status')
    tag = request.args.get('tag')
    category = request.args.get('category')

    role = getattr(request, 'user_role', None)
    user_id = getattr(request, 'user_id', None)

    if status and status != 'published':
        if not role:
            from .. import require_auth as _rq
            auth_resp = _rq(lambda: None)()
            if auth_resp is not None and getattr(auth_resp, 'status_code', None) == 401:
                status = 'published'
            else:
                role = getattr(request, 'user_role', None)
                user_id = getattr(request, 'user_id', None)
        if role not in ('editor', 'admin'):
            status = 'published'
    if not status:
        status = 'published'

    cache_key = f"articles:list:{page}:{size}:{status or '_'}:{tag or '_'}:{category or '_'}"
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            try:
                payload = json.loads(cached)
                if CACHE_HIT_TOTAL:
                    try:
                        CACHE_HIT_TOTAL.labels('articles_list_internal').inc()
                    except Exception:
                        pass
                etag = compute_etag(payload)
                if request.headers.get('If-None-Match') == etag:
                    return ('', 304, {'ETag': etag})
                resp = jsonify({'code': 0, 'data': payload, 'message': 'ok'})
                resp.headers['ETag'] = etag
                return resp
            except Exception:
                pass
        else:
            if CACHE_MISS_TOTAL:
                try:
                    CACHE_MISS_TOTAL.labels('articles_list_internal').inc()
                except Exception:
                    pass

    from ..models import Tag
    q = Article.query.filter_by(deleted=False)
    if status:
        q = q.filter_by(status=status)
    if tag:
        q = q.join(Article.tags).filter(Tag.slug == tag)
    if category:
        q = q.filter(Article.category_id == category)
    total = q.count()
    items = q.order_by(Article.created_at.desc()).offset((page - 1) * size).limit(size).all()
    payload = {
        'total': total, 'page': page, 'page_size': size,
        'has_next': page * size < total,
        'list': serialize_articles_batch(items),
    }

    etag = compute_etag(payload)
    if request.headers.get('If-None-Match') == etag:
        return ('', 304, {'ETag': etag})
    if redis_client:
        try:
            cache_track_set(cache_key, current_app.config['CACHE_ARTICLE_LIST_TTL'], json.dumps(payload))
        except Exception:
            pass
    resp = jsonify({'code': 0, 'data': payload, 'message': 'ok'})
    resp.headers['ETag'] = etag
    return resp


# ─── Slug 访问 ────────────────────────────────────────────

@articles_bp.route('/slug/<slug>', methods=['GET'])
def get_article_by_slug(slug):
    cache_key = f"article:slug:{slug}"
    article = Article.query.filter_by(slug=slug, deleted=False).first()
    if not article:
        return jsonify({'code': 4040, 'message': 'not found'}), 404

    if article.status != 'published':
        role = getattr(request, 'user_role', None)
        user_id = getattr(request, 'user_id', None)
        if role is None:
            from .. import require_auth as _rq
            auth_resp = _rq(lambda: None)()
            if auth_resp is None:
                role = getattr(request, 'user_role', None)
                user_id = getattr(request, 'user_id', None)
        if not check_article_visibility(article, role, user_id):
            return jsonify({'code': 4040, 'message': 'not found'}), 404

    data = serialize_article(article, detail=True, include_user_flags=True, user_id=getattr(request, 'user_id', None))
    if redis_client and article.status == 'published':
        try:
            cache_track_set(cache_key, current_app.config['CACHE_ARTICLE_DETAIL_TTL'], json.dumps(data))
        except Exception:
            pass
    etag = compute_etag(data)
    if request.headers.get('If-None-Match') == etag:
        return ('', 304, {'ETag': etag})
    resp = jsonify({'code': 0, 'data': data, 'message': 'ok'})
    resp.headers['ETag'] = etag
    return resp


# ─── 点赞 / 收藏 ──────────────────────────────────────────

@articles_bp.route('/<int:article_id>/like', methods=['POST'])
@require_auth
@limiter.limit('30/minute')
def like_toggle_route(article_id):
    try:
        action, count = toggle_like(article_id, request.user_id)
        return jsonify({'code': 0, 'data': {'action': action, 'likes_count': count}, 'message': 'ok'})
    except BusinessError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.http_status


@articles_bp.route('/<int:article_id>/bookmark', methods=['POST'])
@require_auth
@limiter.limit('30/minute')
def bookmark_toggle_route(article_id):
    try:
        action, count = toggle_bookmark(article_id, request.user_id)
        return jsonify({'code': 0, 'data': {'action': action, 'bookmarks_count': count}, 'message': 'ok'})
    except BusinessError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.http_status


@articles_bp.route('/bookmarks', methods=['GET'])
@require_auth
def list_bookmarks():
    from ..models import ArticleBookmark
    page = int(request.args.get('page', 1))
    size = min(int(request.args.get('page_size', 10)), 50)
    q = Article.query.join(ArticleBookmark, Article.id == ArticleBookmark.article_id) \
        .filter(ArticleBookmark.user_id == request.user_id, Article.deleted == False)
    total = q.count()
    items = q.order_by(ArticleBookmark.created_at.desc()).offset((page - 1) * size).limit(size).all()
    payload = {
        'total': total, 'page': page, 'page_size': size,
        'has_next': page * size < total,
        'list': serialize_articles_batch(items),
    }
    return jsonify({'code': 0, 'data': payload, 'message': 'ok'})


# ─── 版本控制 ─────────────────────────────────────────────

@articles_bp.route('/<int:article_id>/versions', methods=['GET'])
@require_auth
def list_versions(article_id):
    article = Article.query.get_or_404(article_id)
    if article.author_id != request.user_id and request.user_role not in ('editor', 'admin'):
        return jsonify({'code': 4030, 'message': 'forbidden'}), 403
    detail = request.args.get('detail') == '1'
    versions = ArticleVersion.query.filter_by(article_id=article_id).order_by(ArticleVersion.version_no.desc()).all()
    data = []
    for v in versions:
        item = {'id': v.id, 'version_no': v.version_no, 'created_at': v.created_at.isoformat() + 'Z'}
        if detail:
            item['content_md'] = v.content_md
            item['content_html'] = v.content_html
        data.append(item)
    return jsonify({'code': 0, 'data': data, 'message': 'ok'})


@articles_bp.route('/<int:article_id>/versions', methods=['POST'])
@require_auth
def create_version_route(article_id):
    article = Article.query.get_or_404(article_id)
    if article.author_id != request.user_id and request.user_role not in ('editor', 'admin'):
        return jsonify({'code': 4030, 'message': 'forbidden'}), 403
    next_no = create_version_snapshot(article, request.user_id)
    return jsonify({'code': 0, 'data': {'version_no': next_no}, 'message': 'ok'}), 201


@articles_bp.route('/<int:article_id>/versions/<int:version_no>', methods=['GET'])
@require_auth
def get_version(article_id, version_no):
    article = Article.query.get_or_404(article_id)
    if article.author_id != request.user_id and request.user_role not in ('editor', 'admin'):
        return jsonify({'code': 4030, 'message': 'forbidden'}), 403
    v = ArticleVersion.query.filter_by(article_id=article_id, version_no=version_no).first()
    if not v:
        return jsonify({'code': 4040, 'message': 'version not found'}), 404
    data = {
        'id': v.id, 'version_no': v.version_no,
        'created_at': v.created_at.isoformat() + 'Z',
        'content_md': v.content_md, 'content_html': v.content_html,
    }
    return jsonify({'code': 0, 'data': data, 'message': 'ok'})


@articles_bp.route('/<int:article_id>/versions/<int:version_no>/rollback', methods=['POST'])
@require_auth
def rollback_version_route(article_id, version_no):
    article = Article.query.get_or_404(article_id)
    if article.author_id != request.user_id and request.user_role not in ('editor', 'admin'):
        return jsonify({'code': 4030, 'message': 'forbidden'}), 403
    try:
        new_no, target_no = rollback_to_version(article, version_no, request.user_id)
        return jsonify({'code': 0, 'data': {'rolled_back_to': target_no, 'new_version_no': new_no}, 'message': 'ok'})
    except BusinessError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.http_status


@articles_bp.route('/<int:article_id>/versions/<int:version_no>/diff', methods=['GET'])
@require_auth
def diff_version_route(article_id, version_no):
    target_no = request.args.get('target')
    if not target_no or not target_no.isdigit():
        return jsonify({'code': 4001, 'message': 'target version required'}), 400
    target_no = int(target_no)
    if target_no == version_no:
        return jsonify({'code': 4002, 'message': 'same version'}), 400

    article = Article.query.get_or_404(article_id)
    if article.author_id != request.user_id and request.user_role not in ('editor', 'admin'):
        return jsonify({'code': 4030, 'message': 'forbidden'}), 403

    diff = diff_versions(article_id, version_no, target_no)
    return jsonify({'code': 0, 'data': {'from': version_no, 'to': target_no, 'diff': diff}, 'message': 'ok'})


# ─── 工作流 ───────────────────────────────────────────────

@articles_bp.route('/<int:article_id>/approve', methods=['POST'])
@permission_required('workflow:approve')
@workflow_transition(lambda article_id: Article.query.get(article_id), target_status='published')
def approve_article_route(article_id, article):
    try:
        svc_approve(article, request.user_id)
        return jsonify({'code': 0, 'data': {
            'id': article.id, 'status': article.status,
            'published_at': article.published_at.isoformat() + 'Z' if article.published_at else None,
        }, 'message': 'ok'})
    except BusinessError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.http_status


@articles_bp.route('/<int:article_id>/reject', methods=['POST'])
@permission_required('workflow:reject')
@workflow_transition(lambda article_id: Article.query.get(article_id), target_status='draft')
def reject_article_route(article_id, article):
    try:
        data = request.get_json() or {}
        reason = (data.get('reason') or '').strip()
        svc_reject(article, reason, request.user_id)
        return jsonify({'code': 0, 'data': {
            'id': article.id, 'status': article.status, 'reject_reason': article.reject_reason,
        }, 'message': 'ok'})
    except BusinessError as e:
        return jsonify({'code': e.code, 'message': e.message, 'data': e.data}), e.http_status


@articles_bp.route('/<int:article_id>/submit', methods=['POST'])
@permission_required('workflow:submit')
@workflow_transition(lambda article_id: Article.query.get(article_id), target_status='pending')
def submit_article_route(article_id, article):
    try:
        svc_submit(article, request.user_id)
        return jsonify({'code': 0, 'data': {'id': article.id, 'status': article.status}, 'message': 'ok'})
    except BusinessError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.http_status


@articles_bp.route('/<int:article_id>/schedule', methods=['POST'])
@permission_required('workflow:submit')
@workflow_transition(lambda article_id: Article.query.get(article_id), target_status='scheduled')
def schedule_article_route(article_id, article):
    try:
        data = request.get_json() or {}
        raw = data.get('scheduled_at')
        if not raw:
            return jsonify({'code': 4001, 'message': 'validation_error', 'data': {'field': 'scheduled_at'}}), 400
        dt = parse_dt(raw)
        if not dt:
            return jsonify({'code': 4001, 'message': 'validation_error', 'data': {'field': 'scheduled_at', 'reason': 'invalid datetime'}}), 400
        svc_schedule(article, dt, request.user_id, request.user_role)
        return jsonify({'code': 0, 'data': {
            'id': article.id, 'status': article.status,
            'scheduled_at': article.scheduled_at.isoformat() + 'Z',
        }, 'message': 'ok'})
    except BusinessError as e:
        return jsonify({'code': e.code, 'message': e.message, 'data': e.data}), e.http_status


@articles_bp.route('/<int:article_id>/unschedule', methods=['POST'])
@permission_required('workflow:submit')
@workflow_transition(lambda article_id: Article.query.get(article_id), target_status='draft')
def unschedule_article_route(article_id, article):
    try:
        svc_unschedule(article, request.user_id, request.user_role)
        return jsonify({'code': 0, 'data': {'id': article.id, 'status': article.status}, 'message': 'ok'})
    except BusinessError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.http_status


@articles_bp.route('/<int:article_id>/unpublish', methods=['POST'])
@permission_required('workflow:publish')
@workflow_transition(lambda article_id: Article.query.get(article_id), target_status='draft')
def unpublish_article_route(article_id, article):
    try:
        svc_unpublish(article, request.user_id)
        return jsonify({'code': 0, 'data': {'id': article.id, 'status': article.status}, 'message': 'ok'})
    except BusinessError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.http_status


# ─── 删除 ─────────────────────────────────────────────────

@articles_bp.route('/<int:article_id>', methods=['DELETE'])
@permission_required('articles:delete')
def delete_article_route(article_id):
    article = Article.query.get_or_404(article_id)
    try:
        svc_delete(article, request.user_id)
        return jsonify({'code': 0, 'data': {'id': article.id, 'deleted': True}, 'message': 'ok'})
    except BusinessError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.http_status


# ─── 审计日志 ─────────────────────────────────────────────

@articles_bp.route('/<int:article_id>/audit_logs', methods=['GET'])
@require_roles('editor', 'admin')
def list_audit_logs(article_id):
    Article.query.get_or_404(article_id)
    logs = AuditLog.query.filter_by(article_id=article_id).order_by(AuditLog.created_at.asc()).all()
    data = [{'id': l.id, 'action': l.action, 'note': l.note, 'operator_id': l.operator_id,
             'created_at': l.created_at.isoformat() + 'Z'} for l in logs]
    return jsonify({'code': 0, 'message': 'ok', 'data': data})


# ─── 公开接口 ─────────────────────────────────────────────

@articles_bp.route('/public/', methods=['GET'])
def public_list_articles():
    page = int(request.args.get('page', 1))
    size = min(int(request.args.get('page_size', 10)), 50)
    tag = request.args.get('tag')
    category_id = request.args.get('category_id')
    author_id = request.args.get('author_id')
    sort = request.args.get('sort', 'published_at:desc')
    sort_field, _, sort_dir = sort.partition(':')
    if sort_field not in ('published_at', 'created_at'):
        sort_field = 'published_at'
    desc = (sort_dir or 'desc').lower() != 'asc'

    cache_key = f"public:articles:list:{page}:{size}:{tag or '_'}:{category_id or '_'}:{author_id or '_'}:{sort_field}:{'d' if desc else 'a'}"
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            payload = json.loads(cached)
            if CACHE_HIT_TOTAL:
                try:
                    CACHE_HIT_TOTAL.labels('public_article_list').inc()
                except Exception:
                    pass
            etag = compute_etag(payload)
            if request.headers.get('If-None-Match') == etag:
                return ('', 304, {'ETag': etag})
            resp = jsonify({'code': 0, 'message': 'ok', 'data': payload})
            resp.headers['ETag'] = etag
            return resp
        else:
            if CACHE_MISS_TOTAL:
                try:
                    CACHE_MISS_TOTAL.labels('public_article_list').inc()
                except Exception:
                    pass

    from ..models import Tag
    q = Article.query.filter_by(deleted=False, status='published')
    if tag:
        q = q.join(Article.tags).filter(Tag.slug == tag)
    if category_id:
        q = q.filter(Article.category_id == category_id)
    if author_id:
        q = q.filter(Article.author_id == author_id)
    total = q.count()
    order_col = Article.published_at if sort_field == 'published_at' else Article.created_at
    order_col = order_col.desc() if desc else order_col
    items = q.order_by(order_col).offset((page - 1) * size).limit(size).all()

    data_payload = {
        'total': total, 'page': page, 'page_size': size,
        'has_next': page * size < total,
        'list': serialize_articles_batch(items),
    }
    if redis_client:
        try:
            cache_track_set(cache_key, current_app.config['CACHE_PUBLIC_LIST_TTL'], json.dumps(data_payload))
        except Exception:
            pass
    etag = compute_etag(data_payload)
    if request.headers.get('If-None-Match') == etag:
        return ('', 304, {'ETag': etag})
    resp = jsonify({'code': 0, 'message': 'ok', 'data': data_payload})
    resp.headers['ETag'] = etag
    return resp


@articles_bp.route('/public/slug/<slug>', methods=['GET'])
def public_article_by_slug(slug):
    cache_key = f"public:article:slug:{slug}"
    user_id = None
    try:
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            import jwt as _jwt
            token = auth.split(' ', 1)[1]
            payload = _jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            user_id = int(payload.get('sub', 0)) or None
    except Exception:
        user_id = None

    if redis_client and not user_id:
        cached = redis_client.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                etag = compute_etag(data)
                if request.headers.get('If-None-Match') == etag:
                    return ('', 304, {'ETag': etag})
                resp = jsonify({'code': 0, 'message': 'ok', 'data': data})
                resp.headers['ETag'] = etag
                return resp
            except Exception:
                pass

    article = Article.query.filter_by(slug=slug, deleted=False).first()
    if not article:
        return jsonify({'code': 4040, 'message': 'not found'}), 404

    incremented = False
    new_views = article.views_count
    try:
        if redis_client:
            fp = _view_fingerprint()
            vkey = f"article:view:{article.id}:{fp}"
            if redis_client.set(vkey, '1', ex=3600, nx=True):
                Article.query.filter_by(id=article.id).update({Article.views_count: Article.views_count + 1})
                db.session.commit()
                incremented = True
        else:
            Article.query.filter_by(id=article.id).update({Article.views_count: Article.views_count + 1})
            db.session.commit()
            incremented = True
    except Exception:
        db.session.rollback()
    if incremented:
        new_views = (article.views_count or 0) + 1

    data = serialize_article(article, detail=True, include_user_flags=True, user_id=user_id)
    if new_views is not None:
        data['views_count'] = new_views

    if redis_client and not user_id:
        try:
            cache_track_set(cache_key, current_app.config['CACHE_PUBLIC_ARTICLE_TTL'], json.dumps(data))
        except Exception:
            pass
    etag = compute_etag(data)
    if request.headers.get('If-None-Match') == etag:
        return ('', 304, {'ETag': etag})
    resp = jsonify({'code': 0, 'message': 'ok', 'data': data})
    resp.headers['ETag'] = etag
    return resp


@articles_bp.route('/public/hot', methods=['GET'])
def public_hot_articles():
    try:
        page = int(request.args.get('page', 1))
        size = min(int(request.args.get('page_size', 10)), 50)
        start = (page - 1) * size
        from sqlalchemy import case

        articles = (Article.query.filter_by(deleted=False, status='published')
                    .order_by(case(
                        (Article.views_count.is_(None), 0),
                        else_=Article.views_count
                    ).desc())
                    .offset(start).limit(size).all())
        total = Article.query.filter_by(deleted=False, status='published').count()

        data_list = serialize_articles_batch(articles)
        for item in data_list:
            views = item.get('views_count', 0) or 0
            item['views_count'] = views
            item['likes_count'] = 0
            item['score'] = views

        payload = {
            'total': total, 'page': page, 'page_size': size,
            'has_next': start + size < total,
            'list': data_list,
        }
        return jsonify({'code': 0, 'message': 'ok', 'data': payload})
    except Exception as e:
        current_app.logger.error(f"Hot articles API failed: {e}")
        return jsonify({'code': 0, 'message': 'ok', 'data': {
            'total': 0, 'page': page if 'page' in locals() else 1,
            'page_size': size if 'size' in locals() else 10,
            'has_next': False, 'list': [],
        }})


# 保留测试/调试端点
@articles_bp.route('/public/hot-test', methods=['GET'])
def public_hot_articles_test():
    try:
        count = Article.query.filter_by(deleted=False, status='published').count()
        return jsonify({'code': 0, 'message': f'Found {count} articles', 'data': {'count': count}})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@articles_bp.route('/public/hot-simple', methods=['GET'])
def public_hot_articles_simple():
    try:
        page = int(request.args.get('page', 1))
        size = min(int(request.args.get('page_size', 10)), 50)
        from sqlalchemy import case
        articles = (Article.query.filter_by(deleted=False, status='published')
                    .order_by(case(
                        (Article.views_count.is_(None), 0),
                        else_=Article.views_count
                    ).desc()).limit(size).all())
        data_list = []
        for a in articles:
            data_list.append({
                'id': a.id, 'title': a.title, 'slug': a.slug,
                'summary': a.summary or '', 'views_count': getattr(a, 'views_count', 0) or 0,
                'likes_count': 0, 'score': getattr(a, 'views_count', 0) or 0,
            })
        payload = {'total': len(data_list), 'page': page, 'page_size': size, 'has_next': False, 'list': data_list}
        return jsonify({'code': 0, 'message': 'ok', 'data': payload})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500
