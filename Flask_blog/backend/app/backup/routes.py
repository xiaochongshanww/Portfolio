"""
备份系统API路由

提供备份管理的RESTful API接口
"""

from flask import request, jsonify, current_app
from datetime import datetime, timezone, timedelta
import json
from .. import db, require_auth, require_roles
from ..models import BackupRecord, BackupConfig, BackupTask, RestoreRecord, SHANGHAI_TZ
from . import backup_bp
from .physical_backup_engine import PhysicalBackupEngine
from .physical_restore_engine import PhysicalRestoreEngine
from .backup_records_external import get_external_metadata_manager


# 物理备份引擎实例
physical_backup_engine = None
physical_restore_engine = None


def get_physical_backup_engine():
    """获取物理备份引擎实例 (懒加载)"""
    global physical_backup_engine
    if physical_backup_engine is None:
        config = {
            "mysql_container": current_app.config.get('MYSQL_CONTAINER_NAME', 'blog-mysql'),
            "mysql_volume": current_app.config.get('MYSQL_VOLUME_NAME', 'auto-detect'), 
            "backup_root": current_app.config.get('PHYSICAL_BACKUP_ROOT', './backups/physical'),
            "hot_backup": current_app.config.get('PHYSICAL_HOT_BACKUP', True),
            "compress_backup": current_app.config.get('PHYSICAL_COMPRESS_BACKUP', True)
        }
        physical_backup_engine = PhysicalBackupEngine(config)
    return physical_backup_engine


def get_physical_restore_engine():
    """获取物理恢复引擎实例 (懒加载)"""
    global physical_restore_engine
    if physical_restore_engine is None:
        config = {
            "mysql_container": current_app.config.get('MYSQL_CONTAINER_NAME', 'blog-mysql'),
            "mysql_volume": current_app.config.get('MYSQL_VOLUME_NAME', 'auto-detect'),
            "backup_root": current_app.config.get('PHYSICAL_BACKUP_ROOT', './backups/physical')
        }
        physical_restore_engine = PhysicalRestoreEngine(config)
    return physical_restore_engine


def _should_resolve_conflict_in_stats(conflict) -> bool:
    """判断是否应该在统计页面中解决冲突（保守策略）"""
    try:
        # 只有以下情况才在统计页面解决冲突：
        
        # 1. 物理恢复后的正常现象：MySQL=running，外部=completed
        if (conflict.conflict_reason and 
            'MySQL=running' in conflict.conflict_reason and 
            '外部=completed' in conflict.conflict_reason):
            return True  # 这种情况应该以外部元数据为准
        
        # 2. 状态从pending/running到completed的明显完成情况
        if (conflict.conflict_reason and 
            'MySQL=completed' in conflict.conflict_reason and 
            ('外部=pending' in conflict.conflict_reason or '外部=running' in conflict.conflict_reason)):
            return True
        
        # 3. 有明确完成时间但状态不一致的情况
        if conflict.completed_at and conflict.status in ['pending', 'running']:
            return True
        
        # 4. 其他情况采用保守策略，不修改
        return False
        
    except Exception:
        # 判断逻辑出错，采用保守策略
        return False


def sync_physical_backups_to_database():
    """同步物理备份到数据库（确保数据一致性）"""
    try:
        engine = get_physical_backup_engine()
        physical_backups = engine.list_backups()
        
        synced_count = 0
        for physical_backup in physical_backups:
            backup_id = physical_backup.get('backup_id')
            
            # 检查数据库中是否已存在该备份记录
            existing_record = BackupRecord.query.filter_by(backup_id=backup_id).first()
            
            if not existing_record:
                # 创建数据库记录
                metadata = physical_backup
                
                backup_record = BackupRecord(
                    backup_id=backup_id,
                    backup_type='physical',
                    status='completed',  # 能被引擎列出的都是完成的
                    created_at=datetime.fromisoformat(metadata.get('created_at', '').replace('Z', '+00:00')) if metadata.get('created_at') else datetime.now(SHANGHAI_TZ),
                    started_at=datetime.fromisoformat(metadata.get('created_at', '').replace('Z', '+00:00')) if metadata.get('created_at') else None,
                    completed_at=datetime.fromisoformat(metadata.get('completed_at', '').replace('Z', '+00:00')) if metadata.get('completed_at') else None,
                    file_size=metadata.get('backup_size', 0),
                    compressed_size=metadata.get('compressed_size', 0),
                    compression_ratio=metadata.get('compression_ratio', 0),
                    databases_count=1,
                    encryption_enabled=False,
                    file_path=metadata.get('archive_path') or f"backups/physical/{backup_id}/mysql_data.tar.gz"
                )
                
                # 设置额外数据
                extra_data = {
                    'engine': 'physical_backup_engine',
                    'timing': metadata.get('timing', {}),
                    'performance': metadata.get('performance', {}),
                    'database_info': metadata.get('database_info', {}),
                    'compressed': metadata.get('compressed', False),
                    'synced_from_physical': True  # 标记为从物理备份同步
                }
                backup_record.set_extra_data(extra_data)
                
                db.session.add(backup_record)
                synced_count += 1
        
        if synced_count > 0:
            db.session.commit()
            current_app.logger.info(f"同步了 {synced_count} 个物理备份到数据库")
        
        return synced_count
        
    except Exception as e:
        current_app.logger.error(f"同步物理备份到数据库失败: {e}")
        db.session.rollback()
        return 0


@backup_bp.route('/records', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_backup_records():
    """获取备份记录列表（从数据库查询，必要时使用外部元数据进行冲突解决）"""
    try:
        current_app.logger.info("查询备份记录列表")
        
        # 获取外部元数据管理器
        external_manager = get_external_metadata_manager()
        
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        backup_type = request.args.get('backup_type', 'physical')  # 默认查询物理备份
        status = request.args.get('status')
        
        per_page = min(per_page, 100)  # 限制每页数量
        
        # 检查数据库连接状态并处理连接错误（带重试机制）
        db_connected = False
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 先尝试简单的数据库连接测试
                db.session.execute(db.text('SELECT 1'))
                db_connected = True
                break
            except Exception as conn_error:
                if attempt < max_retries - 1:
                    current_app.logger.info(f"数据库连接测试失败 (尝试 {attempt + 1}/{max_retries})，正在重试...")
                    import time
                    time.sleep(1)  # 短暂延迟后重试
                else:
                    current_app.logger.warning(f"数据库连接失败（已重试{max_retries}次）: {conn_error}")
                    db_conn_error = conn_error
        
        if not db_connected:
            
            # 如果数据库不可用，尝试从外部元数据获取备份记录
            if external_manager:
                try:
                    current_app.logger.info("数据库不可用，从外部元数据获取备份记录")
                    external_backups = external_manager.get_all_backup_records()
                    
                    # 过滤和分页处理
                    filtered_backups = []
                    for backup in external_backups:
                        if backup_type and backup.get('backup_type') != backup_type:
                            continue
                        if status and backup.get('status') != status:
                            continue
                        filtered_backups.append(backup)
                    
                    # 手动分页
                    total = len(filtered_backups)
                    start = (page - 1) * per_page
                    end = start + per_page
                    items = filtered_backups[start:end]
                    
                    # 转换为前端期望格式
                    formatted_items = []
                    for backup in items:
                        formatted_items.append({
                            'id': backup.get('id'),
                            'backup_id': backup.get('backup_id'),
                            'backup_type': backup.get('backup_type'),
                            'status': backup.get('status'),
                            'created_at': backup.get('created_at'),
                            'started_at': backup.get('started_at'),
                            'completed_at': backup.get('completed_at'),
                            'file_path': backup.get('file_path'),
                            'file_size': backup.get('file_size'),
                            'compressed_size': backup.get('compressed_size'),
                            'compression_ratio': backup.get('compression_ratio'),
                            'error_message': backup.get('error_message')
                        })
                    
                    return jsonify({
                        'code': 0,
                        'message': '备份记录查询成功（来源：外部元数据，数据库暂时不可用）',
                        'data': {
                            'items': formatted_items,
                            'total': total,
                            'pages': (total + per_page - 1) // per_page,
                            'current_page': page,
                            'per_page': per_page,
                            'source': 'external_metadata',
                            'database_status': 'offline'
                        }
                    })
                except Exception as external_error:
                    current_app.logger.error(f"外部元数据获取失败: {external_error}")
            
            # 如果外部元数据也不可用，返回空结果但提示原因
            return jsonify({
                'code': 0,
                'message': '数据库暂时不可用（可能正在进行恢复操作），请稍后重试',
                'data': {
                    'items': [],
                    'total': 0,
                    'pages': 0,
                    'current_page': page,
                    'per_page': per_page,
                    'source': 'unavailable',
                    'database_status': 'offline',
                    'reason': 'database_temporarily_unavailable'
                }
            })
        
        # 如果数据库连接正常，继续正常查询流程
        if db_connected:
            # 构建查询
            query = BackupRecord.query
            
            # 筛选备份类型
            if backup_type:
                query = query.filter_by(backup_type=backup_type)
            
            # 筛选状态
            if status:
                query = query.filter_by(status=status)
            
            # 按创建时间倒序排列
            query = query.order_by(BackupRecord.created_at.desc())
            
            # 分页查询
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
            # 如果没有数据库记录但可能有物理备份文件，自动同步一次
            if pagination.total == 0 and backup_type == 'physical':
                current_app.logger.info("数据库中无物理备份记录，尝试从物理文件同步")
                synced_count = sync_physical_backups_to_database()
                if synced_count > 0:
                    # 重新查询
                    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
            # 轻量级冲突监控（避免会话冲突，将复杂同步移至后台任务）
            data_conflicts_resolved = False
            if external_manager and pagination.total > 0:
                try:
                    # 只进行轻量级检查，避免会话冲突
                    conflict_count = external_manager.get_conflict_count()
                    if conflict_count > 0:
                        current_app.logger.info(f"检测到 {conflict_count} 个潜在数据冲突")
                        # 注意：完整的智能路由应通过独立的后台任务或定时任务执行
                        # 以避免HTTP请求中的SQLAlchemy会话冲突
                except Exception as e:
                    current_app.logger.warning(f"轻量级冲突检测失败: {e}")
                    # 静默处理，不影响前端数据返回
            
            # 转换为前端需要的格式
            formatted_backups = []
            for backup_record in pagination.items:
                extra_data = backup_record.get_extra_data()
                
                # 格式化文件大小
                def format_size(size_bytes):
                    if size_bytes == 0 or size_bytes is None:
                        return "0 B"
                    size_names = ["B", "KB", "MB", "GB", "TB"]
                    i = 0
                    size = float(size_bytes)
                    while size >= 1024.0 and i < len(size_names) - 1:
                        size /= 1024.0
                        i += 1
                    if i == 0:
                        return f"{int(size)} {size_names[i]}"
                    else:
                        return f"{size:.1f} {size_names[i]}"
                
                # 计算最终使用的大小
                backup_size = backup_record.compressed_size or backup_record.file_size or 0
                
                # 计算持续时间
                duration = backup_record.get_duration() or 0
                timing = extra_data.get('timing', {})
                if not duration and timing:
                    duration = timing.get('total_duration', 0)
                
                # 获取性能信息
                performance = extra_data.get('performance', {})
                
                formatted_backup = {
                    'id': backup_record.id,
                    'backup_id': backup_record.backup_id,
                    'backup_type': backup_record.backup_type,
                    'status': backup_record.status,
                    
                    # 文件大小信息
                    'backup_size': backup_size,
                    'backup_size_text': format_size(backup_size),
                    'file_size': backup_size,  # 添加前端期望的 file_size 字段
                    'raw_size': backup_record.file_size or 0,
                    'compressed_size': backup_record.compressed_size,
                    'compression_ratio': backup_record.compression_ratio,
                    
                    # 时间信息
                    'duration': duration,
                    'duration_text': f"{duration:.1f} 秒" if duration > 0 else '',
                    'created_at': backup_record.created_at.isoformat() if backup_record.created_at else None,
                    'started_at': backup_record.started_at.isoformat() if backup_record.started_at else None,
                    'completed_at': backup_record.completed_at.isoformat() if backup_record.completed_at else None,
                    
                    # 性能信息
                    'backup_speed': performance.get('total_speed_mbps', 0),
                    
                    # 其他信息
                    'database_version': extra_data.get('database_info', {}).get('version', ''),
                    'description': extra_data.get('description', ''),
                    'compressed': extra_data.get('compressed', False),
                    'mysql_version': extra_data.get('database_info', {}).get('version', ''),
                    'error_message': backup_record.error_message,
                    'file_path': backup_record.file_path,
                    'checksum': backup_record.checksum,
                    'encryption_enabled': backup_record.encryption_enabled
                }
                formatted_backups.append(formatted_backup)
            
            # 计算存储统计摘要（基于数据库记录）
            try:
                # 统计所有完成的物理备份
                completed_backups = BackupRecord.query.filter_by(
                    backup_type=backup_type or 'physical', 
                    status='completed'
                ).all()
                
                total_storage = sum((backup.compressed_size or backup.file_size or 0) for backup in completed_backups)
                total_raw_size = sum((backup.file_size or 0) for backup in completed_backups)
                total_compressed_size = sum((backup.compressed_size or 0) for backup in completed_backups if backup.compressed_size)
                
                def format_size_helper(size_bytes):
                    if size_bytes == 0 or size_bytes is None:
                        return "0 B"
                    size_names = ["B", "KB", "MB", "GB", "TB"]
                    i = 0
                    size = float(size_bytes)
                    while size >= 1024.0 and i < len(size_names) - 1:
                        size /= 1024.0
                        i += 1
                    if i == 0:
                        return f"{int(size)} {size_names[i]}"
                    else:
                        return f"{size:.1f} {size_names[i]}"
                
                average_size = total_storage // len(completed_backups) if completed_backups else 0
                compression_savings = total_raw_size - total_compressed_size
                compression_ratio = total_compressed_size / total_raw_size if total_raw_size > 0 else 0
                
                summary = {
                    'total_storage_used': total_storage,
                    'total_storage_used_text': format_size_helper(total_storage),
                    'total_backups': len(completed_backups),
                    'average_backup_size_text': format_size_helper(average_size),
                    'compression_savings_text': format_size_helper(compression_savings),
                    'overall_compression_ratio': round(compression_ratio, 3)
                }
            except Exception as e:
                current_app.logger.warning(f"获取存储摘要失败: {e}")
                summary = {
                    'total_storage_used': 0,
                    'total_storage_used_text': '0 B',
                    'total_backups': pagination.total,
                    'average_backup_size_text': '0 B',
                    'compression_savings_text': '0 B',
                    'overall_compression_ratio': 0
                }
            
            result = {
                'records': formatted_backups,
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
                'pages': pagination.pages,
                'storage_summary': summary,  # 新增存储摘要
                'data_source_info': {  # 新增数据源信息
                    'conflicts_resolved': data_conflicts_resolved,
                    'external_metadata_active': external_manager is not None,
                    'data_integrity_checked': True,
                    'last_sync_status': 'ok' if data_conflicts_resolved else 'no_conflicts'
                }
            }
            
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get physical backup records: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取备份记录失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/create', methods=['POST'])
@require_auth
@require_roles('admin', 'editor')  
def create_backup():
    """创建物理备份（主要接口）"""
    try:
        current_app.logger.info("开始创建物理备份")
        
        data = request.get_json() or {}
        backup_id = data.get('backup_id')  # 可选的自定义备份ID
        description = data.get('description', '')
        
        # 获取物理备份引擎
        engine = get_physical_backup_engine()
        
        # 生成backup_id（如果未提供）
        if not backup_id:
            backup_id = f"physical_{datetime.now(SHANGHAI_TZ).strftime('%Y%m%d_%H%M%S')}"
        
        # 先创建MySQL数据库记录（状态为running）
        backup_record = BackupRecord(
            backup_id=backup_id,
            backup_type='physical',
            status='running',
            started_at=datetime.now(SHANGHAI_TZ),
            databases_count=1,
            encryption_enabled=False,  # 物理备份暂不加密
            extra_data=json.dumps({
                'description': description,
                'requested_by': getattr(request, 'user_email', 'unknown'),
                'engine': 'physical_backup_engine'
            })
        )
        db.session.add(backup_record)
        db.session.commit()
        
        # 同时创建外部元数据记录
        external_manager = get_external_metadata_manager()
        if external_manager:
            try:
                external_manager.create_backup_record(
                    backup_id=backup_id,
                    backup_type='physical',
                    status='running',
                    description=description,
                    requested_by=getattr(request, 'user_email', 'unknown')
                )
                current_app.logger.info(f"外部元数据记录已创建: {backup_id}")
            except Exception as e:
                current_app.logger.warning(f"创建外部元数据记录失败: {e}")
        
        try:
            # 执行物理备份
            result = engine.create_backup(backup_record.backup_id)
            
            if result['success']:
                current_app.logger.info(f"物理备份创建成功: {result['backup_id']}")
                
                # 更新MySQL数据库记录为完成状态
                metadata = result.get('metadata', {})
                summary = result.get('summary', {})
                
                backup_record.status = 'completed'
                backup_record.completed_at = datetime.now(SHANGHAI_TZ)
                backup_record.file_size = summary.get('raw_size', 0)
                backup_record.compressed_size = summary.get('compressed_size', 0) 
                backup_record.compression_ratio = summary.get('compression_ratio', 0)
                backup_record.checksum = metadata.get('checksum')  # 如果有的话
                
                # 设置文件路径
                archive_path = metadata.get('archive_path')
                if archive_path:
                    backup_record.file_path = str(archive_path)
                else:
                    backup_record.file_path = f"backups/physical/{backup_record.backup_id}/mysql_data.tar.gz"
                
                # 合并额外数据
                existing_extra = backup_record.get_extra_data()
                existing_extra.update({
                    'description': description,
                    'requested_by': getattr(request, 'user_email', 'unknown'),
                    'engine': 'physical_backup_engine',
                    'timing': metadata.get('timing', {}),
                    'performance': metadata.get('performance', {}),
                    'database_info': metadata.get('database_info', {}),
                    'compressed': metadata.get('compressed', False)
                })
                backup_record.set_extra_data(existing_extra)
                
                db.session.commit()
                
                # 同时更新外部元数据记录（外部元数据是权威数据源）
                if external_manager:
                    try:
                        external_manager.update_backup_record(
                            backup_id=backup_id,
                            status='completed',
                            file_size=summary.get('raw_size', 0),
                            compressed_size=summary.get('compressed_size', 0),
                            compression_ratio=summary.get('compression_ratio', 0),
                            file_path=backup_record.file_path,
                            checksum=metadata.get('checksum'),
                            extra_data={
                                'timing': metadata.get('timing', {}),
                                'performance': metadata.get('performance', {}),
                                'database_info': metadata.get('database_info', {}),
                                'compressed': metadata.get('compressed', False)
                            }
                        )
                        current_app.logger.info(f"外部元数据记录已更新为completed状态: {backup_id}")
                    except Exception as e:
                        current_app.logger.warning(f"更新外部元数据记录失败: {e}")
                
                # 添加用户描述到返回结果的元数据中
                if description and 'metadata' in result:
                    result['metadata']['description'] = description
                    result['metadata']['requested_by'] = getattr(request, 'user_email', 'unknown')
                
                # 获取详细信息
                summary = result.get('summary', {})
                metadata = result.get('metadata', {})
                
                return jsonify({
                    'code': 0,
                    'message': '备份创建成功',
                    'data': {
                        'backup_id': result['backup_id'],
                        'backup_type': 'physical',
                        
                        # 文件大小信息
                        'backup_size': summary.get('backup_size', 0),
                        'backup_size_text': summary.get('backup_size_text', ''),
                        'raw_size': summary.get('raw_size', 0),
                        'compressed_size': summary.get('compressed_size'),
                        'compression_ratio': summary.get('compression_ratio'),
                        
                        # 时间信息
                        'duration': summary.get('duration', 0),
                        'duration_text': summary.get('duration_text', ''),
                        'backup_speed': summary.get('backup_speed', 0),
                        'created_at': metadata.get('created_at'),
                        'completed_at': metadata.get('completed_at'),
                        
                        # 其他信息
                        'database_version': metadata.get('mysql_version', ''),
                        'description': description,
                        'compressed': metadata.get('compressed', False),
                        
                        # 详细时间分解（可选）
                        'timing_details': metadata.get('timing', {})
                    }
                })
            else:
                # 备份失败，更新MySQL数据库记录
                backup_record.status = 'failed'
                backup_record.completed_at = datetime.now(SHANGHAI_TZ)
                backup_record.error_message = result.get('error', '未知错误')
                db.session.commit()
                
                # 同时更新外部元数据记录
                if external_manager:
                    try:
                        external_manager.update_backup_record(
                            backup_id=backup_id,
                            status='failed',
                            error_message=result.get('error', '未知错误')
                        )
                        current_app.logger.info(f"外部元数据记录已更新为失败状态: {backup_id}")
                    except Exception as e:
                        current_app.logger.warning(f"更新外部元数据失败记录失败: {e}")
                
                current_app.logger.error(f"物理备份创建失败: {result.get('error')}")
                return jsonify({
                    'code': 5000,
                    'message': f"备份创建失败: {result.get('error')}",
                    'data': None
                }), 500
                
        except Exception as engine_error:
            # 引擎执行异常，更新MySQL数据库记录
            backup_record.status = 'failed'
            backup_record.completed_at = datetime.now(SHANGHAI_TZ)
            backup_record.error_message = str(engine_error)
            db.session.commit()
            
            # 同时更新外部元数据记录
            if external_manager:
                try:
                    external_manager.update_backup_record(
                        backup_id=backup_id,
                        status='failed',
                        error_message=str(engine_error)
                    )
                except Exception as e:
                    current_app.logger.warning(f"更新外部元数据异常记录失败: {e}")
            
            raise engine_error
            
    except Exception as e:
        current_app.logger.error(f"创建物理备份异常: {e}")
        return jsonify({
            'code': 5000,
            'message': f'创建备份失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/<backup_id>/download', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def download_backup(backup_id):
    """下载物理备份文件"""
    try:
        # 获取物理备份引擎
        engine = get_physical_backup_engine()
        
        # 检查备份是否存在
        backup_info = engine.get_backup_info(backup_id)
        if not backup_info:
            return jsonify({
                'code': 4004,
                'message': '物理备份不存在',
                'data': None
            }), 404
        
        # 直接从物理备份目录下载文件
        from flask import send_file
        from pathlib import Path
        
        # 检查是否有压缩归档
        if backup_info.get('compressed', False) and 'archive_path' in backup_info:
            # 使用压缩归档文件
            archive_path = Path(backup_info['archive_path'])
            if archive_path.exists():
                return send_file(
                    str(archive_path),
                    as_attachment=True,
                    download_name=f"{backup_id}.tar.gz",
                    mimetype='application/gzip'
                )
        
        # 否则查找备份目录下的 mysql_data.tar.gz 文件
        backup_root = Path(engine.config.get('backup_root', './backups/physical'))
        backup_dir = backup_root / backup_id
        mysql_data_file = backup_dir / 'mysql_data.tar.gz'
        
        if mysql_data_file.exists():
            return send_file(
                str(mysql_data_file),
                as_attachment=True,
                download_name=f"{backup_id}_mysql_data.tar.gz",
                mimetype='application/gzip'
            )
        
        return jsonify({
            'code': 4004,
            'message': '物理备份文件不存在',
            'data': None
        }), 404
            
    except Exception as e:
        current_app.logger.error(f"Failed to download physical backup {backup_id}: {e}")
        return jsonify({
            'code': 5000,
            'message': f'下载物理备份失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/<backup_id>', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_backup_record(backup_id):
    """获取物理备份详情"""
    try:
        # 获取物理备份引擎
        engine = get_physical_backup_engine()
        
        # 获取备份信息
        backup_info = engine.get_backup_info(backup_id)
        
        if not backup_info:
            return jsonify({
                'code': 4004,
                'message': '物理备份不存在',
                'data': None
            }), 404
        
        # 转换为前端需要的格式
        formatted_backup = {
            'id': backup_info.get('backup_id'),
            'backup_id': backup_info.get('backup_id'),
            'backup_type': 'physical',
            'status': 'completed',  # 物理备份都是完成的
            'backup_size': backup_info.get('backup_size', 0),
            'file_size': backup_info.get('backup_size', 0),  # 添加前端期望的 file_size 字段
            'created_at': backup_info.get('created_at'),
            'database_version': backup_info.get('database_info', {}).get('version', ''),
            'description': backup_info.get('description', ''),
            'compressed': backup_info.get('compressed', False),
            'mysql_version': backup_info.get('mysql_version', ''),
            'container_name': backup_info.get('container_name', ''),
            'volume_name': backup_info.get('volume_name', ''),
            'database_info': backup_info.get('database_info', {})
        }
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': formatted_backup
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get physical backup record {backup_id}: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取物理备份详情失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/<backup_id>/cancel', methods=['POST'])
@require_auth
@require_roles('admin', 'editor')
def cancel_backup(backup_id):
    """取消备份任务（物理备份不支持取消）"""
    try:
        # 物理备份通常很快完成，不支持取消功能
        current_app.logger.info(f"收到取消物理备份请求: {backup_id}")
        
        # 获取物理备份引擎检查备份是否存在
        engine = get_physical_backup_engine()
        backup_info = engine.get_backup_info(backup_id)
        
        if not backup_info:
            return jsonify({
                'code': 4004,
                'message': '物理备份不存在',
                'data': None
            }), 404
        
        # 物理备份通常瞬时完成，无法取消
        return jsonify({
            'code': 4000,
            'message': '物理备份通常瞬时完成，无法取消。如需删除已完成的备份，请使用删除功能。',
            'data': {
                'backup_id': backup_id,
                'backup_type': 'physical',
                'status': 'completed'
            }
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"处理取消物理备份请求失败 {backup_id}: {e}")
        return jsonify({
            'code': 5000,
            'message': f'处理取消请求失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/<backup_id>/restore', methods=['POST'])
@require_auth
@require_roles('admin')
def restore_backup(backup_id):
    """恢复物理备份（主要接口）"""
    try:
        current_app.logger.info(f"开始物理恢复: {backup_id}")
        
        data = request.get_json() or {}
        restore_id = data.get('restore_id')  # 可选的自定义恢复ID
        restore_type = data.get('restore_type', 'full')
        restore_options = data.get('options', {})
        
        # 根据前端传入的恢复类型映射到物理恢复支持的类型
        restore_type_mapping = {
            'full': 'full',                    # 完整恢复(数据库+文件)
            'database_only': 'database_only', # 仅恢复数据库
            'files_only': 'files_only',       # 仅恢复文件  
            'partial': 'partial',             # 自定义恢复
            'custom': 'partial'               # 自定义恢复映射到partial
        }
        
        restore_type = restore_type_mapping.get(restore_type, 'full')
        current_app.logger.info(f"恢复类型: {restore_type}, 选项: {restore_options}")
        
        # 生成恢复ID（如果没有提供）
        if not restore_id:
            restore_id = f"restore_{datetime.now(SHANGHAI_TZ).strftime('%Y%m%d_%H%M%S')}"
        
        current_app.logger.info(f"开始物理恢复，恢复ID: {restore_id}")
        
        try:
            # 获取物理恢复引擎
            engine = get_physical_restore_engine()
            
            # 执行物理恢复（注意：这会清空数据库，所以记录要在恢复后创建）
            result = engine.restore_database(backup_id, restore_id)
            
            if result['success']:
                # 物理恢复成功后，创建恢复记录（此时数据库已恢复，可以安全创建记录）
                try:
                    # 先检查是否已存在相同的 restore_id（避免重复）
                    existing_record = RestoreRecord.query.filter_by(restore_id=restore_id).first()
                    if existing_record:
                        current_app.logger.warning(f"恢复记录已存在: {restore_id}，将更新现有记录")
                        # 更新现有记录而不是创建新记录
                        existing_record.status = 'completed'
                        existing_record.progress = 100
                        existing_record.status_message = '物理恢复完成'
                        existing_record.completed_at = datetime.now(SHANGHAI_TZ)
                        existing_record.restored_databases_count = 1
                        restore_record = existing_record
                    else:
                        # 创建新记录
                        restore_record = RestoreRecord(
                            restore_id=restore_id,
                            backup_record_id=None,  # 物理恢复不依赖传统备份记录
                            restore_type=restore_type,
                            status='completed',
                            progress=100,
                            status_message='物理恢复完成',
                            restore_options=json.dumps(restore_options) if restore_options else None,
                            requested_by=getattr(request, 'user_email', 'unknown'),
                            started_at=datetime.now(SHANGHAI_TZ) - timedelta(seconds=int(result.get('duration', 0))),  # 估算开始时间
                            completed_at=datetime.now(SHANGHAI_TZ),
                            restored_databases_count=1  # 物理恢复恢复整个数据库
                        )
                        db.session.add(restore_record)
                    
                    db.session.commit()
                    record_id = restore_record.id
                    
                    # 修复AUTO_INCREMENT问题：使用更强力的方案避免ID冲突
                    try:
                        from sqlalchemy import text
                        import time
                        
                        # 方案1：尝试设置 AUTO_INCREMENT 到一个足够大的值
                        timestamp_based_id = int(time.time()) % 1000000  # 使用时间戳生成唯一ID
                        safe_auto_increment = max(record_id + 1000, timestamp_based_id)
                        
                        db.session.execute(text(f'ALTER TABLE restore_records AUTO_INCREMENT = {safe_auto_increment}'))
                        db.session.commit()
                        current_app.logger.info(f"已设置 AUTO_INCREMENT 为安全值: {safe_auto_increment}")
                        
                        # 方案2：验证设置是否生效，如果不生效则记录警告
                        actual_auto_inc = db.session.execute(text("""
                            SELECT AUTO_INCREMENT 
                            FROM information_schema.TABLES 
                            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'restore_records'
                        """)).fetchone()
                        
                        if actual_auto_inc and actual_auto_inc[0] < safe_auto_increment:
                            current_app.logger.warning(f"AUTO_INCREMENT 设置未生效，实际值: {actual_auto_inc[0]}，MySQL可能在容器重启时重置了该值")
                        
                    except Exception as auto_inc_error:
                        current_app.logger.warning(f"修复AUTO_INCREMENT失败: {auto_inc_error}")
                    
                    current_app.logger.info(f"恢复记录创建成功: {restore_id} (ID: {record_id})")
                    
                except Exception as record_error:
                    current_app.logger.warning(f"创建恢复记录失败，但恢复操作成功: {record_error}")
                    record_id = None
                
                current_app.logger.info(f"物理恢复成功: {result['restore_id']}")
                return jsonify({
                    'code': 0,
                    'message': '物理恢复成功',
                    'data': {
                        **result,
                        'restore_record_id': record_id
                    }
                })
            else:
                # 恢复失败时也创建记录以便跟踪
                try:
                    restore_record = RestoreRecord(
                        restore_id=restore_id,
                        backup_record_id=None,
                        restore_type=restore_type,
                        status='failed',
                        progress=0,
                        status_message='物理恢复失败',
                        error_message=result.get('error', '未知错误'),
                        restore_options=json.dumps(restore_options) if restore_options else None,
                        requested_by=getattr(request, 'user_email', 'unknown'),
                        started_at=datetime.now(SHANGHAI_TZ),
                        completed_at=datetime.now(SHANGHAI_TZ),
                        restored_databases_count=0
                    )
                    
                    db.session.add(restore_record)
                    db.session.commit()
                    current_app.logger.info(f"失败恢复记录创建成功: {restore_id}")
                    
                except Exception as record_error:
                    current_app.logger.warning(f"创建失败记录失败: {record_error}")
                
                current_app.logger.error(f"物理恢复失败: {result.get('error')}")
                return jsonify({
                    'code': 5000,
                    'message': f"物理恢复失败: {result.get('error')}",
                    'data': None
                }), 500
                
        except Exception as restore_error:
            # 异常情况也创建记录
            try:
                restore_record = RestoreRecord(
                    restore_id=restore_id,
                    backup_record_id=None,
                    restore_type=restore_type,
                    status='failed',
                    progress=0,
                    status_message='物理恢复异常',
                    error_message=str(restore_error),
                    restore_options=json.dumps(restore_options) if restore_options else None,
                    requested_by=getattr(request, 'user_email', 'unknown'),
                    started_at=datetime.now(SHANGHAI_TZ),
                    completed_at=datetime.now(SHANGHAI_TZ),
                    restored_databases_count=0
                )
                
                db.session.add(restore_record)
                db.session.commit()
                current_app.logger.info(f"异常恢复记录创建成功: {restore_id}")
                
            except Exception as record_error:
                current_app.logger.warning(f"创建异常记录失败: {record_error}")
            
            raise restore_error
            
    except Exception as e:
        current_app.logger.error(f"执行物理恢复异常: {e}")
        return jsonify({
            'code': 5000,
            'message': f'执行物理恢复异常: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/sync', methods=['POST'])
@require_auth
@require_roles('admin')
def sync_backup_records():
    """手动同步物理备份到数据库"""
    try:
        current_app.logger.info("手动同步物理备份到数据库")
        
        synced_count = sync_physical_backups_to_database()
        
        return jsonify({
            'code': 0,
            'message': f'同步完成，新增了 {synced_count} 条备份记录',
            'data': {
                'synced_count': synced_count,
                'sync_time': datetime.now(SHANGHAI_TZ).isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"手动同步备份记录失败: {e}")
        return jsonify({
            'code': 5000,
            'message': f'同步备份记录失败: {str(e)}',
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
    """获取备份统计信息（从数据库查询）"""
    try:
        current_app.logger.info("查询备份统计信息")
        
        # 获取查询参数
        backup_type = request.args.get('backup_type', 'physical')  # 默认查询物理备份
        
        # 如果没有数据库记录，先尝试同步一次
        backup_count = BackupRecord.query.filter_by(backup_type=backup_type).count()
        if backup_count == 0 and backup_type == 'physical':
            current_app.logger.info("数据库中无备份记录，尝试从物理文件同步")
            synced_count = sync_physical_backups_to_database()
            if synced_count > 0:
                current_app.logger.info(f"同步了 {synced_count} 个备份记录")
        
        # 获取外部元数据管理器进行轻量级冲突检查（避免频繁的状态修改）
        external_manager = get_external_metadata_manager()
        if external_manager:
            try:
                # 同步MySQL到外部元数据库
                external_manager.sync_from_mysql_backup_records()
                
                # 检查冲突但采用保守的解决策略
                conflicts = external_manager.find_conflicts()
                if conflicts:
                    current_app.logger.info(f"统计页面发现 {len(conflicts)} 个备份记录冲突")
                    
                    # 只解决明显的冲突，避免误判
                    resolved_count = 0
                    for conflict in conflicts:
                        # 检查冲突的严重性，只处理高置信度的冲突
                        if _should_resolve_conflict_in_stats(conflict):
                            try:
                                result = conflict.resolve_conflict_by_file_check()
                                if result in ['fixed_to_completed', 'fixed_to_failed']:
                                    external_manager.save_record(conflict)
                                    resolved_count += 1
                            except Exception as resolve_error:
                                current_app.logger.warning(f"解决冲突失败 {conflict.backup_id}: {resolve_error}")
                    
                    if resolved_count > 0:
                        # 将解决结果同步回 MySQL
                        external_manager.sync_to_mysql_backup_records()
                        current_app.logger.info(f"统计页面解决了 {resolved_count}/{len(conflicts)} 个冲突")
                    else:
                        current_app.logger.info("统计页面：所有冲突都采用保守策略，未修改状态")
            except Exception as e:
                current_app.logger.warning(f"统计页面外部元数据冲突检查失败: {e}")
        
        # 从数据库查询统计信息
        from collections import defaultdict
        from sqlalchemy import func
        
        # 基本统计
        total_backups = BackupRecord.query.filter_by(backup_type=backup_type).count()
        completed_backups = BackupRecord.query.filter_by(backup_type=backup_type, status='completed').count()
        failed_backups = BackupRecord.query.filter_by(backup_type=backup_type, status='failed').count()
        running_backups = BackupRecord.query.filter_by(backup_type=backup_type, status='running').count()
        
        # 成功率计算
        success_rate = (completed_backups / total_backups * 100) if total_backups > 0 else 0
        
        # 存储统计 - 仅统计已完成的备份
        completed_backup_records = BackupRecord.query.filter_by(
            backup_type=backup_type, 
            status='completed'
        ).all()
        
        total_raw_size = sum((backup.file_size or 0) for backup in completed_backup_records)
        total_compressed_size = sum((backup.compressed_size or 0) for backup in completed_backup_records if backup.compressed_size)
        total_storage_used = sum((backup.compressed_size or backup.file_size or 0) for backup in completed_backup_records)
        
        # 压缩统计
        compressed_backups = sum(1 for backup in completed_backup_records if backup.compressed_size and backup.compressed_size > 0)
        uncompressed_backups = completed_backups - compressed_backups
        
        # 压缩节省空间和比例
        compression_savings = total_raw_size - total_compressed_size if total_compressed_size > 0 else 0
        overall_compression_ratio = total_compressed_size / total_raw_size if total_raw_size > 0 else 0
        
        # 平均大小
        average_backup_size = total_storage_used // completed_backups if completed_backups > 0 else 0
        
        # 文件大小格式化函数
        def format_size(size_bytes):
            if size_bytes == 0 or size_bytes is None:
                return "0 B"
            size_names = ["B", "KB", "MB", "GB", "TB"]
            i = 0
            size = float(size_bytes)
            while size >= 1024.0 and i < len(size_names) - 1:
                size /= 1024.0
                i += 1
            if i == 0:
                return f"{int(size)} {size_names[i]}"
            else:
                return f"{size:.1f} {size_names[i]}"
        
        # 按日期分组统计
        daily_counts = defaultdict(int)
        monthly_counts = defaultdict(int)
        daily_storage = defaultdict(int)
        monthly_storage = defaultdict(int)
        
        for backup in completed_backup_records:
            if backup.created_at:
                daily_key = backup.created_at.strftime('%Y-%m-%d')
                monthly_key = backup.created_at.strftime('%Y-%m')
                
                daily_counts[daily_key] += 1
                monthly_counts[monthly_key] += 1
                
                backup_size = backup.compressed_size or backup.file_size or 0
                daily_storage[daily_key] += backup_size
                monthly_storage[monthly_key] += backup_size
        
        # 格式化月度存储
        monthly_storage_formatted = {
            month: format_size(size) for month, size in monthly_storage.items()
        }
        
        # 获取最近的备份记录（用于兼容性）
        recent_backups_records = BackupRecord.query.filter_by(
            backup_type=backup_type,
            status='completed'
        ).order_by(BackupRecord.created_at.desc()).limit(10).all()
        
        # 转换为前端期望的格式
        recent_backups = []
        for backup_record in recent_backups_records:
            extra_data = backup_record.get_extra_data()
            recent_backups.append({
                'backup_id': backup_record.backup_id,
                'created_at': backup_record.created_at.isoformat() if backup_record.created_at else None,
                'backup_size': backup_record.compressed_size or backup_record.file_size or 0,
                'backup_size_text': format_size(backup_record.compressed_size or backup_record.file_size or 0),
                'compressed': extra_data.get('compressed', False),
                'duration': backup_record.get_duration() or 0,
                'database_version': extra_data.get('database_info', {}).get('version', ''),
                'description': extra_data.get('description', '')
            })
        
        # 大小分布分析
        size_ranges = {
            'small': 0,      # < 100MB
            'medium': 0,     # 100MB - 1GB
            'large': 0,      # 1GB - 10GB
            'extra_large': 0 # > 10GB
        }
        
        for backup in completed_backup_records:
            size = backup.compressed_size or backup.file_size or 0
            if size < 100 * 1024 * 1024:  # < 100MB
                size_ranges['small'] += 1
            elif size < 1024 * 1024 * 1024:  # < 1GB
                size_ranges['medium'] += 1
            elif size < 10 * 1024 * 1024 * 1024:  # < 10GB
                size_ranges['large'] += 1
            else:  # > 10GB
                size_ranges['extra_large'] += 1
        
        # 组合统计信息 - 匹配前端期望格式
        stats = {
            # 前端直接使用的字段
            'total_backups': total_backups,
            'completed_backups': completed_backups,
            'failed_backups': failed_backups,
            'running_backups': running_backups,
            'total_storage_size': total_storage_used,  # 前端用formatFileSize处理
            'success_rate': round(success_rate, 1),
            
            # 兼容旧版本的字段
            'backup_type': backup_type,
            'total_size': total_storage_used,
            'average_size': average_backup_size,
            'recent_backups': recent_backups,
            'daily_counts': dict(daily_counts),
            'monthly_counts': dict(monthly_counts),
            
            # 详细存储统计（供高级功能使用）
            'storage': {
                'total_storage_used': total_storage_used,
                'total_storage_used_text': format_size(total_storage_used),
                'total_raw_size': total_raw_size,
                'total_raw_size_text': format_size(total_raw_size),
                'total_compressed_size': total_compressed_size,
                'total_compressed_size_text': format_size(total_compressed_size),
                'compression_savings': compression_savings,
                'compression_savings_text': format_size(compression_savings)
            },
            
            # 压缩统计
            'compression': {
                'compressed_backups': compressed_backups,
                'uncompressed_backups': uncompressed_backups,
                'overall_compression_ratio': round(overall_compression_ratio, 3),
                'compression_effectiveness': round((compression_savings / total_raw_size * 100) if total_raw_size > 0 else 0, 1)
            },
            
            # 大小分布
            'size_distribution': size_ranges,
            
            # 存储按时间分布
            'storage_by_time': {
                'monthly_storage': dict(monthly_storage),
                'monthly_storage_formatted': monthly_storage_formatted,
                'daily_storage': dict(daily_storage)
            },
            
            # 存储效率分析
            'efficiency': {
                'compression_effectiveness': round((compression_savings / total_raw_size * 100) if total_raw_size > 0 else 0, 1),
                'average_compression_ratio': round(overall_compression_ratio, 3),
                'storage_efficiency': round((total_storage_used / total_raw_size * 100) if total_raw_size > 0 else 100, 1)
            },
            
            # 统计时间
            'calculated_at': datetime.now(SHANGHAI_TZ).isoformat()
        }
        
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
    """清理过期的物理备份"""
    try:
        data = request.get_json() or {}
        # 默认保留最近7天的备份
        days_to_keep = data.get('days_to_keep', 7)
        
        # 获取物理备份引擎
        engine = get_physical_backup_engine()
        
        # 获取所有物理备份
        backups = engine.list_backups()
        
        # 计算过期的备份
        from datetime import datetime, timezone, timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
        deleted_backups = []
        deleted_count = 0
        freed_space = 0
        
        for backup in backups:
            created_at = backup.get('created_at', '')
            if created_at:
                try:
                    backup_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if backup_date < cutoff_date:
                        # 删除过期备份
                        backup_id = backup.get('backup_id')
                        result = engine.delete_backup(backup_id)
                        if result.get('success'):
                            deleted_backups.append(backup_id)
                            deleted_count += 1
                            freed_space += backup.get('backup_size', 0)
                            current_app.logger.info(f"清理过期物理备份: {backup_id}")
                        else:
                            current_app.logger.warning(f"清理物理备份失败: {backup_id}, {result.get('error')}")
                except Exception as e:
                    current_app.logger.warning(f"解析备份日期失败: {created_at}, {e}")
        
        result = {
            'deleted_count': deleted_count,
            'freed_space': freed_space,
            'deleted_backups': deleted_backups,
            'days_to_keep': days_to_keep,
            'cleanup_time': datetime.now().isoformat()
        }
        
        return jsonify({
            'code': 0,
            'message': f'清理完成，删除了 {deleted_count} 个过期备份，释放了 {freed_space} 字节空间',
            'data': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to cleanup expired physical backups: {e}")
        return jsonify({
            'code': 5000,
            'message': f'清理过期物理备份失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/<backup_id>', methods=['DELETE'])
@require_auth
@require_roles('admin')
def delete_backup(backup_id):
    """删除物理备份（包括数据库记录和物理文件）"""
    try:
        current_app.logger.info(f"删除物理备份: {backup_id}")
        
        # 先查找数据库记录
        backup_record = BackupRecord.query.filter_by(backup_id=backup_id).first()
        
        # 获取物理备份引擎
        engine = get_physical_backup_engine()
        
        # 执行物理文件删除
        result = engine.delete_backup(backup_id)
        
        if result['success']:
            # 物理文件删除成功，同时删除MySQL数据库记录
            if backup_record:
                try:
                    db.session.delete(backup_record)
                    db.session.commit()
                    current_app.logger.info(f"MySQL数据库记录删除成功: {backup_id}")
                except Exception as db_error:
                    current_app.logger.warning(f"删除MySQL数据库记录失败，但物理文件已删除: {db_error}")
                    db.session.rollback()
            else:
                current_app.logger.info(f"MySQL数据库中未找到备份记录: {backup_id}")
            
            # 同时删除外部元数据记录
            external_manager = get_external_metadata_manager()
            if external_manager:
                try:
                    external_manager.delete_backup_record(backup_id)
                    current_app.logger.info(f"外部元数据记录删除成功: {backup_id}")
                except Exception as e:
                    current_app.logger.warning(f"删除外部元数据记录失败: {e}")
            
            current_app.logger.info(f"物理备份删除成功: {backup_id}")
            return jsonify({
                'code': 0,
                'message': result['message'],
                'data': {
                    'backup_id': backup_id,
                    'deleted_at': datetime.now().isoformat(),
                    'mysql_record_deleted': backup_record is not None,
                    'external_record_deleted': True
                }
            })
        else:
            current_app.logger.error(f"物理备份删除失败: {result.get('error')}")
            return jsonify({
                'code': 5000,
                'message': f"删除物理备份失败: {result.get('error')}",
                'data': None
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"删除物理备份异常: {e}")
        return jsonify({
            'code': 5000,
            'message': f'删除物理备份异常: {str(e)}',
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
            'items': [record.to_dict() for record in pagination.items],
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


@backup_bp.route('/restores/cleanup', methods=['POST'])
@require_auth
@require_roles(['admin'])
def cleanup_stuck_restores():
    """清理卡住的恢复任务"""
    try:
        current_app.logger.info("Starting cleanup of stuck restore tasks")
        
        # 查找状态为running但已经超过10分钟的任务（正常恢复不应该超过10分钟）
        threshold_time = datetime.now(SHANGHAI_TZ) - timedelta(minutes=10)
        
        stuck_restores = RestoreRecord.query.filter(
            RestoreRecord.status == 'running',
            RestoreRecord.started_at < threshold_time
        ).all()
        
        if not stuck_restores:
            return jsonify({
                'code': 0,
                'message': '没有发现卡住的恢复任务',
                'data': {'cleaned_count': 0}
            })
        
        # 清理卡住的任务
        cleaned_count = 0
        for restore in stuck_restores:
            current_app.logger.info(f"Cleaning stuck restore task: {restore.restore_id}")
            
            restore.status = 'failed'
            restore.error_message = '任务执行超时，已自动清理。可能原因：mysql命令未找到、数据库连接异常或备份文件过大'
            restore.status_message = '恢复失败: 执行超过10分钟，已被自动清理'
            restore.completed_at = datetime.now(SHANGHAI_TZ)
            cleaned_count += 1
        
        # 提交更改
        db.session.commit()
        
        current_app.logger.info(f"Successfully cleaned {cleaned_count} stuck restore tasks")
        
        return jsonify({
            'code': 0,
            'message': f'成功清理了 {cleaned_count} 个卡住的恢复任务',
            'data': {'cleaned_count': cleaned_count}
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to cleanup stuck restores: {e}")
        db.session.rollback()
        return jsonify({
            'code': 5000,
            'message': f'清理卡住的恢复任务失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/tasks/cleaner/status', methods=['GET'])
@require_auth
@require_roles('admin')
def get_cleaner_status():
    """获取任务清理器状态"""
    try:
        from .task_cleaner import task_cleaner
        status = task_cleaner.get_cleanup_status()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': status
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get cleaner status: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取清理器状态失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/tasks/cleaner/trigger', methods=['POST'])
@require_auth
@require_roles('admin')
def trigger_manual_cleanup():
    """手动触发任务清理"""
    try:
        from .task_cleaner import task_cleaner
        
        # 在应用上下文中执行清理
        result = task_cleaner.cleanup_stuck_tasks()
        
        current_app.logger.info(f"手动触发任务清理完成: {result}")
        
        return jsonify({
            'code': 0,
            'message': '手动清理完成',
            'data': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Manual cleanup failed: {e}")
        return jsonify({
            'code': 5000,
            'message': f'手动清理失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/status/sync', methods=['POST'])
@require_auth
@require_roles(['admin'])
def sync_task_status():
    """同步任务状态 - 修复状态不一致问题"""
    try:
        from pathlib import Path
        
        current_app.logger.info("Starting task status synchronization")
        
        fixed_backup_count = 0
        fixed_restore_count = 0
        
        # 1. 修复备份任务状态不一致
        running_backups = BackupRecord.query.filter_by(status='running').all()
        for backup in running_backups:
            backup_file = Path('backups/snapshots') / f'{backup.backup_id}.tar.gz'
            if backup_file.exists():
                # 文件存在，更新为completed
                file_stats = backup_file.stat()
                backup.status = 'completed'
                backup.completed_at = datetime.now(SHANGHAI_TZ)
                backup.file_size = file_stats.st_size
                backup.compressed_size = file_stats.st_size
                backup.file_path = f'backups/snapshots/{backup.backup_id}.tar.gz'
                fixed_backup_count += 1
                current_app.logger.info(f"Fixed backup task {backup.backup_id}: running -> completed")
            else:
                # 文件不存在且创建时间超过1小时，设为失败
                time_diff = datetime.now(SHANGHAI_TZ) - backup.created_at
                if time_diff.total_seconds() > 3600:  # 1小时
                    backup.status = 'failed'
                    backup.completed_at = datetime.now(SHANGHAI_TZ)
                    fixed_backup_count += 1
                    current_app.logger.info(f"Fixed backup task {backup.backup_id}: running -> failed (no file)")
        
        # 2. 修复恢复任务状态不一致
        running_restores = RestoreRecord.query.filter_by(status='running').all()
        for restore in running_restores:
            if restore.started_at:
                time_diff = datetime.now(SHANGHAI_TZ) - restore.started_at
                # 如果超过30分钟还在running，很可能已经卡住
                if time_diff.total_seconds() > 1800:  # 30分钟
                    restore.status = 'failed'
                    restore.status_message = '恢复任务超时，已自动标记为失败'
                    restore.completed_at = datetime.now(SHANGHAI_TZ)
                    fixed_restore_count += 1
                    current_app.logger.info(f"Fixed restore task {restore.restore_id}: running -> failed (timeout)")
        
        # 提交更改
        if fixed_backup_count > 0 or fixed_restore_count > 0:
            db.session.commit()
        
        current_app.logger.info(f"Status sync completed: {fixed_backup_count} backup tasks, {fixed_restore_count} restore tasks fixed")
        
        return jsonify({
            'code': 0,
            'message': '任务状态同步完成',
            'data': {
                'fixed_backup_count': fixed_backup_count,
                'fixed_restore_count': fixed_restore_count,
                'total_fixed': fixed_backup_count + fixed_restore_count
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to sync task status: {e}")
        db.session.rollback()
        return jsonify({
            'code': 5000,
            'message': f'状态同步失败: {str(e)}',
            'data': None
        }), 500


# ==================== 物理备份API ====================

@backup_bp.route('/physical/create', methods=['POST'])
@require_auth
@require_roles('admin')
def create_physical_backup():
    """创建物理备份"""
    try:
        current_app.logger.info("开始创建物理备份")
        
        data = request.get_json() or {}
        backup_id = data.get('backup_id')  # 可选的自定义备份ID
        
        # 获取物理备份引擎
        engine = get_physical_backup_engine()
        
        # 执行物理备份
        result = engine.create_backup(backup_id)
        
        if result['success']:
            current_app.logger.info(f"物理备份创建成功: {result['backup_id']}")
            return jsonify({
                'code': 0,
                'message': '物理备份创建成功',
                'data': result
            })
        else:
            current_app.logger.error(f"物理备份创建失败: {result.get('error')}")
            return jsonify({
                'code': 5000,
                'message': f"物理备份创建失败: {result.get('error')}",
                'data': None
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"创建物理备份异常: {e}")
        return jsonify({
            'code': 5000,
            'message': f'创建物理备份异常: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/physical/list', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def list_physical_backups():
    """列出所有物理备份"""
    try:
        # 获取物理备份引擎
        engine = get_physical_backup_engine()
        
        # 获取备份列表
        backups = engine.list_backups()
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'backups': backups,
                'total': len(backups)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"获取物理备份列表失败: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取物理备份列表失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/physical/<backup_id>', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_physical_backup_info(backup_id):
    """获取物理备份详情"""
    try:
        # 获取物理备份引擎
        engine = get_physical_backup_engine()
        
        # 获取备份信息
        backup_info = engine.get_backup_info(backup_id)
        
        if not backup_info:
            return jsonify({
                'code': 4004,
                'message': '物理备份不存在',
                'data': None
            }), 404
            
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': backup_info
        })
        
    except Exception as e:
        current_app.logger.error(f"获取物理备份信息失败: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取物理备份信息失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/physical/<backup_id>/restore', methods=['POST'])
@require_auth
@require_roles('admin')
def restore_physical_backup(backup_id):
    """执行物理恢复"""
    try:
        current_app.logger.info(f"开始物理恢复: {backup_id}")
        
        data = request.get_json() or {}
        restore_id = data.get('restore_id')  # 可选的自定义恢复ID
        
        # 获取物理恢复引擎
        engine = get_physical_restore_engine()
        
        # 执行物理恢复
        result = engine.restore_database(backup_id, restore_id)
        
        if result['success']:
            current_app.logger.info(f"物理恢复成功: {result['restore_id']}")
            return jsonify({
                'code': 0,
                'message': '物理恢复成功',
                'data': result
            })
        else:
            current_app.logger.error(f"物理恢复失败: {result.get('error')}")
            return jsonify({
                'code': 5000,
                'message': f"物理恢复失败: {result.get('error')}",
                'data': None
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"执行物理恢复异常: {e}")
        return jsonify({
            'code': 5000,
            'message': f'执行物理恢复异常: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/physical/<backup_id>/delete', methods=['DELETE'])
@require_auth
@require_roles('admin')
def delete_physical_backup(backup_id):
    """删除物理备份（包括数据库记录和物理文件）"""
    try:
        current_app.logger.info(f"删除物理备份: {backup_id}")
        
        # 先查找数据库记录
        backup_record = BackupRecord.query.filter_by(backup_id=backup_id).first()
        
        # 获取物理备份引擎
        engine = get_physical_backup_engine()
        
        # 删除物理文件
        result = engine.delete_backup(backup_id)
        
        if result['success']:
            # 物理文件删除成功，同时删除数据库记录
            if backup_record:
                try:
                    db.session.delete(backup_record)
                    db.session.commit()
                    current_app.logger.info(f"数据库记录删除成功: {backup_id}")
                except Exception as db_error:
                    current_app.logger.warning(f"删除数据库记录失败，但物理文件已删除: {db_error}")
                    db.session.rollback()
            else:
                current_app.logger.info(f"数据库中未找到备份记录: {backup_id}")
            
            current_app.logger.info(f"物理备份删除成功: {backup_id}")
            return jsonify({
                'code': 0,
                'message': '物理备份删除成功',
                'data': {
                    **result,
                    'database_record_deleted': backup_record is not None
                }
            })
        else:
            current_app.logger.error(f"物理备份删除失败: {result.get('error')}")
            return jsonify({
                'code': 5000,
                'message': f"物理备份删除失败: {result.get('error')}",
                'data': None
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"删除物理备份异常: {e}")
        return jsonify({
            'code': 5000,
            'message': f'删除物理备份异常: {str(e)}',
            'data': None
        }), 500


# ==================== 外部元数据管理API ====================

@backup_bp.route('/external/sync', methods=['POST'])
@require_auth
@require_roles('admin')
def sync_external_metadata():
    """同步外部元数据系统（手动触发同步和冲突解决）"""
    try:
        current_app.logger.info("手动同步外部元数据系统")
        
        data = request.get_json() or {}
        sync_direction = data.get('direction', 'bidirectional')  # from_mysql, to_mysql, bidirectional
        auto_resolve_conflicts = data.get('auto_resolve_conflicts', True)
        
        external_manager = get_external_metadata_manager()
        if not external_manager:
            return jsonify({
                'code': 5000,
                'message': '外部元数据管理器未初始化',
                'data': None
            }), 500
        
        sync_result = {
            'sync_direction': sync_direction,
            'mysql_to_external': 0,
            'external_to_mysql': 0,
            'conflicts_found': 0,
            'conflicts_resolved': 0,
            'errors': []
        }
        
        try:
            # 根据同步方向执行操作
            if sync_direction in ['from_mysql', 'bidirectional']:
                # 从MySQL同步到外部数据库
                sync_result['mysql_to_external'] = external_manager.sync_from_mysql_backup_records()
                current_app.logger.info(f"MySQL到外部同步: {sync_result['mysql_to_external']} 条记录")
            
            if sync_direction in ['to_mysql', 'bidirectional']:
                # 从外部数据库同步到MySQL
                sync_result['external_to_mysql'] = external_manager.sync_to_mysql_backup_records()
                current_app.logger.info(f"外部到MySQL同步: {sync_result['external_to_mysql']} 条记录")
            
            # 查找并解决冲突
            conflicts = external_manager.find_conflicts()
            sync_result['conflicts_found'] = len(conflicts)
            
            if conflicts and auto_resolve_conflicts:
                for conflict in conflicts:
                    try:
                        resolution = conflict.resolve_conflict_by_file_check()
                        if resolution in ['fixed_to_completed', 'fixed_to_failed']:
                            sync_result['conflicts_resolved'] += 1
                            external_manager.save_record(conflict)
                    except Exception as e:
                        sync_result['errors'].append(f"解决冲突失败 {conflict.backup_id}: {e}")
                
                # 将解决结果同步回MySQL
                if sync_result['conflicts_resolved'] > 0:
                    external_manager.sync_to_mysql_backup_records()
                    current_app.logger.info(f"冲突解决完成，已同步 {sync_result['conflicts_resolved']} 条记录回MySQL")
            
            # 获取统计信息
            stats = external_manager.get_statistics()
            sync_result.update({
                'total_external_records': stats.get('total_backup_records', 0),
                'external_conflicts': stats.get('conflict_records', 0),
                'sync_time': datetime.now(SHANGHAI_TZ).isoformat()
            })
            
        except Exception as e:
            sync_result['errors'].append(f"同步过程异常: {e}")
            current_app.logger.error(f"外部元数据同步异常: {e}")
        
        return jsonify({
            'code': 0,
            'message': '外部元数据同步完成',
            'data': sync_result
        })
        
    except Exception as e:
        current_app.logger.error(f"外部元数据同步失败: {e}")
        return jsonify({
            'code': 5000,
            'message': f'外部元数据同步失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/external/conflicts', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_external_conflicts():
    """获取外部元数据冲突列表"""
    try:
        external_manager = get_external_metadata_manager()
        if not external_manager:
            return jsonify({
                'code': 5000,
                'message': '外部元数据管理器未初始化',
                'data': None
            }), 500
        
        # 首先同步最新数据
        try:
            external_manager.sync_from_mysql_backup_records()
        except Exception as e:
            current_app.logger.warning(f"同步数据时出错: {e}")
        
        # 查找冲突
        conflicts = external_manager.find_conflicts()
        
        # 转换为前端需要的格式
        conflict_data = []
        for conflict in conflicts:
            conflict_info = {
                'backup_id': conflict.backup_id,
                'backup_type': conflict.backup_type,
                'status': conflict.status,
                'sync_status': conflict.sync_status,
                'conflict_reason': conflict.conflict_reason,
                'file_exists': conflict.verify_file_exists(),
                'created_at': conflict.created_at.isoformat() if conflict.created_at else None,
                'completed_at': conflict.completed_at.isoformat() if conflict.completed_at else None,
                'file_path': conflict.file_path,
                'file_size': conflict.file_size,
                'error_message': conflict.error_message,
                'last_sync_at': conflict.last_sync_at.isoformat() if conflict.last_sync_at else None
            }
            conflict_data.append(conflict_info)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'conflicts': conflict_data,
                'total_conflicts': len(conflicts),
                'query_time': datetime.now(SHANGHAI_TZ).isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"获取外部元数据冲突失败: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取冲突列表失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/external/conflicts/<backup_id>/resolve', methods=['POST'])
@require_auth
@require_roles('admin')
def resolve_external_conflict(backup_id):
    """解决特定备份记录的冲突"""
    try:
        external_manager = get_external_metadata_manager()
        if not external_manager:
            return jsonify({
                'code': 5000,
                'message': '外部元数据管理器未初始化',
                'data': None
            }), 500
        
        # 获取冲突记录
        conflict_record = external_manager.get_backup_record(backup_id)
        if not conflict_record:
            return jsonify({
                'code': 4004,
                'message': '备份记录不存在',
                'data': None
            }), 404
        
        if conflict_record.sync_status != 'conflict':
            return jsonify({
                'code': 4000,
                'message': '该记录没有冲突需要解决',
                'data': {
                    'backup_id': backup_id,
                    'current_status': conflict_record.sync_status
                }
            }), 400
        
        # 解决冲突
        resolution_result = conflict_record.resolve_conflict_by_file_check()
        external_manager.save_record(conflict_record)
        
        # 同步回MySQL
        external_manager.sync_to_mysql_backup_records()
        
        return jsonify({
            'code': 0,
            'message': '冲突解决完成',
            'data': {
                'backup_id': backup_id,
                'resolution_result': resolution_result,
                'new_status': conflict_record.status,
                'new_sync_status': conflict_record.sync_status,
                'resolved_at': datetime.now(SHANGHAI_TZ).isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"解决外部元数据冲突失败: {e}")
        return jsonify({
            'code': 5000,
            'message': f'解决冲突失败: {str(e)}',
            'data': None
        }), 500


@backup_bp.route('/external/statistics', methods=['GET'])
@require_auth
@require_roles('admin', 'editor')
def get_external_metadata_statistics():
    """获取外部元数据系统统计信息"""
    try:
        external_manager = get_external_metadata_manager()
        if not external_manager:
            return jsonify({
                'code': 5000,
                'message': '外部元数据管理器未初始化',
                'data': None
            }), 500
        
        # 获取统计信息
        stats = external_manager.get_statistics()
        
        # 添加系统状态信息
        stats.update({
            'system_status': 'active',
            'database_path': external_manager.db_path,
            'query_time': datetime.now(SHANGHAI_TZ).isoformat()
        })
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"获取外部元数据统计失败: {e}")
        return jsonify({
            'code': 5000,
            'message': f'获取外部元数据统计失败: {str(e)}',
            'data': None
        }), 500


# ==================== 错误处理 ====================
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