"""评论业务逻辑层 — 供 routes.py 编排调用"""

from datetime import datetime, timezone

from .. import db
from ..models import Article, Comment


class CommentServiceError(Exception):
    """评论业务异常，携带 HTTP 状态码与错误码。"""

    def __init__(self, message, code=4001, status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def create_comment(user_id, article_id, content, parent_id=None):
    """创建评论，含文章存在性校验与回复层级限制。"""
    art = Article.query.get(article_id)
    if not art or art.deleted or art.status != "published":
        raise CommentServiceError("article not found", code=4040, status=404)
    level = 1
    if parent_id:
        parent = Comment.query.get(parent_id)
        if not parent or parent.article_id != article_id:
            raise CommentServiceError("invalid parent")
        tmp = parent
        while tmp.parent_id:
            level += 1
            tmp = Comment.query.get(tmp.parent_id)
            if level >= 3:
                raise CommentServiceError("max depth reached")
    comment = Comment(
        article_id=article_id,
        parent_id=parent_id,
        user_id=user_id,
        content=content,
    )
    db.session.add(comment)
    db.session.commit()
    return comment


def serialize_comment(c, include_status=False):
    """序列化单条评论。"""
    data = {
        "id": c.id,
        "parent_id": c.parent_id,
        "content": c.content,
        "created_at": c.created_at.isoformat(),
        "user_id": c.user_id,
    }
    if include_status:
        data["status"] = c.status
    return data


def build_comment_tree(comments):
    """将扁平评论列表构建为树结构。"""
    nodes = {
        c.id: {**serialize_comment(c, include_status=True), "children": []}
        for c in comments
    }
    roots = []
    for c in comments:
        if c.parent_id and c.parent_id in nodes:
            nodes[c.parent_id]["children"].append(nodes[c.id])
        else:
            roots.append(nodes[c.id])
    return roots


def list_approved(article_id):
    """获取某文章已审核通过评论（按时间升序）。"""
    return (
        Comment.query.filter_by(article_id=article_id, status="approved")
        .order_by(Comment.created_at.asc())
        .all()
    )


def list_pending(page, size, article_id=None):
    """分页列出待审核评论。"""
    q = Comment.query.filter_by(status="pending")
    if article_id is not None:
        q = q.filter_by(article_id=article_id)
    total = q.count()
    items = (
        q.order_by(Comment.created_at.asc()).offset((page - 1) * size).limit(size).all()
    )
    data = [serialize_comment(c) for c in items]
    return {
        "total": total,
        "page": page,
        "page_size": size,
        "has_next": page * size < total,
        "list": data,
    }


def admin_list(page, size, status=None, article_id=None, content=None):
    """管理员评论列表，支持状态/文章/内容筛选。"""
    q = Comment.query
    if status in ("pending", "approved", "rejected"):
        q = q.filter_by(status=status)
    if article_id is not None:
        q = q.filter_by(article_id=article_id)
    if content:
        q = q.filter(Comment.content.contains(content))
    q = q.order_by(Comment.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    data = [serialize_comment(c, include_status=True) for c in items]
    return {
        "total": total,
        "page": page,
        "page_size": size,
        "has_next": page * size < total,
        "list": data,
    }


def get_stats():
    """管理员统计：待审核 / 今日 / 总数 / 已通过 / 已拒绝。"""
    pending_count = Comment.query.filter_by(status="pending").count()
    today = datetime.now(timezone.utc).date()
    today_start = datetime.combine(today, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    today_count = Comment.query.filter(Comment.created_at >= today_start).count()
    total_count = Comment.query.count()
    approved_count = Comment.query.filter_by(status="approved").count()
    rejected_count = Comment.query.filter_by(status="rejected").count()
    return {
        "pending": pending_count,
        "today": today_count,
        "total": total_count,
        "approved": approved_count,
        "rejected": rejected_count,
    }


def moderate_comment(comment, action):
    """审核单条评论。"""
    if action == "approve":
        comment.status = "approved"
    elif action == "reject":
        comment.status = "rejected"
    else:
        raise CommentServiceError("invalid action")
    db.session.commit()
    return comment


def moderate_batch(comments, action):
    """批量审核评论。"""
    new_status = "approved" if action == "approve" else "rejected"
    for comment in comments:
        comment.status = new_status
    db.session.commit()
    return new_status, len(comments)
