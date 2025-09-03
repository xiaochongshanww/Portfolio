"""
日志管理API路由
提供日志查看、搜索、统计等功能
"""

from flask import Blueprint, request, jsonify, g
from sqlalchemy import desc, and_, func, text
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from .. import db, require_auth, require_roles
from ..models import LogEntry, LogConfig, User
from ..utils.logging_utils import (
    log_user_action, log_system_event, LogLevel, LogSource,
    get_log_config, cleanup_old_logs
)

logs_bp = Blueprint('logs', __name__)


@logs_bp.route('/test', methods=['GET'])
def test_logs_route():
    """测试路由是否工作"""
    print("=== TEST ROUTE HIT ===")
    import sys; sys.stdout.flush()
    return jsonify({'code': 0, 'message': 'logs blueprint working', 'data': None})


@logs_bp.route('/debug-auth', methods=['GET'])  
@require_auth
def debug_auth_route():
    """调试认证路由"""
    from flask import current_app
    current_app.logger.warning("=== DEBUG AUTH ROUTE HIT WITH VALID TOKEN ===")
    auth = request.headers.get('Authorization','')
    current_app.logger.warning(f"=== AUTH HEADER: {auth} ===")
    return jsonify({'code': 0, 'message': 'debug route with auth', 'auth_header': auth})

@logs_bp.route('/public-check', methods=['GET'])
def public_check():
    """无需鉴权，用于对比 header 传递情况"""
    from flask import current_app
    hdr = {k: v for k,v in request.headers.items()}
    current_app.logger.warning(f"=== PUBLIC_CHECK HEADERS: {list(hdr.keys())} ===")
    return jsonify({'code':0,'message':'ok','data':{'headers':hdr}})

def _query_logs_common(page:int,size:int,level:str,source:str,keyword:str,user_id,request_id,start_time,end_time):
    query = LogEntry.query
    if level and level in [LogLevel.ERROR, LogLevel.WARNING, LogLevel.INFO, LogLevel.DEBUG]:
        query = query.filter(LogEntry.level == level)
    if source:
        query = query.filter(LogEntry.source.ilike(f'%{source}%'))
    if keyword:
        query = query.filter(LogEntry.message.ilike(f'%{keyword}%'))
    if user_id:
        query = query.filter(LogEntry.user_id == user_id)
    if request_id:
        query = query.filter(LogEntry.request_id == request_id)
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            query = query.filter(LogEntry.timestamp >= start_dt)
        except ValueError:
            pass
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            query = query.filter(LogEntry.timestamp <= end_dt)
        except ValueError:
            pass
    total = query.count()
    logs = query.order_by(desc(LogEntry.timestamp)).offset((page-1)*size).limit(size).all()
    logs_data = []
    for log in logs:
        d = log.to_dict()
        if log.user:
            d['user_name'] = log.user.nickname or log.user.email
        logs_data.append(d)
    return total, logs_data

@logs_bp.route('', methods=['GET'])  # 兼容保留 GET
@require_auth
@require_roles('admin', 'editor')
@log_user_action('VIEW_LOGS')
def get_logs():
    try:
        page = int(request.args.get('page', 1))
        size = min(int(request.args.get('size', 50)), 100)
        level = request.args.get('level', '').upper()
        source = request.args.get('source', '')
        keyword = request.args.get('keyword', '')
        user_id = request.args.get('user_id', type=int)
        start_time = request.args.get('start_time', '')
        end_time = request.args.get('end_time', '')
        request_id = request.args.get('request_id', '')
        total, logs_data = _query_logs_common(page,size,level,source,keyword,user_id,request_id,start_time,end_time)
        return jsonify({'code':0,'message':'success','data':{
            'total': total,
            'page': page,
            'size': size,
            'has_next': page*size < total,
            'logs': logs_data
        }})
    except Exception as e:
        return jsonify({'code':5000,'message':f'获取日志失败: {e}','data':None}), 500

# 新增 POST 查询端点，避免某些浏览器/代理对 GET 的额外预检/重复请求
@logs_bp.route('/query', methods=['POST'])
@require_auth
@require_roles('admin', 'editor')
@log_user_action('VIEW_LOGS')
def post_query_logs():
    try:
        body = request.get_json() or {}
        page = int(body.get('page', 1))
        size = min(int(body.get('size', 50)), 100)
        level = (body.get('level') or '').upper()
        source = body.get('source') or ''
        keyword = body.get('keyword') or ''
        user_id = body.get('user_id')
        start_time = body.get('start_time') or ''
        end_time = body.get('end_time') or ''
        request_id = body.get('request_id') or ''
        total, logs_data = _query_logs_common(page,size,level,source,keyword,user_id,request_id,start_time,end_time)
        return jsonify({'code':0,'message':'success','data':{
            'total': total,
            'page': page,
            'size': size,
            'has_next': page*size < total,
            'logs': logs_data
        }})
    except Exception as e:
        return jsonify({'code':5000,'message':f'获取日志失败: {e}','data':None}), 500
# Root OPTIONS (放在 get_logs 之后避免覆盖上方定义)
@logs_bp.route('', methods=['OPTIONS'])
@logs_bp.route('/', methods=['OPTIONS'])
def logs_root_options():
    from flask import make_response
    resp = make_response('', 200)
    resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-XSRF-TOKEN'
    return resp


@logs_bp.route('/stats', methods=['OPTIONS'])
def handle_stats_options():
    """处理CORS预检请求"""
    from flask import make_response
    response = make_response('', 200)
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-XSRF-TOKEN'
    return response

@logs_bp.route('/stats', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
@log_user_action('VIEW_LOG_STATS')
def get_log_stats():
    """获取日志统计信息"""
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
            and_(LogEntry.level == LogLevel.ERROR, LogEntry.timestamp >= today)
        ).count()
        
        stats['warnings'] = LogEntry.query.filter(
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
            
            trend_data.append({
                'date': day.strftime('%Y-%m-%d'),
                'count': day_count
            })
        
        stats['weekly_trend'] = list(reversed(trend_data))
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': stats
        })
        
    except Exception as e:
        return jsonify({
            'code': 5000,
            'message': f'获取统计信息失败: {str(e)}',
            'data': None
        }), 500


@logs_bp.route('/<int:log_id>', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
@log_user_action('VIEW_LOG_DETAIL')
def get_log_detail(log_id: int):
    """获取日志详情"""
    try:
        log_entry = LogEntry.query.get_or_404(log_id)
        
        # 获取相关日志（同一request_id）
        related_logs = []
        if log_entry.request_id:
            related_logs = LogEntry.query.filter(
                and_(
                    LogEntry.request_id == log_entry.request_id,
                    LogEntry.id != log_id
                )
            ).order_by(LogEntry.timestamp).all()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'log': log_entry.to_dict(),
                'related_logs': [log.to_dict() for log in related_logs]
            }
        })
        
    except Exception as e:
        return jsonify({
            'code': 5000,
            'message': f'获取日志详情失败: {str(e)}',
            'data': None
        }), 500


@logs_bp.route('/export', methods=['GET'])
@require_auth
@require_roles('admin')
@log_user_action('EXPORT_LOGS')
def export_logs():
    """导出日志"""
    try:
        # 获取查询参数（复用get_logs的过滤逻辑）
        level = request.args.get('level', '').upper()
        source = request.args.get('source', '')
        keyword = request.args.get('keyword', '')
        start_time = request.args.get('start_time', '')
        end_time = request.args.get('end_time', '')
        format_type = request.args.get('format', 'json').lower()
        limit = min(int(request.args.get('limit', 1000)), 5000)  # 限制导出数量
        
        # 构建查询（与get_logs相同的逻辑）
        query = LogEntry.query
        
        if level and level in [LogLevel.ERROR, LogLevel.WARNING, LogLevel.INFO, LogLevel.DEBUG]:
            query = query.filter(LogEntry.level == level)
            
        if source:
            query = query.filter(LogEntry.source.ilike(f'%{source}%'))
            
        if keyword:
            query = query.filter(LogEntry.message.ilike(f'%{keyword}%'))
            
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                query = query.filter(LogEntry.timestamp >= start_dt)
            except ValueError:
                pass
                
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                query = query.filter(LogEntry.timestamp <= end_dt)
            except ValueError:
                pass
        
        # 获取数据
        logs = query.order_by(desc(LogEntry.timestamp)).limit(limit).all()
        logs_data = [log.to_dict() for log in logs]
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'logs': logs_data,
                'total': len(logs_data),
                'export_time': datetime.utcnow().isoformat(),
                'filters': {
                    'level': level,
                    'source': source,
                    'keyword': keyword,
                    'start_time': start_time,
                    'end_time': end_time
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'code': 5000,
            'message': f'导出日志失败: {str(e)}',
            'data': None
        }), 500


@logs_bp.route('/cleanup', methods=['OPTIONS'])
def handle_cleanup_options():
    from flask import make_response
    resp = make_response('', 200)
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-XSRF-TOKEN'
    return resp

@logs_bp.route('/cleanup', methods=['POST'])
@require_auth
@require_roles('admin')
@log_user_action('CLEANUP_LOGS')
def cleanup_logs():
    try:
        data = request.get_json() or {}
        days = data.get('days', get_log_config('max_log_days', 30))
        if days < 1:
            return jsonify({'code': 4000,'message': '保留天数不能少于1天','data': None}), 400
        deleted_count = cleanup_old_logs(days)
        return jsonify({'code': 0,'message': 'success','data': {'deleted_count': deleted_count,'days': days}})
    except Exception as e:
        return jsonify({'code': 5000,'message': f'清理日志失败: {str(e)}','data': None}), 500


@logs_bp.route('/config', methods=['OPTIONS'])
def handle_config_options():
    """处理CORS预检请求"""
    from flask import make_response
    response = make_response('', 200)
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-XSRF-TOKEN'
    return response

@logs_bp.route('/config', methods=['GET'])
@require_auth
@require_roles('admin')
def get_log_config_list():
    """获取日志配置"""
    try:
        configs = LogConfig.query.all()
        config_data = []
        
        for config in configs:
            config_data.append({
                'id': config.id,
                'config_key': config.config_key,
                'config_value': config.config_value,
                'description': config.description,
                'created_at': config.created_at.isoformat() if config.created_at else None,
                'updated_at': config.updated_at.isoformat() if config.updated_at else None
            })
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': config_data
        })
        
    except Exception as e:
        return jsonify({
            'code': 5000,
            'message': f'获取配置失败: {str(e)}',
            'data': None
        }), 500


@logs_bp.route('/config', methods=['POST'])
@require_auth
@require_roles('admin')
@log_user_action('UPDATE_LOG_CONFIG')
def update_log_config():
    """更新日志配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 4000,
                'message': '请求数据不能为空',
                'data': None
            }), 400
        
        config_key = data.get('config_key')
        config_value = data.get('config_value')
        
        if not config_key or config_value is None:
            return jsonify({
                'code': 4000,
                'message': '配置键和值不能为空',
                'data': None
            }), 400
        
        # 查找或创建配置
        config = LogConfig.query.filter_by(config_key=config_key).first()
        if config:
            config.config_value = str(config_value)
            config.updated_at = datetime.utcnow()
        else:
            config = LogConfig(
                config_key=config_key,
                config_value=str(config_value),
                description=data.get('description', '')
            )
            db.session.add(config)
        
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'config_key': config.config_key,
                'config_value': config.config_value
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 5000,
            'message': f'更新配置失败: {str(e)}',
            'data': None
        }), 500


@logs_bp.route('/sources', methods=['OPTIONS'])
def handle_sources_options():
    """处理CORS预检请求"""
    from flask import make_response
    response = make_response('', 200)
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-XSRF-TOKEN'
    return response

@logs_bp.route('/sources', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_log_sources():
    """获取日志来源列表"""
    try:
        sources = db.session.query(LogEntry.source)\
            .distinct()\
            .order_by(LogEntry.source)\
            .all()
        
        source_list = [source[0] for source in sources if source[0]]
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': source_list
        })
        
    except Exception as e:
        return jsonify({
            'code': 5000,
            'message': f'获取日志来源失败: {str(e)}',
            'data': None
        }), 500


@logs_bp.route('/users', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_log_users():
    """获取有日志记录的用户列表"""
    try:
        users = db.session.query(User.id, User.nickname, User.email)\
            .join(LogEntry, User.id == LogEntry.user_id)\
            .distinct()\
            .order_by(User.nickname)\
            .all()
        
        user_list = []
        for user in users:
            user_list.append({
                'id': user.id,
                'name': user.nickname or user.email,
                'email': user.email
            })
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': user_list
        })
        
    except Exception as e:
        return jsonify({
            'code': 5000,
            'message': f'获取用户列表失败: {str(e)}',
            'data': None
        }), 500