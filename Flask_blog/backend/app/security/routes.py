from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from .. import db, require_auth, require_roles
from ..models import User, Article, Comment
import logging
import json
import random
import time
from typing import Dict, List, Any

security_bp = Blueprint('security', __name__)

# 安全日志配置
security_logger = logging.getLogger('security')

# 模拟数据生成器（实际环境中应该从真实的安全监控系统获取数据）
class SecurityDataGenerator:
    @staticmethod
    def generate_threat_level() -> Dict[str, Any]:
        """生成威胁等级数据"""
        # 在实际环境中，这些数据应该从安全监控系统获取
        threat_scores = {
            'low': random.randint(0, 5),
            'medium': random.randint(6, 20),
            'high': random.randint(21, 50),
            'critical': random.randint(51, 100)
        }
        
        current_score = random.choice(list(threat_scores.values()))
        
        if current_score <= 5:
            return {'level': 'low', 'text': '低危', 'class': 'low', 'score': current_score}
        elif current_score <= 20:
            return {'level': 'medium', 'text': '警戒', 'class': 'medium', 'score': current_score}
        elif current_score <= 50:
            return {'level': 'high', 'text': '中危', 'class': 'high', 'score': current_score}
        else:
            return {'level': 'critical', 'text': '高危', 'class': 'critical', 'score': current_score}
    
    @staticmethod
    def generate_security_events(limit: int = 10) -> List[Dict[str, Any]]:
        """生成安全事件数据"""
        event_types = [
            'brute_force_attack',
            'sql_injection', 
            'xss_attack',
            'user_behavior_anomaly',
            'login_failure',
            'suspicious_access'
        ]
        
        severities = ['low', 'medium', 'high', 'critical']
        
        events = []
        for i in range(limit):
            event = {
                'id': f'evt_{datetime.now().strftime("%Y%m%d")}_{1000 + i}',
                'timestamp': (datetime.now() - timedelta(minutes=random.randint(1, 1440))).isoformat(),
                'type': random.choice(event_types),
                'severity': random.choice(severities),
                'source_ip': f'192.168.1.{random.randint(1, 254)}',
                'user_id': random.randint(1, 100) if random.random() > 0.3 else None,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'description': SecurityDataGenerator._generate_event_description(),
                'handled': random.random() > 0.7,
                'raw_data': {
                    'request_path': f'/api/endpoint_{random.randint(1, 10)}',
                    'method': random.choice(['GET', 'POST', 'PUT', 'DELETE']),
                    'status_code': random.choice([200, 400, 401, 403, 500]),
                    'response_time': random.uniform(0.1, 5.0)
                }
            }
            events.append(event)
        
        return sorted(events, key=lambda x: x['timestamp'], reverse=True)
    
    @staticmethod
    def _generate_event_description() -> str:
        descriptions = [
            "检测到多次登录失败尝试",
            "发现可疑的SQL查询模式",
            "检测到XSS攻击载荷",
            "用户访问模式异常",
            "IP地址访问频率过高",
            "检测到潜在的文件上传攻击",
            "发现异常的API调用模式",
            "检测到暴力破解尝试"
        ]
        return random.choice(descriptions)

@security_bp.route('/stats', methods=['GET'])
@require_roles('editor', 'admin')
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
        
        # 今日评论数量（活跃度指标）
        comments_today = Comment.query.filter(Comment.created_at >= today_start).count()
        
        # 模拟其他安全数据
        stats = {
            'todayEvents': random.randint(5, 50),
            'eventsTrend': random.randint(-10, 15),
            'blockedAttacks': random.randint(10, 100),
            'blockedToday': random.randint(1, 20),
            'anomalousUsers': min(new_users_today, random.randint(0, 5)),
            'userTrend': random.randint(-5, 8),
            'threatLevel': SecurityDataGenerator.generate_threat_level()
        }
        
        security_logger.info(f"安全统计数据已请求: {stats}")
        
        return jsonify({
            'code': 0,
            'message': 'ok',
            'data': stats
        })
        
    except Exception as e:
        security_logger.error(f"获取安全统计失败: {str(e)}")
        return jsonify({
            'code': 5000,
            'message': '获取安全统计失败',
            'data': None
        }), 500

@security_bp.route('/system-health', methods=['GET'])
@require_roles('editor', 'admin')
def get_system_health():
    """获取系统健康状态"""
    try:
        import psutil
        import os
        
        # 获取真实系统指标
        # CPU 信息 - 使用更短的间隔避免阻塞
        cpu_percent = psutil.cpu_percent(interval=0.1)  # 减少间隔时间
        cpu_count_logical = psutil.cpu_count(logical=True)   # 逻辑核心数（包括超线程）
        cpu_count_physical = psutil.cpu_count(logical=False) # 物理核心数
        
        # 内存信息
        memory_info = psutil.virtual_memory()
        memory_percent = memory_info.percent
        memory_total_gb = memory_info.total / (1024**3)
        
        # 磁盘信息 (根据操作系统选择根目录)
        if os.name == 'nt':  # Windows
            disk_usage = psutil.disk_usage('C:\\')
        else:  # Linux/Unix
            disk_usage = psutil.disk_usage('/')
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        disk_total_gb = disk_usage.total / (1024**3)
        
        # 网络流量 (获取网络接口统计)
        network_io = psutil.net_io_counters()
        if network_io:
            # 简化的网络速率模拟（实际生产中应该计算差值）
            network_in = min(network_io.bytes_recv % 100000, 50000)
            network_out = min(network_io.bytes_sent % 50000, 25000)
        else:
            network_in = random.randint(1000, 10000)
            network_out = random.randint(500, 5000)
        
        # 系统运行时间
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_hours = uptime_seconds / 3600
        
        # 进程数量
        process_count = len(psutil.pids())
        
        health_data = {
            'cpu': round(cpu_percent, 1),
            'memory': round(memory_percent, 1),
            'disk': round(disk_percent, 1),
            'networkIn': int(network_in),
            'networkOut': int(network_out),
            # 详细系统信息
            'uptime_hours': round(uptime_hours, 1),
            'process_count': process_count,
            'memory_total_gb': round(memory_total_gb, 1),  # 四舍五入到1位小数
            'disk_total_gb': round(disk_total_gb, 0),      # 四舍五入到整数
            'cpu_count': cpu_count_logical,                # 使用逻辑核心数
            'cpu_count_physical': cpu_count_physical,      # 添加物理核心数
            # 新增详细CPU信息
            'cpu_freq': round(psutil.cpu_freq().current, 0) if psutil.cpu_freq() else 0,  # CPU频率
        }
        
        return jsonify({
            'code': 0,
            'message': 'ok',
            'data': health_data
        })
        
    except ImportError as e:
        security_logger.warning(f"psutil未安装，使用模拟数据: {str(e)}")
        # 如果没有安装psutil，使用模拟数据
        health_data = {
            'cpu': round(random.uniform(10, 80), 1),
            'memory': round(random.uniform(20, 90), 1),
            'disk': round(random.uniform(30, 85), 1),
            'networkIn': random.randint(1000, 10000),
            'networkOut': random.randint(500, 5000),
            'uptime_hours': random.uniform(1, 100),
            'process_count': random.randint(50, 200),
            'memory_total_gb': 32.0,        # 修正为32GB
            'disk_total_gb': 1907.0,        # 修正为实际磁盘大小
            'cpu_count': 8,                 # 修正为8核
            'cpu_count_physical': 8,        # 物理核心数
            'cpu_freq': 3000               # 模拟CPU频率
        }
        
        return jsonify({
            'code': 0,
            'message': 'ok (模拟数据)',
            'data': health_data
        })
        
    except Exception as e:
        security_logger.error(f"获取系统健康状态失败: {str(e)}")
        return jsonify({
            'code': 5000,
            'message': '获取系统健康状态失败',
            'data': None
        }), 500

@security_bp.route('/events/recent', methods=['GET'])
@require_roles('editor', 'admin')
def get_recent_security_events():
    """获取最近的安全事件"""
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 100)  # 限制最大返回数量
        
        # 生成模拟的安全事件数据
        events = SecurityDataGenerator.generate_security_events(limit)
        
        return jsonify({
            'code': 0,
            'message': 'ok',
            'data': events
        })
        
    except Exception as e:
        security_logger.error(f"获取安全事件失败: {str(e)}")
        return jsonify({
            'code': 5000,
            'message': '获取安全事件失败',
            'data': None
        }), 500

@security_bp.route('/access-stats/today', methods=['GET'])
@require_roles('editor', 'admin')
def get_today_access_stats():
    """获取今日访问统计"""
    try:
        # 在实际环境中，这些数据应该从日志分析系统获取
        stats = {
            'totalVisits': random.randint(100, 1000),
            'uniqueIPs': random.randint(50, 300),
            'suspiciousVisits': random.randint(0, 20),
            'blockedRequests': random.randint(0, 50)
        }
        
        return jsonify({
            'code': 0,
            'message': 'ok',
            'data': stats
        })
        
    except Exception as e:
        security_logger.error(f"获取访问统计失败: {str(e)}")
        return jsonify({
            'code': 5000,
            'message': '获取访问统计失败',
            'data': None
        }), 500

@security_bp.route('/events/<event_id>/handle', methods=['POST'])
@require_roles('editor', 'admin')
def handle_security_event(event_id):
    """处理安全事件"""
    try:
        # 在实际环境中，这里应该更新安全事件的处理状态
        security_logger.info(f"安全事件 {event_id} 已被用户处理")
        
        return jsonify({
            'code': 0,
            'message': '事件处理成功',
            'data': {'event_id': event_id, 'handled': True}
        })
        
    except Exception as e:
        security_logger.error(f"处理安全事件失败: {str(e)}")
        return jsonify({
            'code': 5000,
            'message': '处理事件失败',
            'data': None
        }), 500

@security_bp.route('/block-ip', methods=['POST'])
@require_roles('admin')
def block_ip_address():
    """封禁IP地址"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address')
        
        if not ip_address:
            return jsonify({
                'code': 4001,
                'message': 'IP地址不能为空'
            }), 400
        
        # 在实际环境中，这里应该调用防火墙API或更新IP黑名单
        security_logger.warning(f"IP地址 {ip_address} 已被管理员封禁")
        
        # 模拟封禁操作成功
        return jsonify({
            'code': 0,
            'message': f'IP地址 {ip_address} 封禁成功',
            'data': {'ip_address': ip_address, 'blocked_at': datetime.now().isoformat()}
        })
        
    except Exception as e:
        security_logger.error(f"封禁IP失败: {str(e)}")
        return jsonify({
            'code': 5000,
            'message': '封禁IP失败',
            'data': None
        }), 500

@security_bp.route('/suspend-user', methods=['POST'])
@require_roles('admin')
def suspend_user_account():
    """暂停用户账户"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                'code': 4001,
                'message': '用户ID不能为空'
            }), 400
        
        # 查找用户
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'code': 4040,
                'message': '用户不存在'
            }), 404
        
        # 在实际环境中，这里应该添加用户暂停逻辑
        # 例如添加一个suspended字段或状态字段
        security_logger.warning(f"用户 {user.email} (ID: {user_id}) 已被管理员暂停")
        
        return jsonify({
            'code': 0,
            'message': f'用户 {user.email} 暂停成功',
            'data': {'user_id': user_id, 'suspended_at': datetime.now().isoformat()}
        })
        
    except Exception as e:
        security_logger.error(f"暂停用户失败: {str(e)}")
        return jsonify({
            'code': 5000,
            'message': '暂停用户失败',
            'data': None
        }), 500

@security_bp.route('/enable-protection-mode', methods=['POST'])
@require_roles('admin')
def enable_protection_mode():
    """启用保护模式"""
    try:
        # 在实际环境中，这里应该调整安全策略的敏感度
        security_logger.info("保护模式已被管理员启用")
        
        return jsonify({
            'code': 0,
            'message': '保护模式已启用',
            'data': {
                'protection_mode': True,
                'enabled_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=2)).isoformat()
            }
        })
        
    except Exception as e:
        security_logger.error(f"启用保护模式失败: {str(e)}")
        return jsonify({
            'code': 5000,
            'message': '启用保护模式失败',
            'data': None
        }), 500

@security_bp.route('/report/download', methods=['GET'])
@require_roles('admin')
def download_security_report():
    """下载安全报告"""
    try:
        from flask import make_response
        import io
        
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
        response.headers['Content-Type'] = 'application/octet-stream'
        response.headers['Content-Disposition'] = f'attachment; filename=security_report_{datetime.now().strftime("%Y%m%d")}.txt'
        
        security_logger.info("安全报告已被下载")
        return response
        
    except Exception as e:
        security_logger.error(f"生成安全报告失败: {str(e)}")
        return jsonify({
            'code': 5000,
            'message': '生成安全报告失败',
            'data': None
        }), 500

@security_bp.route('/threat-trends', methods=['GET'])
@require_roles('editor', 'admin')
def get_threat_trends():
    """获取威胁趋势数据"""
    try:
        timerange = request.args.get('timerange', '24h')
        
        # 根据时间范围生成模拟数据
        if timerange == '1h':
            # 1小时数据，每5分钟一个点
            data_points = 12
            interval = 5
        elif timerange == '6h':
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
            trends.append({
                'timestamp': point_time.isoformat(),
                'threat_score': random.randint(0, 100),
                'events_count': random.randint(0, 20),
                'blocked_count': random.randint(0, 10)
            })
        
        return jsonify({
            'code': 0,
            'message': 'ok',
            'data': {
                'timerange': timerange,
                'trends': trends
            }
        })
        
    except Exception as e:
        security_logger.error(f"获取威胁趋势失败: {str(e)}")
        return jsonify({
            'code': 5000,
            'message': '获取威胁趋势失败',
            'data': None
        }), 500

# 安全事件记录函数（供其他模块使用）
def log_security_event(event_type: str, description: str, 
                      source_ip: str = None, user_id: int = None, 
                      severity: str = 'low', additional_data: Dict = None):
    """记录安全事件"""
    try:
        event_data = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'description': description,
            'source_ip': source_ip,
            'user_id': user_id,
            'severity': severity,
            'additional_data': additional_data or {}
        }
        
        security_logger.warning(f"安全事件: {json.dumps(event_data, ensure_ascii=False)}")
        
        # 在实际环境中，这里应该将事件写入安全事件数据库
        
    except Exception as e:
        security_logger.error(f"记录安全事件失败: {str(e)}")