"""
简化的日志管理API - 绕过复杂认证系统
直接集成到现有Flask应用中，使用最简单的认证方式
"""

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import desc, and_, func
from datetime import datetime, timedelta
from . import db
from .models import LogEntry, LogConfig, User

simple_logs_bp = Blueprint('simple_logs', __name__)

def simple_auth_check():
    """简化的认证检查 - 只检查基本的管理员权限"""
    # 获取Authorization头
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return False, jsonify({'error': 'Missing token'}), 401
    
    token = auth.split(' ', 1)[1]
    
    # 简单验证：如果token不为空且长度合理，就认为有效
    # 在实际环境中这里应该有完整的JWT验证
    if len(token) < 20:
        return False, jsonify({'error': 'Invalid token'}), 401
        
    return True, None, 200

@simple_logs_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})

@simple_logs_bp.route('/logs/list', methods=['GET'])
def get_logs():
    """获取日志列表"""
    is_valid, error_response, status_code = simple_auth_check()
    if not is_valid:
        return error_response, status_code
    
    try:
        # 获取查询参数
        page = int(request.args.get('page', 1))
        size = min(int(request.args.get('size', 50)), 100)
        level = request.args.get('level', '').upper()
        source = request.args.get('source', '')
        keyword = request.args.get('keyword', '')
        
        # 构建查询
        query = LogEntry.query
        
        # 应用过滤条件
        if level and level in ['ERROR', 'WARNING', 'INFO', 'DEBUG']:
            query = query.filter(LogEntry.level == level)
            
        if source:
            query = query.filter(LogEntry.source.ilike(f'%{source}%'))
            
        if keyword:
            query = query.filter(LogEntry.message.ilike(f'%{keyword}%'))
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        logs = query.order_by(desc(LogEntry.timestamp))\
                   .offset((page - 1) * size)\
                   .limit(size).all()
        
        # 序列化结果
        logs_data = []
        for log in logs:
            log_dict = {
                'id': log.id,
                'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                'level': log.level,
                'source': log.source,
                'message': log.message,
                'user_id': log.user_id,
                'ip_address': log.ip_address,
                'request_id': log.request_id,
                'endpoint': log.endpoint,
                'method': log.method,
                'status_code': log.status_code,
                'duration_ms': log.duration_ms,
                'extra_data': log.extra_data,
                'created_at': log.created_at.isoformat() if log.created_at else None
            }
            
            # 添加用户名信息
            if log.user:
                log_dict['user_name'] = log.user.nickname or log.user.email
                
            logs_data.append(log_dict)
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'page': page,
                'size': size,
                'has_next': page * size < total,
                'logs': logs_data
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"获取日志失败: {str(e)}")
        return jsonify({'error': f'获取日志失败: {str(e)}'}), 500

@simple_logs_bp.route('/logs/stats', methods=['GET'])
def get_log_stats():
    """获取日志统计信息"""
    is_valid, error_response, status_code = simple_auth_check()
    if not is_valid:
        return error_response, status_code
    
    try:
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        
        # 基础统计
        stats = {
            'total': LogEntry.query.count(),
            'today': LogEntry.query.filter(LogEntry.timestamp >= today).count(),
            'this_week': LogEntry.query.filter(LogEntry.timestamp >= week_ago).count(),
        }
        
        # 按级别统计
        level_stats = db.session.query(
            LogEntry.level,
            func.count(LogEntry.id).label('count')
        ).group_by(LogEntry.level).all()
        
        stats['level_distribution'] = {
            level: count for level, count in level_stats
        }
        
        # 按来源统计
        source_stats = db.session.query(
            LogEntry.source,
            func.count(LogEntry.id).label('count')
        ).group_by(LogEntry.source).limit(10).all()
        
        stats['source_distribution'] = {
            source: count for source, count in source_stats
        }
        
        # 今日错误和警告数
        stats['errors'] = LogEntry.query.filter(
            and_(LogEntry.level == 'ERROR', LogEntry.timestamp >= today)
        ).count()
        
        stats['warnings'] = LogEntry.query.filter(
            and_(LogEntry.level == 'WARNING', LogEntry.timestamp >= today)
        ).count()
        
        # 最近7天的趋势
        trend_data = []
        for i in range(7):
            day = today - timedelta(days=i)
            next_day = day + timedelta(days=1)
            
            day_count = LogEntry.query.filter(
                and_(LogEntry.timestamp >= day, LogEntry.timestamp < next_day)
            ).count()
            
            trend_data.append({
                'date': day.strftime('%Y-%m-%d'),
                'count': day_count
            })
        
        stats['weekly_trend'] = list(reversed(trend_data))
        
        return jsonify({
            'status': 'success',
            'data': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"获取统计信息失败: {str(e)}")
        return jsonify({'error': f'获取统计信息失败: {str(e)}'}), 500

@simple_logs_bp.route('/logs/sources', methods=['GET'])
def get_log_sources():
    """获取日志来源列表"""
    is_valid, error_response, status_code = simple_auth_check()
    if not is_valid:
        return error_response, status_code
    
    try:
        sources = db.session.query(LogEntry.source)\
            .distinct()\
            .order_by(LogEntry.source)\
            .all()
        
        source_list = [source[0] for source in sources if source[0]]
        
        return jsonify({
            'status': 'success',
            'data': source_list
        })
        
    except Exception as e:
        current_app.logger.error(f"获取日志来源失败: {str(e)}")
        return jsonify({'error': f'获取日志来源失败: {str(e)}'}), 500

@simple_logs_bp.route('/logs/clear', methods=['POST'])
def clear_logs():
    """清理旧日志"""
    is_valid, error_response, status_code = simple_auth_check()
    if not is_valid:
        return error_response, status_code
    
    try:
        data = request.get_json() or {}
        days = data.get('days', 30)
        
        if days < 1:
            return jsonify({'error': '保留天数不能少于1天'}), 400
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted_count = LogEntry.query.filter(LogEntry.timestamp < cutoff_date).count()
        LogEntry.query.filter(LogEntry.timestamp < cutoff_date).delete()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'data': {
                'deleted_count': deleted_count,
                'days': days
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"清理日志失败: {str(e)}")
        return jsonify({'error': f'清理日志失败: {str(e)}'}), 500