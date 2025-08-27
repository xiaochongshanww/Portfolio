"""
备份系统API路由

提供备份管理的RESTful API接口
"""

from flask import request, jsonify, current_app
from datetime import datetime
import json
from .. import db, require_auth, require_roles
from ..models import BackupRecord, BackupConfig, BackupTask, RestoreRecord
from . import backup_bp
from .backup_manager import BackupManager


# 备份管理器实例
backup_manager = None


def get_backup_manager():
    """获取备份管理器实例 (懒加载)"""
    global backup_manager
    if backup_manager is None:
        backup_manager = BackupManager()
    return backup_manager


@backup_bp.route('/records', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_backup_records():
    """获取备份记录列表"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        backup_type = request.args.get('type')
        status = request.args.get('status')
        
        # 限制每页数量
        per_page = min(per_page, 100)
        
        # 获取备份记录
        manager = get_backup_manager()
        result = manager.get_backup_records(page, per_page, backup_type, status)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get backup records: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取备份记录失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/create', methods=['POST'])
@require_auth
@require_roles('admin', 'editor')
def create_backup():
    """创建新备份"""
    try:
        data = request.get_json() or {}
        
        # 获取备份参数
        backup_type = data.get('backup_type', 'incremental')
        # 如果没有指定包含模式，使用None让备份管理器使用默认值
        include_patterns = data.get('include_patterns')
        if not include_patterns:  # 空列表或None都使用默认值
            include_patterns = None
            
        exclude_patterns = data.get('exclude_patterns')
        if not exclude_patterns:  # 空列表或None都使用默认值
            exclude_patterns = None
        
        options = {
            'include_database': data.get('include_database', True),
            'include_files': data.get('include_files', True),
            'include_patterns': include_patterns,
            'exclude_patterns': exclude_patterns,
            'storage_providers': data.get('storage_providers', ['local']),
            'description': data.get('description', ''),
            'requested_by': getattr(request, 'user_email', 'unknown')
        }
        
        # 验证备份类型
        if backup_type not in ['full', 'incremental', 'snapshot']:
            return jsonify({
                'code': 4001,
                'message': '无效的备份类型',
                'data': None
            }), 400
        
        # 创建备份
        manager = get_backup_manager()
        backup_id = manager.create_backup(backup_type, options)
        
        return jsonify({
            'code': 0,
            'message': '备份创建成功',
            'data': {
                'backup_id': backup_id,
                'backup_type': backup_type
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to create backup: {e}")
        return jsonify({
            'code': 5000,
            'message': f'创建备份失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/<backup_id>/download', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def download_backup(backup_id):
    """下载备份文件"""
    try:
        manager = get_backup_manager()
        backup_record = manager.get_backup_record(backup_id)
        
        if not backup_record:
            return jsonify({
                'code': 4004,
                'message': '备份记录不存在',
                'data': None
            }), 404
        
        if backup_record['status'] != 'completed':
            return jsonify({
                'code': 4000,
                'message': '备份未完成，无法下载',
                'data': None
            }), 400
        
        # 直接从本地存储下载文件
        from flask import send_file
        from pathlib import Path
        
        # 构建本地备份文件路径
        backup_root = Path(current_app.root_path).parent / 'backups' / 'local'
        backup_file = backup_root / f"{backup_id}.tar.gz"
        
        if not backup_file.exists():
            return jsonify({
                'code': 4004,
                'message': '备份文件不存在',
                'data': None
            }), 404
        
        return send_file(
            str(backup_file),
            as_attachment=True,
            download_name=f"{backup_id}.tar.gz",
            mimetype='application/gzip'
        )
            
    except Exception as e:
        current_app.logger.error(f"Failed to download backup {backup_id}: {e}")
        return jsonify({
            'code': 5000,
            'message': f'下载备份失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/<backup_id>', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_backup_record(backup_id):
    """获取单个备份记录详情"""
    try:
        manager = get_backup_manager()
        record = manager.get_backup_record(backup_id)
        
        if not record:
            return jsonify({
                'code': 4004,
                'message': '备份记录不存在',
                'data': None
            }), 404
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': record
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get backup record {backup_id}: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取备份记录失败: {str(e)}',
            'data': None
        }), 500



@backup_bp.route('/<backup_id>/restore', methods=['POST'])
@require_auth
@require_roles('admin')
def restore_backup(backup_id):
    """恢复备份"""
    try:
        data = request.get_json() or {}
        
        # 获取恢复参数
        restore_type = data.get('restore_type', 'full')
        target_path = data.get('target_path')
        restore_options = data.get('options', {})
        
        # 验证备份记录是否存在
        manager = get_backup_manager()
        backup_record = manager.get_backup_record(backup_id)
        if not backup_record:
            return jsonify({
                'code': 4004,
                'message': '备份记录不存在',
                'data': None
            }), 404
        
        if backup_record['status'] != 'completed':
            return jsonify({
                'code': 4000,
                'message': '只能恢复已完成的备份',
                'data': None
            }), 400
        
        # 创建恢复记录
        restore_id = f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        restore_record = RestoreRecord(
            restore_id=restore_id,
            backup_record_id=backup_record['id'],
            restore_type=restore_type,
            target_path=target_path,
            restore_options=json.dumps(restore_options) if restore_options else None,
            status='pending',
            requested_by=getattr(request, 'user_email', 'unknown')
        )
        
        db.session.add(restore_record)
        db.session.commit()
        
        # 启动异步恢复任务
        from .restore_manager import RestoreManager
        restore_manager = RestoreManager()
        
        # 在实际生产环境中，这里应该使用Celery等异步任务队列
        # 目前使用同步执行，但已经具备了异步的框架结构
        import threading
        
        # 创建局部变量副本以避免闭包问题
        record_id = restore_record.id
        options_copy = dict(restore_options) if restore_options else {}
        
        def async_restore():
            try:
                with current_app.app_context():
                    restore_manager.restore_backup(record_id, options_copy)
            except Exception as e:
                current_app.logger.error(f"Thread error in restore_backup: {e}")
        
        # 启动后台线程执行恢复（生产环境应使用Celery）
        thread = threading.Thread(target=async_restore, daemon=True)
        thread.start()
        
        return jsonify({
            'code': 0,
            'message': '恢复任务创建成功',
            'data': {
                'restore_id': restore_id,
                'backup_id': backup_id,
                'restore_type': restore_type
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to restore backup {backup_id}: {e}")
        return jsonify({
            'code': 5000,
            'message': f'恢复备份失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/config', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_backup_config():
    """获取备份配置"""
    try:
        # 获取查询参数
        category = request.args.get('category')
        
        query = BackupConfig.query.filter_by(is_active=True)
        if category:
            query = query.filter_by(category=category)
        
        configs = query.all()
        
        # 按分类组织配置
        result = {}
        for config in configs:
            if config.category not in result:
                result[config.category] = {}
            
            result[config.category][config.config_key] = config.to_dict()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get backup config: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取备份配置失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/config', methods=['PUT'])
@require_auth
@require_roles('admin')
def update_backup_config():
    """更新备份配置"""
    try:
        data = request.get_json() or {}
        
        updated_count = 0
        for config_key, config_value in data.items():
            config = BackupConfig.query.filter_by(config_key=config_key, is_active=True).first()
            if config:
                config.config_value = str(config_value)
                config.updated_at = datetime.utcnow()
                config.updated_by = getattr(request, 'user_email', 'unknown')
                updated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'message': f'成功更新 {updated_count} 个配置项',
            'data': {'updated_count': updated_count}
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to update backup config: {e}")
        db.session.rollback()
        return jsonify({
            'code': 5000,
            'message': f'更新备份配置失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/statistics', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_backup_statistics():
    """获取备份统计信息"""
    try:
        manager = get_backup_manager()
        stats = manager.get_backup_statistics()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get backup statistics: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取备份统计失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/cleanup', methods=['POST'])
@require_auth
@require_roles('admin')
def cleanup_expired_backups():
    """清理过期的备份"""
    try:
        manager = get_backup_manager()
        result = manager.cleanup_expired_backups()
        
        return jsonify({
            'code': 0,
            'message': '清理完成',
            'data': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to cleanup expired backups: {e}")
        return jsonify({
            'code': 5000,
            'message': f'清理过期备份失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/<backup_id>', methods=['DELETE'])
@require_auth
@require_roles('admin')
def delete_backup(backup_id):
    """删除备份记录和文件"""
    try:
        manager = get_backup_manager()
        
        # 获取备份记录
        from ..models import BackupRecord
        backup_record = BackupRecord.query.filter_by(backup_id=backup_id).first()
        
        if not backup_record:
            return jsonify({
                'code': 4004,
                'message': '备份记录不存在',
                'data': None
            }), 404
        
        # 检查是否有正在进行的备份
        if backup_record.status in ['pending', 'running']:
            return jsonify({
                'code': 4000,
                'message': '无法删除正在进行的备份任务',
                'data': None
            }), 400
        
        # 删除文件
        from pathlib import Path
        backup_root = Path(current_app.root_path).parent / 'backups'
        
        # 删除本地备份文件
        local_file = backup_root / 'local' / f"{backup_id}.tar.gz"
        if local_file.exists():
            local_file.unlink()
            current_app.logger.info(f"Deleted local backup file: {local_file}")
        
        # 删除快照文件
        snapshot_file = backup_root / 'snapshots' / f"{backup_id}.tar.gz"
        if snapshot_file.exists():
            snapshot_file.unlink()
            current_app.logger.info(f"Deleted snapshot file: {snapshot_file}")
        
        # 删除数据库记录
        db.session.delete(backup_record)
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'message': '备份删除成功',
            'data': {
                'backup_id': backup_id,
                'deleted_at': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to delete backup {backup_id}: {e}")
        db.session.rollback()
        return jsonify({
            'code': 5000,
            'message': f'删除备份失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/tasks', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_backup_tasks():
    """获取备份任务列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 限制每页数量
        per_page = min(per_page, 100)
        
        pagination = BackupTask.query.order_by(BackupTask.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        result = {
            'tasks': [task.to_dict() for task in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get backup tasks: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取备份任务失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/restores', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_restore_records():
    """获取恢复记录列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        
        # 限制每页数量
        per_page = min(per_page, 100)
        
        query = RestoreRecord.query.order_by(RestoreRecord.created_at.desc())
        if status:
            query = query.filter_by(status=status)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        result = {
            'records': [record.to_dict() for record in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get restore records: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取恢复记录失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/restores/<restore_id>', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_restore_record_detail(restore_id):
    """获取恢复记录详情"""
    try:
        from ..models import RestoreRecord
        restore_record = RestoreRecord.query.filter_by(restore_id=restore_id).first()
        
        if not restore_record:
            return jsonify({
                'code': 4004,
                'message': '恢复记录不存在',
                'data': None
            }), 404
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': restore_record.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get restore record {restore_id}: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取恢复记录详情失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/restores/<restore_id>/cancel', methods=['POST'])
@require_auth
@require_roles('admin')
def cancel_restore_task(restore_id):
    """取消恢复任务"""
    try:
        from .restore_manager import RestoreManager
        restore_manager = RestoreManager()
        
        success = restore_manager.cancel_restore(restore_id)
        
        if not success:
            return jsonify({
                'code': 4000,
                'message': '无法取消此恢复任务（可能已完成或不存在）',
                'data': None
            }), 400
        
        return jsonify({
            'code': 0,
            'message': '恢复任务已取消',
            'data': {'restore_id': restore_id}
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to cancel restore {restore_id}: {e}")
        return jsonify({
            'code': 5000,
            'message': f'取消恢复任务失败: {str(e)}',
            'data': None
        }), 500


# 恢复任务详情监控API

@backup_bp.route('/restores/<restore_id>/detail', methods=['GET'])
@require_auth
@require_roles('admin')
def get_restore_progress(restore_id):
    """获取恢复任务详情和进度（用于实时监控）"""
    try:
        restore_record = RestoreRecord.query.filter_by(restore_id=restore_id).first()
        if not restore_record:
            return jsonify({
                'code': 4004,
                'message': '恢复记录不存在',
                'data': None
            }), 404
        
        result = restore_record.to_dict()
        
        # 获取关联的备份记录信息
        if restore_record.backup_record:
            result['backup_info'] = {
                'backup_id': restore_record.backup_record.backup_id,
                'backup_type': restore_record.backup_record.backup_type,
                'created_at': restore_record.backup_record.created_at.isoformat() if restore_record.backup_record.created_at else None,
                'file_size': restore_record.backup_record.file_size,
                'file_path': restore_record.backup_record.file_path
            }
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get restore progress {restore_id}: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取恢复进度失败: {str(e)}',
            'data': None
        }), 500


# 错误处理
@backup_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'code': 4004,
        'message': '接口不存在',
        'data': None
    }), 404


@backup_bp.errorhandler(403)
def forbidden(error):
    return jsonify({
        'code': 4003,
        'message': '权限不足',
        'data': None
    }), 403


@backup_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'code': 5000,
        'message': '服务器内部错误',
        'data': None
    }), 500