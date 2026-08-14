from flask import Blueprint, jsonify, request
from pydantic import BaseModel, ValidationError, field_validator

from .. import require_auth, require_roles
from ..models import Category, Tag
from ..utils import audit_log
from .service import (
    TaxonomyError,
    create_category,
    create_tag,
    delete_category,
    delete_tag,
    get_stats,
    is_valid_slug,
    list_categories,
    list_categories_public,
    list_tags,
    list_tags_public,
    update_category,
    update_tag,
)

taxonomy_bp = Blueprint("taxonomy", __name__)


class CategoryCreateModel(BaseModel):
    name: str
    slug: str | None = None
    parent_id: int | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str):
        if not v or not v.strip():
            raise ValueError("name required")
        return v.strip()

    @field_validator("slug")
    @classmethod
    def slug_fmt(cls, v: str | None):
        if v is None or is_valid_slug(v):
            return v
        raise ValueError("invalid slug")


class CategoryUpdateModel(BaseModel):
    name: str | None = None
    slug: str | None = None
    parent_id: int | None = None

    @field_validator("slug")
    @classmethod
    def slug_fmt(cls, v: str | None):
        if v is None or is_valid_slug(v):
            return v
        raise ValueError("invalid slug")


class TagCreateModel(BaseModel):
    name: str
    slug: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str):
        if not v or not v.strip():
            raise ValueError("name required")
        return v.strip()

    @field_validator("slug")
    @classmethod
    def slug_fmt(cls, v: str | None):
        if v is None or is_valid_slug(v):
            return v
        raise ValueError("invalid slug")


class TagUpdateModel(BaseModel):
    name: str | None = None
    slug: str | None = None

    @field_validator("slug")
    @classmethod
    def slug_fmt(cls, v: str | None):
        if v is None or is_valid_slug(v):
            return v
        raise ValueError("invalid slug")


def _ok(data):
    return jsonify({"code": 0, "message": "ok", "data": data})


def _validation_error(e):
    return (
        jsonify({"code": 4001, "message": "validation error", "data": e.errors()}),
        400,
    )


# Categories
@taxonomy_bp.route("/categories/", methods=["POST"])
@require_roles("editor", "admin")
def create_category_route():
    try:
        data = CategoryCreateModel(**request.json)
    except ValidationError as e:
        return _validation_error(e)
    try:
        c = create_category(data.name, data.slug, data.parent_id)
    except TaxonomyError as e:
        return jsonify({"code": e.code, "message": e.message}), e.status
    audit_log(
        "category:create",
        getattr(request, "user_id", 0),
        f"创建分类: {c.name} (slug={c.slug})",
    )
    return (
        _ok(
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "parent_id": c.parent_id,
            }
        ),
        201,
    )


@taxonomy_bp.route("/categories/", methods=["GET"])
@require_auth
def list_categories_route():
    parent_id = request.args.get("parent_id", type=int)
    items = list_categories(parent_id)
    data = [
        {"id": c.id, "name": c.name, "slug": c.slug, "parent_id": c.parent_id}
        for c in items
    ]
    return _ok(data)


@taxonomy_bp.route("/categories/<int:cid>", methods=["PATCH"])
@require_roles("editor", "admin")
def update_category_route(cid):
    c = Category.query.get(cid)
    if not c:
        return jsonify({"code": 4040, "message": "not found"}), 404
    try:
        data = CategoryUpdateModel(**request.json)
    except ValidationError as e:
        return _validation_error(e)
    try:
        update_category(c, data.name, data.slug, data.parent_id)
    except TaxonomyError as e:
        return jsonify({"code": e.code, "message": e.message}), e.status
    audit_log(
        "category:update", getattr(request, "user_id", 0), f"更新分类 {cid}: {c.name}"
    )
    return _ok({"id": c.id, "name": c.name, "slug": c.slug, "parent_id": c.parent_id})


@taxonomy_bp.route("/categories/<int:cid>", methods=["DELETE"])
@require_roles("editor", "admin")
def delete_category_route(cid):
    c = Category.query.get(cid)
    if not c:
        return jsonify({"code": 4040, "message": "not found"}), 404
    affected = delete_category(c)
    audit_log(
        "category:delete", getattr(request, "user_id", 0), f"删除分类 {cid}: {c.name}"
    )
    return _ok({"affected_articles": affected})


# Tags
@taxonomy_bp.route("/tags/", methods=["POST"])
@require_roles("editor", "admin")
def create_tag_route():
    try:
        data = TagCreateModel(**request.json)
    except ValidationError as e:
        return _validation_error(e)
    try:
        t = create_tag(data.name, data.slug)
    except TaxonomyError as e:
        return jsonify({"code": e.code, "message": e.message}), e.status
    audit_log("tag:create", getattr(request, "user_id", 0), f"创建标签: {t.name}")
    return _ok({"id": t.id, "name": t.name, "slug": t.slug}), 201


@taxonomy_bp.route("/tags/", methods=["GET"])
@require_auth
def list_tags_route():
    items = list_tags()
    return _ok([{"id": t.id, "name": t.name, "slug": t.slug} for t in items])


@taxonomy_bp.route("/tags/<int:tid>", methods=["PATCH"])
@require_roles("editor", "admin")
def update_tag_route(tid):
    t = Tag.query.get(tid)
    if not t:
        return jsonify({"code": 4040, "message": "not found"}), 404
    try:
        data = TagUpdateModel(**request.json)
    except ValidationError as e:
        return _validation_error(e)
    try:
        update_tag(t, data.name, data.slug)
    except TaxonomyError as e:
        return jsonify({"code": e.code, "message": e.message}), e.status
    audit_log("tag:update", getattr(request, "user_id", 0), f"更新标签 {tid}: {t.name}")
    return _ok({"id": t.id, "name": t.name, "slug": t.slug})


@taxonomy_bp.route("/tags/<int:tid>", methods=["DELETE"])
@require_roles("editor", "admin")
def delete_tag_route(tid):
    t = Tag.query.get(tid)
    if not t:
        return jsonify({"code": 4040, "message": "not found"}), 404
    try:
        delete_tag(t)
    except TaxonomyError as e:
        return jsonify({"code": e.code, "message": e.message}), e.status
    audit_log("tag:delete", getattr(request, "user_id", 0), f"删除标签 {tid}: {t.name}")
    return jsonify({"code": 0, "message": "ok"})


# Public endpoints for unauthenticated access
@taxonomy_bp.route("/categories/public", methods=["GET"])
def list_categories_public_route():
    """公开的分类列表API，包含文章数量统计"""
    return _ok(list_categories_public())


@taxonomy_bp.route("/tags/public", methods=["GET"])
def list_tags_public_route():
    """公开的标签列表API，包含文章数量统计"""
    return _ok(list_tags_public())


# Statistics
@taxonomy_bp.route("/stats", methods=["GET"])
@require_roles("editor", "admin")
def get_stats_route():
    """获取分类和标签的统计信息"""
    return _ok(get_stats())
