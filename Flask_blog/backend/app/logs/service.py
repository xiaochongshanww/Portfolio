"""日志管理业务逻辑层 — 供 routes.py 编排调用。"""

from datetime import datetime, timedelta

from sqlalchemy import and_, desc, func

from .. import db
from ..models import LogConfig, LogEntry, User
from ..utils.logging_utils import LogLevel


def query_logs_common(
    page: int,
    size: int,
    level: str,
    source: str,
    keyword: str,
    user_id,
    request_id,
    start_time,
    end_time,
):
    """按过滤条件分页查询日志。"""
    query = LogEntry.query
    if level and level in [
        LogLevel.ERROR,
        LogLevel.WARNING,
        LogLevel.INFO,
        LogLevel.DEBUG,
    ]:
        query = query.filter(LogEntry.level == level)
    if source:
        query = query.filter(LogEntry.source.ilike(f"%{source}%"))
    if keyword:
        query = query.filter(LogEntry.message.ilike(f"%{keyword}%"))
    if user_id:
        query = query.filter(LogEntry.user_id == user_id)
    if request_id:
        query = query.filter(LogEntry.request_id == request_id)
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            query = query.filter(LogEntry.timestamp >= start_dt)
        except ValueError:
            pass
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            query = query.filter(LogEntry.timestamp <= end_dt)
        except ValueError:
            pass
    total = query.count()
    logs = (
        query.order_by(desc(LogEntry.timestamp))
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    logs_data = []
    for log in logs:
        d = log.to_dict()
        if log.user:
            d["user_name"] = log.user.nickname or log.user.email
        logs_data.append(d)
    return total, logs_data


def build_log_query(
    level: str,
    source: str,
    keyword: str,
    start_time: str,
    end_time: str,
):
    """构建日志查询（与 query_logs_common 相同的过滤逻辑），供导出使用。"""
    query = LogEntry.query
    if level and level in [
        LogLevel.ERROR,
        LogLevel.WARNING,
        LogLevel.INFO,
        LogLevel.DEBUG,
    ]:
        query = query.filter(LogEntry.level == level)
    if source:
        query = query.filter(LogEntry.source.ilike(f"%{source}%"))
    if keyword:
        query = query.filter(LogEntry.message.ilike(f"%{keyword}%"))
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            query = query.filter(LogEntry.timestamp >= start_dt)
        except ValueError:
            pass
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            query = query.filter(LogEntry.timestamp <= end_dt)
        except ValueError:
            pass
    return query


def get_log_stats_data() -> dict:
    """获取日志统计信息。"""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)

    # 基础统计
    stats = {
        "total": LogEntry.query.count(),
        "today": LogEntry.query.filter(LogEntry.timestamp >= today).count(),
        "this_week": LogEntry.query.filter(LogEntry.timestamp >= week_ago).count(),
    }

    # 按级别统计
    level_stats = (
        db.session.query(LogEntry.level, func.count(LogEntry.id).label("count"))
        .group_by(LogEntry.level)
        .all()
    )
    stats["level_distribution"] = {level: count for level, count in level_stats}

    # 按来源统计
    source_stats = (
        db.session.query(LogEntry.source, func.count(LogEntry.id).label("count"))
        .group_by(LogEntry.source)
        .limit(10)
        .all()
    )
    stats["source_distribution"] = {source: count for source, count in source_stats}

    # 今日错误和警告数
    stats["errors"] = LogEntry.query.filter(
        and_(LogEntry.level == LogLevel.ERROR, LogEntry.timestamp >= today)
    ).count()
    stats["warnings"] = LogEntry.query.filter(
        and_(LogEntry.level == LogLevel.WARNING, LogEntry.timestamp >= today)
    ).count()

    # 最近7天的趋势
    trend_data = []
    for i in range(7):
        day = today - timedelta(days=i)
        next_day = day + timedelta(days=1)
        day_count = LogEntry.query.filter(
            and_(LogEntry.timestamp >= day, LogEntry.timestamp < next_day)
        ).count()
        trend_data.append({"date": day.strftime("%Y-%m-%d"), "count": day_count})
    stats["weekly_trend"] = list(reversed(trend_data))

    return stats


def get_log_detail_data(log_id: int) -> dict:
    """获取日志详情及其同请求链路的关联日志。"""
    log_entry = LogEntry.query.get_or_404(log_id)

    related_logs = []
    if log_entry.request_id:
        related_logs = (
            LogEntry.query.filter(
                and_(
                    LogEntry.request_id == log_entry.request_id,
                    LogEntry.id != log_id,
                )
            )
            .order_by(LogEntry.timestamp)
            .all()
        )

    return {
        "log": log_entry.to_dict(),
        "related_logs": [log.to_dict() for log in related_logs],
    }


def get_log_config_list_data() -> list:
    """获取日志配置列表。"""
    configs = LogConfig.query.all()
    config_data = []
    for config in configs:
        config_data.append(
            {
                "id": config.id,
                "config_key": config.config_key,
                "config_value": config.config_value,
                "description": config.description,
                "created_at": (
                    config.created_at.isoformat() if config.created_at else None
                ),
                "updated_at": (
                    config.updated_at.isoformat() if config.updated_at else None
                ),
            }
        )
    return config_data


def upsert_log_config(
    config_key: str, config_value, description: str = ""
) -> LogConfig:
    """创建或更新日志配置，返回配置记录。"""
    config = LogConfig.query.filter_by(config_key=config_key).first()
    if config:
        config.config_value = str(config_value)
        config.updated_at = datetime.utcnow()
    else:
        config = LogConfig(
            config_key=config_key,
            config_value=str(config_value),
            description=description,
        )
        db.session.add(config)
    db.session.commit()
    return config


def get_log_sources_data() -> list:
    """获取日志来源列表。"""
    sources = (
        db.session.query(LogEntry.source).distinct().order_by(LogEntry.source).all()
    )
    return [source[0] for source in sources if source[0]]


def get_log_users_data() -> list:
    """获取有日志记录的用户列表。"""
    users = (
        db.session.query(User.id, User.nickname, User.email)
        .join(LogEntry, User.id == LogEntry.user_id)
        .distinct()
        .order_by(User.nickname)
        .all()
    )
    user_list = []
    for user in users:
        user_list.append(
            {
                "id": user.id,
                "name": user.nickname or user.email,
                "email": user.email,
            }
        )
    return user_list
