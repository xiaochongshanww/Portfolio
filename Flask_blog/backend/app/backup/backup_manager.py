"""
核心备份管理器

提供数据库备份、文件系统快照、增量备份等核心功能
"""

import os
import shutil
import sqlite3
import hashlib
import json
import tarfile
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from flask import current_app
from .. import db
from ..models import BackupRecord, BackupConfig
from .storage_manager import StorageManager


class BackupManager:
    """备份管理器"""
    
    def __init__(self):
        self.storage_manager = StorageManager()
        self.backup_base_dir = Path(current_app.config.get('BACKUP_BASE_DIR', 'backups'))
        self.backup_base_dir.mkdir(exist_ok=True)
        
        # 创建子目录
        (self.backup_base_dir / 'database').mkdir(exist_ok=True)
        (self.backup_base_dir / 'files').mkdir(exist_ok=True)
        (self.backup_base_dir / 'snapshots').mkdir(exist_ok=True)
        (self.backup_base_dir / 'temp').mkdir(exist_ok=True)
    
    def create_backup(self, backup_type: str = 'incremental', options: Dict[str, Any] = None) -> str:
        """
        创建备份
        
        Args:
            backup_type: 备份类型 (full, incremental, snapshot)
            options: 备份选项
            
        Returns:
            备份ID
        """
        if options is None:
            options = {}
            
        # 生成备份ID
        backup_id = f"{backup_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建备份记录
        backup_record = BackupRecord(
            backup_id=backup_id,
            backup_type=backup_type,
            status='pending'
        )
        backup_record.set_extra_data(options)
        
        try:
            db.session.add(backup_record)
            db.session.commit()
            
            # 执行备份
            self._execute_backup(backup_record, options)
            
            return backup_id
            
        except Exception as e:
            backup_record.status = 'failed'
            backup_record.error_message = str(e)
            backup_record.completed_at = datetime.utcnow()
            db.session.commit()
            current_app.logger.error(f"Backup {backup_id} failed: {e}")
            raise
    
    def _execute_backup(self, backup_record: BackupRecord, options: Dict[str, Any]):
        """执行备份操作"""
        backup_record.status = 'running'
        backup_record.started_at = datetime.utcnow()
        db.session.commit()
        
        try:
            # 创建备份目录
            backup_dir = self.backup_base_dir / 'snapshots' / backup_record.backup_id
            backup_dir.mkdir(exist_ok=True)
            
            files_count = 0
            databases_count = 0
            
            # 备份数据库
            if options.get('include_database', True):
                db_backup_path = self._backup_database(backup_dir)
                if db_backup_path:
                    databases_count += 1
                    current_app.logger.info(f"Database backed up to {db_backup_path}")
            
            # 备份文件
            if options.get('include_files', True):
                files_count = self._backup_files(backup_dir, backup_record.backup_type, options)
                current_app.logger.info(f"Backed up {files_count} files")
            
            # 创建压缩包
            archive_path = self._create_archive(backup_dir)
            
            # 计算校验和
            checksum = self._calculate_checksum(archive_path)
            
            # 获取文件信息
            file_size = archive_path.stat().st_size
            compressed_size = file_size  # 已经是压缩后的大小
            
            # 上传到存储后端
            storage_info = self.storage_manager.store_backup(archive_path, backup_record.backup_id)
            
            # 更新备份记录
            backup_record.status = 'completed'
            backup_record.completed_at = datetime.utcnow()
            backup_record.file_path = str(archive_path)
            backup_record.file_size = file_size
            backup_record.compressed_size = compressed_size
            backup_record.checksum = checksum
            backup_record.files_count = files_count
            backup_record.databases_count = databases_count
            backup_record.set_storage_providers(storage_info)
            
            # 计算压缩比
            if backup_record.backup_type == 'full':
                original_size = self._calculate_original_size(backup_dir)
                if original_size > 0:
                    backup_record.compression_ratio = compressed_size / original_size
            
            db.session.commit()
            
            # 清理临时目录
            shutil.rmtree(backup_dir, ignore_errors=True)
            
            current_app.logger.info(f"Backup {backup_record.backup_id} completed successfully")
            
        except Exception as e:
            backup_record.status = 'failed'
            backup_record.error_message = str(e)
            backup_record.completed_at = datetime.utcnow()
            db.session.commit()
            
            # 清理失败的备份文件
            backup_dir = self.backup_base_dir / 'snapshots' / backup_record.backup_id
            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)
                
            raise
    
    def _backup_database(self, backup_dir: Path) -> Optional[Path]:
        """备份数据库"""
        try:
            db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if db_uri.startswith('sqlite:'):
                return self._backup_sqlite(db_uri, backup_dir, timestamp)
            elif db_uri.startswith('mysql'):
                return self._backup_mysql(db_uri, backup_dir, timestamp)
            else:
                current_app.logger.warning(f"Unsupported database type for backup: {db_uri}")
                return None
                
        except Exception as e:
            current_app.logger.error(f"Database backup failed: {e}")
            raise
    
    def _backup_sqlite(self, db_uri: str, backup_dir: Path, timestamp: str) -> Optional[Path]:
        """备份SQLite数据库"""
        try:
            db_path = db_uri.replace('sqlite:///', '')
            if not os.path.isabs(db_path):
                db_path = str(Path(current_app.root_path).parent / db_path)
            
            if os.path.exists(db_path):
                backup_file = backup_dir / f"database_{timestamp}.db"
                shutil.copy2(db_path, backup_file)
                
                # SQL导出备份 (作为额外保险)
                sql_backup_file = backup_dir / f"database_{timestamp}.sql"
                self._export_sqlite_to_sql(db_path, sql_backup_file)
                
                current_app.logger.info(f"SQLite database backed up: {backup_file}")
                return backup_file
            else:
                current_app.logger.error(f"SQLite database file not found: {db_path}")
                return None
                
        except Exception as e:
            current_app.logger.error(f"SQLite backup failed: {e}")
            raise
    
    def _backup_mysql(self, db_uri: str, backup_dir: Path, timestamp: str) -> Optional[Path]:
        """备份MySQL数据库"""
        try:
            import urllib.parse
            from sqlalchemy import create_engine, text
            
            # 解析数据库连接信息
            parsed = urllib.parse.urlparse(db_uri)
            host = parsed.hostname or 'localhost'
            port = parsed.port or 3306
            username = parsed.username
            password = parsed.password
            database = parsed.path.lstrip('/')
            
            # 使用mysqldump命令备份
            backup_file = backup_dir / f"database_{timestamp}.sql"
            
            # 尝试使用mysqldump
            import subprocess
            try:
                cmd = [
                    'mysqldump',
                    f'--host={host}',
                    f'--port={port}',
                    f'--user={username}',
                    f'--password={password}',
                    '--single-transaction',
                    '--routines',
                    '--triggers',
                    database
                ]
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, 
                                         check=True, text=True)
                
                current_app.logger.info(f"MySQL database backed up with mysqldump: {backup_file}")
                return backup_file
                
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                current_app.logger.warning(f"mysqldump failed, trying SQLAlchemy approach: {e}")
                
                # 回退到SQLAlchemy方法
                return self._backup_mysql_with_sqlalchemy(db_uri, backup_dir, timestamp)
                
        except Exception as e:
            current_app.logger.error(f"MySQL backup failed: {e}")
            raise
    
    def _backup_mysql_with_sqlalchemy(self, db_uri: str, backup_dir: Path, timestamp: str) -> Optional[Path]:
        """使用SQLAlchemy备份MySQL数据库"""
        try:
            from sqlalchemy import create_engine, text, inspect
            
            engine = create_engine(db_uri)
            inspector = inspect(engine)
            
            backup_file = backup_dir / f"database_{timestamp}.sql"
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(f"-- MySQL Database Backup\\n")
                f.write(f"-- Generated at: {datetime.now()}\\n\\n")
                
                # 备份每个表
                for table_name in inspector.get_table_names():
                    f.write(f"\\n-- Table: {table_name}\\n")
                    
                    # 获取表结构
                    f.write(f"DROP TABLE IF EXISTS `{table_name}`;\\n")
                    
                    # 获取创建表语句 (简化版)
                    with engine.connect() as conn:
                        result = conn.execute(text(f"SHOW CREATE TABLE `{table_name}`"))
                        create_stmt = result.fetchone()[1]
                        f.write(f"{create_stmt};\\n\\n")
                        
                        # 备份数据
                        data_result = conn.execute(text(f"SELECT * FROM `{table_name}`"))
                        rows = data_result.fetchall()
                        
                        if rows:
                            columns = data_result.keys()
                            col_names = '`, `'.join(columns)
                            f.write(f"INSERT INTO `{table_name}` (`{col_names}`) VALUES\\n")
                            
                            for i, row in enumerate(rows):
                                values = []
                                for value in row:
                                    if value is None:
                                        values.append('NULL')
                                    elif isinstance(value, str):
                                        # 转义SQL字符
                                        escaped = value.replace("'", "\\'").replace("\\", "\\\\")
                                        values.append(f"'{escaped}'")
                                    else:
                                        values.append(str(value))
                                
                                f.write(f"({', '.join(values)})")
                                if i < len(rows) - 1:
                                    f.write(',\\n')
                                else:
                                    f.write(';\\n\\n')
            
            current_app.logger.info(f"MySQL database backed up with SQLAlchemy: {backup_file}")
            return backup_file
            
        except Exception as e:
            current_app.logger.error(f"MySQL SQLAlchemy backup failed: {e}")
            raise
    
    def _export_sqlite_to_sql(self, db_path: str, output_file: Path):
        """导出SQLite为SQL文件"""
        try:
            conn = sqlite3.connect(db_path)
            with open(output_file, 'w', encoding='utf-8') as f:
                for line in conn.iterdump():
                    f.write(f'{line}\n')
            conn.close()
        except Exception as e:
            current_app.logger.error(f"SQLite export failed: {e}")
            raise
    
    def _backup_files(self, backup_dir: Path, backup_type: str, options: Dict[str, Any]) -> int:
        """备份文件系统"""
        files_count = 0
        
        try:
            # 获取需要备份的目录
            default_include_patterns = [
                'uploads/**/*',
                'instance/**/*',
                'config/**/*', 
                'logs/**/*',
                'migrations/**/*',
                'app/**/*.py',  # 备份应用代码
                'requirements.txt',
                'run.py'
            ]
            
            default_exclude_patterns = [
                '*.pyc',
                '__pycache__/*',
                'backups/*',
                '.git/*',
                '*.tmp',
                '*.swp'
            ]
            
            include_patterns = options.get('include_patterns') or default_include_patterns
            exclude_patterns = options.get('exclude_patterns') or default_exclude_patterns
            
            app_root = Path(current_app.root_path).parent
            files_backup_dir = backup_dir / 'files'
            files_backup_dir.mkdir(exist_ok=True)
            
            if backup_type == 'incremental':
                files_count = self._incremental_backup(app_root, files_backup_dir, include_patterns, exclude_patterns)
            else:
                files_count = self._full_backup(app_root, files_backup_dir, include_patterns, exclude_patterns)
                
            return files_count
            
        except Exception as e:
            current_app.logger.error(f"File backup failed: {e}")
            raise
    
    def _full_backup(self, source_dir: Path, backup_dir: Path, include_patterns: List[str], exclude_patterns: List[str]) -> int:
        """全量文件备份"""
        files_count = 0
        
        for pattern in include_patterns:
            for file_path in source_dir.glob(pattern):
                if file_path.is_file() and not self._should_exclude(file_path, exclude_patterns, source_dir):
                    # 创建相对路径结构
                    rel_path = file_path.relative_to(source_dir)
                    target_path = backup_dir / rel_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 复制文件
                    shutil.copy2(file_path, target_path)
                    files_count += 1
        return files_count
    
    def _incremental_backup(self, source_dir: Path, backup_dir: Path, include_patterns: List[str], exclude_patterns: List[str]) -> int:
        """增量文件备份"""
        files_count = 0
        
        # 获取上次备份的清单
        last_manifest = self._get_last_backup_manifest()
        current_manifest = {}
        
        for pattern in include_patterns:
            for file_path in source_dir.glob(pattern):
                if file_path.is_file() and not self._should_exclude(file_path, exclude_patterns, source_dir):
                    # 计算文件hash
                    file_hash = self._calculate_file_hash(file_path)
                    rel_path = str(file_path.relative_to(source_dir))
                    
                    current_manifest[rel_path] = {
                        'hash': file_hash,
                        'mtime': file_path.stat().st_mtime,
                        'size': file_path.stat().st_size
                    }
                    
                    # 检查是否需要备份
                    if rel_path not in last_manifest or last_manifest[rel_path]['hash'] != file_hash:
                        target_path = backup_dir / rel_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, target_path)
                        files_count += 1
        
        # 保存当前清单
        self._save_backup_manifest(current_manifest)
        
        return files_count
    
    def _should_exclude(self, file_path: Path, exclude_patterns: List[str], source_dir: Path) -> bool:
        """检查文件是否应该排除"""
        import fnmatch
        
        rel_path = file_path.relative_to(source_dir)
        rel_path_str = str(rel_path).replace('\\', '/')  # 统一使用正斜杠
        
        for pattern in exclude_patterns:
            # 使用fnmatch进行模式匹配
            if fnmatch.fnmatch(rel_path_str, pattern):
                return True
            # 对于目录模式，检查路径是否在该目录下
            if pattern.endswith('/*') and rel_path_str.startswith(pattern[:-2] + '/'):
                return True
        return False
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件MD5哈希"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _get_last_backup_manifest(self) -> Dict[str, Any]:
        """获取上次备份的清单"""
        try:
            manifest_file = self.backup_base_dir / 'last_manifest.json'
            if manifest_file.exists():
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            current_app.logger.warning(f"Failed to load last backup manifest: {e}")
        return {}
    
    def _save_backup_manifest(self, manifest: Dict[str, Any]):
        """保存备份清单"""
        try:
            manifest_file = self.backup_base_dir / 'last_manifest.json'
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            current_app.logger.error(f"Failed to save backup manifest: {e}")
    
    def _create_archive(self, backup_dir: Path) -> Path:
        """创建备份压缩包"""
        try:
            archive_path = backup_dir.parent / f"{backup_dir.name}.tar.gz"
            
            with tarfile.open(archive_path, "w:gz", compresslevel=6) as tar:
                tar.add(backup_dir, arcname=backup_dir.name)
                
            return archive_path
            
        except Exception as e:
            current_app.logger.error(f"Archive creation failed: {e}")
            raise
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件SHA-256校验和"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _calculate_original_size(self, backup_dir: Path) -> int:
        """计算原始文件大小"""
        total_size = 0
        for file_path in backup_dir.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def get_backup_records(self, page: int = 1, per_page: int = 20, backup_type: str = None, status: str = None) -> Dict[str, Any]:
        """获取备份记录列表"""
        query = BackupRecord.query.order_by(BackupRecord.created_at.desc())
        
        if backup_type:
            query = query.filter(BackupRecord.backup_type == backup_type)
        if status:
            query = query.filter(BackupRecord.status == status)
            
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'records': [record.to_dict() for record in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    
    def get_backup_record(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """获取单个备份记录"""
        record = BackupRecord.query.filter_by(backup_id=backup_id).first()
        return record.to_dict() if record else None
    
    def delete_backup(self, backup_id: str) -> bool:
        """删除备份"""
        try:
            record = BackupRecord.query.filter_by(backup_id=backup_id).first()
            if not record:
                return False
            
            # 删除存储后端的文件
            if record.storage_providers:
                self.storage_manager.delete_backup(backup_id, record.storage_providers)
            
            # 删除本地文件
            if record.file_path and os.path.exists(record.file_path):
                os.remove(record.file_path)
            
            # 删除数据库记录
            db.session.delete(record)
            db.session.commit()
            
            current_app.logger.info(f"Backup {backup_id} deleted successfully")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to delete backup {backup_id}: {e}")
            db.session.rollback()
            return False
    
    def cleanup_expired_backups(self) -> Dict[str, int]:
        """清理过期的备份"""
        try:
            # 获取保留天数配置
            retention_config = BackupConfig.query.filter_by(config_key='backup_retention_days').first()
            retention_days = int(retention_config.config_value) if retention_config else 30
            
            # 计算过期时间
            expiry_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # 查询过期的备份
            expired_records = BackupRecord.query.filter(
                BackupRecord.created_at < expiry_date,
                BackupRecord.status == 'completed'
            ).all()
            
            deleted_count = 0
            failed_count = 0
            
            for record in expired_records:
                if self.delete_backup(record.backup_id):
                    deleted_count += 1
                else:
                    failed_count += 1
            
            current_app.logger.info(f"Cleanup completed: {deleted_count} backups deleted, {failed_count} failed")
            
            return {
                'deleted_count': deleted_count,
                'failed_count': failed_count,
                'total_expired': len(expired_records)
            }
            
        except Exception as e:
            current_app.logger.error(f"Cleanup failed: {e}")
            return {
                'deleted_count': 0,
                'failed_count': 0,
                'total_expired': 0,
                'error': str(e)
            }
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """获取备份统计信息"""
        try:
            total_backups = BackupRecord.query.count()
            completed_backups = BackupRecord.query.filter_by(status='completed').count()
            failed_backups = BackupRecord.query.filter_by(status='failed').count()
            
            # 最近30天的备份
            recent_date = datetime.utcnow() - timedelta(days=30)
            recent_backups = BackupRecord.query.filter(BackupRecord.created_at >= recent_date).count()
            
            # 存储使用量
            total_size = db.session.query(db.func.sum(BackupRecord.file_size)).filter_by(status='completed').scalar() or 0
            compressed_size = db.session.query(db.func.sum(BackupRecord.compressed_size)).filter_by(status='completed').scalar() or 0
            
            # 备份类型分布
            backup_types = db.session.query(
                BackupRecord.backup_type,
                db.func.count(BackupRecord.id)
            ).filter_by(status='completed').group_by(BackupRecord.backup_type).all()
            
            return {
                'total_backups': total_backups,
                'completed_backups': completed_backups,
                'failed_backups': failed_backups,
                'recent_backups': recent_backups,
                'success_rate': round(completed_backups / total_backups * 100, 2) if total_backups > 0 else 0,
                'total_storage_size': total_size,
                'compressed_storage_size': compressed_size,
                'compression_ratio': round(compressed_size / total_size, 3) if total_size > 0 else 0,
                'backup_types': dict(backup_types)
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to get backup statistics: {e}")
            return {}