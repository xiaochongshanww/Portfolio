from flask import Blueprint, request, jsonify
from sqlalchemy import func, and_
from .. import db, require_auth, require_roles
from ..models import Category, Tag
from pydantic import BaseModel, field_validator, ValidationError
import re

taxonomy_bp = Blueprint('taxonomy', __name__)

slug_re = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

class CategoryCreateModel(BaseModel):
    name: str
    slug: str | None = None
    parent_id: int | None = None

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str):
        if not v or not v.strip():
            raise ValueError('name required')
        return v.strip()

    @field_validator('slug')
    @classmethod
    def slug_fmt(cls, v: str | None):
        if v is None:
            return v
        if not slug_re.match(v):
            raise ValueError('invalid slug')
        return v

class CategoryUpdateModel(BaseModel):
    name: str | None = None
    slug: str | None = None
    parent_id: int | None = None

    @field_validator('slug')
    @classmethod
    def slug_fmt(cls, v: str | None):
        if v is None:
            return v
        if not slug_re.match(v):
            raise ValueError('invalid slug')
        return v

class TagCreateModel(BaseModel):
    name: str
    slug: str | None = None

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str):
        if not v or not v.strip():
            raise ValueError('name required')
        return v.strip()

    @field_validator('slug')
    @classmethod
    def slug_fmt(cls, v: str | None):
        if v is None:
            return v
        if not slug_re.match(v):
            raise ValueError('invalid slug')
        return v

class TagUpdateModel(BaseModel):
    name: str | None = None
    slug: str | None = None

    @field_validator('slug')
    @classmethod
    def slug_fmt(cls, v: str | None):
        if v is None:
            return v
        if not slug_re.match(v):
            raise ValueError('invalid slug')
        return v

# Categories
@taxonomy_bp.route('/categories/', methods=['POST'])
@require_roles('editor','admin')
def create_category():
    print(f"访问 create_category")
    try:
        data = CategoryCreateModel(**request.json)
    except ValidationError as e:
        return jsonify({'code':4001,'message':'validation error','data':e.errors()}), 400
    slug = data.slug or re.sub(r'[^a-z0-9]+','-', data.name.lower()).strip('-')
    # ensure unique slug
    if Category.query.filter(func.lower(Category.slug)==slug.lower()).first():
        return jsonify({'code':4090,'message':'slug exists'}), 409
    parent = None
    if data.parent_id:
        parent = Category.query.get(data.parent_id)
        if not parent:
            return jsonify({'code':4040,'message':'parent not found'}), 404
    c = Category(name=data.name, slug=slug, parent_id=parent.id if parent else None)
    db.session.add(c)
    db.session.commit()
    return jsonify({'code':0,'message':'ok','data':{'id':c.id,'name':c.name,'slug':c.slug,'parent_id':c.parent_id}}), 201

@taxonomy_bp.route('/categories/', methods=['GET'])
@require_auth
def list_categories():
    print(f"访问 list_categories")
    # allow filter parent_id
    parent_id = request.args.get('parent_id', type=int)
    q = Category.query
    if parent_id is not None:
        q = q.filter(Category.parent_id==parent_id)
    items = q.order_by(Category.id.desc()).all()
    data = [{'id':c.id,'name':c.name,'slug':c.slug,'parent_id':c.parent_id} for c in items]
    return jsonify({'code':0,'message':'ok','data':data})

@taxonomy_bp.route('/categories/<int:cid>', methods=['PATCH'])
@require_roles('editor','admin')
def update_category(cid):
    c = Category.query.get(cid)
    if not c:
        return jsonify({'code':4040,'message':'not found'}), 404
    try:
        data = CategoryUpdateModel(**request.json)
    except ValidationError as e:
        return jsonify({'code':4001,'message':'validation error','data':e.errors()}), 400
    if data.name is not None:
        c.name = data.name.strip()
    if data.slug is not None:
        if Category.query.filter(func.lower(Category.slug)==data.slug.lower(), Category.id!=c.id).first():
            return jsonify({'code':4090,'message':'slug exists'}), 409
        c.slug = data.slug
    if data.parent_id is not None:
        if data.parent_id == c.id:
            return jsonify({'code':4001,'message':'cannot set self as parent'}), 400
        parent = Category.query.get(data.parent_id)
        if not parent:
            return jsonify({'code':4040,'message':'parent not found'}), 404
        c.parent_id = parent.id
    db.session.commit()
    return jsonify({'code':0,'message':'ok','data':{'id':c.id,'name':c.name,'slug':c.slug,'parent_id':c.parent_id}})

@taxonomy_bp.route('/categories/<int:cid>', methods=['DELETE'])
@require_roles('editor','admin')
def delete_category(cid):
    c = Category.query.get(cid)
    if not c:
        return jsonify({'code':4040,'message':'not found'}), 404
    
    # 将使用此分类的文章设为无分类（category_id = NULL）
    from ..models import Article
    affected_articles = Article.query.filter(Article.category_id == cid).count()
    Article.query.filter(Article.category_id == cid).update({'category_id': None})
    
    db.session.delete(c)
    db.session.commit()
    
    return jsonify({
        'code': 0, 
        'message': 'ok',
        'data': {
            'affected_articles': affected_articles
        }
    })

# Tags
@taxonomy_bp.route('/tags/', methods=['POST'])
@require_roles('editor','admin')
def create_tag():
    try:
        data = TagCreateModel(**request.json)
    except ValidationError as e:
        return jsonify({'code':4001,'message':'validation error','data':e.errors()}), 400
    slug = data.slug or re.sub(r'[^a-z0-9]+','-', data.name.lower()).strip('-')
    if Tag.query.filter(func.lower(Tag.slug)==slug.lower()).first():
        return jsonify({'code':4090,'message':'slug exists'}), 409
    t = Tag(name=data.name.strip(), slug=slug)
    db.session.add(t)
    db.session.commit()
    return jsonify({'code':0,'message':'ok','data':{'id':t.id,'name':t.name,'slug':t.slug}}), 201

@taxonomy_bp.route('/tags/', methods=['GET'])
@require_auth
def list_tags():
    items = Tag.query.order_by(Tag.id.desc()).all()
    return jsonify({'code':0,'message':'ok','data':[{'id':t.id,'name':t.name,'slug':t.slug} for t in items]})

@taxonomy_bp.route('/tags/<int:tid>', methods=['PATCH'])
@require_roles('editor','admin')
def update_tag(tid):
    t = Tag.query.get(tid)
    if not t:
        return jsonify({'code':4040,'message':'not found'}), 404
    try:
        data = TagUpdateModel(**request.json)
    except ValidationError as e:
        return jsonify({'code':4001,'message':'validation error','data':e.errors()}), 400
    if data.name is not None:
        t.name = data.name.strip()
    if data.slug is not None:
        if Tag.query.filter(func.lower(Tag.slug)==data.slug.lower(), Tag.id!=t.id).first():
            return jsonify({'code':4090,'message':'slug exists'}), 409
        t.slug = data.slug
    db.session.commit()
    return jsonify({'code':0,'message':'ok','data':{'id':t.id,'name':t.name,'slug':t.slug}})

@taxonomy_bp.route('/tags/<int:tid>', methods=['DELETE'])
@require_roles('editor','admin')
def delete_tag(tid):
    t = Tag.query.get(tid)
    if not t:
        return jsonify({'code':4040,'message':'not found'}), 404
    from ..models import ArticleTag
    if ArticleTag.query.filter_by(tag_id=tid).first():
        return jsonify({'code':4002,'message':'tag in use'}), 400
    db.session.delete(t)
    db.session.commit()
    return jsonify({'code':0,'message':'ok'})

# Statistics
@taxonomy_bp.route('/stats', methods=['GET'])
@require_roles('editor','admin')
def get_stats():
    """获取分类和标签的统计信息"""
    from ..models import Article, ArticleTag
    
    # 分类统计
    categories_with_count = db.session.query(
        Category.id, Category.name, Category.slug, Category.parent_id,
        func.count(Article.id).label('article_count')
    ).outerjoin(Article, and_(
        Category.id == Article.category_id,
        Article.deleted != True
    )).group_by(Category.id, Category.name, Category.slug, Category.parent_id)\
     .order_by(Category.id.desc()).all()
    
    categories_data = [{
        'id': c.id,
        'name': c.name,
        'slug': c.slug,
        'parent_id': c.parent_id,
        'article_count': c.article_count
    } for c in categories_with_count]
    
    # 标签统计  
    tags_with_count = db.session.query(
        Tag.id, Tag.name, Tag.slug,
        func.count(ArticleTag.article_id).label('article_count')
    ).outerjoin(ArticleTag, Tag.id == ArticleTag.tag_id)\
     .group_by(Tag.id, Tag.name, Tag.slug)\
     .order_by(func.count(ArticleTag.article_id).desc()).all()
    
    tags_data = [{
        'id': t.id,
        'name': t.name,
        'slug': t.slug,
        'article_count': t.article_count
    } for t in tags_with_count]
    
    # 总计统计
    total_categories = Category.query.count()
    total_tags = Tag.query.count()
    categories_with_articles = Category.query.join(Article).filter(Article.deleted != True).distinct().count()
    tags_with_articles = Tag.query.join(ArticleTag).distinct().count()
    
    return jsonify({
        'code': 0,
        'message': 'ok',
        'data': {
            'categories': categories_data,
            'tags': tags_data,
            'summary': {
                'total_categories': total_categories,
                'total_tags': total_tags,
                'categories_with_articles': categories_with_articles,
                'tags_with_articles': tags_with_articles,
                'unused_categories': total_categories - categories_with_articles,
                'unused_tags': total_tags - tags_with_articles
            }
        }
    })
