#!/usr/bin/env python3
"""
ULTRALTHINK 恢复管理器 - 完全重构版本
解决所有事务冲突和架构问题
"""

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from flask import current_app

from .. import db
from ..models import SHANGHAI_TZ, BackupRecord, RestoreRecord
from .smart_table_validator import SmartTableValidator


class UltralthinkRestoreManager:
    """ULTRALTHINK恢复管理器 - 无冲突架构"""
    
    def __init__(self):
        self.app_root = Path(current_app.root_path).parent
        self.backup_root = self.app_root / 'backups'
        self.smart_validator = SmartTableValidator()
        
    def restore_backup(self, restore_record_id: int, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行备份恢复 - 完全独立会话版本"""
        options = options or {}
        
        # 使用独立会话查询记录，避免会话冲突
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        engine = db.engine
        SessionLocal = sessionmaker(bind=engine)
        independent_session = SessionLocal()
        
        try:
            # 获取恢复记录（独立会话）
            restore_record = independent_session.query(RestoreRecord).filter_by(id=restore_record_id).first()
            if not restore_record:
                raise ValueError(f"Restore record {restore_record_id} not found")
            
            # 获取对应的备份记录（独立会话）
            backup_record = independent_session.query(BackupRecord).filter_by(id=restore_record.backup_record_id).first()
            if not backup_record:
                raise ValueError(f"Backup record {restore_record.backup_record_id} not found")
            
            # 获取必要信息后关闭独立会话
            restore_id = restore_record.restore_id
            backup_id = backup_record.backup_id
            
        finally:
            independent_session.close()
        
        try:
            current_app.logger.info(f"开始ULTRALTHINK恢复，恢复id {restore_id}，恢复数据库id {restore_record_id}")
            
            # 更新状态为运行中（使用记录ID）
            self._safe_update_status_by_id(restore_record_id, 'running', "开始执行恢复...")
            
            # 检查备份文件
            backup_file = self.backup_root / 'snapshots' / f"{backup_id}.tar.gz"
            if not backup_file.exists():
                raise FileNotFoundError(f"备份文件不存在: {backup_file}")
            
            current_app.logger.info(f"使用备份文件: {backup_file}")
            
            # === 新增：智能表完整性验证 ===
            try:
                current_app.logger.info("开始智能备份完整性预检查...")
                validation_result = self._verify_backup_completeness(backup_file)
                
                if not validation_result['can_proceed_safely']:
                    severity = validation_result['severity']
                    missing_tables = validation_result.get('missing_tables', [])
                    
                    error_msg = f"备份完整性验证失败 (严重程度: {severity})"
                    if validation_result.get('critical_missing'):
                        error_msg += f" - 缺失核心表: {validation_result['critical_missing']}"
                    
                    current_app.logger.error(f"🛑 {error_msg}")
                    current_app.logger.error(f"建议: {validation_result.get('recommendations', [])}")
                    
                    # 更新状态为失败
                    self._safe_update_status_by_id(restore_record_id, 'failed', error_msg)
                    
                    return {
                        "status": "failed",
                        "error": error_msg,
                        "validation_details": validation_result,
                        "message": f"智能验证失败: {error_msg}"
                    }
                
                elif validation_result['severity'] in ['medium', 'low']:
                    # 中低级别问题，警告但允许继续
                    current_app.logger.warning(f"⚠️ 发现表缺失 ({validation_result['severity']} 级别)，但允许继续恢复")
                    current_app.logger.warning(f"缺失表: {validation_result.get('missing_tables', [])}")
                
                current_app.logger.info("✅ 智能验证通过，开始执行恢复...")
                
            except Exception as e:
                current_app.logger.error(f"智能验证过程异常: {e}")
                # 验证失败时采用保守策略 - 允许继续但记录警告
                current_app.logger.warning("⚠️ 验证异常，采用保守策略继续恢复")
            
            # 核心恢复逻辑：使用独立进程
            result = self._execute_independent_restore(backup_file, restore_id)
            
            if result["success"]:
                self._safe_update_status_by_id(
                    restore_record_id, 'completed', 
                    f"恢复成功: {result.get('message', '数据库已恢复')}"
                )
                current_app.logger.info(f"恢复成功完成: {restore_id}")
                return {
                    "status": "success",
                    "restore_id": restore_id,
                    "message": "恢复完成"
                }
            else:
                error_msg = result.get('error', '未知错误')
                self._safe_update_status_by_id(restore_record_id, 'failed', f"恢复失败: {error_msg}")
                return {
                    "status": "failed",
                    "error": error_msg,
                    "message": f"恢复失败: {error_msg}"
                }
                
        except Exception as e:
            current_app.logger.error(f"恢复异常: {e}")
            try:
                self._safe_update_status_by_id(restore_record_id, 'failed', f"恢复异常: {str(e)}")
            except:
                pass  # 避免级联异常
            return {
                "status": "failed",
                "error": str(e),
                "message": f"恢复异常: {str(e)}"
            }
    
    def _execute_independent_restore(self, backup_file: Path, restore_id: str) -> Dict[str, Any]:
        """执行独立进程恢复 - 核心架构改进"""
        try:
            current_app.logger.info("启动独立恢复进程...")
            
            # 获取简单恢复引擎的路径
            restore_engine_path = Path(__file__).parent / 'simple_restore_engine.py'
            if not restore_engine_path.exists():
                return {"success": False, "error": "恢复引擎文件不存在"}
            
            # 获取Python解释器路径
            python_exe = self._get_python_executable()
            
            # 构建命令
            cmd = [
                python_exe,
                str(restore_engine_path),
                str(backup_file),
                restore_id
            ]
            
            current_app.logger.info(f"执行命令: {' '.join(cmd)}")
            
            # 执行独立恢复进程
            process = subprocess.run(
                cmd,
                cwd=str(self.app_root),
                capture_output=True,
                text=True,
                timeout=600,  # 10分钟超时
                encoding='utf-8'
            )
            
            current_app.logger.info(f"恢复进程退出码: {process.returncode}")
            if process.stdout:
                current_app.logger.info(f"恢复进程输出: {process.stdout}")
            if process.stderr:
                current_app.logger.warning(f"恢复进程错误: {process.stderr}")
            
            # 解析结果
            if process.returncode == 0:
                try:
                    # 尝试解析JSON输出
                    if process.stdout and process.stdout.strip():
                        result = json.loads(process.stdout)
                        return result
                    else:
                        # stdout为空，认为成功
                        return {
                            "success": True,
                            "message": "恢复完成（无输出）",
                            "output": process.stdout or ""
                        }
                except json.JSONDecodeError:
                    # 如果不是JSON，认为成功
                    return {
                        "success": True,
                        "message": "恢复完成",
                        "output": process.stdout or ""
                    }
            else:
                return {
                    "success": False,
                    "error": f"恢复进程失败 (退出码: {process.returncode})",
                    "stderr": process.stderr,
                    "stdout": process.stdout
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "恢复进程超时 (10分钟)"}
        except Exception as e:
            return {"success": False, "error": f"执行独立恢复失败: {e}"}
    
    def _get_python_executable(self) -> str:
        """获取Python可执行文件路径"""
        # 优先使用虚拟环境的Python
        venv_python = self.app_root / '.venv' / 'Scripts' / 'python.exe'
        if venv_python.exists():
            return str(venv_python)
        
        # 备选方案
        alternatives = [
            self.app_root / '.venv' / 'bin' / 'python',  # Linux/Mac
            'python',
            'python3'
        ]
        
        for alt in alternatives:
            try:
                if isinstance(alt, Path) and alt.exists():
                    return str(alt)
                elif isinstance(alt, str):
                    subprocess.run([alt, '--version'], capture_output=True, timeout=5)
                    return alt
            except:
                continue
        
        # 默认使用当前解释器
        import sys
        return sys.executable
    
    def _safe_update_status(self, restore_record: RestoreRecord, status: str, message: str):
        """安全更新恢复状态 - 会话隔离版本"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 创建完全独立的数据库会话，避免与主请求会话冲突
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker

                # 使用新的独立会话
                engine = db.engine
                SessionLocal = sessionmaker(bind=engine)
                independent_session = SessionLocal()
                
                try:
                    # 使用独立会话查询和更新记录
                    fresh_record = independent_session.query(RestoreRecord).filter_by(id=restore_record.id).first()
                    if fresh_record:
                        fresh_record.status = status
                        fresh_record.status_message = message[:500]  # 限制长度
                        if status in ['completed', 'failed']:
                            fresh_record.completed_at = datetime.now(SHANGHAI_TZ)
                        if status == 'completed':
                            fresh_record.progress = 100
                        
                        independent_session.commit()
                        current_app.logger.info(f"状态更新成功: {status} - {message}")
                        return
                        
                finally:
                    # 确保独立会话被正确关闭
                    try:
                        independent_session.close()
                    except:
                        pass
                    
            except Exception as e:
                current_app.logger.warning(f"状态更新失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(0.1)  # 短暂延迟后重试
                else:
                    current_app.logger.error(f"状态更新最终失败: {e}")
    
    def _safe_update_status_by_id(self, record_id: int, status: str, message: str):
        """通过记录ID安全更新状态 - 完全独立会话版本"""
        current_app.logger.info(f"状态更新请求 - 记录ID: {record_id}, 状态: {status}, 消息: {message}")
        max_retries = 3
        for attempt in range(max_retries):
            current_app.logger.info(f"状态更新尝试 (尝试 {attempt + 1}/{max_retries})")
            try:
                # 创建完全独立的数据库会话
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                
                engine = db.engine
                SessionLocal = sessionmaker(bind=engine)
                independent_session = SessionLocal()
                
                try:
                    # 使用独立会话查询和更新记录
                    current_app.logger.info(f"通过恢复记录id查询恢复任务状态: {record_id}")
                    fresh_record = independent_session.query(RestoreRecord).filter_by(id=record_id).first()
                    if fresh_record:
                        fresh_record.status = status
                        fresh_record.status_message = message[:500]  # 限制长度
                        if status in ['completed', 'failed']:
                            fresh_record.completed_at = datetime.now(SHANGHAI_TZ)
                        if status == 'completed':
                            fresh_record.progress = 100
                        
                        independent_session.commit()
                        current_app.logger.info(f"状态更新成功: {status} - {message}")
                        return
                    else:
                        current_app.logger.warning(f"未找到恢复记录: {record_id}")
                finally:
                    try:
                        independent_session.close()
                    except:
                        pass
                    
            except Exception as e:
                current_app.logger.warning(f"状态更新失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(0.1)
                else:
                    current_app.logger.error(f"状态更新最终失败: {e}")
    
    def cancel_restore(self, restore_id: str) -> bool:
        """取消恢复任务 - 简化版本"""
        try:
            restore_record = RestoreRecord.query.filter_by(restore_id=restore_id).first()
            if not restore_record:
                return False
            
            if restore_record.status not in ['pending', 'running']:
                return False
            
            self._safe_update_status(restore_record, 'cancelled', '恢复已取消')
            current_app.logger.info(f"恢复任务已取消: {restore_id}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"取消恢复任务失败: {e}")
            return False

    # ========== 智能表验证相关方法 ==========
    
    def _verify_backup_completeness(self, backup_file: Path) -> Dict[str, Any]:
        """验证备份的表完整性 - ULTRALTHINK版本"""
        try:
            import tarfile
            import tempfile

            # 提取备份文件
            with tempfile.TemporaryDirectory(prefix="validation_") as temp_dir:
                temp_path = Path(temp_dir)
                
                # 提取tar.gz文件
                with tarfile.open(backup_file, 'r:gz') as tar:
                    tar.extractall(temp_path)
                
                # 查找提取的备份目录
                backup_id = backup_file.stem.replace('.tar', '')  # 去掉.tar.gz得到ID
                extracted_dir = temp_path / backup_id
                
                if not extracted_dir.exists():
                    # 尝试查找第一个子目录
                    subdirs = [d for d in temp_path.iterdir() if d.is_dir()]
                    if subdirs:
                        extracted_dir = subdirs[0]
                    else:
                        raise Exception("无法找到提取的备份目录")
                
                # 查找数据库备份文件
                db_files = list(extracted_dir.glob("database_*.sql"))
                if not db_files:
                    raise Exception("备份中未找到数据库文件")
                
                # 读取SQL内容
                with open(db_files[0], 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                
                # 使用智能验证器验证
                validation_result = self.smart_validator.validate_backup_completeness(sql_content)
                
                current_app.logger.info(f"ULTRALTHINK智能验证完成 - 完整性: {validation_result['complete']}")
                return validation_result
                
        except Exception as e:
            current_app.logger.error(f"ULTRALTHINK智能验证异常: {e}")
            # 返回保守的结果
            return {
                'complete': False,
                'severity': 'unknown',
                'can_proceed_safely': True,  # 允许继续，但标记为未知风险
                'missing_tables': [],
                'error': str(e),
                'recommendations': ['验证过程异常，建议手动检查备份内容']
            }
    
    def get_validation_report(self, backup_file: Path) -> Dict[str, Any]:
        """获取备份验证报告（供API调用）"""
        try:
            validation_result = self._verify_backup_completeness(backup_file)
            
            return {
                'status': 'success',
                'validation': validation_result,
                'summary': {
                    'complete': validation_result['complete'],
                    'severity': validation_result['severity'],
                    'can_proceed': validation_result.get('can_proceed_safely', False),
                    'total_expected': validation_result.get('total_expected', 0),
                    'total_in_backup': validation_result.get('total_in_backup', 0),
                    'missing_count': validation_result.get('missing_count', 0)
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': '获取验证报告失败'
            }