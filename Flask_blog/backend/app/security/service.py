"""安全监控业务逻辑层 — 供 routes.py 编排调用。

包含模拟安全数据生成器与安全事件记录函数。
"""

import json
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# 安全日志配置
security_logger = logging.getLogger("security")


class SecurityDataGenerator:
    """模拟数据生成器（实际环境中应该从真实的安全监控系统获取数据）"""

    @staticmethod
    def generate_threat_level() -> Dict[str, Any]:
        """生成威胁等级数据"""
        # 在实际环境中，这些数据应该从安全监控系统获取
        threat_scores = {
            "low": random.randint(0, 5),
            "medium": random.randint(6, 20),
            "high": random.randint(21, 50),
            "critical": random.randint(51, 100),
        }

        current_score = random.choice(list(threat_scores.values()))

        if current_score <= 5:
            return {
                "level": "low",
                "text": "低危",
                "class": "low",
                "score": current_score,
            }
        elif current_score <= 20:
            return {
                "level": "medium",
                "text": "警戒",
                "class": "medium",
                "score": current_score,
            }
        elif current_score <= 50:
            return {
                "level": "high",
                "text": "中危",
                "class": "high",
                "score": current_score,
            }
        else:
            return {
                "level": "critical",
                "text": "高危",
                "class": "critical",
                "score": current_score,
            }

    @staticmethod
    def generate_security_events(limit: int = 10) -> List[Dict[str, Any]]:
        """生成安全事件数据"""
        event_types = [
            "brute_force_attack",
            "sql_injection",
            "xss_attack",
            "user_behavior_anomaly",
            "login_failure",
            "suspicious_access",
        ]

        severities = ["low", "medium", "high", "critical"]

        events = []
        for i in range(limit):
            event = {
                "id": f'evt_{datetime.now().strftime("%Y%m%d")}_{1000 + i}',
                "timestamp": (
                    datetime.now() - timedelta(minutes=random.randint(1, 1440))
                ).isoformat(),
                "type": random.choice(event_types),
                "severity": random.choice(severities),
                "source_ip": f"192.168.1.{random.randint(1, 254)}",
                "user_id": random.randint(1, 100) if random.random() > 0.3 else None,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",  # noqa: E501
                "description": SecurityDataGenerator._generate_event_description(),
                "handled": random.random() > 0.7,
                "raw_data": {
                    "request_path": f"/api/endpoint_{random.randint(1, 10)}",
                    "method": random.choice(["GET", "POST", "PUT", "DELETE"]),
                    "status_code": random.choice([200, 400, 401, 403, 500]),
                    "response_time": random.uniform(0.1, 5.0),
                },
            }
            events.append(event)

        return sorted(events, key=lambda x: x["timestamp"], reverse=True)

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
            "检测到暴力破解尝试",
        ]
        return random.choice(descriptions)

    @staticmethod
    def generate_system_health() -> Dict[str, Any]:
        """生成系统健康状态（含 psutil 真实指标与模拟降级）"""
        import os
        import time

        import psutil

        # 获取真实系统指标
        # CPU 信息 - 使用更短的间隔避免阻塞
        cpu_percent = psutil.cpu_percent(interval=0.1)  # 减少间隔时间
        cpu_count_logical = psutil.cpu_count(logical=True)  # 逻辑核心数（包括超线程）
        cpu_count_physical = psutil.cpu_count(logical=False)  # 物理核心数

        # 内存信息
        memory_info = psutil.virtual_memory()
        memory_percent = memory_info.percent
        memory_total_gb = memory_info.total / (1024**3)

        # 磁盘信息 (根据操作系统选择根目录)
        if os.name == "nt":  # Windows
            disk_usage = psutil.disk_usage("C:\\")
        else:  # Linux/Unix
            disk_usage = psutil.disk_usage("/")
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

        return {
            "cpu": round(cpu_percent, 1),
            "memory": round(memory_percent, 1),
            "disk": round(disk_percent, 1),
            "networkIn": int(network_in),
            "networkOut": int(network_out),
            "uptime_hours": round(uptime_hours, 1),
            "process_count": process_count,
            "memory_total_gb": round(memory_total_gb, 1),  # 四舍五入到1位小数
            "disk_total_gb": round(disk_total_gb, 0),  # 四舍五入到整数
            "cpu_count": cpu_count_logical,  # 使用逻辑核心数
            "cpu_count_physical": cpu_count_physical,  # 添加物理核心数
            "cpu_freq": (
                round(psutil.cpu_freq().current, 0) if psutil.cpu_freq() else 0
            ),  # CPU频率
        }

    @staticmethod
    def generate_health_fallback() -> Dict[str, Any]:
        """生成系统健康状态的模拟降级数据（psutil 不可用时）"""
        return {
            "cpu": round(random.uniform(10, 80), 1),
            "memory": round(random.uniform(20, 90), 1),
            "disk": round(random.uniform(30, 85), 1),
            "networkIn": random.randint(1000, 10000),
            "networkOut": random.randint(500, 5000),
            "uptime_hours": random.uniform(1, 100),
            "process_count": random.randint(50, 200),
            "memory_total_gb": 32.0,
            "disk_total_gb": 1907.0,
            "cpu_count": 8,
            "cpu_count_physical": 8,
            "cpu_freq": 3000,
        }


def log_security_event(
    event_type: str,
    description: str,
    source_ip: Optional[str] = None,
    user_id: Optional[int] = None,
    severity: str = "low",
    additional_data: Optional[Dict] = None,
):
    """记录安全事件"""
    try:
        event_data = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "description": description,
            "source_ip": source_ip,
            "user_id": user_id,
            "severity": severity,
            "additional_data": additional_data or {},
        }

        security_logger.warning(
            f"安全事件: {json.dumps(event_data, ensure_ascii=False)}"
        )

        # 在实际环境中，这里应该将事件写入安全事件数据库

    except Exception as e:
        security_logger.error(f"记录安全事件失败: {str(e)}")
