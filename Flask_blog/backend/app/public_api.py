from flask import Blueprint, request, jsonify
from .models import Article, Category, Tag
from . import redis_client, db
from .utils import compute_etag
from datetime import datetime

public_bp = Blueprint('public_api', __name__)

# 只读列表：已发布 + 未删除

def _serialize_article_brief(a: Article, user_id=None):
    from .models import ArticleLike, ArticleBookmark  # 导入模型
    
    # 正确计算点赞数
    likes_count = ArticleLike.query.filter_by(article_id=a.id).count()
    
    data = {
        'id': a.id,
        'title': a.title,
        'slug': a.slug,
        'summary': a.summary,
        'published_at': a.published_at.isoformat() if a.published_at else None,
        'featured_image': a.featured_image,
        'category_id': a.category_id,
        'tags': [t.slug for t in a.tags],
        'views_count': a.views_count,
        'likes_count': likes_count,
        # 添加作者信息
        'author': {
            'id': a.author.id,
            'name': a.author.nickname or a.author.username,
            'bio': a.author.bio,
            'avatar': a.author.avatar
        } if a.author else None
    }
    
    # 如果用户已登录，添加用户特定的状态
    if user_id:
        try:
            data['liked'] = ArticleLike.query.filter_by(article_id=a.id, user_id=user_id).first() is not None
            data['bookmarked'] = ArticleBookmark.query.filter_by(article_id=a.id, user_id=user_id).first() is not None
        except Exception:
            data['liked'] = False
            data['bookmarked'] = False
    else:
        data['liked'] = False
        data['bookmarked'] = False
    
    return data

def _serialize_article_detail(a: Article, user_id=None):
    data = _serialize_article_brief(a, user_id)
    data['content_html'] = a.content_html
    data['seo_title'] = a.seo_title
    data['seo_desc'] = a.seo_desc
    return data

@public_bp.route('/articles', methods=['GET'])
def public_articles():
    page = int(request.args.get('page', 1))
    size = min(int(request.args.get('page_size', 20)), 50)
    category_id = request.args.get('category_id', type=int)
    tag = request.args.get('tag')
    cache_key = f"public:articles:list:{page}:{size}:{category_id or 'all'}:{tag or 'all'}"
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            import json
            try:
                payload = json.loads(cached)
                etag = compute_etag(payload)
                if request.headers.get('If-None-Match') == etag:
                    return ('',304,{'ETag': etag})
                resp = jsonify({'code':0,'message':'ok','data':payload})
                resp.headers['ETag'] = etag
                return resp
            except Exception:
                pass
    q = Article.query.filter_by(status='published', deleted=False)
    if category_id:
        q = q.filter(Article.category_id==category_id)
    if tag:
        q = q.join(Article.tags).filter(Tag.slug==tag)
    total = q.count()
    items = q.order_by(Article.published_at.desc()).offset((page-1)*size).limit(size).all()
    
    # 获取可选的用户认证信息
    user_id = None
    try:
        user_id = getattr(request, 'user_id', None)
    except Exception:
        user_id = None
    
    data_list = [_serialize_article_brief(a, user_id) for a in items]
    payload = {'total': total,'page':page,'page_size':size,'has_next':page*size<total,'list':data_list}
    if redis_client:
        try:
            import json
            redis_client.setex(cache_key, 120, json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass
    etag = compute_etag(payload)
    if request.headers.get('If-None-Match') == etag:
        return ('',304,{'ETag':etag})
    resp = jsonify({'code':0,'message':'ok','data':payload})
    resp.headers['ETag'] = etag
    return resp

@public_bp.route('/articles/<slug_or_id>', methods=['GET'])
def public_article_detail(slug_or_id):
    cache_key = f"public:article:{slug_or_id}"
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            import json
            try:
                data = json.loads(cached)
                etag = compute_etag(data)
                if request.headers.get('If-None-Match') == etag:
                    return ('',304,{'ETag':etag})
                resp = jsonify({'code':0,'message':'ok','data':data})
                resp.headers['ETag'] = etag
                return resp
            except Exception:
                pass
    from .models import Article
    a = None
    if slug_or_id.isdigit():
        a = Article.query.filter_by(id=int(slug_or_id), status='published', deleted=False).first()
    if not a:
        a = Article.query.filter_by(slug=slug_or_id, status='published', deleted=False).first()
    if not a:
        return jsonify({'code':4040,'message':'not found'}), 404
    
    # 尝试获取用户认证信息（支持可选认证）
    user_id = None
    try:
        user_id = getattr(request, 'user_id', None)
        if user_id is None:
            # 如果没有用户ID，尝试进行认证（不强制）
            from . import require_auth as _rq
            auth_resp = _rq()
            if auth_resp is None:  # 认证成功
                user_id = getattr(request, 'user_id', None)
    except Exception:
        # 认证失败不影响公共API访问
        user_id = None
    
    data = _serialize_article_detail(a, user_id)
    
    # 不缓存包含用户特定信息的响应
    cache_data = user_id is None
    if cache_data and redis_client:
        try:
            import json
            redis_client.setex(cache_key, 300, json.dumps(data, ensure_ascii=False))
        except Exception:
            pass
    etag = compute_etag(data)
    if request.headers.get('If-None-Match') == etag:
        return ('',304,{'ETag':etag})
    resp = jsonify({'code':0,'message':'ok','data':data})
    resp.headers['ETag'] = etag
    return resp

@public_bp.route('/taxonomy', methods=['GET'])
def public_taxonomy():
    from .models import Category, Tag, ArticleTag
    from sqlalchemy import func, and_
    
    # 添加调试信息
    print(f'[DEBUG] 开始查询分类和标签数据')
    
    # 获取分类及其文章数量（只统计已发布的文章）
    categories_with_count = db.session.query(
        Category.id, Category.name, Category.slug, Category.parent_id,
        func.count(Article.id).label('article_count')
    ).outerjoin(Article, and_(
        Category.id == Article.category_id,
        Article.deleted != True,
        Article.status == 'published'  # 只统计已发布的文章
    )).group_by(Category.id, Category.name, Category.slug, Category.parent_id)\
     .order_by(Category.id.asc()).all()
    
    # 获取标签及其文章数量（只统计已发布的文章）
    tags_with_count = db.session.query(
        Tag.id, Tag.name, Tag.slug,
        func.count(ArticleTag.article_id).label('article_count')
    ).outerjoin(ArticleTag, Tag.id == ArticleTag.tag_id)\
     .outerjoin(Article, and_(
        ArticleTag.article_id == Article.id,
        Article.deleted != True,
        Article.status == 'published'  # 只统计已发布的文章
    )).group_by(Tag.id, Tag.name, Tag.slug)\
     .order_by(Tag.id.asc()).all()
    
    print(f'[DEBUG] 查询到分类数量: {len(categories_with_count)}')
    print(f'[DEBUG] 查询到标签数量: {len(tags_with_count)}')
    
    if len(categories_with_count) > 0:
        print(f'[DEBUG] 前3个分类: {[(c.id, c.name, c.slug, c.article_count) for c in categories_with_count[:3]]}')
    
    data = {
        'categories': [{
            'id': c.id,
            'name': c.name,
            'slug': c.slug,
            'parent_id': c.parent_id,
            'article_count': c.article_count,
            'description': None  # 可以后续扩展分类描述字段
        } for c in categories_with_count],
        'tags': [{
            'id': t.id,
            'name': t.name,
            'slug': t.slug,
            'article_count': t.article_count
        } for t in tags_with_count]
    }
    
    print(f'[DEBUG] 最终数据结构: categories={len(data["categories"])}, tags={len(data["tags"])}')
    
    etag = compute_etag(data)
    if request.headers.get('If-None-Match') == etag:
        return ('',304,{'ETag':etag})
    resp = jsonify({'code':0,'message':'ok','data':data})
    resp.headers['ETag'] = etag
    return resp
