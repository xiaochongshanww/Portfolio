"""
核心备份管理器

提供数据库备份、文件系统快照、增量备份等核心功能
"""

import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import tarfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import current_app

from .. import db
from ..models import SHANGHAI_TZ, BackupConfig, BackupRecord
from .storage_manager import StorageManager


class BackupManager:
    """备份管理器"""
    
    def __init__(self):
        self.storage_manager = StorageManager()
        self.backup_base_dir = Path(current_app.config.get('BACKUP_BASE_DIR', 'backups'))
        self.backup_base_dir.mkdir(exist_ok=True)
        
        # 线程安全的取消标志管理
        self._cancellation_flags = {}  # backup_id -> threading.Event
        self._flags_lock = threading.Lock()
        
        # 活跃的备份线程管理
        self._active_threads = {}  # backup_id -> threading.Thread
        
        # 创建子目录
        (self.backup_base_dir / 'database').mkdir(exist_ok=True)
        (self.backup_base_dir / 'files').mkdir(exist_ok=True)
        (self.backup_base_dir / 'snapshots').mkdir(exist_ok=True)
        (self.backup_base_dir / 'temp').mkdir(exist_ok=True)
        
        # 性能优化配置
        self._connection_pool_config = {
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True
        }
    
    def _create_cancellation_flag(self, backup_id: str) -> threading.Event:
        """创建取消标志"""
        with self._flags_lock:
            cancel_event = threading.Event()
            self._cancellation_flags[backup_id] = cancel_event
            return cancel_event
    
    def _is_cancelled(self, backup_id: str) -> bool:
        """检查是否被取消 - 增强版：支持持久化取消状态"""
        # 首先检查内存中的标志
        with self._flags_lock:
            cancel_event = self._cancellation_flags.get(backup_id)
            if cancel_event and cancel_event.is_set():
                return True
        
        # 如果内存中没有标志，检查数据库中的持久化状态
        try:
            backup_record = BackupRecord.query.filter_by(backup_id=backup_id).first()
            if backup_record and backup_record.status == 'cancelled':
                # 数据库中标记为已取消，同时更新内存标志
                with self._flags_lock:
                    if backup_id not in self._cancellation_flags:
                        self._cancellation_flags[backup_id] = threading.Event()
                    self._cancellation_flags[backup_id].set()
                return True
        except Exception as e:
            current_app.logger.warning(f"检查持久化取消状态失败 {backup_id}: {e}")
        
        return False
    
    def _set_cancelled(self, backup_id: str):
        """设置取消标志 - 增强版：持久化到数据库"""
        # 设置内存标志
        with self._flags_lock:
            cancel_event = self._cancellation_flags.get(backup_id)
            if cancel_event:
                cancel_event.set()
            current_app.logger.info(f"Backup {backup_id} cancellation flag set")
        
        # 持久化取消状态到数据库
        try:
            backup_record = BackupRecord.query.filter_by(backup_id=backup_id).first()
            if backup_record and backup_record.status in ['pending', 'running']:
                backup_record.status = 'cancelled'
                backup_record.error_message = '用户取消'
                # 不设置completed_at，因为任务被取消而非完成
                db.session.commit()
                current_app.logger.info(f"Backup {backup_id} 持久化取消状态已保存到数据库")
        except Exception as e:
            current_app.logger.error(f"持久化取消状态失败 {backup_id}: {e}")
            db.session.rollback()
    
    def _cleanup_cancellation_flag(self, backup_id: str):
        """清理取消标志"""
        with self._flags_lock:
            self._cancellation_flags.pop(backup_id, None)
            self._active_threads.pop(backup_id, None)
    
    def cancel_backup(self, backup_id: str) -> bool:
        """取消正在进行的备份任务 - 增强版：支持持久化取消和强制终止"""
        try:
            # 查找备份记录
            backup_record = BackupRecord.query.filter_by(backup_id=backup_id).first()
            if not backup_record:
                current_app.logger.warning(f"Backup record {backup_id} not found")
                return False
            
            # 检查备份状态
            if backup_record.status not in ['pending', 'running']:
                current_app.logger.info(f"Backup {backup_id} cannot be cancelled, status: {backup_record.status}")
                return False
            
            # 设置取消标志（包含持久化）
            self._set_cancelled(backup_id)
            
            # 尝试强制终止活跃的线程（如果存在）
            with self._flags_lock:
                active_thread = self._active_threads.get(backup_id)
                if active_thread and active_thread.is_alive():
                    current_app.logger.info(f"发现活跃线程 {backup_id}，已设置取消标志，线程将在下一个检查点停止")
                else:
                    current_app.logger.info(f"未发现活跃线程 {backup_id}，可能任务已完成或线程已终止")
            
            # 记录取消操作到日志
            current_app.logger.info(f"Backup {backup_id} cancellation initiated - persistent flags set")
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to cancel backup {backup_id}: {e}")
            return False
    
    def cleanup_temp_files(self):
        """清理临时文件以释放磁盘空间"""
        try:
            current_app.logger.info("开始清理临时文件")
            temp_dir = self.backup_base_dir / 'temp'
            if temp_dir.exists():
                for temp_file in temp_dir.iterdir():
                    try:
                        if temp_file.is_file():
                            # 删除超过1小时的临时文件
                            if time.time() - temp_file.stat().st_mtime > 3600:
                                temp_file.unlink()
                                current_app.logger.info(f"清理临时文件: {temp_file}")
                    except Exception as e:
                        current_app.logger.warning(f"无法删除临时文件 {temp_file}: {e}")
        except Exception as e:
            current_app.logger.error(f"清理临时文件失败: {e}")
    
    def get_engine_with_pool(self, db_uri: str):
        """获取带连接池的数据库引擎以提高性能"""
        try:
            from sqlalchemy import create_engine
            return create_engine(
                db_uri, 
                **self._connection_pool_config,
                echo=False  # 生产环境关闭SQL日志以提高性能
            )
        except Exception as e:
            current_app.logger.error(f"创建数据库连接池失败: {e}")
            # 回退到基本连接
            from sqlalchemy import create_engine
            return create_engine(db_uri)
    
    def monitor_backup_performance(self, start_time: float, backup_id: str, backup_type: str):
        """监控备份性能并记录指标"""
        try:
            import time
            duration = time.time() - start_time
            
            # 记录性能指标
            current_app.logger.info(
                f"备份性能 - ID: {backup_id}, 类型: {backup_type}, "
                f"耗时: {duration:.2f}秒"
            )
            
            # 如果备份耗时过长，记录警告
            if duration > 300:  # 5分钟
                current_app.logger.warning(
                    f"备份耗时较长: {duration:.2f}秒，建议检查系统性能"
                )
                
        except Exception as e:
            current_app.logger.error(f"性能监控失败: {e}")
    
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
            
        # 性能监控：记录开始时间
        start_time = time.time()

        # 清理临时文件
        self.cleanup_temp_files()
        
        # 生成备份ID - 使用上海时区
        from ..models import SHANGHAI_TZ
        backup_id = f"{backup_type}_{datetime.now(SHANGHAI_TZ).strftime('%Y%m%d_%H%M%S')}"
        current_app.logger.info(f"创建备份 - ID: {backup_id}, 类型: {backup_type}, 选项: {options}")

        # 创建备份记录
        backup_record = BackupRecord(
            backup_id=backup_id,
            backup_type=backup_type,
            status='pending'
        )
        backup_record.set_extra_data(options)
        
        try:
            current_app.logger.info("将备份记录提交数据库")
            db.session.add(backup_record)
            db.session.commit()
            
            # 创建取消标志
            cancel_event = self._create_cancellation_flag(backup_id)
            
            # 获取Flask应用实例用于线程中的应用上下文
            app = current_app._get_current_object()
            
            # 异步执行备份 - 传递backup_id而不是整个record对象
            backup_thread = threading.Thread(
                target=self._execute_backup_async,
                args=(app, backup_id, options, start_time),
                name=f"backup-{backup_id}",
                daemon=True
            )
            
            # 记录活跃线程
            with self._flags_lock:
                self._active_threads[backup_id] = backup_thread
            
            # 启动备份线程
            backup_thread.start()
            current_app.logger.info(f"备份 {backup_id} 开始异步执行")
            
            return backup_id
            
        except Exception as e:
            backup_record.status = 'failed'
            backup_record.error_message = str(e)
            backup_record.completed_at = datetime.now(SHANGHAI_TZ)
            db.session.commit()
            current_app.logger.error(f"Backup {backup_id} creation failed: {e}")
            self._cleanup_cancellation_flag(backup_id)
            raise
    
    def _execute_backup_async(self, app, backup_id: str, options: Dict[str, Any], start_time: float):
        """异步执行备份操作的包装方法 - ULTRALTHINK增强版"""
        
        try:
            # 使用传入的Flask应用实例建立应用上下文
            with app.app_context():
                # 获取新的数据库会话，避免线程间共享
                from .. import db

                # 重新查询备份记录以获取线程本地的实例
                backup_record_local = BackupRecord.query.filter_by(backup_id=backup_id).first()
                if not backup_record_local:
                    app.logger.error(f"Backup record {backup_id} not found in async thread")
                    return
                
                # 关键修复：设置心跳机制防止状态卡死
                self._setup_backup_heartbeat(backup_record_local)
                
                # 执行备份
                self._execute_backup(backup_record_local, options)
                
                # 确保状态正确更新为completed
                self._ensure_backup_completion(backup_record_local)
                
                # 性能监控：记录完成时间和性能指标
                backup_type = backup_record_local.backup_type if backup_record_local else 'unknown'
                self.monitor_backup_performance(start_time, backup_id, backup_type)
                
                app.logger.info(f"✅ 备份 {backup_id} 异步执行完成")
                
        except Exception as e:
            self._handle_backup_failure(app, backup_id, str(e))
        finally:
            # 清理取消标志和线程记录
            self._cleanup_cancellation_flag(backup_id)
    
    def _setup_backup_heartbeat(self, backup_record: BackupRecord):
        """设置备份心跳机制，防止状态卡死"""
        backup_record.status = 'running'
        backup_record.started_at = datetime.now(SHANGHAI_TZ)
        backup_record.last_heartbeat = datetime.now(SHANGHAI_TZ)
        db.session.commit()
        current_app.logger.info(f"🔄 备份 {backup_record.backup_id} 心跳已启动")
    
    def _ensure_backup_completion(self, backup_record: BackupRecord):
        """确保备份正确标记为完成状态"""
        try:
            # 双重检查：确保备份文件确实存在
            if backup_record.file_path and os.path.exists(backup_record.file_path):
                backup_record.status = 'completed'
                backup_record.completed_at = datetime.now(SHANGHAI_TZ)
                backup_record.last_heartbeat = datetime.now(SHANGHAI_TZ)
                db.session.commit()
                current_app.logger.info(f"✅ 备份 {backup_record.backup_id} 状态已确认为completed")
            else:
                raise Exception(f"备份文件未找到: {backup_record.file_path}")
        except Exception as e:
            current_app.logger.error(f"确认备份完成状态失败: {e}")
            raise
    
    def _handle_backup_failure(self, app, backup_id: str, error_message: str):
        """处理备份失败的统一方法"""
        try:
            with app.app_context():
                from .. import db
                backup_record_local = BackupRecord.query.filter_by(backup_id=backup_id).first()
                if backup_record_local:
                    backup_record_local.status = 'failed'
                    backup_record_local.error_message = error_message
                    backup_record_local.completed_at = datetime.now(SHANGHAI_TZ)
                    backup_record_local.last_heartbeat = datetime.now(SHANGHAI_TZ)
                    db.session.commit()
                    app.logger.error(f"❌ 备份 {backup_id} 标记为失败: {error_message}")
        except Exception as inner_e:
            app.logger.error(f"处理备份失败状态时出错: {inner_e}")
    
    def _execute_backup(self, backup_record: BackupRecord, options: Dict[str, Any]):
        """执行备份操作"""
        backup_record.status = 'running'
        backup_record.started_at = datetime.now(SHANGHAI_TZ)
        db.session.commit()
        
        try:
            # 检查是否被取消
            if self._is_cancelled(backup_record.backup_id):
                raise InterruptedError("Backup cancelled by user")
            
            # 创建备份目录
            backup_dir = self.backup_base_dir / 'snapshots' / backup_record.backup_id
            backup_dir.mkdir(exist_ok=True)
            
            files_count = 0
            databases_count = 0
            
            # 备份数据库
            if options.get('include_database', True):
                # 检查取消标志
                if self._is_cancelled(backup_record.backup_id):
                    raise InterruptedError("Backup cancelled during database backup")
                
                db_backup_path = self._backup_database(backup_dir, backup_record.backup_id)
                if db_backup_path:
                    databases_count += 1
                    current_app.logger.info(f"Database backed up to {db_backup_path}")
            
            # 备份文件
            if options.get('include_files', True):
                # 检查取消标志
                if self._is_cancelled(backup_record.backup_id):
                    raise InterruptedError("Backup cancelled during file backup")
                
                files_count = self._backup_files(backup_dir, backup_record.backup_type, options, backup_record.backup_id)
                current_app.logger.info(f"Backed up {files_count} files")
            
            # 检查是否在压缩前被取消
            if self._is_cancelled(backup_record.backup_id):
                raise InterruptedError("Backup cancelled before archiving")
            
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
            backup_record.completed_at = datetime.now(SHANGHAI_TZ)
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
            
        except InterruptedError as e:
            # 备份被取消 - 保留部分备份文件
            backup_record.status = 'cancelled'
            backup_record.error_message = str(e)
            # 注意：不设置completed_at，保持为None
            
            # 尝试保存已完成的部分数据
            self._save_partial_backup(backup_record, backup_dir, files_count, databases_count)
            db.session.commit()
            
            current_app.logger.info(f"Backup {backup_record.backup_id} cancelled, partial data preserved")
            
        except Exception as e:
            # 备份失败 - 清理所有文件
            backup_record.status = 'failed'
            backup_record.error_message = str(e)
            backup_record.completed_at = datetime.now(SHANGHAI_TZ)
            db.session.commit()
            
            # 清理失败的备份文件
            backup_dir = self.backup_base_dir / 'snapshots' / backup_record.backup_id
            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)
            
            current_app.logger.error(f"Backup {backup_record.backup_id} failed: {e}")
            raise
    
    def _save_partial_backup(self, backup_record: BackupRecord, backup_dir: Path, files_count: int, databases_count: int):
        """保存被取消备份的部分数据"""
        try:
            if not backup_dir.exists():
                return
                
            # 检查是否有部分文件可以保存
            partial_files = list(backup_dir.rglob('*'))
            if not partial_files:
                return
            
            # 计算部分备份的大小
            total_size = sum(f.stat().st_size for f in partial_files if f.is_file())
            
            if total_size > 0:
                # 创建部分备份的压缩包
                try:
                    partial_archive = backup_dir.parent / f"{backup_record.backup_id}_partial.tar.gz"
                    with tarfile.open(partial_archive, "w:gz", compresslevel=6) as tar:
                        tar.add(backup_dir, arcname=backup_dir.name)
                    
                    # 更新记录信息
                    backup_record.file_path = str(partial_archive)
                    backup_record.file_size = partial_archive.stat().st_size
                    backup_record.compressed_size = backup_record.file_size
                    backup_record.files_count = files_count
                    backup_record.databases_count = databases_count
                    backup_record.checksum = self._calculate_checksum(partial_archive)
                    
                    # 添加部分备份标记到extra_data
                    extra_data = json.loads(backup_record.extra_data) if backup_record.extra_data else {}
                    extra_data['partial_backup'] = True
                    extra_data['preservation_reason'] = 'Cancelled by user'
                    backup_record.set_extra_data(extra_data)
                    
                    current_app.logger.info(f"Partial backup saved: {partial_archive} ({total_size} bytes)")
                    
                except Exception as archive_error:
                    current_app.logger.warning(f"Failed to create partial archive: {archive_error}")
            
        except Exception as e:
            current_app.logger.warning(f"Failed to save partial backup: {e}")
        finally:
            # 清理临时目录
            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)
    
    def _backup_database(self, backup_dir: Path, backup_id: str = None) -> Optional[Path]:
        """备份数据库"""
        try:
            db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
            timestamp = datetime.now(SHANGHAI_TZ).strftime('%Y%m%d_%H%M%S')
            
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
            
            # 尝试使用mysqldump - 优先使用Docker方式
            import subprocess
            try:
                # 检查是否在Docker环境中
                docker_container = self._detect_mysql_docker_container()
                
                if docker_container:
                    # 使用Docker容器内的mysqldump
                    current_app.logger.info(f"使用Docker容器 {docker_container} 执行mysqldump")
                    cmd = [
                        'docker', 'exec', docker_container,
                        'mysqldump',
                        '--host=localhost',  # 容器内部连接
                        '--port=3306',
                        f'--user={username}',
                        f'--password={password}',
                        '--single-transaction',
                        '--routines',
                        '--triggers',
                        '--skip-disable-keys',  # 不生成DISABLE/ENABLE KEYS语句
                        '--skip-lock-tables',   # 不锁表
                        database
                    ]
                    env = None
                else:
                    # 传统方式，使用环境变量传递密码（更安全）
                    cmd = [
                        'mysqldump',
                        f'--host={host}',
                        f'--port={port}',
                        f'--user={username}',
                        '--single-transaction',
                        '--routines',
                        '--triggers',
                        '--skip-disable-keys',  # 不生成DISABLE/ENABLE KEYS语句
                        '--skip-lock-tables',   # 不锁表
                        database
                    ]
                    # 设置环境变量传递密码
                    env = os.environ.copy()
                    env['MYSQL_PWD'] = password
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, 
                                         check=True, text=True, env=env)
                
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
            from sqlalchemy import inspect, text

            # 使用优化的连接池
            engine = self.get_engine_with_pool(db_uri)
            inspector = inspect(engine)
            
            backup_file = backup_dir / f"database_{timestamp}.sql"
            
            # 连接管理：确保连接被正确释放
            connection = None
            try:
                connection = engine.connect()
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(f"-- MySQL Database Backup\\n")
                    f.write(f"-- Generated at: {datetime.now(SHANGHAI_TZ)}\\n\\n")
                    
                    # 备份每个表
                    for table_name in inspector.get_table_names():
                        f.write(f"\\n-- Table: {table_name}\\n")
                        
                        # 获取表结构
                        f.write(f"DROP TABLE IF EXISTS `{table_name}`;\\n")
                        
                        # 获取创建表语句 (简化版)
                        result = connection.execute(text(f"SHOW CREATE TABLE `{table_name}`"))
                        create_stmt = result.fetchone()[1]
                        f.write(f"{create_stmt};\\n\\n")
                        
                        # 优化：使用流式处理避免内存溢出
                        data_result = connection.execute(text(f"SELECT * FROM `{table_name}`"))
                        
                        # 获取列信息
                        columns = data_result.keys()
                        if columns:
                            col_names = '`, `'.join(columns)
                            
                            # 批量处理数据，避免一次性加载所有行到内存
                            batch_size = 1000  # 每批处理1000行
                            batch_rows = []
                            has_data = False
                            
                            for row in data_result:
                                if not has_data:
                                    f.write(f"INSERT INTO `{table_name}` (`{col_names}`) VALUES\\n")
                                    has_data = True
                                
                                batch_rows.append(row)
                                
                                if len(batch_rows) >= batch_size:
                                    self._write_batch_insert(f, batch_rows, False)
                                    batch_rows = []
                            
                            # 处理最后一批数据
                            if batch_rows:
                                self._write_batch_insert(f, batch_rows, True)
                            elif has_data:
                                # 如果有数据但没有剩余批次，需要添加分号
                                f.write(';\\n\\n')
            
                current_app.logger.info(f"MySQL database backed up with SQLAlchemy: {backup_file}")
                return backup_file
                
            finally:
                # 确保连接被正确关闭
                if connection:
                    try:
                        connection.close()
                    except Exception as e:
                        current_app.logger.warning(f"关闭数据库连接时出错: {e}")
            
        except Exception as e:
            current_app.logger.error(f"MySQL SQLAlchemy backup failed: {e}")
            raise
    
    def _write_batch_insert(self, f, batch_rows, is_last_batch):
        """
        写入批量INSERT语句的数据行
        
        Args:
            f: 文件对象
            batch_rows: 批量数据行
            is_last_batch: 是否为最后一批
        """
        try:
            for i, row in enumerate(batch_rows):
                values = []
                for value in row:
                    if value is None:
                        values.append('NULL')
                    elif isinstance(value, str):
                        # 转义SQL字符，防止SQL注入
                        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
                        values.append(f"'{escaped}'")
                    elif isinstance(value, (int, float)):
                        values.append(str(value))
                    elif isinstance(value, datetime):
                        values.append(f"'{value.isoformat()}'")
                    else:
                        values.append(f"'{str(value)}'")
                
                f.write(f"({', '.join(values)})")
                
                # 决定是否添加逗号或分号
                if i == len(batch_rows) - 1:  # 当前批次的最后一行
                    if is_last_batch:
                        f.write(';\\n\\n')  # 最后一批的最后一行，添加分号
                    else:
                        f.write(',\\n')     # 不是最后一批，添加逗号
                else:
                    f.write(',\\n')         # 不是当前批次的最后一行，添加逗号
                    
        except Exception as e:
            current_app.logger.error(f"Error writing batch insert: {e}")
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
    
    def _backup_files(self, backup_dir: Path, backup_type: str, options: Dict[str, Any], backup_id: str = None) -> int:
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
            expiry_date = datetime.now(SHANGHAI_TZ) - timedelta(days=retention_days)
            
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
            # 导入上海时区
            from ..models import SHANGHAI_TZ
            
            total_backups = BackupRecord.query.count()
            completed_backups = BackupRecord.query.filter_by(status='completed').count()
            failed_backups = BackupRecord.query.filter_by(status='failed').count()
            
            # 最近30天的备份
            recent_date = datetime.now(SHANGHAI_TZ) - timedelta(days=30)
            recent_backups = BackupRecord.query.filter(BackupRecord.created_at >= recent_date).count()
            
            # 存储使用量 - 只统计实际有文件大小数据的备份（无论状态如何）
            total_size_result = db.session.query(db.func.sum(BackupRecord.file_size)).filter(
                BackupRecord.file_size.isnot(None), 
                BackupRecord.file_size > 0
            ).scalar()
            total_size = int(total_size_result) if total_size_result else 0
            
            compressed_size_result = db.session.query(db.func.sum(BackupRecord.compressed_size)).filter(
                BackupRecord.compressed_size.isnot(None),
                BackupRecord.compressed_size > 0
            ).scalar()
            compressed_size = int(compressed_size_result) if compressed_size_result else 0
            
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
    
    def _detect_mysql_docker_container(self) -> Optional[str]:
        """检测MySQL Docker容器"""
        try:
            import subprocess

            # 查找运行中的MySQL容器
            cmd = ['docker', 'ps', '--filter', 'ancestor=mysql', '--format', '{{.Names}}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                container_name = result.stdout.strip().split('\n')[0]
                current_app.logger.info(f"检测到MySQL Docker容器: {container_name}")
                return container_name
            
            # 尝试通用的容器名称
            common_names = ['blog-mysql', 'mysql', 'db', 'database']
            for name in common_names:
                check_cmd = ['docker', 'ps', '--filter', f'name={name}', '--format', '{{.Names}}']
                check_result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=5)
                
                if check_result.returncode == 0 and name in check_result.stdout:
                    current_app.logger.info(f"找到MySQL容器: {name}")
                    return name
            
            return None
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            current_app.logger.warning(f"Docker检测失败: {e}")
            return None