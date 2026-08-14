"""备份系统业务逻辑 — 供 routes.py 编排调用"""

import json
from datetime import datetime, timedelta

from flask import current_app

from .. import db
from ..models import SHANGHAI_TZ, BackupConfig, BackupRecord
from .physical_backup_engine import PhysicalBackupEngine
from .physical_restore_engine import PhysicalRestoreEngine

# 引擎实例缓存
_physical_backup_engine = None
_physical_restore_engine = None


def _get_backup_config() -> dict:
    return {
        "mysql_container": current_app.config.get("MYSQL_CONTAINER_NAME", "blog-mysql"),
        "mysql_volume": current_app.config.get("MYSQL_VOLUME_NAME", "auto-detect"),
        "backup_root": current_app.config.get(
            "PHYSICAL_BACKUP_ROOT", "./backups/physical"
        ),
        "hot_backup": current_app.config.get("PHYSICAL_HOT_BACKUP", True),
        "compress_backup": current_app.config.get("PHYSICAL_COMPRESS_BACKUP", True),
    }


def get_physical_backup_engine():
    """获取物理备份引擎实例（懒加载）。"""
    global _physical_backup_engine
    if _physical_backup_engine is None:
        _physical_backup_engine = PhysicalBackupEngine(_get_backup_config())
    return _physical_backup_engine


def get_physical_restore_engine():
    """获取物理恢复引擎实例（懒加载）。"""
    global _physical_restore_engine
    if _physical_restore_engine is None:
        cfg = _get_backup_config()
        _physical_restore_engine = PhysicalRestoreEngine(cfg)
    return _physical_restore_engine


def should_resolve_conflict(conflict) -> bool:
    """判断是否应当在统计页面自动解决冲突（保守策略）。"""
    try:
        reason = conflict.conflict_reason or ""
        if "MySQL=running" in reason and "外部=completed" in reason:
            return True
        if "MySQL=completed" in reason and (
            "外部=pending" in reason or "外部=running" in reason
        ):
            return True
        if conflict.completed_at and conflict.status in ("pending", "running"):
            return True
        return False
    except Exception:
        return False


def sync_physical_backups_to_database():
    """同步物理备份记录到数据库。"""
    engine = get_physical_backup_engine()
    physical_backups = engine.list_backups()
    synced = 0
    for pb in physical_backups:
        bid = pb.get("backup_id")
        if BackupRecord.query.filter_by(backup_id=bid).first():
            continue
        record = BackupRecord(
            backup_id=bid,
            backup_type="physical",
            status="completed",
            created_at=datetime.now(SHANGHAI_TZ),
        )
        db.session.add(record)
        synced += 1
    if synced:
        db.session.commit()
    return synced


def list_backup_records(page, size, status, backup_type, sort_by, sort_order):
    """分页查询备份记录。"""
    q = BackupRecord.query
    if status:
        q = q.filter(BackupRecord.status == status)
    if backup_type:
        q = q.filter(BackupRecord.backup_type == backup_type)
    sort_col = getattr(BackupRecord, sort_by, BackupRecord.created_at)
    order = sort_col.desc() if sort_order == "desc" else sort_col.asc()
    total = q.count()
    items = q.order_by(order).offset((page - 1) * size).limit(size).all()
    return total, items


DEFAULT_CONFIG = {
    "auto_backup": False,
    "backup_interval_hours": 24,
    "retention_days": 30,
    "backup_time": "02:00",
    "backup_type": "full",
    "include_external_metadata": False,
}


_CONFIG_KEY_MAP = {
    "auto_backup": "backup_auto_backup",
    "backup_interval_hours": "backup_interval_hours",
    "retention_days": "backup_retention_days",
    "backup_time": "backup_time",
    "backup_type": "backup_type",
    "include_external_metadata": "backup_include_external_metadata",
}


def _config_value(key):
    rec = BackupConfig.query.filter_by(config_key=key).first()
    if not rec or rec.config_value is None:
        return None
    val = rec.config_value
    if rec.config_type == "int":
        try:
            return int(val)
        except (TypeError, ValueError):
            return None
    if rec.config_type == "bool":
        return str(val).lower() in ("1", "true", "yes", "on")
    if rec.config_type == "json":
        try:
            return json.loads(val)
        except (TypeError, ValueError):
            return None
    return val


def get_config():
    """获取备份配置（key-value 存储）。"""
    result = {}
    for field, key in _CONFIG_KEY_MAP.items():
        val = _config_value(key)
        result[field] = val if val is not None else DEFAULT_CONFIG[field]
    return result


def update_config(data: dict):
    """更新备份配置（key-value 存储）。"""
    for field, key in _CONFIG_KEY_MAP.items():
        if field not in data:
            continue
        value = data[field]
        rec = BackupConfig.query.filter_by(config_key=key).first()
        if isinstance(value, bool):
            config_type = "bool"
            stored = "1" if value else "0"
        elif isinstance(value, int):
            config_type = "int"
            stored = str(value)
        elif isinstance(value, (dict, list)):
            config_type = "json"
            stored = json.dumps(value, ensure_ascii=False)
        else:
            config_type = "string"
            stored = str(value)
        if rec is None:
            rec = BackupConfig(
                config_key=key,
                config_value=stored,
                config_type=config_type,
                category="backup",
            )
            db.session.add(rec)
        else:
            rec.config_value = stored
            rec.config_type = config_type
    db.session.commit()


def cleanup_expired(force: bool = False):
    """清理过期备份。"""
    config = BackupConfig.query.first()
    retention = config.retention_days if config else 30
    cutoff = datetime.now(SHANGHAI_TZ) - timedelta(days=retention)
    expired = BackupRecord.query.filter(
        BackupRecord.created_at < cutoff,
        BackupRecord.status.in_(["completed", "failed"]),
    )
    if not force:
        expired = expired.filter(BackupRecord.backup_type != "physical")
    count = expired.count()
    expired.delete(synchronize_session=False)
    db.session.commit()
    return count
