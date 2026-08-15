"""
日志管理API路由
提供日志查看、搜索、统计等功能
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from .. import db, require_auth, require_roles
from ..models import LogConfig, LogEntry
from ..utils.logging_utils import cleanup_old_logs, get_log_config, log_user_action
from .service import (
    build_log_query,
    get_log_config_list_data,
    get_log_detail_data,
    get_log_sources_data,
    get_log_stats_data,
    get_log_users_data,
    query_logs_common,
    upsert_log_config,
)

logs_bp = Blueprint("logs", __name__)


def _build_logs_payload(total, logs_data, page, size):
    return {
        "total": total,
        "page": page,
        "size": size,
        "has_next": page * size < total,
        "logs": logs_data,
    }


@logs_bp.route("", methods=["GET"])  # 兼容保留 GET
@require_auth
@require_roles("admin", "editor")
@log_user_action("VIEW_LOGS")
def get_logs():
    try:
        page = int(request.args.get("page", 1))
        size = min(int(request.args.get("size", 50)), 100)
        level = request.args.get("level", "").upper()
        source = request.args.get("source", "")
        keyword = request.args.get("keyword", "")
        user_id = request.args.get("user_id", type=int)
        start_time = request.args.get("start_time", "")
        end_time = request.args.get("end_time", "")
        request_id = request.args.get("request_id", "")
        total, logs_data = query_logs_common(
            page,
            size,
            level,
            source,
            keyword,
            user_id,
            request_id,
            start_time,
            end_time,
        )
        return jsonify(
            {
                "code": 0,
                "message": "success",
                "data": _build_logs_payload(total, logs_data, page, size),
            }
        )
    except Exception as e:
        return (
            jsonify({"code": 5000, "message": f"获取日志失败: {e}", "data": None}),
            500,
        )


# 新增 POST 查询端点，避免某些浏览器/代理对 GET 的额外预检/重复请求
@logs_bp.route("/query", methods=["POST"])
@require_auth
@require_roles("admin", "editor")
@log_user_action("VIEW_LOGS")
def post_query_logs():
    try:
        body = request.get_json() or {}
        page = int(body.get("page", 1))
        size = min(int(body.get("size", 50)), 100)
        level = (body.get("level") or "").upper()
        source = body.get("source") or ""
        keyword = body.get("keyword") or ""
        user_id = body.get("user_id")
        start_time = body.get("start_time") or ""
        end_time = body.get("end_time") or ""
        request_id = body.get("request_id") or ""
        total, logs_data = query_logs_common(
            page,
            size,
            level,
            source,
            keyword,
            user_id,
            request_id,
            start_time,
            end_time,
        )
        return jsonify(
            {
                "code": 0,
                "message": "success",
                "data": _build_logs_payload(total, logs_data, page, size),
            }
        )
    except Exception as e:
        return (
            jsonify({"code": 5000, "message": f"获取日志失败: {e}", "data": None}),
            500,
        )


# Root OPTIONS (放在 get_logs 之后避免覆盖上方定义)
@logs_bp.route("", methods=["OPTIONS"])
@logs_bp.route("/", methods=["OPTIONS"])
def logs_root_options():
    from flask import make_response

    resp = make_response("", 200)
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Requested-With, X-XSRF-TOKEN"
    )
    return resp


@logs_bp.route("/stats", methods=["OPTIONS"])
def handle_stats_options():
    """处理CORS预检请求"""
    from flask import make_response

    response = make_response("", 200)
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Requested-With, X-XSRF-TOKEN"
    )
    return response


@logs_bp.route("/stats", methods=["GET"])
@require_auth
@require_roles("admin", "editor")
@log_user_action("VIEW_LOG_STATS")
def get_log_stats():
    """获取日志统计信息"""
    try:
        return jsonify({"code": 0, "message": "success", "data": get_log_stats_data()})
    except Exception as e:
        return (
            jsonify(
                {"code": 5000, "message": f"获取统计信息失败: {str(e)}", "data": None}
            ),
            500,
        )


@logs_bp.route("/<int:log_id>", methods=["GET"])
@require_auth
@require_roles("admin", "editor")
@log_user_action("VIEW_LOG_DETAIL")
def get_log_detail(log_id: int):
    """获取日志详情"""
    try:
        data = get_log_detail_data(log_id)
        return jsonify({"code": 0, "message": "success", "data": data})
    except Exception as e:
        return (
            jsonify(
                {"code": 5000, "message": f"获取日志详情失败: {str(e)}", "data": None}
            ),
            500,
        )


@logs_bp.route("/export", methods=["GET"])
@require_auth
@require_roles("admin")
@log_user_action("EXPORT_LOGS")
def export_logs():
    """导出日志"""
    try:
        level = request.args.get("level", "").upper()
        source = request.args.get("source", "")
        keyword = request.args.get("keyword", "")
        start_time = request.args.get("start_time", "")
        end_time = request.args.get("end_time", "")
        request.args.get("format", "json").lower()
        limit = min(int(request.args.get("limit", 1000)), 5000)  # 限制导出数量

        query = build_log_query(level, source, keyword, start_time, end_time)
        logs = query.order_by(LogEntry.timestamp.desc()).limit(limit).all()
        logs_data = [log.to_dict() for log in logs]

        return jsonify(
            {
                "code": 0,
                "message": "success",
                "data": {
                    "logs": logs_data,
                    "total": len(logs_data),
                    "export_time": datetime.utcnow().isoformat(),
                    "filters": {
                        "level": level,
                        "source": source,
                        "keyword": keyword,
                        "start_time": start_time,
                        "end_time": end_time,
                    },
                },
            }
        )
    except Exception as e:
        return (
            jsonify({"code": 5000, "message": f"导出日志失败: {str(e)}", "data": None}),
            500,
        )


@logs_bp.route("/cleanup", methods=["OPTIONS"])
def handle_cleanup_options():
    from flask import make_response

    resp = make_response("", 200)
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Requested-With, X-XSRF-TOKEN"
    )
    return resp


@logs_bp.route("/cleanup", methods=["POST"])
@require_auth
@require_roles("admin")
@log_user_action("CLEANUP_LOGS")
def cleanup_logs():
    try:
        data = request.get_json() or {}
        days = data.get("days", get_log_config("max_log_days", 30))
        if days < 1:
            return (
                jsonify({"code": 4000, "message": "保留天数不能少于1天", "data": None}),
                400,
            )
        deleted_count = cleanup_old_logs(days)
        return jsonify(
            {
                "code": 0,
                "message": "success",
                "data": {"deleted_count": deleted_count, "days": days},
            }
        )
    except Exception as e:
        return (
            jsonify({"code": 5000, "message": f"清理日志失败: {str(e)}", "data": None}),
            500,
        )


@logs_bp.route("/config", methods=["OPTIONS"])
def handle_config_options():
    """处理CORS预检请求"""
    from flask import make_response

    response = make_response("", 200)
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Requested-With, X-XSRF-TOKEN"
    )
    return response


@logs_bp.route("/config", methods=["GET"])
@require_auth
@require_roles("admin")
def get_log_config_list():
    """获取日志配置"""
    try:
        return jsonify(
            {"code": 0, "message": "success", "data": get_log_config_list_data()}
        )
    except Exception as e:
        return (
            jsonify({"code": 5000, "message": f"获取配置失败: {str(e)}", "data": None}),
            500,
        )


@logs_bp.route("/config", methods=["POST"])
@require_auth
@require_roles("admin")
@log_user_action("UPDATE_LOG_CONFIG")
def update_log_config():
    """更新日志配置"""
    try:
        data = request.get_json()
        if not data:
            return (
                jsonify({"code": 4000, "message": "请求数据不能为空", "data": None}),
                400,
            )

        config_key = data.get("config_key")
        config_value = data.get("config_value")

        if not config_key or config_value is None:
            return (
                jsonify({"code": 4000, "message": "配置键和值不能为空", "data": None}),
                400,
            )

        config = upsert_log_config(config_key, config_value, data.get("description", ""))
        return jsonify(
            {
                "code": 0,
                "message": "success",
                "data": {
                    "config_key": config.config_key,
                    "config_value": config.config_value,
                },
            }
        )
    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"code": 5000, "message": f"更新配置失败: {str(e)}", "data": None}),
            500,
        )


@logs_bp.route("/sources", methods=["OPTIONS"])
def handle_sources_options():
    """处理CORS预检请求"""
    from flask import make_response

    response = make_response("", 200)
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Requested-With, X-XSRF-TOKEN"
    )
    return response


@logs_bp.route("/sources", methods=["GET"])
@require_auth
@require_roles("admin", "editor")
def get_log_sources():
    """获取日志来源列表"""
    try:
        return jsonify(
            {"code": 0, "message": "success", "data": get_log_sources_data()}
        )
    except Exception as e:
        return (
            jsonify(
                {"code": 5000, "message": f"获取日志来源失败: {str(e)}", "data": None}
            ),
            500,
        )


@logs_bp.route("/users", methods=["GET"])
@require_auth
@require_roles("admin", "editor")
def get_log_users():
    """获取有日志记录的用户列表"""
    try:
        return jsonify({"code": 0, "message": "success", "data": get_log_users_data()})
    except Exception as e:
        return (
            jsonify(
                {"code": 5000, "message": f"获取用户列表失败: {str(e)}", "data": None}
            ),
            500,
        )
