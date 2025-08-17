from flask import Blueprint, request, jsonify
from .models import Article, Category, Tag
from . import redis_client
from .utils import compute_etag
from datetime import datetime

public_bp = Blueprint('public_api', __name__)

# 只读列表：已发布 + 未删除

def _serialize_article_brief(a: Article):
    return {
        'id': a.id,
        'title': a.title,
        'slug': a.slug,
        'summary': a.summary,
        'published_at': a.published_at.isoformat() if a.published_at else None,
        'featured_image': a.featured_image,
        'category_id': a.category_id,
        'tags': [t.slug for t in a.tags],
        'views_count': a.views_count,
        'likes_count': 0  # 可选: 延迟查询或单独计数
    }

def _serialize_article_detail(a: Article):
    data = _serialize_article_brief(a)
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
    data_list = [_serialize_article_brief(a) for a in items]
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
    data = _serialize_article_detail(a)
    if redis_client:
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
    from .models import Category, Tag
    cats = Category.query.order_by(Category.id.asc()).all()
    tags = Tag.query.order_by(Tag.id.asc()).all()
    data = {
        'categories': [{'id':c.id,'name':c.name,'slug':c.slug,'parent_id':c.parent_id} for c in cats],
        'tags': [{'id':t.id,'name':t.name,'slug':t.slug} for t in tags]
    }
    etag = compute_etag(data)
    if request.headers.get('If-None-Match') == etag:
        return ('',304,{'ETag':etag})
    resp = jsonify({'code':0,'message':'ok','data':data})
    resp.headers['ETag'] = etag
    return resp
