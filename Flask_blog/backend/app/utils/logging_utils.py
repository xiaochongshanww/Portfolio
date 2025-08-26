"""
日志管理工具模块
提供日志收集、装饰器和工具函数
"""

import uuid
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import request, g, current_app
from typing import Optional, Dict, Any
from ..models import LogEntry, LogConfig
from .. import db


class LogLevel:
    """日志级别常量"""
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    INFO = 'INFO'
    DEBUG = 'DEBUG'


class LogSource:
    """日志来源常量"""
    USER_ACTION = 'USER_ACTION'  # 用户行为
    API_REQUEST = 'API_REQUEST'  # API请求
    SYSTEM = 'SYSTEM'  # 系统日志
    DATABASE = 'DATABASE'  # 数据库操作
    AUTH = 'AUTH'  # 认证授权
    SECURITY = 'SECURITY'  # 安全事件
    ERROR = 'ERROR'  # 错误日志


def get_request_info() -> Dict[str, Any]:
    """获取当前请求信息"""
    if not request:
        return {}
    
    return {
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'endpoint': request.endpoint,
        'method': request.method,
        'url': request.url,
        'referrer': request.referrer
    }


def create_log_entry(
    level: str,
    source: str,
    message: str,
    user_id: Optional[int] = None,
    request_id: Optional[str] = None,
    status_code: Optional[int] = None,
    duration_ms: Optional[int] = None,
    extra_data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Optional[LogEntry]:
    """
    创建日志条目
    
    Args:
        level: 日志级别
        source: 日志来源
        message: 日志消息
        user_id: 用户ID
        request_id: 请求ID
        status_code: HTTP状态码
        duration_ms: 请求耗时
        extra_data: 额外数据
        **kwargs: 其他参数
    
    Returns:
        LogEntry对象或None
    """
    try:
        # 获取请求信息
        request_info = get_request_info()
        
        # 创建日志条目
        log_entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=level,
            source=source,
            message=message,
            user_id=user_id or getattr(request, 'user_id', None),
            ip_address=kwargs.get('ip_address', request_info.get('ip_address')),
            user_agent=kwargs.get('user_agent', request_info.get('user_agent')),
            request_id=request_id or getattr(g, 'request_id', None),
            endpoint=kwargs.get('endpoint', request_info.get('endpoint')),
            method=kwargs.get('method', request_info.get('method')),
            status_code=status_code,
            duration_ms=duration_ms,
            extra_data=extra_data or {}
        )
        
        # 异步保存日志（避免影响主业务）
        try:
            db.session.add(log_entry)
            db.session.commit()
            return log_entry
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to save log entry: {str(e)}")
            return None
            
    except Exception as e:
        current_app.logger.error(f"Error creating log entry: {str(e)}")
        return None


def log_user_action(
    action_type: str, 
    level: str = LogLevel.INFO,
    include_request_body: bool = False,
    include_response_body: bool = False
):
    """
    用户行为日志装饰器
    
    Args:
        action_type: 操作类型
        level: 日志级别
        include_request_body: 是否包含请求体
        include_response_body: 是否包含响应体
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成请求ID
            request_id = str(uuid.uuid4())
            g.request_id = request_id
            
            start_time = time.time()
            error_occurred = None
            response = None
            
            try:
                # 执行原函数
                response = f(*args, **kwargs)
                return response
                
            except Exception as e:
                error_occurred = e
                raise
                
            finally:
                # 计算执行时间
                duration_ms = int((time.time() - start_time) * 1000)
                
                # 准备额外数据
                extra_data = {
                    'action': action_type,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys()) if kwargs else []
                }
                
                # 包含请求体（注意敏感信息）
                if include_request_body and hasattr(request, 'json') and request.json:
                    # 过滤敏感字段
                    filtered_body = {k: v for k, v in request.json.items() 
                                   if k.lower() not in ['password', 'token', 'secret']}
                    extra_data['request_body'] = filtered_body
                
                # 包含响应体（仅状态码和基本信息）
                if include_response_body and response:
                    if hasattr(response, 'status_code'):
                        extra_data['response_status'] = response.status_code
                    if hasattr(response, 'json') and callable(response.json):
                        try:
                            resp_json = response.json()
                            if isinstance(resp_json, dict) and 'code' in resp_json:
                                extra_data['response_code'] = resp_json.get('code')
                        except:
                            pass
                
                # 记录日志
                if error_occurred:
                    create_log_entry(
                        level=LogLevel.ERROR,
                        source=LogSource.USER_ACTION,
                        message=f'{action_type} failed: {str(error_occurred)}',
                        request_id=request_id,
                        duration_ms=duration_ms,
                        extra_data={**extra_data, 'error': str(error_occurred)[:500]}
                    )
                else:
                    # 根据响应状态码确定日志级别
                    status_code = getattr(response, 'status_code', 200) if response else 200
                    log_level = LogLevel.WARNING if status_code >= 400 else level
                    
                    create_log_entry(
                        level=log_level,
                        source=LogSource.USER_ACTION,
                        message=f'{action_type}: {request.endpoint}' if request else f'{action_type}',
                        request_id=request_id,
                        status_code=status_code,
                        duration_ms=duration_ms,
                        extra_data=extra_data
                    )
                
        return decorated_function
    return decorator


def log_api_request():
    """
    API请求日志装饰器
    记录所有API请求的基本信息
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            request_id = str(uuid.uuid4())
            g.request_id = request_id
            
            start_time = time.time()
            
            try:
                response = f(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                status_code = getattr(response, 'status_code', 200)
                
                # 记录API请求日志
                create_log_entry(
                    level=LogLevel.INFO,
                    source=LogSource.API_REQUEST,
                    message=f"API Request: {request.method} {request.endpoint}",
                    request_id=request_id,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    extra_data={
                        'url': request.url,
                        'args': dict(request.args),
                        'content_type': request.content_type
                    }
                )
                
                return response
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                create_log_entry(
                    level=LogLevel.ERROR,
                    source=LogSource.API_REQUEST,
                    message=f"API Request failed: {request.method} {request.endpoint} - {str(e)}",
                    request_id=request_id,
                    status_code=500,
                    duration_ms=duration_ms,
                    extra_data={
                        'error': str(e)[:500],
                        'url': request.url
                    }
                )
                raise
                
        return decorated_function
    return decorator


def log_security_event(
    event_type: str,
    severity: str = LogLevel.WARNING,
    details: Optional[Dict[str, Any]] = None
):
    """
    记录安全事件
    
    Args:
        event_type: 事件类型
        severity: 严重级别
        details: 事件详情
    """
    create_log_entry(
        level=severity,
        source=LogSource.SECURITY,
        message=f"Security Event: {event_type}",
        extra_data={
            'event_type': event_type,
            'details': details or {}
        }
    )


def log_system_event(
    message: str,
    level: str = LogLevel.INFO,
    component: str = 'SYSTEM',
    extra_data: Optional[Dict[str, Any]] = None
):
    """
    记录系统事件
    
    Args:
        message: 日志消息
        level: 日志级别
        component: 组件名称
        extra_data: 额外数据
    """
    create_log_entry(
        level=level,
        source=f"SYSTEM_{component}",
        message=message,
        extra_data=extra_data or {}
    )


def get_log_config(key: str, default: Any = None) -> Any:
    """
    获取日志配置
    
    Args:
        key: 配置键
        default: 默认值
    
    Returns:
        配置值
    """
    try:
        config = LogConfig.query.filter_by(config_key=key).first()
        if config:
            value = config.config_value
            # 尝试转换布尔值
            if value.lower() in ['true', 'false']:
                return value.lower() == 'true'
            # 尝试转换数字
            try:
                if '.' in value:
                    return float(value)
                return int(value)
            except ValueError:
                return value
        return default
    except Exception:
        return default


def is_logging_enabled(log_type: str) -> bool:
    """
    检查指定类型的日志是否启用
    
    Args:
        log_type: 日志类型 (user_logs, api_logs, error_logs)
    
    Returns:
        是否启用
    """
    return get_log_config(f'enable_{log_type}', True)


def cleanup_old_logs(days: int = None) -> int:
    """
    清理旧日志
    
    Args:
        days: 保留天数，为None时使用配置值
    
    Returns:
        删除的日志数量
    """
    try:
        if days is None:
            days = get_log_config('max_log_days', 30)
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 删除过期日志
        deleted_count = db.session.query(LogEntry)\
            .filter(LogEntry.created_at < cutoff_date)\
            .delete(synchronize_session=False)
        
        db.session.commit()
        
        log_system_event(
            f"Cleaned up {deleted_count} old log entries older than {days} days",
            level=LogLevel.INFO,
            component='LOG_CLEANUP',
            extra_data={'deleted_count': deleted_count, 'cutoff_days': days}
        )
        
        return deleted_count
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to cleanup old logs: {str(e)}")
        return 0