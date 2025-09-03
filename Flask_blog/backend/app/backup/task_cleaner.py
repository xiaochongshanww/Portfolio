#!/usr/bin/env python3
"""
自动任务清理器
定期清理卡死的备份和恢复任务，维护系统健康状态
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from flask import Flask, current_app
from sqlalchemy.exc import OperationalError, DisconnectionError
from .. import db
from ..models import BackupRecord, RestoreRecord, SHANGHAI_TZ


class TaskCleaner:
    """任务自动清理器"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.cleaning_thread = None
        self.stop_event = threading.Event()
        self.logger = logging.getLogger(__name__)
        
        # 清理配置
        self.config = {
            'backup_timeout_minutes': 60,      # 备份任务超时时间（分钟）
            'restore_timeout_minutes': 30,     # 恢复任务超时时间（分钟）
            'cleanup_interval_minutes': 5,     # 清理检查间隔（分钟）
            'max_failed_retries': 3,           # 最大失败重试次数
            'enable_auto_cleanup': True        # 是否启用自动清理
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """初始化应用"""
        self.app = app
        
        # 从配置中读取设置
        self.config.update({
            'backup_timeout_minutes': app.config.get('BACKUP_TIMEOUT_MINUTES', 60),
            'restore_timeout_minutes': app.config.get('RESTORE_TIMEOUT_MINUTES', 30),
            'cleanup_interval_minutes': app.config.get('CLEANUP_INTERVAL_MINUTES', 5),
            'enable_auto_cleanup': app.config.get('ENABLE_AUTO_CLEANUP', True)
        })
        
        # 注册清理器到应用
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['task_cleaner'] = self
    
    def start_cleanup_daemon(self):
        """启动清理守护进程"""
        if not self.config['enable_auto_cleanup']:
            self.logger.info("自动任务清理已禁用")
            return
        
        if self.cleaning_thread and self.cleaning_thread.is_alive():
            self.logger.warning("清理守护进程已在运行")
            return
        
        self.stop_event.clear()
        self.cleaning_thread = threading.Thread(
            target=self._cleanup_daemon_worker,
            name='TaskCleanupDaemon',
            daemon=True
        )
        self.cleaning_thread.start()
        self.logger.info("任务清理守护进程已启动")
    
    def stop_cleanup_daemon(self):
        """停止清理守护进程"""
        if self.cleaning_thread and self.cleaning_thread.is_alive():
            self.stop_event.set()
            self.cleaning_thread.join(timeout=10)
            self.logger.info("任务清理守护进程已停止")
    
    def _cleanup_daemon_worker(self):
        """清理守护进程工作线程"""
        self.logger.info("任务清理守护进程开始运行")
        
        while not self.stop_event.is_set():
            try:
                with self.app.app_context():
                    # 执行清理操作
                    cleanup_result = self.cleanup_stuck_tasks()
                    
                    if cleanup_result['total_cleaned'] > 0:
                        self.logger.info(
                            f"清理完成: 备份任务 {cleanup_result['backup_cleaned']} 个, "
                            f"恢复任务 {cleanup_result['restore_cleaned']} 个"
                        )
                
            except (OperationalError, DisconnectionError) as e:
                self.logger.debug(f"清理守护进程数据库连接异常: {e}")
            except Exception as e:
                self.logger.error(f"清理守护进程执行异常: {e}")
            
            # 等待下次清理
            wait_seconds = self.config['cleanup_interval_minutes'] * 60
            if self.stop_event.wait(wait_seconds):
                break
        
        self.logger.info("任务清理守护进程已退出")
    
    def cleanup_stuck_tasks(self) -> Dict[str, Any]:
        """清理卡死的任务"""
        result = {
            'backup_cleaned': 0,
            'restore_cleaned': 0,
            'total_cleaned': 0,
            'errors': []
        }
        
        # 检查数据库连接是否可用
        if not self._check_database_connection():
            self.logger.debug("数据库连接不可用，跳过本次清理")
            return result
        
        try:
            # 清理卡死的备份任务
            backup_result = self._cleanup_stuck_backups()
            result['backup_cleaned'] = backup_result['cleaned_count']
            result['errors'].extend(backup_result.get('errors', []))
            
            # 清理卡死的恢复任务
            restore_result = self._cleanup_stuck_restores()
            result['restore_cleaned'] = restore_result['cleaned_count']
            result['errors'].extend(restore_result.get('errors', []))
            
            result['total_cleaned'] = result['backup_cleaned'] + result['restore_cleaned']
            
        except Exception as e:
            error_msg = f"清理任务时发生异常: {e}"
            self.logger.error(error_msg)
            result['errors'].append(error_msg)
        
        return result
    
    def _check_database_connection(self) -> bool:
        """检查数据库连接是否可用"""
        try:
            # 执行简单的查询来测试连接
            db.session.execute(db.text('SELECT 1'))
            return True
        except (OperationalError, DisconnectionError) as e:
            # 数据库连接不可用（可能正在重启或维护中）
            self.logger.debug(f"数据库连接不可用: {e}")
            return False
        except Exception as e:
            # 其他异常也认为连接不可用
            self.logger.debug(f"数据库连接检查异常: {e}")
            return False
    
    def _safe_database_operation(self, operation_func, operation_name: str, max_retries: int = 3) -> Dict[str, Any]:
        """安全的数据库操作包装器，具有重试机制和指数退避"""
        for attempt in range(max_retries + 1):
            try:
                result = operation_func()
                return {"success": True, "result": result}
            except (OperationalError, DisconnectionError) as e:
                if attempt < max_retries:
                    # 指数退避：1s, 2s, 4s
                    delay = 2 ** attempt
                    self.logger.debug(f"{operation_name} 数据库连接失败 (尝试 {attempt + 1}/{max_retries + 1})，{delay}秒后重试: {e}")
                    time.sleep(delay)
                else:
                    error_msg = f"{operation_name} 最终失败，已达到最大重试次数: {e}"
                    self.logger.debug(error_msg)
                    return {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = f"{operation_name} 执行异常: {e}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}
        
        return {"success": False, "error": f"{operation_name} 未知错误"}
    
    def _cleanup_stuck_backups(self) -> Dict[str, Any]:
        """清理卡死的备份任务"""
        def backup_cleanup_operation():
            result = {'cleaned_count': 0, 'errors': []}
            
            # 计算超时阈值
            timeout_threshold = datetime.now(SHANGHAI_TZ) - timedelta(
                minutes=self.config['backup_timeout_minutes']
            )
            
            # 查找卡死的备份任务
            stuck_backups = BackupRecord.query.filter(
                BackupRecord.status.in_(['pending', 'running']),
                BackupRecord.created_at < timeout_threshold
            ).all()
            
            for backup in stuck_backups:
                try:
                    # 检查文件是否存在，确定真实状态
                    if backup.file_path and backup.file_path.startswith('backups/'):
                        import os
                        full_path = os.path.join(os.getcwd(), backup.file_path)
                        
                        if os.path.exists(full_path):
                            # 文件存在，可能是状态同步问题
                            backup.status = 'completed'
                            backup.completed_at = datetime.now(SHANGHAI_TZ)
                            file_size = os.path.getsize(full_path)
                            backup.file_size = file_size
                            self.logger.info(f"修复备份任务状态: {backup.backup_id} -> completed")
                        else:
                            # 文件不存在，标记为失败
                            backup.status = 'failed'
                            backup.error_message = '任务超时且备份文件未找到，已自动清理'
                            backup.completed_at = datetime.now(SHANGHAI_TZ)
                            self.logger.info(f"清理失败的备份任务: {backup.backup_id}")
                    else:
                        # 没有文件路径，直接标记为失败
                        backup.status = 'failed'
                        backup.error_message = f'任务执行超过{self.config["backup_timeout_minutes"]}分钟，已自动清理'
                        backup.completed_at = datetime.now(SHANGHAI_TZ)
                        self.logger.info(f"清理超时的备份任务: {backup.backup_id}")
                    
                    result['cleaned_count'] += 1
                    
                except Exception as e:
                    error_msg = f"清理备份任务 {backup.backup_id} 失败: {e}"
                    self.logger.error(error_msg)
                    result['errors'].append(error_msg)
            
            # 提交数据库更改
            db.session.commit()
            return result
        
        # 使用安全包装器执行操作
        operation_result = self._safe_database_operation(
            backup_cleanup_operation,
            "清理备份任务",
            max_retries=2
        )
        
        if operation_result['success']:
            return operation_result['result']
        else:
            return {
                'cleaned_count': 0,
                'errors': [operation_result['error']]
            }
    
    def _cleanup_stuck_restores(self) -> Dict[str, Any]:
        """清理卡死的恢复任务"""
        def restore_cleanup_operation():
            result = {'cleaned_count': 0, 'errors': []}
            
            # 计算超时阈值
            timeout_threshold = datetime.now(SHANGHAI_TZ) - timedelta(
                minutes=self.config['restore_timeout_minutes']
            )
            
            # 查找卡死的恢复任务
            stuck_restores = RestoreRecord.query.filter(
                RestoreRecord.status.in_(['pending', 'running']),
                RestoreRecord.created_at < timeout_threshold
            ).all()
            
            for restore in stuck_restores:
                try:
                    restore.status = 'failed'
                    restore.error_message = (
                        f'任务执行超过{self.config["restore_timeout_minutes"]}分钟，'
                        f'已自动清理。可能原因：数据库连接异常或备份文件损坏'
                    )
                    restore.status_message = '自动清理: 任务执行超时'
                    restore.completed_at = datetime.now(SHANGHAI_TZ)
                    
                    self.logger.info(f"清理超时的恢复任务: {restore.restore_id}")
                    result['cleaned_count'] += 1
                    
                except Exception as e:
                    error_msg = f"清理恢复任务 {restore.restore_id} 失败: {e}"
                    self.logger.error(error_msg)
                    result['errors'].append(error_msg)
            
            # 提交数据库更改
            db.session.commit()
            return result
        
        # 使用安全包装器执行操作
        operation_result = self._safe_database_operation(
            restore_cleanup_operation,
            "清理恢复任务",
            max_retries=2
        )
        
        if operation_result['success']:
            return operation_result['result']
        else:
            return {
                'cleaned_count': 0,
                'errors': [operation_result['error']]
            }
    
    def get_cleanup_status(self) -> Dict[str, Any]:
        """获取清理器状态"""
        return {
            'daemon_running': self.cleaning_thread and self.cleaning_thread.is_alive(),
            'config': self.config,
            'last_cleanup': getattr(self, '_last_cleanup', None),
            'total_cleanups': getattr(self, '_total_cleanups', 0)
        }


# 全局清理器实例
task_cleaner = TaskCleaner()


def init_task_cleaner(app: Flask):
    """初始化任务清理器"""
    task_cleaner.init_app(app)
    
    # 在应用初始化完成后立即启动清理守护进程
    # 注意：不能在这里直接调用，因为应用上下文可能还未完全准备好
    # 使用延迟启动机制
    def delayed_start():
        with app.app_context():
            task_cleaner.start_cleanup_daemon()
    
    # 使用Timer在短暂延迟后启动守护进程
    import threading
    startup_timer = threading.Timer(2.0, delayed_start)
    startup_timer.daemon = True
    startup_timer.start()
    
    # 在应用关闭时停止清理守护进程
    import atexit
    atexit.register(task_cleaner.stop_cleanup_daemon)
    
    return task_cleaner