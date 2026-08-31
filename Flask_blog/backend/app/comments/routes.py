from flask import Blueprint, jsonify, request

from .. import limiter, require_auth, require_roles
from ..models import Comment
from .service import (
    CommentServiceError,
    admin_list,
    build_comment_tree,
    create_comment,
    get_stats,
    list_approved,
    list_pending,
    moderate_batch,
    moderate_comment,
)

# pydantic 校验
try:
    from pydantic import BaseModel, ValidationError, field_validator

    HAS_PY = True
except Exception:
    HAS_PY = False

    class BaseModel:  # type: ignore[no-redef]
        pass

    def ValidationError(*a, **k):  # type: ignore[no-redef]
        return Exception("validation error")

    def field_validator(*a, **k):  # type: ignore[no-redef]
        def deco(fn):
            return fn

        return deco


comments_bp = Blueprint("comments", __name__)

if HAS_PY:

    class CommentCreate(BaseModel):
        article_id: int
        content: str
        parent_id: int | None = None

        @field_validator("content")
        @classmethod
        def content_len(cls, v):
            if not v or len(v.strip()) < 2:
                raise ValueError("content too short")
            return v.strip()

    class CommentModerate(BaseModel):
        action: str

        @field_validator("action")
        @classmethod
        def action_ok(cls, v):
            if v not in ("approve", "reject"):
                raise ValueError("invalid action")
            return v

else:

    class CommentCreate:  # type: ignore[no-redef]
        pass

    class CommentModerate:  # type: ignore[no-redef]
        pass


def _ok(data, status=200):
    return jsonify({"code": 0, "data": data, "message": "ok"}), status


@comments_bp.route("/", methods=["POST"])
@require_auth
@limiter.limit("20/minute")  # type: ignore  # 评论发表限速
def add_comment():
    data = request.get_json() or {}
    if HAS_PY:
        try:
            parsed = CommentCreate(**data)
        except ValidationError as ve:
            return (
                jsonify(
                    {"code": 4001, "message": "validation error", "data": ve.errors()}
                ),
                400,
            )
        article_id = parsed.article_id
        content = parsed.content
        parent_id = parsed.parent_id
    else:
        article_id = data.get("article_id")
        content = (data.get("content") or "").strip()
        parent_id = data.get("parent_id")
    if not article_id or not content:
        return jsonify({"code": 4001, "message": "article_id & content required"}), 400
    try:
        comment = create_comment(request.user_id, article_id, content, parent_id)
    except CommentServiceError as e:
        return jsonify({"code": e.code, "message": e.message}), e.status
    return _ok({"id": comment.id, "status": comment.status}, 201)


@comments_bp.route("/article/<int:article_id>", methods=["GET"])
def list_comments(article_id):
    comments = list_approved(article_id)
    data = [
        {
            "id": c.id,
            "parent_id": c.parent_id,
            "content": c.content,
            "created_at": c.created_at.isoformat(),
            "user_id": c.user_id,
        }
        for c in comments
    ]
    return _ok(data)


@comments_bp.route("/article/<int:article_id>/tree", methods=["GET"])
def list_comments_tree(article_id):
    """评论树。默认仅返回 approved；传 include=all 且登录作者本人或 editor/admin 时返回其余状态。"""
    include = request.args.get("include")
    from ..models import Comment as _C

    q = _C.query.filter_by(article_id=article_id).order_by(_C.created_at.asc())
    allowed_all = False
    try:
        # 复用认证: 如果带 Authorization 头则尝试鉴权
        from .. import require_auth as _rq
        from ..models import Article

        if "Authorization" in request.headers:
            auth_resp = _rq(lambda: None)()
            if auth_resp is None:
                art = Article.query.get(article_id)
                if art and (
                    art.author_id == request.user_id
                    or request.user_role in ("editor", "admin")
                ):
                    allowed_all = True
    except Exception:
        pass
    if include != "all" or not allowed_all:
        q = q.filter_by(status="approved")
    comments = q.all()
    return _ok(build_comment_tree(comments))


@comments_bp.route("/pending", methods=["GET"])
@require_roles("editor", "admin")
def list_pending_route():
    # 分页列出待审核评论，可按文章过滤
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("page_size", 10))
    except Exception:
        page, size = 1, 10
    size = max(1, min(size, 50))
    article_id = request.args.get("article_id")
    if article_id and article_id.isdigit():
        article_id = int(article_id)
    else:
        article_id = None
    return _ok(list_pending(page, size, article_id))


@comments_bp.route("/admin/list", methods=["GET"])
@require_roles("editor", "admin")
def admin_list_comments():
    """管理员评论列表，支持状态筛选、内容搜索等"""
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("page_size", 20))
    except Exception:
        page, size = 1, 20
    size = max(1, min(size, 100))
    status = request.args.get("status")
    article_id = request.args.get("article_id")
    if article_id and article_id.isdigit():
        article_id = int(article_id)
    else:
        article_id = None
    content = request.args.get("content")
    return _ok(admin_list(page, size, status, article_id, content))


@comments_bp.route("/admin/stats", methods=["GET"])
@require_roles("editor", "admin")
def admin_stats():
    """管理员统计数据"""
    return _ok(get_stats())


@comments_bp.route("/admin/review-stats", methods=["GET"])
@require_roles("editor", "admin")
def review_queue_stats():
    """审核队列统计:待审核数 + 今日已审核(通过/退回,来自审计日志)。"""
    from datetime import datetime, timezone

    from ..models import AuditLog

    pending_count = Comment.query.filter_by(status="pending").count()
    today_start = datetime.combine(
        datetime.now(timezone.utc).date(), datetime.min.time()
    ).replace(tzinfo=timezone.utc)
    approved_today = (
        AuditLog.query.filter(
            AuditLog.action == "approve",
            AuditLog.created_at >= today_start,
        ).count()
    )
    rejected_today = (
        AuditLog.query.filter(
            AuditLog.action == "reject",
            AuditLog.created_at >= today_start,
        ).count()
    )
    return _ok(
        {
            "pending": pending_count,
            "approved_today": approved_today,
            "rejected_today": rejected_today,
        }
    )


@comments_bp.route("/moderate/<int:comment_id>", methods=["POST"])
@require_roles("editor", "admin")
@limiter.limit("60/minute")  # type: ignore  # 审核操作限速
def moderate(comment_id):
    data = request.get_json() or {}
    if HAS_PY:
        try:
            parsed = CommentModerate(**data)
        except ValidationError as ve:
            return (
                jsonify(
                    {"code": 4001, "message": "validation error", "data": ve.errors()}
                ),
                400,
            )
        action = parsed.action
    else:
        action = data.get("action")
    c = Comment.query.get_or_404(comment_id)
    try:
        moderate_comment(c, action)
    except CommentServiceError as e:
        return jsonify({"code": e.code, "message": e.message}), e.status
    return _ok({"id": c.id, "status": c.status})


@comments_bp.route("/moderate/batch", methods=["POST"])
@require_roles("editor", "admin")
@limiter.limit("30/minute")  # type: ignore  # 批量操作限速
def moderate_batch_route():
    """批量审核评论"""
    data = request.get_json() or {}
    ids = data.get("ids", [])
    action = data.get("action")

    if not ids or not isinstance(ids, list):
        return jsonify({"code": 4001, "message": "ids required as array"}), 400

    if action not in ("approve", "reject"):
        return jsonify({"code": 4001, "message": "invalid action"}), 400

    if len(ids) > 50:  # 限制批量操作数量
        return jsonify({"code": 4001, "message": "too many items, max 50"}), 400

    comments = Comment.query.filter(Comment.id.in_(ids)).all()

    if len(comments) != len(ids):
        return jsonify({"code": 4001, "message": "some comments not found"}), 400

    new_status, updated = moderate_batch(comments, action)

    return _ok({"updated_count": updated, "status": new_status})
