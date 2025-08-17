from flask import Blueprint, request, jsonify
from .. import db, require_auth, require_roles, redis_client, METRICS_ENABLED, PUBLIC_AUTHOR_PROFILE_REQUESTS_TOTAL, PUBLIC_AUTHOR_ARTICLES_REQUESTS_TOTAL, PUBLIC_AUTHOR_ARTICLES_ZERO_RESULT_TOTAL, CACHE_HIT_TOTAL, CACHE_MISS_TOTAL
from ..models import User, Article
from ..utils import compute_etag
import json

users_bp = Blueprint('users', __name__)

class ProfileUpdateModel:
    nickname: str | None = None
    bio: str | None = None
    avatar: str | None = None
    social_links: dict | None = None  # 存 JSON
    @classmethod
    def nick_ok(cls, v):
        if v and len(v) > 80:
            raise ValueError('nickname too long')
        return v
    @classmethod
    def bio_ok(cls, v):
        if v and len(v) > 2000:
            raise ValueError('bio too long')
        return v
class RoleUpdateModel:
    role: str
    @classmethod
    def role_ok(cls, v):
        if v not in ('author','editor','admin'):
            raise ValueError('invalid role')
        return v


def serialize_user(u: User, include_email=False):
    data = {
        'id': u.id,
        'role': u.role,
        'nickname': u.nickname,
        'bio': u.bio,
        'avatar': u.avatar,
    }
    if u.social_links:
        try:
            data['social_links'] = json.loads(u.social_links)
        except Exception:
            data['social_links'] = None
    if include_email:
        data['email'] = u.email
    return data

@users_bp.route('/me', methods=['GET'])
@require_auth
def me():
    u = User.query.get_or_404(request.user_id)
    return jsonify({'code':0,'message':'ok','data':serialize_user(u, include_email=True)})

@users_bp.route('/me', methods=['PATCH'])
@require_auth
def update_me():
    data = request.get_json() or {}
    try:
        parsed = ProfileUpdateModel(**data)
    except Exception as ve:
        return jsonify({'code':4001,'message':'validation error','data':ve.errors()}), 400
    u = User.query.get_or_404(request.user_id)
    for f in ['nickname','bio','avatar']:
        if hasattr(parsed, f) and getattr(parsed, f) is not None:
            setattr(u, f, getattr(parsed,f))
    if hasattr(parsed,'social_links') and parsed.social_links is not None:
        try:
            u.social_links = json.dumps(parsed.social_links, ensure_ascii=False)
        except Exception:
            return jsonify({'code':4001,'message':'invalid social_links'}), 400
    db.session.commit()
    return jsonify({'code':0,'message':'ok','data':serialize_user(u, include_email=True)})

@users_bp.route('/', methods=['GET'])
@require_roles('admin')
def list_users():
    page = int(request.args.get('page',1))
    size = min(int(request.args.get('page_size',20)),100)
    cache_key = f"users:list:{page}:{size}"
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            try:
                payload = json.loads(cached)
                try:
                    from .. import CACHE_HIT_TOTAL
                    if CACHE_HIT_TOTAL:
                        CACHE_HIT_TOTAL.labels('users_list_admin').inc()
                except Exception:
                    pass
                etag = compute_etag(payload)
                if request.headers.get('If-None-Match') == etag:
                    return ('',304,{'ETag': etag})
                resp = jsonify({'code':0,'message':'ok','data':payload})
                resp.headers['ETag'] = etag
                return resp
            except Exception:
                pass
        else:
            try:
                from .. import CACHE_MISS_TOTAL
                if CACHE_MISS_TOTAL:
                    CACHE_MISS_TOTAL.labels('users_list_admin').inc()
            except Exception:
                pass
    q = User.query
    total = q.count()
    users = q.order_by(User.id.asc()).offset((page-1)*size).limit(size).all()
    payload = {'total':total,'page':page,'page_size':size,'has_next':page*size<total,'list':[serialize_user(u, include_email=True) for u in users]}
    etag = compute_etag(payload)
    if request.headers.get('If-None-Match') == etag:
        return ('',304,{'ETag': etag})
    if redis_client:
        try:
            redis_client.setex(cache_key, 120, json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass
    resp = jsonify({'code':0,'message':'ok','data':payload})
    resp.headers['ETag'] = etag
    return resp

@users_bp.route('/<int:user_id>/role', methods=['PATCH'])
@require_roles('admin')
def change_role(user_id):
    data = request.get_json() or {}
    try:
        parsed = RoleUpdateModel(**data)
    except Exception as ve:
        return jsonify({'code':4001,'message':'validation error','data':ve.errors()}), 400
    u = User.query.get_or_404(user_id)
    old = u.role
    u.role = parsed.role
    db.session.commit()
    return jsonify({'code':0,'message':'ok','data':{'id':u.id,'old_role':old,'new_role':u.role}})

@users_bp.route('/public/<int:user_id>', methods=['GET'])
def public_author_profile(user_id):
    """公开作者资料：仅返回非敏感字段与已发布文章统计（带缓存）。"""
    if METRICS_ENABLED and PUBLIC_AUTHOR_PROFILE_REQUESTS_TOTAL:
        try: PUBLIC_AUTHOR_PROFILE_REQUESTS_TOTAL.inc()
        except Exception: pass
    cache_key = f"public:author:{user_id}"
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                if CACHE_HIT_TOTAL:
                    try: CACHE_HIT_TOTAL.labels('public_author_profile').inc()
                    except Exception: pass
                etag = compute_etag(data)
                if request.headers.get('If-None-Match') == etag:
                    return ('',304,{'ETag': etag})
                resp = jsonify({'code':0,'message':'ok','data':data})
                resp.headers['ETag'] = etag
                return resp
            except Exception:
                pass
        else:
            if CACHE_MISS_TOTAL:
                try: CACHE_MISS_TOTAL.labels('public_author_profile').inc()
                except Exception: pass
    u = User.query.get_or_404(user_id)
    pub_count = Article.query.filter_by(author_id=u.id, status='published', deleted=False).count()
    data = serialize_user(u, include_email=False)
    data['published_articles'] = pub_count
    if redis_client:
        try: redis_client.setex(cache_key, 300, json.dumps(data, ensure_ascii=False))
        except Exception: pass
    etag = compute_etag(data)
    if request.headers.get('If-None-Match') == etag:
        return ('',304,{'ETag': etag})
    resp = jsonify({'code':0,'message':'ok','data':data})
    resp.headers['ETag'] = etag
    return resp

@users_bp.route('/public/<int:user_id>/articles', methods=['GET'])
def public_author_articles(user_id):
    """公开作者已发布文章列表。支持分页 & sort(published_at desc|asc)，带缓存和指标。"""
    page = int(request.args.get('page',1))
    size = min(int(request.args.get('page_size',10)),50)
    sort = request.args.get('sort','published_at:desc')
    sort_field, _, sort_dir = sort.partition(':')
    if sort_field not in ('published_at','created_at'):
        sort_field = 'published_at'
    desc = (sort_dir or 'desc').lower() != 'asc'
    if METRICS_ENABLED and PUBLIC_AUTHOR_ARTICLES_REQUESTS_TOTAL:
        try: PUBLIC_AUTHOR_ARTICLES_REQUESTS_TOTAL.inc()
        except Exception: pass
    cache_key = f"public:author_articles:{user_id}:{page}:{size}:{sort_field}:{'d' if desc else 'a'}"
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            try:
                payload = json.loads(cached)
                if CACHE_HIT_TOTAL:
                    try: CACHE_HIT_TOTAL.labels('public_author_articles').inc()
                    except Exception: pass
                etag = compute_etag(payload)
                if request.headers.get('If-None-Match') == etag:
                    return ('',304,{'ETag': etag})
                resp = jsonify({'code':0,'message':'ok','data':payload})
                resp.headers['ETag'] = etag
                return resp
            except Exception:
                pass
        else:
            if CACHE_MISS_TOTAL:
                try: CACHE_MISS_TOTAL.labels('public_author_articles').inc()
                except Exception: pass
    q = Article.query.filter_by(author_id=user_id, status='published', deleted=False)
    total = q.count()
    if total == 0 and METRICS_ENABLED and PUBLIC_AUTHOR_ARTICLES_ZERO_RESULT_TOTAL:
        try: PUBLIC_AUTHOR_ARTICLES_ZERO_RESULT_TOTAL.inc()
        except Exception: pass
    col = Article.published_at if sort_field=='published_at' else Article.created_at
    if desc:
        col = col.desc()
    items = q.order_by(col).offset((page-1)*size).limit(size).all()
    from ..articles.routes import serialize_article
    data_list = [serialize_article(a) for a in items]
    payload = {'total':total,'page':page,'page_size':size,'has_next':page*size<total,'list':data_list}
    if redis_client:
        try: redis_client.setex(cache_key, 120, json.dumps(payload, ensure_ascii=False))
        except Exception: pass
    etag = compute_etag(payload)
    if request.headers.get('If-None-Match') == etag:
        return ('',304,{'ETag': etag})
    resp = jsonify({'code':0,'message':'ok','data':payload})
    resp.headers['ETag'] = etag
    return resp

@users_bp.route('/public/<int:user_id>/stats', methods=['GET'])
def public_author_stats(user_id):
    """作者公开统计：文章数 / 总浏览 / 总点赞 / 最近发布时间。使用轻缓存。"""
    cache_key = f"public:author_stats:{user_id}"
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            try:
                payload = json.loads(cached)
                etag = compute_etag(payload)
                if request.headers.get('If-None-Match') == etag:
                    return ('',304,{'ETag':etag})
                r = jsonify({'code':0,'message':'ok','data':payload})
                r.headers['ETag'] = etag
                return r
            except Exception:
                pass
    u = User.query.get_or_404(user_id)
    q = Article.query.filter_by(author_id=u.id, status='published', deleted=False)
    articles = q.with_entities(Article.id, Article.published_at, Article.views_count).all()
    article_ids = [row.id for row in articles]
    from ..models import ArticleLike
    likes_total = 0
    if article_ids:
        likes_total = ArticleLike.query.filter(ArticleLike.article_id.in_(article_ids)).count()
    total_views = sum(row.views_count or 0 for row in articles)
    last_pub = None
    if articles:
        last_pub = max([row.published_at for row in articles if row.published_at])
    payload = {
        'articles_count': len(article_ids),
        'total_views': total_views,
        'total_likes': likes_total,
        'last_published_at': last_pub.isoformat() if last_pub else None
    }
    if redis_client:
        try: redis_client.setex(cache_key, 120, json.dumps(payload, ensure_ascii=False))
        except Exception: pass
    etag = compute_etag(payload)
    if request.headers.get('If-None-Match') == etag:
        return ('',304,{'ETag':etag})
    r = jsonify({'code':0,'message':'ok','data':payload})
    r.headers['ETag'] = etag
    return r
