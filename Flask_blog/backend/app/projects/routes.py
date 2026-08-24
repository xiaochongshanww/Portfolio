"""Project 实体路由(impl-P2 分组 A)。

- 公开:GET /api/v1/projects/ 列表(is_current 置顶,排除 archived)、
  GET /api/v1/projects/<slug> 详情(404);
- 管理:GET /admin/list 全量、POST /、PUT /<id>、DELETE /<id>(editor/admin);
- is_current 唯一性由 service 层保证:置一个时清其他。
"""

import json

from flask import Blueprint, jsonify, request

from .. import db
from ..decorators import require_roles
from ..models import Project
from ..utils import compute_etag

projects_bp = Blueprint("projects", __name__)

ALLOWED_STATUS = {Project.STATUS_ACTIVE, Project.STATUS_PAUSED, Project.STATUS_ARCHIVED}
ALLOWED_PREVIEW = {Project.PREVIEW_NONE, Project.PREVIEW_IMAGE, Project.PREVIEW_SVG}


def _parse_json(raw, default):
    """JSON 文本列安全解析:坏数据不炸接口,降级为默认值。"""
    if raw is None or raw == "":
        return default
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return default


def serialize_project(p: Project, detail: bool = False) -> dict:
    data = {
        "id": p.id,
        "name": p.name,
        "slug": p.slug,
        "description": p.description,
        "tag": p.tag,
        "tech_stack": _parse_json(p.tech_stack, []),
        "status": p.status,
        "is_current": bool(p.is_current),
        "preview_type": p.preview_type,
        "link_url": p.link_url,
        "repo_url": p.repo_url,
        "sort_order": p.sort_order,
        "created_at": p.created_at.isoformat() + "Z" if p.created_at else None,
        "updated_at": p.updated_at.isoformat() + "Z" if p.updated_at else None,
    }
    if detail:
        data.update(
            {
                "preview_data": _parse_json(p.preview_data, None),
                "motivation": p.motivation,
                "progress": p.progress,
                "design_notes": p.design_notes,
                "related_article_slugs": _parse_json(p.related_article_slugs, []),
                "changelog": _parse_json(p.changelog, []),
            }
        )
    return data


def _clear_other_current(keep_id=None):
    """is_current 唯一性:置一个时清其他(service 层保证,兼容 SQLite)。"""
    q = Project.query.filter(Project.is_current.is_(True))
    if keep_id is not None:
        q = q.filter(Project.id != keep_id)
    for other in q.all():
        other.is_current = False


def _validate_payload(data: dict, partial: bool = False) -> str | None:
    """返回错误消息;None 表示通过。"""
    if not partial or "name" in data:
        if not str(data.get("name") or "").strip():
            return "name 不能为空"
    if not partial or "slug" in data:
        slug = str(data.get("slug") or "").strip()
        if not slug:
            return "slug 不能为空"
        if Project.query.filter(Project.slug == slug).first():
            return "slug 已存在"
    if data.get("status") and data["status"] not in ALLOWED_STATUS:
        return "status 取值非法"
    if data.get("preview_type") and data["preview_type"] not in ALLOWED_PREVIEW:
        return "preview_type 取值非法"
    return None


# ─── 公开接口 ─────────────────────────────────────────────


@projects_bp.route("/", methods=["GET"])
def list_projects():
    """公开列表:is_current 置顶 → sort_order → 更新时间倒序;archived 不外露。"""
    items = (
        Project.query.filter(Project.status != Project.STATUS_ARCHIVED)
        .order_by(
            Project.is_current.desc(),
            Project.sort_order.asc(),
            Project.updated_at.desc(),
        )
        .all()
    )
    payload = {"total": len(items), "list": [serialize_project(p) for p in items]}
    etag = compute_etag(payload)
    if request.headers.get("If-None-Match") == etag:
        return ("", 304, {"ETag": etag})
    resp = jsonify({"code": 0, "message": "ok", "data": payload})
    resp.headers["ETag"] = etag
    return resp


@projects_bp.route("/<string:slug>", methods=["GET"])
def get_project(slug: str):
    """公开详情:archived 视同不存在。"""
    p = Project.query.filter_by(slug=slug).first()
    if not p or p.status == Project.STATUS_ARCHIVED:
        return jsonify({"code": 1404, "message": "project not found"}), 404
    return jsonify(
        {"code": 0, "message": "ok", "data": serialize_project(p, detail=True)}
    )


# ─── 管理接口 ─────────────────────────────────────────────


@projects_bp.route("/admin/list", methods=["GET"])
@require_roles("editor", "admin")
def admin_list_projects():
    """管理列表:含 archived,便于恢复。"""
    items = Project.query.order_by(
        Project.is_current.desc(), Project.sort_order.asc(), Project.updated_at.desc()
    ).all()
    return jsonify(
        {
            "code": 0,
            "message": "ok",
            "data": {
                "total": len(items),
                "list": [serialize_project(p, detail=True) for p in items],
            },
        }
    )


@projects_bp.route("/", methods=["POST"])
@require_roles("editor", "admin")
def create_project():
    data = request.get_json(silent=True) or {}
    err = _validate_payload(data)
    if err:
        return jsonify({"code": 1400, "message": err}), 400

    p = Project(
        name=str(data["name"]).strip(),
        slug=str(data["slug"]).strip(),
        description=data.get("description"),
        tag=data.get("tag"),
        tech_stack=json.dumps(data.get("tech_stack") or [], ensure_ascii=False),
        status=data.get("status") or Project.STATUS_ACTIVE,
        is_current=bool(data.get("is_current")),
        preview_type=data.get("preview_type") or Project.PREVIEW_NONE,
        preview_data=(
            json.dumps(data["preview_data"], ensure_ascii=False)
            if data.get("preview_data") is not None
            else None
        ),
        link_url=data.get("link_url"),
        repo_url=data.get("repo_url"),
        motivation=data.get("motivation"),
        progress=data.get("progress"),
        design_notes=data.get("design_notes"),
        related_article_slugs=json.dumps(
            data.get("related_article_slugs") or [], ensure_ascii=False
        ),
        changelog=json.dumps(data.get("changelog") or [], ensure_ascii=False),
        sort_order=int(data.get("sort_order") or 0),
    )
    if p.is_current:
        _clear_other_current()
    db.session.add(p)
    db.session.commit()
    return (
        jsonify(
            {"code": 0, "message": "ok", "data": serialize_project(p, detail=True)}
        ),
        201,
    )


@projects_bp.route("/<int:project_id>", methods=["PUT"])
@require_roles("editor", "admin")
def update_project(project_id: int):
    p = Project.query.get(project_id)
    if not p:
        return jsonify({"code": 1404, "message": "project not found"}), 404
    data = request.get_json(silent=True) or {}

    if "slug" in data and data["slug"] != p.slug:
        err = _validate_payload({"slug": data["slug"]}, partial=True)
        if err:
            return jsonify({"code": 1400, "message": err}), 400
        p.slug = str(data["slug"]).strip()
    for field in (
        "name",
        "description",
        "tag",
        "link_url",
        "repo_url",
        "motivation",
        "progress",
        "design_notes",
    ):
        if field in data:
            setattr(p, field, data[field])
    if "status" in data:
        if data["status"] not in ALLOWED_STATUS:
            return jsonify({"code": 1400, "message": "status 取值非法"}), 400
        p.status = data["status"]
    if "preview_type" in data:
        if data["preview_type"] not in ALLOWED_PREVIEW:
            return jsonify({"code": 1400, "message": "preview_type 取值非法"}), 400
        p.preview_type = data["preview_type"]
    if "tech_stack" in data:
        p.tech_stack = json.dumps(data["tech_stack"] or [], ensure_ascii=False)
    if "preview_data" in data:
        p.preview_data = (
            json.dumps(data["preview_data"], ensure_ascii=False)
            if data["preview_data"] is not None
            else None
        )
    if "related_article_slugs" in data:
        p.related_article_slugs = json.dumps(
            data["related_article_slugs"] or [], ensure_ascii=False
        )
    if "changelog" in data:
        p.changelog = json.dumps(data["changelog"] or [], ensure_ascii=False)
    if "sort_order" in data:
        p.sort_order = int(data["sort_order"] or 0)
    if "is_current" in data:
        p.is_current = bool(data["is_current"])

    if p.is_current:
        _clear_other_current(keep_id=p.id)
    db.session.commit()
    return jsonify(
        {"code": 0, "message": "ok", "data": serialize_project(p, detail=True)}
    )


@projects_bp.route("/<int:project_id>", methods=["DELETE"])
@require_roles("admin")
def delete_project(project_id: int):
    p = Project.query.get(project_id)
    if not p:
        return jsonify({"code": 1404, "message": "project not found"}), 404
    db.session.delete(p)
    db.session.commit()
    return jsonify({"code": 0, "message": "ok", "data": {"id": project_id}})
