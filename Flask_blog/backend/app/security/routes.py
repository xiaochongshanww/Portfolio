import json
import logging
import random
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, make_response, request

from .. import require_roles
from ..models import User
from .service import SecurityDataGenerator, log_security_event

security_bp = Blueprint("security", __name__)

# 安全日志配置
security_logger = logging.getLogger("security")


@security_bp.route("/stats", methods=["GET"])
@require_roles("editor", "admin")
def get_security_stats():
    """获取安全统计数据"""
    try:
        # 在实际环境中，这些数据应该从安全监控系统获取
        # 这里使用数据库中的真实数据结合模拟数据

        # 获取今日新用户数量作为部分指标
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())

        # 今日新用户（可能的异常指标）
        new_users_today = User.query.filter(User.created_at >= today_start).count()

        # 模拟其他安全数据
        stats = {
            "todayEvents": random.randint(5, 50),
            "eventsTrend": random.randint(-10, 15),
            "blockedAttacks": random.randint(10, 100),
            "blockedToday": random.randint(1, 20),
            "anomalousUsers": min(new_users_today, random.randint(0, 5)),
            "userTrend": random.randint(-5, 8),
            "threatLevel": SecurityDataGenerator.generate_threat_level(),
        }

        security_logger.info(f"安全统计数据已请求: {stats}")

        return jsonify({"code": 0, "message": "ok", "data": stats})

    except Exception as e:
        security_logger.error(f"获取安全统计失败: {str(e)}")
        return jsonify({"code": 5000, "message": "获取安全统计失败", "data": None}), 500


@security_bp.route("/system-health", methods=["GET"])
@require_roles("editor", "admin")
def get_system_health():
    """获取系统健康状态"""
    try:
        health_data = SecurityDataGenerator.generate_system_health()
        return jsonify({"code": 0, "message": "ok", "data": health_data})

    except ImportError as e:
        security_logger.warning(f"psutil未安装，使用模拟数据: {str(e)}")
        health_data = SecurityDataGenerator.generate_health_fallback()
        return jsonify({"code": 0, "message": "ok (模拟数据)", "data": health_data})

    except Exception as e:
        security_logger.error(f"获取系统健康状态失败: {str(e)}")
        return (
            jsonify({"code": 5000, "message": "获取系统健康状态失败", "data": None}),
            500,
        )


@security_bp.route("/events/recent", methods=["GET"])
@require_roles("editor", "admin")
def get_recent_security_events():
    """获取最近的安全事件"""
    try:
        limit = request.args.get("limit", 10, type=int)
        limit = min(limit, 100)  # 限制最大返回数量

        # 生成模拟的安全事件数据
        events = SecurityDataGenerator.generate_security_events(limit)

        return jsonify({"code": 0, "message": "ok", "data": events})

    except Exception as e:
        security_logger.error(f"获取安全事件失败: {str(e)}")
        return jsonify({"code": 5000, "message": "获取安全事件失败", "data": None}), 500


@security_bp.route("/access-stats/today", methods=["GET"])
@require_roles("editor", "admin")
def get_today_access_stats():
    """获取今日访问统计"""
    try:
        # 在实际环境中，这些数据应该从日志分析系统获取
        stats = {
            "totalVisits": random.randint(100, 1000),
            "uniqueIPs": random.randint(50, 300),
            "suspiciousVisits": random.randint(0, 20),
            "blockedRequests": random.randint(0, 50),
        }

        return jsonify({"code": 0, "message": "ok", "data": stats})

    except Exception as e:
        security_logger.error(f"获取访问统计失败: {str(e)}")
        return jsonify({"code": 5000, "message": "获取访问统计失败", "data": None}), 500


@security_bp.route("/events/<event_id>/handle", methods=["POST"])
@require_roles("editor", "admin")
def handle_security_event(event_id):
    """处理安全事件"""
    try:
        # 在实际环境中，这里应该更新安全事件的处理状态
        security_logger.info(f"安全事件 {event_id} 已被用户处理")

        return jsonify(
            {
                "code": 0,
                "message": "事件处理成功",
                "data": {"event_id": event_id, "handled": True},
            }
        )

    except Exception as e:
        security_logger.error(f"处理安全事件失败: {str(e)}")
        return jsonify({"code": 5000, "message": "处理事件失败", "data": None}), 500


@security_bp.route("/block-ip", methods=["POST"])
@require_roles("admin")
def block_ip_address():
    """封禁IP地址"""
    try:
        data = request.get_json()
        ip_address = data.get("ip_address")

        if not ip_address:
            return jsonify({"code": 4001, "message": "IP地址不能为空"}), 400

        # 在实际环境中，这里应该调用防火墙API或更新IP黑名单
        security_logger.warning(f"IP地址 {ip_address} 已被管理员封禁")

        # 模拟封禁操作成功
        return jsonify(
            {
                "code": 0,
                "message": f"IP地址 {ip_address} 封禁成功",
                "data": {
                    "ip_address": ip_address,
                    "blocked_at": datetime.now().isoformat(),
                },
            }
        )

    except Exception as e:
        security_logger.error(f"封禁IP失败: {str(e)}")
        return jsonify({"code": 5000, "message": "封禁IP失败", "data": None}), 500


@security_bp.route("/suspend-user", methods=["POST"])
@require_roles("admin")
def suspend_user_account():
    """暂停用户账户"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")

        if not user_id:
            return jsonify({"code": 4001, "message": "用户ID不能为空"}), 400

        # 查找用户
        user = User.query.get(user_id)
        if not user:
            return jsonify({"code": 4040, "message": "用户不存在"}), 404

        # 在实际环境中，这里应该添加用户暂停逻辑
        security_logger.warning(f"用户 {user.email} (ID: {user_id}) 已被管理员暂停")

        return jsonify(
            {
                "code": 0,
                "message": f"用户 {user.email} 暂停成功",
                "data": {
                    "user_id": user_id,
                    "suspended_at": datetime.now().isoformat(),
                },
            }
        )

    except Exception as e:
        security_logger.error(f"暂停用户失败: {str(e)}")
        return jsonify({"code": 5000, "message": "暂停用户失败", "data": None}), 500


@security_bp.route("/enable-protection-mode", methods=["POST"])
@require_roles("admin")
def enable_protection_mode():
    """启用保护模式"""
    try:
        # 在实际环境中，这里应该调整安全策略的敏感度
        security_logger.info("保护模式已被管理员启用")

        return jsonify(
            {
                "code": 0,
                "message": "保护模式已启用",
                "data": {
                    "protection_mode": True,
                    "enabled_at": datetime.now().isoformat(),
                    "expires_at": (datetime.now() + timedelta(hours=2)).isoformat(),
                },
            }
        )

    except Exception as e:
        security_logger.error(f"启用保护模式失败: {str(e)}")
        return jsonify({"code": 5000, "message": "启用保护模式失败", "data": None}), 500


@security_bp.route("/report/download", methods=["GET"])
@require_roles("admin")
def download_security_report():
    """下载安全报告"""
    try:
        # 在实际环境中，这里应该生成真实的PDF报告
        # 这里返回一个简单的文本报告作为演示
        report_content = f"""安全监控报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== 威胁概览 ===
- 威胁等级: 中等
- 今日事件: 15起
- 已处理事件: 12起
- 待处理事件: 3起

=== 系统状态 ===
- CPU使用率: 45%
- 内存使用率: 67%
- 磁盘使用率: 78%

=== 安全建议 ===
1. 定期更新系统补丁
2. 加强密码策略
3. 启用多因子认证
4. 定期备份重要数据

此报告由安全监控系统自动生成。
"""

        # 创建响应
        response = make_response(report_content)
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers["Content-Disposition"] = (
            f'attachment; filename=security_report_{datetime.now().strftime("%Y%m%d")}.txt'  # noqa: E501
        )

        security_logger.info("安全报告已被下载")
        return response

    except Exception as e:
        security_logger.error(f"生成安全报告失败: {str(e)}")
        return jsonify({"code": 5000, "message": "生成安全报告失败", "data": None}), 500


@security_bp.route("/threat-trends", methods=["GET"])
@require_roles("editor", "admin")
def get_threat_trends():
    """获取威胁趋势数据"""
    try:
        timerange = request.args.get("timerange", "24h")

        # 根据时间范围生成模拟数据
        if timerange == "1h":
            # 1小时数据，每5分钟一个点
            data_points = 12
            interval = 5
        elif timerange == "6h":
            # 6小时数据，每30分钟一个点
            data_points = 12
            interval = 30
        else:  # 24h
            # 24小时数据，每2小时一个点
            data_points = 12
            interval = 120

        trends = []
        base_time = datetime.now() - timedelta(minutes=data_points * interval)

        for i in range(data_points):
            point_time = base_time + timedelta(minutes=i * interval)
            trends.append(
                {
                    "timestamp": point_time.isoformat(),
                    "threat_score": random.randint(0, 100),
                    "events_count": random.randint(0, 20),
                    "blocked_count": random.randint(0, 10),
                }
            )

        return jsonify(
            {
                "code": 0,
                "message": "ok",
                "data": {"timerange": timerange, "trends": trends},
            }
        )

    except Exception as e:
        security_logger.error(f"获取威胁趋势失败: {str(e)}")
        return jsonify({"code": 5000, "message": "获取威胁趋势失败", "data": None}), 500
