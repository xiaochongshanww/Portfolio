import logging

from flask import Blueprint, jsonify, request

from .. import require_roles
from .service import (
    DEFAULT_SETTINGS,
    cleanup_logs_operation,
    clear_cache_operation,
    create_backup_operation,
    generate_sitemap_operation,
    get_backup_history_data,
    get_system_info_data,
    load_settings,
    optimize_database_operation,
    save_settings,
)

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/all", methods=["GET"])
@require_roles("admin")
def get_all_settings():
    """获取所有设置"""
    try:
        settings = load_settings()
        return jsonify({"code": 0, "message": "ok", "data": settings})
    except Exception as e:
        logging.error(f"获取设置失败: {e}")
        return jsonify({"code": 5000, "message": "获取设置失败", "data": None}), 500


@settings_bp.route("/general", methods=["GET"])
@require_roles("admin")
def get_general_settings():
    """获取基本设置"""
    try:
        settings = load_settings()
        return jsonify(
            {
                "code": 0,
                "message": "ok",
                "data": settings.get("general", DEFAULT_SETTINGS["general"]),
            }
        )
    except Exception as e:
        logging.error(f"获取基本设置失败: {e}")
        return jsonify({"code": 5000, "message": "获取基本设置失败", "data": None}), 500


@settings_bp.route("/general", methods=["PUT"])
@require_roles("admin")
def update_general_settings():
    """更新基本设置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 4001, "message": "无效的数据格式"}), 400

        settings = load_settings()
        settings["general"].update(data)

        if save_settings(settings):
            return jsonify(
                {"code": 0, "message": "基本设置保存成功", "data": settings["general"]}
            )
        else:
            return jsonify({"code": 5000, "message": "保存设置失败"}), 500

    except Exception as e:
        logging.error(f"更新基本设置失败: {e}")
        return jsonify({"code": 5000, "message": "更新基本设置失败", "data": None}), 500


@settings_bp.route("/content", methods=["GET"])
@require_roles("admin")
def get_content_settings():
    """获取内容设置"""
    try:
        settings = load_settings()
        return jsonify(
            {
                "code": 0,
                "message": "ok",
                "data": settings.get("content", DEFAULT_SETTINGS["content"]),
            }
        )
    except Exception as e:
        logging.error(f"获取内容设置失败: {e}")
        return jsonify({"code": 5000, "message": "获取内容设置失败", "data": None}), 500


@settings_bp.route("/content", methods=["PUT"])
@require_roles("admin")
def update_content_settings():
    """更新内容设置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 4001, "message": "无效的数据格式"}), 400

        settings = load_settings()
        settings["content"].update(data)

        if save_settings(settings):
            return jsonify(
                {"code": 0, "message": "内容设置保存成功", "data": settings["content"]}
            )
        else:
            return jsonify({"code": 5000, "message": "保存设置失败"}), 500

    except Exception as e:
        logging.error(f"更新内容设置失败: {e}")
        return jsonify({"code": 5000, "message": "更新内容设置失败", "data": None}), 500


@settings_bp.route("/security", methods=["GET"])
@require_roles("admin")
def get_security_settings():
    """获取安全设置"""
    try:
        settings = load_settings()
        return jsonify(
            {
                "code": 0,
                "message": "ok",
                "data": settings.get("security", DEFAULT_SETTINGS["security"]),
            }
        )
    except Exception as e:
        logging.error(f"获取安全设置失败: {e}")
        return jsonify({"code": 5000, "message": "获取安全设置失败", "data": None}), 500


@settings_bp.route("/security", methods=["PUT"])
@require_roles("admin")
def update_security_settings():
    """更新安全设置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"code": 4001, "message": "无效的数据格式"}), 400

        settings = load_settings()
        settings["security"].update(data)

        if save_settings(settings):
            return jsonify(
                {"code": 0, "message": "安全设置保存成功", "data": settings["security"]}
            )
        else:
            return jsonify({"code": 5000, "message": "保存设置失败"}), 500

    except Exception as e:
        logging.error(f"更新安全设置失败: {e}")
        return jsonify({"code": 5000, "message": "更新安全设置失败", "data": None}), 500


@settings_bp.route("/system/info", methods=["GET"])
@require_roles("admin")
def get_system_info():
    """获取系统信息"""
    try:
        return jsonify({"code": 0, "message": "ok", "data": get_system_info_data()})
    except Exception as e:
        logging.error(f"获取系统信息失败: {e}")
        return jsonify({"code": 5000, "message": "获取系统信息失败", "data": None}), 500


@settings_bp.route("/system/optimize-database", methods=["POST"])
@require_roles("admin")
def optimize_database():
    """优化数据库"""
    try:
        data = optimize_database_operation()
        return jsonify({"code": 0, "message": "数据库优化完成", "data": data})
    except Exception as e:
        logging.error(f"数据库优化失败: {e}")
        return jsonify({"code": 5000, "message": "数据库优化失败", "data": None}), 500


@settings_bp.route("/system/clear-cache", methods=["POST"])
@require_roles("admin")
def clear_cache():
    """清理缓存"""
    try:
        data = clear_cache_operation()
        return jsonify({"code": 0, "message": "缓存清理完成", "data": data})
    except Exception as e:
        logging.error(f"清理缓存失败: {e}")
        return jsonify({"code": 5000, "message": "清理缓存失败", "data": None}), 500


@settings_bp.route("/system/cleanup-logs", methods=["POST"])
@require_roles("admin")
def cleanup_logs():
    """清理日志"""
    try:
        data = cleanup_logs_operation()
        return jsonify({"code": 0, "message": "日志清理完成", "data": data})
    except Exception as e:
        logging.error(f"清理日志失败: {e}")
        return jsonify({"code": 5000, "message": "清理日志失败", "data": None}), 500


@settings_bp.route("/system/generate-sitemap", methods=["POST"])
@require_roles("admin")
def generate_sitemap():
    """生成站点地图"""
    try:
        data = generate_sitemap_operation()
        return jsonify({"code": 0, "message": "站点地图生成完成", "data": data})
    except Exception as e:
        logging.error(f"生成站点地图失败: {e}")
        return jsonify({"code": 5000, "message": "生成站点地图失败", "data": None}), 500


@settings_bp.route("/system/backup", methods=["POST"])
@require_roles("admin")
def create_backup():
    """创建系统备份"""
    try:
        data = create_backup_operation()
        return jsonify({"code": 0, "message": "系统备份创建完成", "data": data})
    except Exception as e:
        logging.error(f"创建系统备份失败: {e}")
        return jsonify({"code": 5000, "message": "创建系统备份失败", "data": None}), 500


@settings_bp.route("/backup/history", methods=["GET"])
@require_roles("admin")
def get_backup_history():
    """获取备份历史"""
    try:
        return jsonify({"code": 0, "message": "ok", "data": get_backup_history_data()})
    except Exception as e:
        logging.error(f"获取备份历史失败: {e}")
        return jsonify({"code": 5000, "message": "获取备份历史失败", "data": None}), 500
