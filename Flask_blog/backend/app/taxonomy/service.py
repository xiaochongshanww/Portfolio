"""分类/标签业务逻辑层 — 供 routes.py 编排调用"""

import re

from sqlalchemy import and_, func

from .. import db
from ..models import Article, ArticleTag, Category, Tag

slug_re = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TaxonomyError(Exception):
    """分类/标签业务异常，携带 HTTP 状态码与错误码。"""

    def __init__(self, message, code=4001, status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def is_valid_slug(slug):
    return bool(slug_re.match(slug or ""))


def make_slug(name):
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def create_category(name, slug=None, parent_id=None, user_id=0):
    """创建分类，含 slug 唯一性与父分类校验。"""
    slug = slug or make_slug(name)
    if Category.query.filter(func.lower(Category.slug) == slug.lower()).first():
        raise TaxonomyError("slug exists", code=4090, status=409)
    parent = None
    if parent_id:
        parent = Category.query.get(parent_id)
        if not parent:
            raise TaxonomyError("parent not found", code=4040, status=404)
    c = Category(name=name, slug=slug, parent_id=parent.id if parent else None)
    db.session.add(c)
    db.session.commit()
    return c


def list_categories(parent_id=None):
    """分类列表，可按父分类过滤。"""
    q = Category.query
    if parent_id is not None:
        q = q.filter(Category.parent_id == parent_id)
    return q.order_by(Category.id.desc()).all()


def update_category(category, name=None, slug=None, parent_id=None, user_id=0):
    """更新分类，含 slug 唯一性与自引用校验。"""
    if name is not None:
        category.name = name.strip()
    if slug is not None:
        if Category.query.filter(
            func.lower(Category.slug) == slug.lower(), Category.id != category.id
        ).first():
            raise TaxonomyError("slug exists", code=4090, status=409)
        category.slug = slug
    if parent_id is not None:
        if parent_id == category.id:
            raise TaxonomyError("cannot set self as parent")
        parent = Category.query.get(parent_id)
        if not parent:
            raise TaxonomyError("parent not found", code=4040, status=404)
        category.parent_id = parent.id
    db.session.commit()
    return category


def delete_category(category):
    """删除分类，并将关联文章置为无分类。"""
    affected = Article.query.filter(Article.category_id == category.id).count()
    Article.query.filter(Article.category_id == category.id).update(
        {"category_id": None}
    )
    db.session.delete(category)
    db.session.commit()
    return affected


def create_tag(name, slug=None, user_id=0):
    """创建标签，含 slug 唯一性校验。"""
    slug = slug or make_slug(name)
    if Tag.query.filter(func.lower(Tag.slug) == slug.lower()).first():
        raise TaxonomyError("slug exists", code=4090, status=409)
    t = Tag(name=name.strip(), slug=slug)
    db.session.add(t)
    db.session.commit()
    return t


def list_tags():
    return Tag.query.order_by(Tag.id.desc()).all()


def update_tag(tag, name=None, slug=None, user_id=0):
    """更新标签，含 slug 唯一性校验。"""
    if name is not None:
        tag.name = name.strip()
    if slug is not None:
        if Tag.query.filter(
            func.lower(Tag.slug) == slug.lower(), Tag.id != tag.id
        ).first():
            raise TaxonomyError("slug exists", code=4090, status=409)
        tag.slug = slug
    db.session.commit()
    return tag


def delete_tag(tag):
    """删除标签；被使用时禁止删除。"""
    if ArticleTag.query.filter_by(tag_id=tag.id).first():
        raise TaxonomyError("tag in use", code=4002)
    db.session.delete(tag)
    db.session.commit()


def _categories_with_count(published_only=False):
    onclause = and_(Category.id == Article.category_id, Article.deleted.isnot(True))
    if published_only:
        onclause = and_(
            Category.id == Article.category_id,
            Article.deleted.isnot(True),
            Article.status == "published",
        )
    return (
        db.session.query(
            Category.id,
            Category.name,
            Category.slug,
            Category.parent_id,
            func.count(Article.id).label("article_count"),
        )
        .outerjoin(Article, onclause)
        .group_by(Category.id, Category.name, Category.slug, Category.parent_id)
        .order_by(Category.id.desc())
        .all()
    )


def _tags_with_count(published_only=False):
    q = (
        db.session.query(
            Tag.id,
            Tag.name,
            Tag.slug,
            func.count(ArticleTag.article_id).label("article_count"),
        )
        .outerjoin(ArticleTag, Tag.id == ArticleTag.tag_id)
        .group_by(Tag.id, Tag.name, Tag.slug)
    )
    if published_only:
        q = q.outerjoin(
            Article,
            and_(
                ArticleTag.article_id == Article.id,
                Article.deleted.isnot(True),
                Article.status == "published",
            ),
        ).order_by(func.count(ArticleTag.article_id).desc())
    else:
        q = q.order_by(func.count(ArticleTag.article_id).desc())
    return q.all()


def list_categories_public():
    """公开分类列表，仅统计已发布文章。"""
    rows = _categories_with_count(published_only=True)
    return [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "parent_id": c.parent_id,
            "article_count": c.article_count,
            "description": None,
        }
        for c in rows
    ]


def list_tags_public():
    """公开标签列表，仅统计已发布文章。"""
    rows = _tags_with_count(published_only=True)
    return [
        {"id": t.id, "name": t.name, "slug": t.slug, "article_count": t.article_count}
        for t in rows
    ]


def get_stats():
    """分类/标签统计信息。"""
    categories_data = [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "parent_id": c.parent_id,
            "article_count": c.article_count,
        }
        for c in _categories_with_count()
    ]
    tags_data = [
        {"id": t.id, "name": t.name, "slug": t.slug, "article_count": t.article_count}
        for t in _tags_with_count()
    ]
    total_categories = Category.query.count()
    total_tags = Tag.query.count()
    categories_with_articles = (
        Category.query.join(Article)
        .filter(Article.deleted.isnot(True))
        .distinct()
        .count()
    )
    tags_with_articles = Tag.query.join(ArticleTag).distinct().count()
    return {
        "categories": categories_data,
        "tags": tags_data,
        "summary": {
            "total_categories": total_categories,
            "total_tags": total_tags,
            "categories_with_articles": categories_with_articles,
            "tags_with_articles": tags_with_articles,
            "unused_categories": total_categories - categories_with_articles,
            "unused_tags": total_tags - tags_with_articles,
        },
    }
