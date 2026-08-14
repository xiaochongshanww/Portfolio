from flask import Blueprint, current_app, jsonify, request

from .. import require_auth, require_roles
from ..models import User
from .service import (
    UserServiceError,
    change_role,
    etag_response,
    list_users,
    public_author_articles,
    public_author_profile,
    public_author_stats,
    serialize_user,
    update_profile,
)

users_bp = Blueprint("users", __name__)


class ProfileUpdateModel:
    def __init__(self, **kwargs):
        self.nickname = kwargs.get("nickname")
        self.bio = kwargs.get("bio")
        self.avatar = kwargs.get("avatar")
        self.social_links = kwargs.get("social_links")

        # 验证数据
        if self.nickname is not None:
            self.nickname = self.nick_ok(self.nickname)
        if self.bio is not None:
            self.bio = self.bio_ok(self.bio)

    @classmethod
    def nick_ok(cls, v):
        if v and len(v) > 80:
            raise ValueError("nickname too long")
        return v

    @classmethod
    def bio_ok(cls, v):
        if v and len(v) > 2000:
            raise ValueError("bio too long")
        return v


class RoleUpdateModel:
    def __init__(self, **kwargs):
        self.role = kwargs.get("role")
        if self.role is None:
            raise ValueError("role is required")
        self.role = self.role_ok(self.role)

    @classmethod
    def role_ok(cls, v):
        if v not in ("author", "editor", "admin"):
            raise ValueError("invalid role")
        return v


def _validation_error(e):
    return (
        jsonify({"code": 4001, "message": "validation error", "data": str(e)}),
        400,
    )


def _service_error(e):
    data = {"code": e.code, "message": e.message}
    if e.data is not None:
        data["data"] = str(e.data)
    return jsonify(data), e.status


def _ok(data):
    return jsonify({"code": 0, "message": "ok", "data": data})


@users_bp.route("/me", methods=["GET"])
@require_auth
def me():
    current_app.logger.info(f"用户信息请求 - 用户ID: {request.user_id}")
    u = User.query.get_or_404(request.user_id)
    return _ok(serialize_user(u, include_email=True))


@users_bp.route("/me", methods=["PATCH"])
@require_auth
def update_me():
    current_app.logger.info(f"用户信息请求 - 用户ID: {request.user_id}")
    data = request.get_json() or {}
    try:
        parsed = ProfileUpdateModel(**data)
    except Exception as ve:
        return _validation_error(ve)

    u = User.query.get_or_404(request.user_id)
    try:
        u = update_profile(
            u,
            parsed.nickname,
            parsed.bio,
            parsed.avatar,
            parsed.social_links,
        )
    except UserServiceError as e:
        return _service_error(e)
    return _ok(serialize_user(u, include_email=True))


@users_bp.route("/", methods=["GET"])
@require_roles("admin")
def list_users_route():
    page = int(request.args.get("page", 1))
    size = min(int(request.args.get("page_size", 20)), 100)
    return etag_response(list_users(page, size))


@users_bp.route("/<int:user_id>/role", methods=["PATCH"])
@require_roles("admin")
def change_role_route(user_id):
    data = request.get_json() or {}
    try:
        parsed = RoleUpdateModel(**data)
    except Exception as ve:
        return _validation_error(ve)

    u = User.query.get_or_404(user_id)
    try:
        old = change_role(u, parsed.role, getattr(request, "user_id", 0))
    except UserServiceError as e:
        return _service_error(e)
    return _ok({"id": u.id, "old_role": old, "new_role": u.role})


@users_bp.route("/public/<int:user_id>", methods=["GET"])
def public_author_profile_route(user_id):
    """公开作者资料：仅返回非敏感字段与已发布文章统计（带缓存）。"""
    return public_author_profile(user_id)


@users_bp.route("/public/<int:user_id>/articles", methods=["GET"])
def public_author_articles_route(user_id):
    """公开作者已发布文章列表。支持分页 & sort(published_at desc|asc)，带缓存和指标。"""
    page = int(request.args.get("page", 1))
    size = min(int(request.args.get("page_size", 10)), 50)
    sort = request.args.get("sort", "published_at:desc")
    return public_author_articles(user_id, page, size, sort)


@users_bp.route("/public/<int:user_id>/stats", methods=["GET"])
def public_author_stats_route(user_id):
    """作者公开统计：文章数 / 总浏览 / 总点赞 / 最近发布时间。使用轻缓存。"""
    return public_author_stats(user_id)
