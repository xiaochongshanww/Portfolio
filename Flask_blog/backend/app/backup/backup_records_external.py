"""
外部备份记录数据库模型
用于解决备份状态管理与数据库恢复冲突问题

设计原理：
- 独立的SQLite数据库存储，完全与主MySQL隔离
- 增加同步状态管理和冲突解决机制
- 支持物理文件验证和状态修复
"""

from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
from typing import Optional, Dict, Any, List
import json
import os
from pathlib import Path

# 使用独立的SQLAlchemy实例，配置为SQLite
external_db = SQLAlchemy()

# 时区设置 - 上海时区
try:
    from zoneinfo import ZoneInfo
    SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
except ImportError:
    # Python 3.8及以下版本的兼容性处理
    from datetime import timezone, timedelta
    SHANGHAI_TZ = timezone(timedelta(hours=8))


class BackupRecordExternal(external_db.Model):
    """外部备份记录模型 - 存储在独立SQLite数据库中"""
    __tablename__ = 'backup_records_external'

    # 基础字段
    id = external_db.Column(external_db.Integer, primary_key=True)
    backup_id = external_db.Column(external_db.String(255), nullable=False, unique=True, index=True)
    backup_type = external_db.Column(external_db.String(50), nullable=False, default='physical')
    status = external_db.Column(external_db.String(50), nullable=False, default='pending', index=True)
    
    # 文件信息
    file_path = external_db.Column(external_db.String(512), nullable=True)
    file_size = external_db.Column(external_db.BigInteger, nullable=True)
    compressed_size = external_db.Column(external_db.BigInteger, nullable=True)
    compression_ratio = external_db.Column(external_db.Float, nullable=True)
    checksum = external_db.Column(external_db.String(255), nullable=True)
    
    # 配置信息
    databases_count = external_db.Column(external_db.Integer, nullable=False, default=1)
    encryption_enabled = external_db.Column(external_db.Boolean, nullable=False, default=False)
    
    # 错误信息
    error_message = external_db.Column(external_db.Text, nullable=True)
    
    # 时间字段
    created_at = external_db.Column(external_db.DateTime, nullable=False, default=lambda: datetime.now(SHANGHAI_TZ))
    started_at = external_db.Column(external_db.DateTime, nullable=True)
    completed_at = external_db.Column(external_db.DateTime, nullable=True)
    
    # 同步管理字段
    mysql_record_id = external_db.Column(external_db.Integer, nullable=True, index=True)  # 主数据库记录ID
    sync_status = external_db.Column(external_db.String(20), nullable=False, default='pending', index=True)  # pending, synced, conflict, verified
    last_sync_at = external_db.Column(external_db.DateTime, nullable=True)
    file_verified_at = external_db.Column(external_db.DateTime, nullable=True)
    conflict_reason = external_db.Column(external_db.Text, nullable=True)
    
    # 扩展数据（JSON格式存储）
    extra_data_json = external_db.Column(external_db.Text, nullable=True)
    
    # 审计字段
    updated_at = external_db.Column(external_db.DateTime, nullable=False, default=lambda: datetime.now(SHANGHAI_TZ), onupdate=lambda: datetime.now(SHANGHAI_TZ))

    @property
    def extra_data(self) -> Optional[Dict]:
        """获取扩展数据"""
        if self.extra_data_json:
            try:
                return json.loads(self.extra_data_json)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    @extra_data.setter
    def extra_data(self, value: Optional[Dict]):
        """设置扩展数据"""
        if value is None:
            self.extra_data_json = None
        else:
            try:
                self.extra_data_json = json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                self.extra_data_json = None

    def get_duration(self) -> Optional[float]:
        """获取备份持续时间（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def verify_file_exists(self) -> bool:
        """验证备份文件是否存在 - 增强版本，支持物理备份检查"""
        if not self.file_path:
            # 对于物理备份，可能没有传统文件路径，需要特殊处理
            if self.backup_type == 'physical':
                return self._verify_physical_backup_exists()
            return False
        
        # 支持相对路径和绝对路径
        if os.path.isabs(self.file_path):
            file_path = Path(self.file_path)
        else:
            # 相对于项目根目录
            base_dir = Path(__file__).parent.parent.parent.parent
            file_path = base_dir / self.file_path
        
        exists = file_path.exists()
        if exists:
            # 更新验证时间
            self.file_verified_at = datetime.now(SHANGHAI_TZ)
        
        return exists
    
    def _verify_physical_backup_exists(self) -> bool:
        """验证物理备份是否存在"""
        try:
            # 对于物理备份，检查多个可能的位置
            base_dir = Path(__file__).parent.parent.parent.parent
            backup_locations = [
                # 标准物理备份目录
                base_dir / 'backups' / 'physical' / self.backup_id,
                base_dir / 'backups' / 'physical' / f"{self.backup_id}.tar.gz",
                # 快照目录
                base_dir / 'backups' / 'snapshots' / f"{self.backup_id}.tar.gz",
                # 其他可能的位置
                base_dir / 'backend' / 'backups' / 'physical' / self.backup_id,
                base_dir / 'backend' / 'backups' / 'physical' / f"{self.backup_id}.tar.gz"
            ]
            
            for location in backup_locations:
                if location.exists():
                    # 找到备份文件，更新验证时间
                    self.file_verified_at = datetime.now(SHANGHAI_TZ)
                    return True
            
            # 如果都没找到，可能是Docker Volume备份，尝试通过Docker检查
            return self._check_docker_volume_backup()
            
        except Exception as e:
            # 验证过程出错，保守返回True（不改变状态）
            return True
    
    def _check_docker_volume_backup(self) -> bool:
        """检查Docker Volume物理备份是否可用"""
        try:
            import subprocess
            
            # 尝试检查是否有相关的Docker资源
            # 这里使用保守策略：如果无法验证，就认为备份可能存在
            # 避免误删除正确的备份状态
            
            # 检查Docker是否可用
            result = subprocess.run(['docker', 'version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                # Docker不可用，无法验证，保守返回True
                return True
            
            # Docker可用，但无法直接验证Volume备份的完整性
            # 使用保守策略
            return True
            
        except Exception:
            # 任何异常都使用保守策略
            return True

    def update_sync_status(self, new_status: str, reason: str = None):
        """更新同步状态"""
        old_status = self.sync_status
        self.sync_status = new_status
        self.last_sync_at = datetime.now(SHANGHAI_TZ)
        
        if new_status == 'conflict' and reason:
            self.conflict_reason = reason
        elif new_status != 'conflict':
            self.conflict_reason = None
        
        # 记录状态变更
        if old_status != new_status:
            self.updated_at = datetime.now(SHANGHAI_TZ)

    def resolve_conflict_by_file_check(self) -> str:
        """通过文件检查解决冲突 - 增强版本，避免误判"""
        if self.sync_status != 'conflict':
            return 'no_conflict'
        
        # 检查冲突原因，如果是状态冲突，需要更智能的处理
        if self.conflict_reason and '状态冲突' in self.conflict_reason:
            return self._resolve_status_conflict_intelligently()
        
        # 对于其他类型的冲突，进行文件检查
        file_exists = self.verify_file_exists()
        
        if file_exists:
            # 文件存在，应该是completed状态
            if self.status in ['pending', 'running']:
                old_status = self.status
                self.status = 'completed'
                if not self.completed_at:
                    self.completed_at = datetime.now(SHANGHAI_TZ)
                
                self.update_sync_status('verified', f'状态从{old_status}修复为completed（文件存在）')
                return 'fixed_to_completed'
            else:
                self.update_sync_status('verified', '状态与文件存在性一致')
                return 'verified_consistent'
        else:
            # 文件不存在 - 但需要考虑物理备份的特殊性
            if self.backup_type == 'physical' and self.status == 'completed':
                # 物理备份可能没有传统意义的文件，使用保守策略
                self.update_sync_status('verified', '物理备份：文件检查不适用，维持原状态')
                return 'verified_consistent'
            elif self.status == 'completed':
                old_status = self.status
                self.status = 'failed'
                self.error_message = '备份文件丢失，状态已修正为失败'
                
                self.update_sync_status('verified', f'状态从{old_status}修复为failed（文件不存在）')
                return 'fixed_to_failed'
            else:
                self.update_sync_status('verified', '状态与文件不存在一致')
                return 'verified_consistent'
    
    def _resolve_status_conflict_intelligently(self) -> str:
        """智能解决状态冲突"""
        try:
            # 解析冲突原因中的状态信息
            if not self.conflict_reason:
                return 'no_conflict'
            
            # 提取MySQL和外部状态
            import re
            match = re.search(r'MySQL=(\w+), 外部=(\w+)', self.conflict_reason)
            if not match:
                return 'verified_consistent'
            
            mysql_status = match.group(1)
            external_status = match.group(2)
            
            # 智能判断哪个状态更准确
            
            # 1. 如果外部状态是completed，但MySQL是running，这是物理恢复后的正常现象
            if external_status == 'completed' and mysql_status == 'running':
                # 外部元数据是权威数据源，应该以外部状态为准
                # 这种情况通常发生在物理恢复后，MySQL被恢复到备份创建过程中的状态
                old_status = self.status
                self.status = 'completed'  # 以外部元数据为准
                self.update_sync_status('verified', f'智能解决：以外部元数据为准，从{old_status}修复为completed（物理恢复后正常现象）')
                return 'fixed_to_completed'
            
            # 2. 如果MySQL状态是completed，而外部是pending/running，通常MySQL更准确
            elif mysql_status == 'completed' and external_status in ['pending', 'running']:
                # 检查时间逻辑，如果有completed_at时间，说明确实已完成
                if self.completed_at:
                    old_status = self.status
                    self.status = mysql_status
                    self.update_sync_status('verified', f'智能解决：从{old_status}同步为{mysql_status}（有完成时间）')
                    return 'fixed_to_completed'
            
            # 2. 如果外部状态是completed，但MySQL是failed，需要文件验证
            elif external_status == 'completed' and mysql_status == 'failed':
                file_exists = self.verify_file_exists()
                if file_exists or self.backup_type == 'physical':
                    # 文件存在或是物理备份，保持completed状态
                    self.update_sync_status('verified', '智能解决：维持completed状态（文件存在或物理备份）')
                    return 'verified_consistent'
                else:
                    # 文件不存在，采用MySQL的failed状态
                    old_status = self.status
                    self.status = mysql_status
                    self.update_sync_status('verified', f'智能解决：从{old_status}同步为{mysql_status}（文件不存在）')
                    return 'fixed_to_failed'
            
            # 3. 其他情况使用保守策略
            else:
                self.update_sync_status('verified', '智能解决：状态冲突复杂，维持当前状态')
                return 'verified_consistent'
                
        except Exception as e:
            # 智能解决出错，使用保守策略
            self.update_sync_status('verified', f'智能解决异常，维持原状态: {e}')
            return 'verified_consistent'

    def to_dict(self, include_extra_data: bool = True) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'id': self.id,
            'backup_id': self.backup_id,
            'backup_type': self.backup_type,
            'status': self.status,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'compressed_size': self.compressed_size,
            'compression_ratio': self.compression_ratio,
            'checksum': self.checksum,
            'databases_count': self.databases_count,
            'encryption_enabled': self.encryption_enabled,
            'error_message': self.error_message,
            
            # 时间字段
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            
            # 同步字段
            'mysql_record_id': self.mysql_record_id,
            'sync_status': self.sync_status,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'file_verified_at': self.file_verified_at.isoformat() if self.file_verified_at else None,
            'conflict_reason': self.conflict_reason,
            
            # 计算字段
            'duration': self.get_duration(),
            'file_exists': self.verify_file_exists(),
            
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_extra_data:
            result['extra_data'] = self.extra_data
            
        return result

    @classmethod
    def from_mysql_record(cls, mysql_record: Dict) -> 'BackupRecordExternal':
        """从MySQL记录创建外部记录"""
        extra_data = mysql_record.get('extra_data')
        if isinstance(extra_data, str):
            try:
                extra_data = json.loads(extra_data)
            except (json.JSONDecodeError, TypeError):
                extra_data = None
        
        return cls(
            backup_id=mysql_record['backup_id'],
            backup_type=mysql_record.get('backup_type', 'physical'),
            status=mysql_record.get('status', 'pending'),
            file_path=mysql_record.get('file_path'),
            file_size=mysql_record.get('file_size'),
            compressed_size=mysql_record.get('compressed_size'),
            compression_ratio=mysql_record.get('compression_ratio'),
            checksum=mysql_record.get('checksum'),
            databases_count=mysql_record.get('databases_count', 1),
            encryption_enabled=mysql_record.get('encryption_enabled', False),
            error_message=mysql_record.get('error_message'),
            
            created_at=mysql_record.get('created_at'),
            started_at=mysql_record.get('started_at'),
            completed_at=mysql_record.get('completed_at'),
            
            mysql_record_id=mysql_record.get('id'),
            sync_status='synced',
            last_sync_at=datetime.now(SHANGHAI_TZ),
            extra_data=extra_data
        )

    def __repr__(self):
        return f"<BackupRecordExternal {self.backup_id} status={self.status} sync={self.sync_status}>"


class RestoreRecordExternal(external_db.Model):
    """外部恢复记录模型"""
    __tablename__ = 'restore_records_external'

    # 基础字段
    id = external_db.Column(external_db.Integer, primary_key=True)
    restore_id = external_db.Column(external_db.String(255), nullable=False, unique=True, index=True)
    backup_id = external_db.Column(external_db.String(255), nullable=True)
    backup_record_id = external_db.Column(external_db.Integer, nullable=True)
    restore_type = external_db.Column(external_db.String(50), nullable=False, default='full')
    status = external_db.Column(external_db.String(50), nullable=False, default='pending', index=True)
    progress = external_db.Column(external_db.Integer, nullable=False, default=0)
    
    # 状态信息
    status_message = external_db.Column(external_db.Text, nullable=True)
    error_message = external_db.Column(external_db.Text, nullable=True)
    restore_options_json = external_db.Column(external_db.Text, nullable=True)  # JSON格式
    requested_by = external_db.Column(external_db.String(255), nullable=False, default='unknown')
    restored_databases_count = external_db.Column(external_db.Integer, nullable=False, default=0)
    
    # 时间字段
    created_at = external_db.Column(external_db.DateTime, nullable=False, default=lambda: datetime.now(SHANGHAI_TZ))
    started_at = external_db.Column(external_db.DateTime, nullable=True)
    completed_at = external_db.Column(external_db.DateTime, nullable=True)
    
    # 同步管理字段
    mysql_record_id = external_db.Column(external_db.Integer, nullable=True, index=True)
    sync_status = external_db.Column(external_db.String(20), nullable=False, default='pending', index=True)
    last_sync_at = external_db.Column(external_db.DateTime, nullable=True)
    
    # 审计字段
    updated_at = external_db.Column(external_db.DateTime, nullable=False, default=lambda: datetime.now(SHANGHAI_TZ), onupdate=lambda: datetime.now(SHANGHAI_TZ))

    @property
    def restore_options(self) -> Optional[Dict]:
        """获取恢复选项"""
        if self.restore_options_json:
            try:
                return json.loads(self.restore_options_json)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    @restore_options.setter
    def restore_options(self, value: Optional[Dict]):
        """设置恢复选项"""
        if value is None:
            self.restore_options_json = None
        else:
            try:
                self.restore_options_json = json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                self.restore_options_json = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'restore_id': self.restore_id,
            'backup_id': self.backup_id,
            'backup_record_id': self.backup_record_id,
            'restore_type': self.restore_type,
            'status': self.status,
            'progress': self.progress,
            'status_message': self.status_message,
            'error_message': self.error_message,
            'restore_options': self.restore_options,
            'requested_by': self.requested_by,
            'restored_databases_count': self.restored_databases_count,
            
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            
            'mysql_record_id': self.mysql_record_id,
            'sync_status': self.sync_status,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<RestoreRecordExternal {self.restore_id} status={self.status} sync={self.sync_status}>"


class SyncLogExternal(external_db.Model):
    """同步操作日志"""
    __tablename__ = 'sync_logs_external'

    id = external_db.Column(external_db.Integer, primary_key=True)
    operation = external_db.Column(external_db.String(100), nullable=False, index=True)  # sync_backup, sync_restore, verify_files, resolve_conflict
    record_type = external_db.Column(external_db.String(50), nullable=False)  # backup, restore
    record_id = external_db.Column(external_db.String(255), nullable=False, index=True)  # backup_id or restore_id
    
    old_status = external_db.Column(external_db.String(50), nullable=True)
    new_status = external_db.Column(external_db.String(50), nullable=True)
    sync_direction = external_db.Column(external_db.String(50), nullable=False, default='mysql_to_sqlite')  # mysql_to_sqlite, sqlite_to_mysql, bidirectional
    conflict_resolved = external_db.Column(external_db.Boolean, nullable=False, default=False)
    file_exists = external_db.Column(external_db.Boolean, nullable=True)
    
    details_json = external_db.Column(external_db.Text, nullable=True)  # 详细信息JSON
    created_at = external_db.Column(external_db.DateTime, nullable=False, default=lambda: datetime.now(SHANGHAI_TZ))

    @property
    def details(self) -> Optional[Dict]:
        """获取详细信息"""
        if self.details_json:
            try:
                return json.loads(self.details_json)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    @details.setter
    def details(self, value: Optional[Dict]):
        """设置详细信息"""
        if value is None:
            self.details_json = None
        else:
            try:
                self.details_json = json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                self.details_json = None

    def __repr__(self):
        return f"<SyncLogExternal {self.operation} {self.record_type}:{self.record_id}>"


# TODO(human): 实现外部元数据管理器类
class ExternalMetadataManager:
    """外部元数据管理器"""
    
    def __init__(self, app=None, db_path: str = None):
        self.app = app
        self.db_path = db_path or self._get_default_db_path()
        self._standalone_engine = None
        self._standalone_session = None
        
        if app:
            self.init_app(app)
        else:
            # 独立模式，不依赖Flask应用
            self._init_standalone_db()
    
    def _get_default_db_path(self) -> str:
        """获取默认数据库路径"""
        # 默认存储在backend/metadata/目录下
        base_dir = Path(__file__).parent.parent.parent
        metadata_dir = base_dir / 'metadata'
        metadata_dir.mkdir(exist_ok=True)
        return f"sqlite:///{metadata_dir / 'backup_external_v2.db'}"
    
    def _init_standalone_db(self):
        """独立模式初始化数据库"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # 创建引擎和会话
        self._standalone_engine = create_engine(self.db_path, echo=False)
        
        # 创建表结构
        external_db.metadata.create_all(self._standalone_engine)
        
        Session = sessionmaker(bind=self._standalone_engine)
        self._standalone_session = Session()
    
    def init_app(self, app):
        """初始化Flask应用"""
        # 配置外部数据库连接
        app.config.setdefault('EXTERNAL_BACKUP_DATABASE_URI', self.db_path)
        
        # 不使用Flask-SQLAlchemy的app注册，改用独立引擎
        self._init_standalone_db()
        
        # 在应用上下文中验证数据库
        with app.app_context():
            try:
                # 验证数据库连接
                stats = self.get_statistics()
                app.logger.info(f"外部元数据数据库验证成功: {stats['total_backup_records']} 条记录")
            except Exception as e:
                app.logger.warning(f"外部元数据数据库验证失败: {e}")
    
    def sync_from_mysql(self, mysql_records: list) -> dict:
        """从MySQL同步备份记录到外部数据库"""
        result = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'conflicts': 0,
            'unchanged': 0,
            'errors': []
        }
        
        try:
            for mysql_record in mysql_records:
                result['total_processed'] += 1
                
                try:
                    # 转换MySQL记录为字典格式（如果需要）
                    if hasattr(mysql_record, '__dict__'):
                        record_dict = {
                            'id': mysql_record.id,
                            'backup_id': mysql_record.backup_id,
                            'backup_type': mysql_record.backup_type,
                            'status': mysql_record.status,
                            'file_path': mysql_record.file_path,
                            'file_size': mysql_record.file_size,
                            'compressed_size': mysql_record.compressed_size,
                            'compression_ratio': mysql_record.compression_ratio,
                            'checksum': mysql_record.checksum,
                            'databases_count': mysql_record.databases_count,
                            'encryption_enabled': mysql_record.encryption_enabled,
                            'error_message': mysql_record.error_message,
                            'created_at': mysql_record.created_at,
                            'started_at': mysql_record.started_at,
                            'completed_at': mysql_record.completed_at,
                            'extra_data': mysql_record.get_extra_data() if hasattr(mysql_record, 'get_extra_data') else None
                        }
                    else:
                        record_dict = mysql_record
                    
                    backup_id = record_dict['backup_id']
                    
                    # 查找外部数据库中是否存在该记录
                    existing_record = BackupRecordExternal.query.filter_by(backup_id=backup_id).first()
                    
                    if not existing_record:
                        # 创建新记录
                        new_record = BackupRecordExternal.from_mysql_record(record_dict)
                        external_db.session.add(new_record)
                        result['created'] += 1
                        
                        # 记录同步日志
                        self._log_sync_operation(
                            operation='sync_backup',
                            record_type='backup',
                            record_id=backup_id,
                            new_status=record_dict['status'],
                            sync_direction='mysql_to_sqlite',
                            details={'action': 'created', 'mysql_id': record_dict.get('id')}
                        )
                        
                    else:
                        # 检查是否需要更新
                        sync_result = self._sync_existing_record(existing_record, record_dict)
                        
                        if sync_result == 'updated':
                            result['updated'] += 1
                        elif sync_result == 'conflict':
                            result['conflicts'] += 1
                        else:
                            result['unchanged'] += 1
                    
                except Exception as e:
                    error_msg = f"同步备份记录 {mysql_record.get('backup_id', 'unknown')} 失败: {e}"
                    result['errors'].append(error_msg)
                    continue
            
            # 提交所有更改
            external_db.session.commit()
            
        except Exception as e:
            external_db.session.rollback()
            result['errors'].append(f"同步过程发生异常: {e}")
        
        return result
    
    def _sync_existing_record(self, existing_record: BackupRecordExternal, mysql_record: dict) -> str:
        """同步现有记录"""
        old_status = existing_record.status
        mysql_status = mysql_record['status']
        
        # 更新MySQL记录ID
        existing_record.mysql_record_id = mysql_record.get('id')
        
        # 检查状态是否一致
        if old_status != mysql_status:
            # 状态不一致，需要判断是否为冲突
            file_exists = existing_record.verify_file_exists()
            
            # 冲突检测逻辑
            if self._is_status_conflict(old_status, mysql_status, file_exists):
                existing_record.update_sync_status('conflict', 
                    f'状态冲突: 外部({old_status}) vs MySQL({mysql_status}), 文件存在: {file_exists}')
                
                self._log_sync_operation(
                    operation='detect_conflict',
                    record_type='backup',
                    record_id=existing_record.backup_id,
                    old_status=old_status,
                    new_status=mysql_status,
                    sync_direction='mysql_to_sqlite',
                    file_exists=file_exists,
                    details={'conflict_reason': existing_record.conflict_reason}
                )
                return 'conflict'
            else:
                # 不是冲突，直接更新
                self._update_record_from_mysql(existing_record, mysql_record)
                existing_record.update_sync_status('synced')
                
                self._log_sync_operation(
                    operation='sync_backup',
                    record_type='backup', 
                    record_id=existing_record.backup_id,
                    old_status=old_status,
                    new_status=mysql_status,
                    sync_direction='mysql_to_sqlite'
                )
                return 'updated'
        else:
            # 状态一致，更新其他字段
            self._update_record_from_mysql(existing_record, mysql_record)
            existing_record.update_sync_status('synced')
            return 'unchanged'
    
    def _is_status_conflict(self, external_status: str, mysql_status: str, file_exists: bool) -> bool:
        """判断是否为状态冲突"""
        # 常见冲突场景：
        # 1. MySQL恢复后状态回滚为running，但文件已存在应该是completed
        # 2. 外部状态为completed，但MySQL为running（典型的恢复后冲突）
        # 3. 文件不存在但状态为completed
        
        if external_status == 'completed' and mysql_status in ['running', 'pending']:
            return file_exists  # 如果文件存在，说明确实完成了，是冲突
        
        if external_status in ['running', 'pending'] and mysql_status == 'completed':
            return not file_exists  # 如果文件不存在但MySQL说完成了，是冲突
            
        if mysql_status == 'completed' and not file_exists:
            return True  # 状态说完成了但文件不存在，明显冲突
            
        if mysql_status in ['running', 'pending'] and file_exists:
            return True  # 状态说在进行中但文件已存在，可能冲突
        
        return False
    
    def _update_record_from_mysql(self, external_record: BackupRecordExternal, mysql_record: dict):
        """从MySQL记录更新外部记录"""
        external_record.status = mysql_record.get('status', external_record.status)
        external_record.file_path = mysql_record.get('file_path', external_record.file_path)
        external_record.file_size = mysql_record.get('file_size', external_record.file_size)
        external_record.compressed_size = mysql_record.get('compressed_size', external_record.compressed_size)
        external_record.compression_ratio = mysql_record.get('compression_ratio', external_record.compression_ratio)
        external_record.checksum = mysql_record.get('checksum', external_record.checksum)
        external_record.encryption_enabled = mysql_record.get('encryption_enabled', external_record.encryption_enabled)
        external_record.error_message = mysql_record.get('error_message', external_record.error_message)
        
        # 更新时间字段（如果MySQL有更新的话）
        if mysql_record.get('started_at'):
            external_record.started_at = mysql_record['started_at']
        if mysql_record.get('completed_at'):
            external_record.completed_at = mysql_record['completed_at']
            
        # 更新额外数据
        external_record.extra_data = mysql_record.get('extra_data', external_record.extra_data)
    
    def resolve_all_conflicts(self) -> dict:
        """解决所有状态冲突"""
        result = {
            'total_conflicts': 0,
            'resolved': 0,
            'fixed_to_completed': 0,
            'fixed_to_failed': 0,
            'verified_consistent': 0,
            'unresolved': 0,
            'errors': []
        }
        
        try:
            # 查找所有冲突状态的记录
            conflict_records = BackupRecordExternal.query.filter_by(sync_status='conflict').all()
            result['total_conflicts'] = len(conflict_records)
            
            for record in conflict_records:
                try:
                    old_status = record.status
                    resolution_result = record.resolve_conflict_by_file_check()
                    
                    if resolution_result == 'fixed_to_completed':
                        result['fixed_to_completed'] += 1
                        result['resolved'] += 1
                    elif resolution_result == 'fixed_to_failed':
                        result['fixed_to_failed'] += 1
                        result['resolved'] += 1
                    elif resolution_result in ['verified_consistent']:
                        result['verified_consistent'] += 1
                        result['resolved'] += 1
                    else:
                        result['unresolved'] += 1
                    
                    # 记录解决日志
                    self._log_sync_operation(
                        operation='resolve_conflict',
                        record_type='backup',
                        record_id=record.backup_id,
                        old_status=old_status,
                        new_status=record.status,
                        conflict_resolved=resolution_result != 'no_conflict',
                        file_exists=record.verify_file_exists(),
                        details={'resolution_result': resolution_result}
                    )
                    
                except Exception as e:
                    error_msg = f"解决冲突失败 {record.backup_id}: {e}"
                    result['errors'].append(error_msg)
                    result['unresolved'] += 1
            
            # 提交所有更改
            external_db.session.commit()
            
        except Exception as e:
            external_db.session.rollback()
            result['errors'].append(f"解决冲突过程发生异常: {e}")
        
        return result
    
    def _log_sync_operation(self, operation: str, record_type: str, record_id: str,
                           old_status: str = None, new_status: str = None,
                           sync_direction: str = 'mysql_to_sqlite',
                           conflict_resolved: bool = False, file_exists: bool = None,
                           details: dict = None):
        """记录同步操作日志"""
        try:
            log_entry = SyncLogExternal(
                operation=operation,
                record_type=record_type,
                record_id=record_id,
                old_status=old_status,
                new_status=new_status,
                sync_direction=sync_direction,
                conflict_resolved=conflict_resolved,
                file_exists=file_exists,
                details=details,
                created_at=datetime.now(SHANGHAI_TZ)
            )
            external_db.session.add(log_entry)
        except Exception as e:
            # 日志记录失败不应影响主要操作
            pass
    
    def get_sync_statistics(self) -> dict:
        """获取同步统计信息"""
        try:
            # 备份记录统计
            backup_stats = external_db.session.query(
                external_db.func.count(BackupRecordExternal.id).label('total'),
                external_db.func.sum(external_db.case((BackupRecordExternal.sync_status == 'synced', 1), else_=0)).label('synced'),
                external_db.func.sum(external_db.case((BackupRecordExternal.sync_status == 'conflict', 1), else_=0)).label('conflicts'),
                external_db.func.sum(external_db.case((BackupRecordExternal.sync_status == 'pending', 1), else_=0)).label('pending'),
                external_db.func.sum(external_db.case((BackupRecordExternal.sync_status == 'verified', 1), else_=0)).label('verified')
            ).first()
            
            # 最近同步时间
            last_sync_result = external_db.session.query(
                external_db.func.max(BackupRecordExternal.last_sync_at)
            ).scalar()
            
            # 文件验证统计
            file_verified_count = BackupRecordExternal.query.filter(
                BackupRecordExternal.file_verified_at.isnot(None)
            ).count()
            
            # 同步日志统计
            recent_operations = external_db.session.query(
                SyncLogExternal.operation,
                external_db.func.count(SyncLogExternal.id).label('count')
            ).filter(
                SyncLogExternal.created_at >= datetime.now(SHANGHAI_TZ) - timedelta(hours=24)
            ).group_by(SyncLogExternal.operation).all()
            
            return {
                'backup_records': {
                    'total': backup_stats.total or 0,
                    'synced': backup_stats.synced or 0,
                    'conflicts': backup_stats.conflicts or 0,
                    'pending': backup_stats.pending or 0,
                    'verified': backup_stats.verified or 0
                },
                'last_sync_time': last_sync_result.isoformat() if last_sync_result else None,
                'file_verified_count': file_verified_count,
                'recent_operations_24h': {op.operation: op.count for op in recent_operations},
                'database_path': self.db_path,
                'database_size_mb': self._get_database_size_mb()
            }
        except Exception as e:
            return {
                'error': f'获取统计信息失败: {e}',
                'database_path': self.db_path
            }
    
    def _get_database_size_mb(self) -> float:
        """获取数据库文件大小（MB）"""
        try:
            # 从SQLite URI中提取文件路径
            if self.db_path.startswith('sqlite:///'):
                file_path = self.db_path[10:]  # 移除 'sqlite:///' 前缀
                if os.path.exists(file_path):
                    return round(os.path.getsize(file_path) / 1024 / 1024, 2)
            return 0.0
        except Exception:
            return 0.0
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """清理旧的同步日志"""
        try:
            cutoff_date = datetime.now(SHANGHAI_TZ) - timedelta(days=days_to_keep)
            old_logs = SyncLogExternal.query.filter(
                SyncLogExternal.created_at < cutoff_date
            ).all()
            
            count = len(old_logs)
            for log in old_logs:
                external_db.session.delete(log)
            
            external_db.session.commit()
            return count
        except Exception as e:
            external_db.session.rollback()
            return 0
    
    # ==================== 辅助方法 ====================
    
    def _get_session(self):
        """获取数据库会话"""
        # 总是使用独立会话，避免Flask-SQLAlchemy冲突
        if self._standalone_session:
            return self._standalone_session
        else:
            raise Exception("数据库会话未初始化")
    
    def _create_new_session(self):
        """创建新的独立会话（用于避免会话冲突）"""
        try:
            from sqlalchemy.orm import sessionmaker
            if self._standalone_engine:
                Session = sessionmaker(bind=self._standalone_engine)
                return Session()
            else:
                raise Exception("数据库引擎未初始化")
        except Exception as e:
            raise Exception(f"创建新会话失败: {e}")
    
    def _reinit_session(self):
        """重新初始化会话（用于会话状态冲突恢复）"""
        try:
            if self._standalone_session:
                self._standalone_session.close()
                
            from sqlalchemy.orm import sessionmaker
            if self._standalone_engine:
                Session = sessionmaker(bind=self._standalone_engine)
                self._standalone_session = Session()
            else:
                raise Exception("数据库引擎未初始化")
        except Exception as e:
            raise Exception(f"重新初始化会话失败: {e}")
            
    def _get_fresh_session(self):
        """获取新的独立数据库会话（用于避免会话状态冲突）"""
        if self._standalone_engine:
            from contextlib import contextmanager
            from sqlalchemy.orm import sessionmaker
            
            @contextmanager
            def session_scope():
                """提供事务性会话范围"""
                Session = sessionmaker(bind=self._standalone_engine)
                session = Session()
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()
            
            return session_scope()
        else:
            raise Exception("数据库引擎未初始化")
    
    def _get_query_class(self, model_class):
        """获取查询类"""
        # 总是使用独立会话查询
        if self._standalone_session:
            return self._standalone_session.query(model_class)
        else:
            raise Exception("数据库会话未初始化")
    
    # ==================== 核心CRUD方法 ====================
    
    def create_backup_record(self, backup_id: str, backup_type: str = 'physical', 
                           status: str = 'pending', description: str = '', 
                           requested_by: str = '') -> 'BackupRecordExternal':
        """创建备份记录"""
        try:
            session = self._get_session()
            
            # 将description和requested_by存储在extra_data中
            extra_data = {
                'description': description,
                'requested_by': requested_by
            }
            
            record = BackupRecordExternal(
                backup_id=backup_id,
                backup_type=backup_type,
                status=status,
                created_at=datetime.now(SHANGHAI_TZ)
            )
            
            # 设置extra_data
            record.extra_data = extra_data
            
            session.add(record)
            session.commit()
            
            try:
                self._log_sync_operation('create', 'backup', backup_id, 'manual')
            except:
                pass  # 忽略日志错误
            return record
            
        except Exception as e:
            try:
                session.rollback()
            except:
                pass
            raise Exception(f"创建备份记录失败: {e}")
    
    def get_backup_record(self, backup_id: str) -> Optional['BackupRecordExternal']:
        """获取备份记录"""
        try:
            query = self._get_query_class(BackupRecordExternal)
            return query.filter_by(backup_id=backup_id).first()
        except Exception as e:
            raise Exception(f"查询备份记录失败: {e}")
    
    def update_backup_record(self, backup_id: str, **kwargs) -> bool:
        """更新备份记录 - 使用独立会话避免冲突"""
        session = None
        try:
            # 创建新的独立会话，避免与其他操作的会话冲突
            session = self._create_new_session()
            record = session.query(BackupRecordExternal).filter_by(backup_id=backup_id).first()
            if not record:
                return False
            
            # 更新允许的字段
            allowed_fields = ['status', 'file_size', 'compressed_size', 'compression_ratio', 
                             'file_path', 'checksum', 'error_message', 'completed_at', 
                             'extra_data', 'description']
            
            for key, value in kwargs.items():
                if key in allowed_fields and hasattr(record, key):
                    setattr(record, key, value)
            
            record.last_sync_at = datetime.now(SHANGHAI_TZ)
            session.commit()
            
            try:
                self._log_sync_operation('update', 'backup', backup_id, 'manual')
            except:
                pass  # 忽略日志错误
            return True
            
        except Exception as e:
            if session:
                try:
                    session.rollback()
                except:
                    pass
            raise Exception(f"更新备份记录失败: {e}")
        finally:
            if session:
                try:
                    session.close()
                except:
                    pass
    
    def delete_backup_record(self, backup_id: str) -> bool:
        """删除备份记录"""
        try:
            session = self._get_session()
            query = self._get_query_class(BackupRecordExternal)
            record = query.filter_by(backup_id=backup_id).first()
            if not record:
                return False
            
            session.delete(record)
            session.commit()
            
            try:
                self._log_sync_operation('delete', 'backup', backup_id, 'manual')
            except:
                pass  # 忽略日志错误
            return True
            
        except Exception as e:
            try:
                session.rollback()
            except:
                pass
            raise Exception(f"删除备份记录失败: {e}")
    
    def get_conflict_count(self) -> int:
        """获取冲突记录数量（只读操作，避免会话冲突）"""
        try:
            # 先尝试重置会话状态
            if self._standalone_session:
                try:
                    self._standalone_session.rollback()
                except:
                    pass
                    
            query = self._get_query_class(BackupRecordExternal)
            return query.filter_by(sync_status='conflict').count()
        except Exception as e:
            # 静默失败，返回0以避免前端错误
            return 0
    
    def find_conflicts(self) -> List['BackupRecordExternal']:
        """查找冲突的备份记录"""
        try:
            # 先尝试重置会话状态，避免prepared state问题
            if self._standalone_session:
                try:
                    self._standalone_session.rollback()
                except:
                    pass
                    
            query = self._get_query_class(BackupRecordExternal)
            return query.filter_by(sync_status='conflict').all()
        except Exception as e:
            # 如果仍然失败，尝试重新创建会话
            try:
                self._reinit_session()
                query = self._get_query_class(BackupRecordExternal) 
                return query.filter_by(sync_status='conflict').all()
            except Exception as retry_error:
                raise Exception(f"查找冲突记录失败: {e}, 重试失败: {retry_error}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取外部数据库统计信息"""
        try:
            # 先尝试重置会话状态
            if self._standalone_session:
                try:
                    self._standalone_session.rollback()
                except:
                    pass
                    
            query = self._get_query_class(BackupRecordExternal)
            total_backups = query.count()
            completed_backups = query.filter_by(status='completed').count()
            failed_backups = query.filter_by(status='failed').count()
            conflict_backups = query.filter_by(sync_status='conflict').count()
            
            return {
                'total_backup_records': total_backups,
                'completed_backups': completed_backups,
                'failed_backups': failed_backups,
                'conflict_records': conflict_backups,
                'success_rate': round(completed_backups / total_backups * 100, 2) if total_backups > 0 else 0,
                'database_path': self.db_path,
                'query_time': datetime.now(SHANGHAI_TZ).isoformat()
            }
        except Exception as e:
            return {'error': f'获取统计信息失败: {e}'}
    
    def save_record(self, record):
        """保存记录到数据库"""
        try:
            session = self._get_session()
            session.add(record)
            session.commit()
        except Exception as e:
            try:
                session.rollback()
            except:
                pass
            raise Exception(f"保存记录失败: {e}")
    
    def sync_from_mysql_backup_records(self) -> int:
        """从MySQL备份记录同步到外部数据库"""
        try:
            # 需要在Flask应用上下文中调用
            from ..models import BackupRecord
            from flask import has_app_context, current_app
            
            if not has_app_context():
                return 0
            
            # 获取所有MySQL备份记录
            mysql_records = BackupRecord.query.filter_by(backup_type='physical').all()
            synced_count = 0
            
            for mysql_record in mysql_records:
                # 检查外部数据库中是否已存在
                external_record = self.get_backup_record(mysql_record.backup_id)
                
                if not external_record:
                    # 创建新的外部记录
                    try:
                        self.create_backup_record(
                            backup_id=mysql_record.backup_id,
                            backup_type=mysql_record.backup_type,
                            status=mysql_record.status,
                            description=mysql_record.get_extra_data().get('description', ''),
                            requested_by=mysql_record.get_extra_data().get('requested_by', '')
                        )
                        synced_count += 1
                    except Exception as e:
                        current_app.logger.warning(f"同步记录 {mysql_record.backup_id} 失败: {e}")
                else:
                    # 检测状态冲突而不是直接覆盖
                    mysql_status = mysql_record.status
                    external_status = external_record.status
                    
                    if mysql_status != external_status:
                        # 发现状态冲突，标记为冲突状态
                        current_app.logger.info(f"检测到状态冲突 {mysql_record.backup_id}: MySQL={mysql_status}, 外部={external_status}")
                        
                        # 使用独立会话设置冲突状态，避免会话冲突
                        conflict_session = None
                        try:
                            conflict_session = self._create_new_session()
                            # 重新获取记录以避免会话混淆
                            fresh_record = conflict_session.query(BackupRecordExternal).filter_by(backup_id=mysql_record.backup_id).first()
                            if fresh_record:
                                fresh_record.sync_status = 'conflict'
                                fresh_record.conflict_reason = f'状态冲突: MySQL={mysql_status}, 外部={external_status}'
                                fresh_record.last_sync_at = datetime.now(SHANGHAI_TZ)
                                conflict_session.commit()
                        except Exception as conflict_error:
                            current_app.logger.warning(f"设置冲突状态失败 {mysql_record.backup_id}: {conflict_error}")
                            if conflict_session:
                                try:
                                    conflict_session.rollback()
                                except:
                                    pass
                        finally:
                            if conflict_session:
                                try:
                                    conflict_session.close()
                                except:
                                    pass
                    else:
                        # 状态一致，更新其他字段（非冲突状态时）
                        if external_record.sync_status != 'conflict':
                            self.update_backup_record(
                                backup_id=mysql_record.backup_id,
                                file_size=mysql_record.file_size,
                                compressed_size=mysql_record.compressed_size,
                                compression_ratio=mysql_record.compression_ratio,
                                file_path=mysql_record.file_path,
                                completed_at=mysql_record.completed_at
                            )
                
            return synced_count
            
        except Exception as e:
            current_app.logger.error(f"从MySQL同步失败: {e}")
            return 0
    
    def sync_to_mysql_backup_records(self) -> int:
        """从外部数据库同步到MySQL备份记录"""  
        try:
            from ..models import BackupRecord
            from .. import db
            from flask import has_app_context, current_app
            import json
            
            if not has_app_context():
                return 0
            
            # 获取所有外部数据库记录
            external_records = self._get_query_class(BackupRecordExternal).all()
            synced_count = 0
            
            for external_record in external_records:
                # 查找对应的MySQL记录
                mysql_record = BackupRecord.query.filter_by(backup_id=external_record.backup_id).first()
                
                if mysql_record:
                    # 更新MySQL记录（以外部数据库为准）
                    mysql_record.status = external_record.status
                    mysql_record.file_size = external_record.file_size
                    mysql_record.compressed_size = external_record.compressed_size
                    mysql_record.compression_ratio = external_record.compression_ratio
                    mysql_record.file_path = external_record.file_path
                    mysql_record.completed_at = external_record.completed_at
                    mysql_record.error_message = external_record.error_message
                    synced_count += 1
                else:
                    # 创建新的MySQL记录
                    extra_data = external_record.extra_data or {}
                    mysql_record = BackupRecord(
                        backup_id=external_record.backup_id,
                        backup_type=external_record.backup_type,
                        status=external_record.status,
                        created_at=external_record.created_at,
                        started_at=external_record.started_at,
                        completed_at=external_record.completed_at,
                        file_size=external_record.file_size,
                        compressed_size=external_record.compressed_size,
                        compression_ratio=external_record.compression_ratio,
                        file_path=external_record.file_path,
                        checksum=external_record.checksum,
                        databases_count=external_record.databases_count,
                        encryption_enabled=external_record.encryption_enabled,
                        error_message=external_record.error_message,
                        extra_data=json.dumps(extra_data) if extra_data else None
                    )
                    db.session.add(mysql_record)
                    synced_count += 1
            
            db.session.commit()
            return synced_count
            
        except Exception as e:
            current_app.logger.error(f"同步到MySQL失败: {e}")
            db.session.rollback()
            return 0


# 全局实例
external_metadata_manager = None

def get_external_metadata_manager():
    """获取外部元数据管理器实例"""
    global external_metadata_manager
    return external_metadata_manager

def init_external_metadata_system(app):
    """初始化外部元数据系统"""
    global external_metadata_manager
    external_metadata_manager = ExternalMetadataManager(app)
    return external_metadata_manager