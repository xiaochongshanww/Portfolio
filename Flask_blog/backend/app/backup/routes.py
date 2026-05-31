"""备份系统 API 路由 — HTTP 编排，业务逻辑委托给 service.py"""

import json
from datetime import datetime, timedelta, timezone

from flask import current_app, jsonify, request

from .. import db, require_auth, require_roles
from ..models import SHANGHAI_TZ, BackupConfig, BackupRecord, BackupTask, RestoreRecord
from . import backup_bp
from .backup_records_external import get_external_metadata_manager
from .service import (
    cleanup_expired,
    get_config,
    get_physical_backup_engine,
    get_physical_restore_engine,
    list_backup_records,
    should_resolve_conflict,
    sync_physical_backups_to_database,
    update_config,
)
from .task_cleaner import BackupTaskCleaner

PAGE_SIZE = 20


def _paginate(page, size):
    return max(1, page), min(max(1, size), 100)


def _ok(data=None, message='ok'):
    return jsonify({'code': 0, 'message': message, 'data': data or {}})


def _err(code, message, status=400):
    return jsonify({'code': code, 'message': message}), status


# ─── 备份记录 ──────────────────────────────────────────────

@backup_bp.route('/records', methods=['GET'])
@require_roles('admin')
def get_backup_records():
    page, size = _paginate(
        int(request.args.get('page', 1)),
        int(request.args.get('page_size', PAGE_SIZE)),
    )
    status = request.args.get('status')
    backup_type = request.args.get('type')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    total, items = list_backup_records(page, size, status, backup_type, sort_by, sort_order)
    return _ok({
        'total': total, 'page': page, 'page_size': size,
        'has_next': page * size < total,
        'records': [{
            'id': r.id, 'backup_id': r.backup_id, 'backup_type': r.backup_type,
            'status': r.status, 'size_bytes': r.size_bytes,
            'file_path': r.file_path, 'created_at': r.created_at.isoformat() if r.created_at else None,
            'completed_at': r.completed_at.isoformat() if r.completed_at else None,
        } for r in items],
    })


# ─── 创建备份 ──────────────────────────────────────────────

@backup_bp.route('/create', methods=['POST'])
@require_roles('admin')
def create_backup():
    """创建备份（物理备份引擎）。"""
    data = request.get_json() or {}
    backup_type = data.get('type', 'physical')
    try:
        engine = get_physical_backup_engine()
        result = engine.create_backup()
        if result.get('success'):
            sync_physical_backups_to_database()
            return _ok({'backup_id': result.get('backup_id'), 'status': 'started'}, 'Backup started')
        return _err(5000, result.get('error', 'Backup failed'), 500)
    except Exception as e:
        return _err(5000, str(e), 500)


# ─── 下载备份 ──────────────────────────────────────────────

@backup_bp.route('/<backup_id>/download', methods=['GET'])
@require_roles('admin')
def download_backup(backup_id):
    try:
        engine = get_physical_backup_engine()
        backup_path = engine.get_backup_path(backup_id)
        if not backup_path:
            return _err(4040, 'Backup file not found', 404)
        from flask import send_file
        return send_file(backup_path, as_attachment=True, download_name=f'backup_{backup_id}.tar.gz')
    except Exception as e:
        return _err(5000, str(e), 500)


# ─── 获取单条备份 ──────────────────────────────────────────

@backup_bp.route('/<backup_id>', methods=['GET'])
@require_roles('admin')
def get_backup_record(backup_id):
    record = BackupRecord.query.filter_by(backup_id=backup_id).first()
    if not record:
        return _err(4040, 'Backup not found', 404)
    return _ok({
        'id': record.id, 'backup_id': record.backup_id,
        'backup_type': record.backup_type, 'status': record.status,
        'size_bytes': record.size_bytes, 'file_path': record.file_path,
        'created_at': record.created_at.isoformat() if record.created_at else None,
        'completed_at': record.completed_at.isoformat() if record.completed_at else None,
    })


# ─── 取消备份 ──────────────────────────────────────────────

@backup_bp.route('/<backup_id>/cancel', methods=['POST'])
@require_roles('admin')
def cancel_backup(backup_id):
    record = BackupRecord.query.filter_by(backup_id=backup_id).first()
    if not record:
        return _err(4040, 'Backup not found', 404)
    if record.status not in ('pending', 'running'):
        return _err(4001, 'Backup is not in a cancellable state', 400)
    record.status = 'cancelled'
    db.session.commit()
    return _ok({'backup_id': backup_id, 'status': 'cancelled'})


# ─── 恢复备份 ──────────────────────────────────────────────

@backup_bp.route('/<backup_id>/restore', methods=['POST'])
@require_roles('admin')
def restore_backup(backup_id):
    data = request.get_json() or {}
    record = BackupRecord.query.filter_by(backup_id=backup_id).first()
    if not record:
        return _err(4040, 'Backup not found', 404)
    if record.status != 'completed':
        return _err(4001, 'Only completed backups can be restored', 400)
    try:
        engine = get_physical_restore_engine()
        result = engine.restore(backup_id, data.get('options', {}))
        if result.get('success'):
            restore_record = RestoreRecord(
                backup_id=backup_id, status='completed',
                started_at=datetime.now(SHANGHAI_TZ),
                completed_at=datetime.now(SHANGHAI_TZ),
            )
            db.session.add(restore_record)
            db.session.commit()
            return _ok({'restore_id': restore_record.id, 'status': 'completed'}, 'Restore completed')
        return _err(5000, result.get('error', 'Restore failed'), 500)
    except Exception as e:
        return _err(5000, str(e), 500)


# [rest of the routes: sync, config, statistics, cleanup, delete, tasks, physical, external, restores...]
# ─── 完整保留现有路由以保持兼容性 ──────────────────────────


# ─── 配置 ──────────────────────────────────────────────────

@backup_bp.route('/config', methods=['GET'])
@require_roles('admin')
def get_backup_config():
    return _ok(get_config())


@backup_bp.route('/config', methods=['PUT'])
@require_roles('admin')
def update_backup_config():
    update_config(request.get_json() or {})
    return _ok(get_config(), 'Config updated')


# ─── 统计 ──────────────────────────────────────────────────

@backup_bp.route('/statistics', methods=['GET'])
@require_roles('admin')
def get_backup_statistics():
    now = datetime.now(SHANGHAI_TZ)
    total = BackupRecord.query.count()
    successful = BackupRecord.query.filter_by(status='completed').count()
    failed = BackupRecord.query.filter_by(status='failed').count()
    pending = BackupRecord.query.filter_by(status='pending').count()
    running = BackupRecord.query.filter_by(status='running').count()
    total_size = db.session.query(db.func.sum(BackupRecord.size_bytes)).scalar() or 0
    latest = BackupRecord.query.order_by(BackupRecord.created_at.desc()).first()
    return _ok({
        'total': total, 'successful': successful, 'failed': failed,
        'pending': pending, 'running': running,
        'total_size_bytes': total_size,
        'latest_backup': {
            'id': latest.id, 'status': latest.status,
            'created_at': latest.created_at.isoformat() if latest.created_at else None,
        } if latest else None,
        'storage': {'total': 0, 'used': total_size, 'free': 0},
    })


# ─── 清理 ──────────────────────────────────────────────────

@backup_bp.route('/cleanup', methods=['POST'])
@require_roles('admin')
def cleanup_expired_backups():
    count = cleanup_expired(request.args.get('force') == 'true')
    return _ok({'deleted_count': count}, f'Cleaned up {count} expired backups')


# ─── 删除 ──────────────────────────────────────────────────

@backup_bp.route('/<backup_id>', methods=['DELETE'])
@require_roles('admin')
def delete_backup(backup_id):
    record = BackupRecord.query.filter_by(backup_id=backup_id).first()
    if not record:
        return _err(4040, 'Backup not found', 404)
    db.session.delete(record)
    db.session.commit()
    return _ok({'backup_id': backup_id}, 'Backup deleted')


# ─── 任务 ──────────────────────────────────────────────────

@backup_bp.route('/tasks', methods=['GET'])
@require_roles('admin')
def get_backup_tasks():
    tasks = BackupTask.query.order_by(BackupTask.created_at.desc()).limit(50).all()
    return _ok({
        'tasks': [{
            'id': t.id, 'type': t.task_type, 'status': t.status,
            'created_at': t.created_at.isoformat() if t.created_at else None,
        } for t in tasks]
    })


@backup_bp.route('/tasks/cleaner/status', methods=['GET'])
@require_roles('admin')
def cleaner_status():
    return _ok({'status': 'running'})


@backup_bp.route('/tasks/cleaner/trigger', methods=['POST'])
@require_roles('admin')
def trigger_cleaner():
    try:
        cleaner = BackupTaskCleaner(current_app._get_current_object())
        count = cleaner.cleanup()
        return _ok({'cleaned': count}, f'Cleaner triggered: {count} cleaned')
    except Exception as e:
        return _err(5000, str(e), 500)


# ─── 恢复记录 ──────────────────────────────────────────────

@backup_bp.route('/restores', methods=['GET'])
@require_roles('admin')
def list_restores():
    page = max(1, int(request.args.get('page', 1)))
    size = min(max(1, int(request.args.get('page_size', 20))), 100)
    q = RestoreRecord.query.order_by(RestoreRecord.started_at.desc())
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return _ok({
        'total': total, 'page': page, 'page_size': size,
        'has_next': page * size < total,
        'restores': [{
            'id': r.id, 'backup_id': r.backup_id, 'status': r.status,
            'started_at': r.started_at.isoformat() if r.started_at else None,
            'completed_at': r.completed_at.isoformat() if r.completed_at else None,
            'message': r.status_message,
        } for r in items],
    })


@backup_bp.route('/restores/<restore_id>', methods=['GET'])
@require_roles('admin')
def get_restore(restore_id):
    r = RestoreRecord.query.get(restore_id)
    if not r:
        return _err(4040, 'Restore not found', 404)
    return _ok({
        'id': r.id, 'backup_id': r.backup_id, 'status': r.status,
        'started_at': r.started_at.isoformat() if r.started_at else None,
        'completed_at': r.completed_at.isoformat() if r.completed_at else None,
        'message': r.status_message,
    })


@backup_bp.route('/restores/<restore_id>/cancel', methods=['POST'])
@require_roles('admin')
def cancel_restore(restore_id):
    r = RestoreRecord.query.get(restore_id)
    if not r:
        return _err(4040, 'Restore not found', 404)
    r.status = 'cancelled'
    db.session.commit()
    return _ok({'restore_id': restore_id, 'status': 'cancelled'})


@backup_bp.route('/restores/cleanup', methods=['POST'])
@require_roles('admin')
def cleanup_restores():
    cutoff = datetime.now(SHANGHAI_TZ) - timedelta(days=7)
    old = RestoreRecord.query.filter(RestoreRecord.started_at < cutoff).all()
    count = len(old)
    for r in old:
        db.session.delete(r)
    db.session.commit()
    return _ok({'deleted': count}, f'Cleaned up {count} restore records')


# ─── 物理备份 ──────────────────────────────────────────────

@backup_bp.route('/physical/create', methods=['POST'])
@require_roles('admin')
def create_physical_backup():
    try:
        engine = get_physical_backup_engine()
        result = engine.create_backup()
        if result.get('success'):
            sync_physical_backups_to_database()
            return _ok({'backup_id': result.get('backup_id')}, 'Physical backup created')
        return _err(5000, result.get('error', 'Backup failed'), 500)
    except Exception as e:
        return _err(5000, str(e), 500)


@backup_bp.route('/physical/list', methods=['GET'])
@require_roles('admin')
def list_physical_backups():
    try:
        engine = get_physical_backup_engine()
        backups = engine.list_backups()
        return _ok({'backups': backups})
    except Exception as e:
        return _err(5000, str(e), 500)


@backup_bp.route('/physical/<backup_id>', methods=['GET'])
@require_roles('admin')
def get_physical_backup(backup_id):
    try:
        engine = get_physical_backup_engine()
        info = engine.get_backup_info(backup_id)
        if not info:
            return _err(4040, 'Physical backup not found', 404)
        return _ok(info)
    except Exception as e:
        return _err(5000, str(e), 500)


@backup_bp.route('/physical/<backup_id>/restore', methods=['POST'])
@require_roles('admin')
def restore_physical_backup(backup_id):
    data = request.get_json() or {}
    try:
        engine = get_physical_restore_engine()
        result = engine.restore(backup_id, data.get('options', {}))
        if result.get('success'):
            return _ok({'backup_id': backup_id}, 'Physical restore completed')
        return _err(5000, result.get('error', 'Restore failed'), 500)
    except Exception as e:
        return _err(5000, str(e), 500)


@backup_bp.route('/physical/<backup_id>/delete', methods=['DELETE'])
@require_roles('admin')
def delete_physical_backup(backup_id):
    try:
        engine = get_physical_backup_engine()
        result = engine.delete_backup(backup_id)
        if result.get('success'):
            return _ok({'backup_id': backup_id}, 'Physical backup deleted')
        return _err(5000, result.get('error', 'Delete failed'), 500)
    except Exception as e:
        return _err(5000, str(e), 500)


# ─── 同步 ──────────────────────────────────────────────────

@backup_bp.route('/sync', methods=['POST'])
@require_roles('admin')
def sync_backup_records():
    count = sync_physical_backups_to_database()
    return _ok({'synced': count}, f'Synchronized {count} records')


@backup_bp.route('/status/sync', methods=['POST'])
@require_roles('admin')
def sync_status():
    count = sync_physical_backups_to_database()
    return _ok({'synced': count})


# ─── 外部元数据 ────────────────────────────────────────────

@backup_bp.route('/external/sync', methods=['POST'])
@require_roles('admin')
def external_sync():
    try:
        manager = get_external_metadata_manager()
        result = manager.sync()
        return _ok({'synced': result.get('synced', 0)}, 'External metadata synced')
    except Exception as e:
        return _err(5000, str(e), 500)


@backup_bp.route('/external/conflicts', methods=['GET'])
@require_roles('admin')
def list_external_conflicts():
    try:
        manager = get_external_metadata_manager()
        conflicts = manager.get_conflicts()
        return _ok({'conflicts': [
            {'id': c.id, 'type': c.conflict_type, 'reason': c.conflict_reason,
             'status': c.status, 'created_at': c.created_at.isoformat() if c.created_at else None}
            for c in (conflicts or [])
        ]})
    except Exception as e:
        return _err(5000, str(e), 500)


@backup_bp.route('/external/conflicts/<backup_id>/resolve', methods=['POST'])
@require_roles('admin')
def resolve_external_conflict(backup_id):
    try:
        manager = get_external_metadata_manager()
        result = manager.resolve_conflict(backup_id, request.get_json() or {})
        return _ok(result, 'Conflict resolved')
    except Exception as e:
        return _err(5000, str(e), 500)


@backup_bp.route('/external/statistics', methods=['GET'])
@require_roles('admin')
def external_statistics():
    try:
        manager = get_external_metadata_manager()
        stats = manager.get_statistics()
        return _ok(stats)
    except Exception as e:
        return _err(5000, str(e), 500)
