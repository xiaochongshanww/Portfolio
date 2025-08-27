#!/usr/bin/env python3
"""备份恢复管理器"""

import os
import shutil
import tempfile
import tarfile
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import subprocess

from flask import current_app
from .. import db
from ..models import BackupRecord, RestoreRecord


class RestoreManager:
    """备份恢复管理器"""
    
    def __init__(self):
        self.app_root = Path(current_app.root_path).parent
        self.backup_root = self.app_root / 'backups'
    
    def restore_backup(self, restore_record_id: int, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行备份恢复"""
        options = options or {}
        
        try:
            # 获取恢复记录
            restore_record = RestoreRecord.query.get(restore_record_id)
            if not restore_record:
                raise ValueError(f"Restore record {restore_record_id} not found")
            
            # 获取对应的备份记录
            backup_record = BackupRecord.query.get(restore_record.backup_record_id)
            if not backup_record:
                raise ValueError(f"Backup record {restore_record.backup_record_id} not found")
            
            current_app.logger.info(f"Starting restore {restore_record.restore_id} from backup {backup_record.backup_id}")
            
            # 更新恢复记录状态
            restore_record.status = 'running'
            restore_record.started_at = datetime.now(timezone.utc)
            restore_record.progress = 0
            db.session.commit()
            
            # 解析恢复选项
            restore_options = json.loads(restore_record.restore_options or '{}')
            restore_options.update(options)
            
            # 创建临时工作目录
            with tempfile.TemporaryDirectory(prefix="restore_") as temp_dir:
                temp_path = Path(temp_dir)
                
                # 第1步：提取备份文件 (0-30%)
                self._update_progress(restore_record, 10, "正在提取备份文件...")
                extracted_path = self._extract_backup(backup_record, temp_path)
                
                # 第2步：验证备份完整性 (30-40%)
                self._update_progress(restore_record, 30, "正在验证备份完整性...")
                if not self._verify_backup_integrity(extracted_path, backup_record):
                    raise Exception("备份文件完整性验证失败")
                
                # 第3步：根据恢复类型执行相应操作 (40-90%)
                if restore_record.restore_type == 'database_only':
                    self._restore_database_only(extracted_path, restore_record, restore_options)
                elif restore_record.restore_type == 'files_only':
                    self._restore_files_only(extracted_path, restore_record, restore_options)
                elif restore_record.restore_type == 'partial':
                    self._restore_partial(extracted_path, restore_record, restore_options)
                else:  # full restore
                    self._restore_full(extracted_path, restore_record, restore_options)
                
                # 第4步：最终验证 (90-100%)
                self._update_progress(restore_record, 90, "正在进行最终验证...")
                if not self._verify_restore_result(restore_record, restore_options):
                    raise Exception("恢复结果验证失败")
                
                # 完成恢复
                self._complete_restore(restore_record)
                
                current_app.logger.info(f"Restore {restore_record.restore_id} completed successfully")
                return {
                    'status': 'success',
                    'restore_id': restore_record.restore_id,
                    'message': '恢复完成'
                }
                
        except Exception as e:
            current_app.logger.error(f"Restore failed for {restore_record_id}: {e}")
            self._fail_restore(restore_record, str(e))
            return {
                'status': 'failed',
                'error': str(e),
                'message': f'恢复失败: {str(e)}'
            }
    
    def _extract_backup(self, backup_record: BackupRecord, temp_path: Path) -> Path:
        """提取备份文件"""
        backup_file = self.backup_root / 'snapshots' / f"{backup_record.backup_id}.tar.gz"
        
        if not backup_file.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_file}")
        
        # 提取到临时目录
        with tarfile.open(backup_file, 'r:gz') as tar:
            tar.extractall(temp_path)
        
        # 返回提取后的备份目录路径
        extracted_dir = temp_path / backup_record.backup_id
        if not extracted_dir.exists():
            raise Exception(f"提取的备份目录不存在: {extracted_dir}")
            
        return extracted_dir
    
    def _verify_backup_integrity(self, extracted_path: Path, backup_record: BackupRecord) -> bool:
        """验证备份完整性"""
        try:
            # 检查数据库文件
            db_files = list(extracted_path.glob("database_*.sql"))
            if not db_files and backup_record.databases_count > 0:
                current_app.logger.error("数据库备份文件缺失")
                return False
            
            # 检查文件目录
            files_dir = extracted_path / 'files'
            if not files_dir.exists() and backup_record.files_count > 0:
                current_app.logger.error("文件备份目录缺失")
                return False
            
            # 可以添加更多完整性检查（如校验和验证）
            if backup_record.checksum:
                # TODO: 实现校验和验证
                pass
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"完整性验证失败: {e}")
            return False
    
    def _restore_database_only(self, extracted_path: Path, restore_record: RestoreRecord, options: Dict[str, Any]):
        """仅恢复数据库"""
        self._update_progress(restore_record, 50, "正在恢复数据库...")
        
        db_files = list(extracted_path.glob("database_*.sql"))
        if not db_files:
            raise Exception("没有找到数据库备份文件")
        
        db_file = db_files[0]  # 取第一个数据库文件
        
        # 获取数据库连接信息
        database_url = current_app.config.get('DATABASE_URL') or current_app.config.get('SQLALCHEMY_DATABASE_URI')
        
        if not database_url:
            raise Exception("无法获取数据库连接信息")
        
        # 根据数据库类型执行恢复
        if 'mysql' in database_url.lower():
            self._restore_mysql_database(db_file, database_url, options)
        else:
            # SQLite 或其他数据库
            self._restore_sqlite_database(db_file, options)
        
        self._update_progress(restore_record, 80, "数据库恢复完成")
    
    def _restore_files_only(self, extracted_path: Path, restore_record: RestoreRecord, options: Dict[str, Any]):
        """仅恢复文件系统"""
        self._update_progress(restore_record, 50, "正在恢复文件...")
        
        files_dir = extracted_path / 'files'
        if not files_dir.exists():
            raise Exception("没有找到文件备份目录")
        
        target_path = Path(restore_record.target_path) if restore_record.target_path else self.app_root
        
        # 安全性检查
        if not self._is_safe_restore_path(target_path):
            raise Exception(f"不安全的恢复路径: {target_path}")
        
        # 恢复文件
        file_count = self._copy_files_recursive(files_dir, target_path, options)
        
        current_app.logger.info(f"恢复了 {file_count} 个文件到 {target_path}")
        self._update_progress(restore_record, 80, f"文件恢复完成，共 {file_count} 个文件")
    
    def _restore_partial(self, extracted_path: Path, restore_record: RestoreRecord, options: Dict[str, Any]):
        """部分恢复（根据选项决定恢复内容）"""
        self._update_progress(restore_record, 50, "正在执行部分恢复...")
        
        if options.get('include_database', True):
            self._restore_database_only(extracted_path, restore_record, options)
        
        if options.get('include_files', True):
            self._restore_files_only(extracted_path, restore_record, options)
        
        self._update_progress(restore_record, 80, "部分恢复完成")
    
    def _restore_full(self, extracted_path: Path, restore_record: RestoreRecord, options: Dict[str, Any]):
        """完整恢复"""
        self._update_progress(restore_record, 50, "正在执行完整恢复...")
        
        # 先恢复数据库
        self._restore_database_only(extracted_path, restore_record, options)
        self._update_progress(restore_record, 70, "数据库恢复完成，正在恢复文件...")
        
        # 再恢复文件
        self._restore_files_only(extracted_path, restore_record, options)
        
        self._update_progress(restore_record, 85, "完整恢复完成")
    
    def _restore_mysql_database(self, db_file: Path, database_url: str, options: Dict[str, Any]):
        """恢复MySQL数据库"""
        import urllib.parse
        
        parsed = urllib.parse.urlparse(database_url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 3306
        username = parsed.username
        password = parsed.password
        database = parsed.path.lstrip('/')
        
        # 构建mysql命令
        cmd = [
            'mysql',
            f'--host={host}',
            f'--port={port}',
            f'--user={username}',
            f'--password={password}',
            database
        ]
        
        try:
            # 执行SQL恢复
            with open(db_file, 'r', encoding='utf-8') as f:
                process = subprocess.run(
                    cmd,
                    input=f.read(),
                    text=True,
                    capture_output=True,
                    timeout=300  # 5分钟超时
                )
            
            if process.returncode != 0:
                raise Exception(f"MySQL恢复失败: {process.stderr}")
                
            current_app.logger.info(f"MySQL数据库恢复成功从: {db_file}")
            
        except subprocess.TimeoutExpired:
            raise Exception("MySQL恢复超时")
        except FileNotFoundError:
            raise Exception("mysql命令未找到，请确保MySQL客户端已安装")
    
    def _restore_sqlite_database(self, db_file: Path, options: Dict[str, Any]):
        """恢复SQLite数据库"""
        # SQLite恢复逻辑 - 这里需要根据具体情况实现
        # 可以直接替换数据库文件或执行SQL命令
        current_app.logger.info("SQLite数据库恢复功能待实现")
        raise NotImplementedError("SQLite数据库恢复功能待实现")
    
    def _copy_files_recursive(self, source_dir: Path, target_dir: Path, options: Dict[str, Any]) -> int:
        """递归复制文件"""
        file_count = 0
        
        # 确保目标目录存在
        target_dir.mkdir(parents=True, exist_ok=True)
        
        for item in source_dir.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(source_dir)
                target_file = target_dir / rel_path
                
                # 创建目标目录
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 复制文件
                shutil.copy2(item, target_file)
                file_count += 1
                
        return file_count
    
    def _is_safe_restore_path(self, path: Path) -> bool:
        """检查恢复路径是否安全"""
        # 防止恢复到危险的系统目录
        dangerous_paths = ['/etc', '/usr', '/bin', '/sbin', '/root', 'C:\\Windows', 'C:\\Program Files']
        
        path_str = str(path.resolve())
        for dangerous in dangerous_paths:
            if path_str.startswith(dangerous):
                return False
                
        return True
    
    def _verify_restore_result(self, restore_record: RestoreRecord, options: Dict[str, Any]) -> bool:
        """验证恢复结果"""
        try:
            # 可以在这里添加各种验证逻辑
            # 例如：检查关键文件是否存在、数据库连接是否正常等
            
            if restore_record.restore_type in ['full', 'database_only']:
                # 验证数据库连接
                if not self._verify_database_connection():
                    return False
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"恢复结果验证失败: {e}")
            return False
    
    def _verify_database_connection(self) -> bool:
        """验证数据库连接"""
        try:
            # 简单的数据库连接测试
            db.session.execute('SELECT 1')
            return True
        except Exception as e:
            current_app.logger.error(f"数据库连接验证失败: {e}")
            return False
    
    def _update_progress(self, restore_record: RestoreRecord, progress: int, message: str):
        """更新恢复进度"""
        restore_record.progress = progress
        restore_record.status_message = message
        db.session.commit()
        current_app.logger.info(f"Restore {restore_record.restore_id}: {progress}% - {message}")
    
    def _complete_restore(self, restore_record: RestoreRecord):
        """完成恢复"""
        restore_record.status = 'completed'
        restore_record.progress = 100
        restore_record.completed_at = datetime.now(timezone.utc)
        restore_record.status_message = '恢复完成'
        db.session.commit()
    
    def _fail_restore(self, restore_record: RestoreRecord, error_message: str):
        """恢复失败"""
        if restore_record:
            restore_record.status = 'failed'
            restore_record.error_message = error_message
            restore_record.status_message = f'恢复失败: {error_message}'
            db.session.commit()
    
    def get_restore_records(self, status: str = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """获取恢复记录列表"""
        query = RestoreRecord.query
        
        if status:
            query = query.filter_by(status=status)
        
        query = query.order_by(RestoreRecord.created_at.desc())
        records = query.limit(limit).offset(offset).all()
        
        return [record.to_dict() for record in records]
    
    def cancel_restore(self, restore_id: str) -> bool:
        """取消恢复任务"""
        restore_record = RestoreRecord.query.filter_by(restore_id=restore_id).first()
        if not restore_record:
            return False
        
        if restore_record.status not in ['pending', 'running']:
            return False
        
        restore_record.status = 'cancelled'
        restore_record.status_message = '恢复已取消'
        db.session.commit()
        
        current_app.logger.info(f"Restore {restore_id} cancelled")
        return True