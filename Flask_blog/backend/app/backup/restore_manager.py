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
from ..models import BackupRecord, RestoreRecord, SHANGHAI_TZ
from .smart_table_validator import SmartTableValidator


class RestoreManager:
    """备份恢复管理器"""
    
    def __init__(self):
        self.app_root = Path(current_app.root_path).parent
        self.backup_root = self.app_root / 'backups'
        self.smart_validator = SmartTableValidator()
    
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
            restore_record.started_at = datetime.now(SHANGHAI_TZ)
            restore_record.progress = 0
            db.session.commit()
            
            # 解析恢复选项
            restore_options = json.loads(restore_record.restore_options or '{}')
            restore_options.update(options)
            
            # 检查测试模式
            test_mode = restore_options.get('test_mode', False)
            if test_mode:
                current_app.logger.info(f"运行在测试模式，仅验证恢复内容而不实际执行")
                return self._test_mode_restore(restore_record, backup_record, restore_options)
            
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
        """验证备份完整性 - 增强版，集成智能表验证"""
        try:
            current_app.logger.info("开始增强版备份完整性验证...")
            
            # === 第1层：基础文件结构验证 ===
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
            
            # === 第2层：智能表结构验证 ===
            if db_files:
                # 使用智能表验证器检查数据库内容
                validation_result = self._verify_database_table_completeness(db_files[0])
                
                if not validation_result['complete']:
                    severity = validation_result['severity']
                    
                    if severity == 'critical':
                        current_app.logger.error("❌ 发现核心表缺失，备份不完整！")
                        current_app.logger.error(f"缺失核心表: {validation_result['critical_missing']}")
                        return False
                    
                    elif severity == 'high':
                        current_app.logger.error("⚠️ 发现重要表缺失，备份可能不完整！")
                        current_app.logger.error(f"缺失重要表: {validation_result['important_missing']}")
                        # 根据配置决定是否继续（这里选择保守策略，失败）
                        return False
                    
                    elif severity in ['medium', 'low']:
                        current_app.logger.warning(f"⚠️ 发现表缺失（严重程度: {severity}），但可以继续")
                        current_app.logger.warning(f"缺失表: {validation_result['missing_tables']}")
                        # 中低级别缺失，允许继续
                
                current_app.logger.info("✅ 智能表结构验证通过")
            
            # === 第3层：校验和验证 ===
            if backup_record.checksum:
                if not self._verify_backup_checksum(extracted_path, backup_record.checksum):
                    current_app.logger.error("备份校验和验证失败")
                    return False
            
            current_app.logger.info("🎉 所有完整性验证通过")
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
        """恢复MySQL数据库 - 多方案自动选择"""
        current_app.logger.info(f"开始恢复MySQL数据库: {db_file}")
        
        # 方案1: 优先使用SQLAlchemy直接执行（无外部依赖）
        try:
            current_app.logger.info("尝试使用SQLAlchemy方案恢复数据库...")
            self._restore_mysql_with_sqlalchemy(db_file, database_url, options)
            current_app.logger.info("SQLAlchemy方案恢复成功")
            return
        except Exception as e:
            current_app.logger.warning(f"SQLAlchemy方案失败: {e}")
        
        # 方案2: 尝试Docker容器执行
        try:
            current_app.logger.info("尝试使用Docker容器方案恢复数据库...")
            self._restore_mysql_with_docker(db_file, database_url, options)
            current_app.logger.info("Docker容器方案恢复成功")
            return
        except Exception as e:
            current_app.logger.warning(f"Docker容器方案失败: {e}")
        
        # 方案3: 最后尝试系统mysql命令
        try:
            current_app.logger.info("尝试使用系统mysql命令恢复数据库...")
            self._restore_mysql_with_command(db_file, database_url, options)
            current_app.logger.info("系统mysql命令恢复成功")
            return
        except Exception as e:
            current_app.logger.error(f"系统mysql命令失败: {e}")
        
        # 所有方案都失败
        raise Exception("所有MySQL恢复方案都失败。建议检查：1) 数据库连接是否正常 2) 备份文件格式是否正确 3) MySQL服务是否运行")
    
    def _restore_mysql_with_command(self, db_file: Path, database_url: str, options: Dict[str, Any]):
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
            # 优化：使用流式处理避免大文件内存溢出
            with open(db_file, 'r', encoding='utf-8') as f:
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # 流式传输文件内容，避免一次性加载到内存
                chunk_size = 8192  # 8KB chunks
                try:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        process.stdin.write(chunk)
                    
                    process.stdin.close()
                    stdout, stderr = process.communicate(timeout=300)  # 5分钟超时
                    
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    raise Exception("MySQL恢复操作超时")
                except Exception as e:
                    process.kill()
                    raise e
            
            if process.returncode != 0:
                raise Exception(f"MySQL恢复失败: {stderr}")
                
            current_app.logger.info(f"MySQL数据库恢复成功从: {db_file}")
            
        except subprocess.TimeoutExpired:
            raise Exception("MySQL恢复超时")
        except FileNotFoundError:
            current_app.logger.warning("mysql命令未找到，尝试其他恢复方案")
            raise Exception("mysql命令未找到")
    
    def _restore_mysql_with_sqlalchemy(self, db_file: Path, database_url: str, options: Dict[str, Any]):
        """使用SQLAlchemy恢复MySQL数据库 - 事务隔离修复版本"""
        from sqlalchemy import create_engine, inspect
        import pymysql
        import urllib.parse
        
        current_app.logger.info(f"使用事务隔离修复版SQLAlchemy恢复数据库: {db_file}")
        
        # 解析数据库连接信息
        parsed = urllib.parse.urlparse(database_url)
        db_config = {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 3306,
            'user': parsed.username,
            'password': parsed.password,
            'database': parsed.path.lstrip('/'),
            'charset': 'utf8mb4',
            'autocommit': False
        }
        
        current_app.logger.info(f"连接参数: {db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")
        
        # 关键修复：为数据恢复创建独立的数据库连接，与恢复任务状态管理隔离
        # 这样数据恢复的rollback不会影响到恢复任务记录的状态更新
        restore_engine = create_engine(database_url)
        raw_connection = restore_engine.raw_connection()
        
        try:
            cursor = raw_connection.cursor()
            
            current_app.logger.info("原生MySQL连接建立成功")
            
            # 读取并清理SQL文件
            sql_content = self._read_and_clean_sql_file(db_file)
            
            # 解析SQL文件，提取表结构和数据
            table_data = self._parse_sql_dump(sql_content)
            
            current_app.logger.info(f"解析出 {len(table_data)} 个表的数据")
            
            if not table_data:
                raise Exception("SQL文件中没有找到有效的INSERT语句")
            
            # 开始事务 - 真正的数据替换，增强错误处理
            try:
                # 设置MySQL会话参数以提高成功率
                current_app.logger.info("设置MySQL会话参数...")
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                cursor.execute("SET UNIQUE_CHECKS = 0") 
                cursor.execute("SET AUTOCOMMIT = 0")
                
                # 定义需要保护的系统表 - ULTRALTHINK关键修复
                PROTECTED_SYSTEM_TABLES = {
                    'alembic_version',       # 数据库版本表
                    'restore_records',       # 🛡️ 恢复任务记录表 - 关键保护！
                    'backup_records',        # 🛡️ 备份记录表
                    'backup_configs',        # 🛡️ 备份配置表
                    'backup_tasks',          # 🛡️ 备份任务表
                    'backup_storage_providers', # 🛡️ 存储提供者表
                    'users',                 # 🛡️ 用户表（可选保护）
                    'user_tokens',           # 🛡️ 用户令牌表
                    'logs',                  # 🛡️ 日志表
                    'visitor_metrics',       # 🛡️ 访客统计表
                    'daily_metrics'          # 🛡️ 日常统计表
                }
                
                # 第二阶段：清空要恢复的业务表（保护系统表）
                current_app.logger.info("开始清空业务表数据（保护系统表）...")
                for table_name in table_data.keys():
                    if table_name in PROTECTED_SYSTEM_TABLES:
                        current_app.logger.warning(f"🛡️ 跳过受保护的系统表: {table_name}")
                        continue
                        
                    current_app.logger.info(f"清空业务表数据: {table_name}")
                    cursor.execute(f"DELETE FROM `{table_name}`")
                
                # 第三阶段：插入备份数据（仅业务表）
                current_app.logger.info("开始插入备份数据（仅业务表）...")
                total_inserted = 0
                skipped_system_tables = 0
                for table_name, inserts in table_data.items():
                    if table_name in PROTECTED_SYSTEM_TABLES:
                        skipped_system_tables += 1
                        current_app.logger.warning(f"🛡️ 跳过受保护的系统表数据插入: {table_name}")
                        continue
                        
                    current_app.logger.info(f"恢复表数据: {table_name} ({len(inserts)} 条记录)")
                    
                    insert_count = 0
                    for insert_sql in inserts:
                        try:
                            # 直接执行原始SQL，不经过SQLAlchemy的text()包装
                            cursor.execute(insert_sql)
                            insert_count += 1
                            total_inserted += 1
                            
                            # 每插入100条记录提交一次，避免长事务
                            if insert_count % 100 == 0:
                                raw_connection.commit()
                                current_app.logger.debug(f"表 {table_name}: 已插入 {insert_count} 条")
                                
                        except Exception as e:
                            current_app.logger.error(f"插入数据失败: {insert_sql[:100]}... 错误: {e}")
                            # 记录详细错误但继续处理其他记录
                            if "Duplicate entry" in str(e):
                                current_app.logger.warning(f"跳过重复记录: {table_name}")
                                continue
                            else:
                                # 对于非主键冲突的错误，必须停止并回滚
                                raise Exception(f"表 {table_name} 数据插入失败: {e}")
                    
                    # 完成该表的插入后提交
                    raw_connection.commit()
                    current_app.logger.info(f"表 {table_name} 恢复完成: {insert_count} 条记录")
                
                # 第四阶段：重新启用外键检查
                current_app.logger.info("重新启用外键检查...")
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                
                # 最终提交
                raw_connection.commit()
                current_app.logger.info(
                    f"🎉 数据库恢复完全成功！共插入 {total_inserted} 条记录，"
                    f"跳过 {skipped_system_tables} 个受保护的系统表"
                )
                
            except Exception as e:
                current_app.logger.error(f"恢复过程出错，正在回滚: {e}")
                raw_connection.rollback()
                # 确保外键检查重新启用
                try:
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                    raw_connection.commit()
                except:
                    pass
                raise Exception(f"数据库恢复失败: {e}")
                
        finally:
            if raw_connection:
                raw_connection.close()
                current_app.logger.info("MySQL连接已关闭")
    
    def _read_and_clean_sql_file(self, db_file: Path) -> str:
        """读取并清理SQL文件，处理编码问题 - 增强版"""
        import chardet
        
        current_app.logger.info(f"读取SQL文件: {db_file}")
        
        # 首先检测文件编码
        with open(db_file, 'rb') as f:
            raw_data = f.read()
            detected = chardet.detect(raw_data)
            current_app.logger.info(f"检测到的文件编码: {detected}")
        
        # 按优先级尝试不同编码方式
        encodings_to_try = []
        
        # 如果检测到编码且置信度高，优先使用
        if detected and detected.get('confidence', 0) > 0.7:
            encodings_to_try.append(detected['encoding'])
        
        # 添加常用编码
        encodings_to_try.extend(['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'gbk'])
        
        content = None
        used_encoding = None
        
        for encoding in encodings_to_try:
            try:
                current_app.logger.info(f"尝试使用编码: {encoding}")
                with open(db_file, 'r', encoding=encoding) as f:
                    content = f.read()
                used_encoding = encoding
                break
            except UnicodeDecodeError as e:
                current_app.logger.warning(f"编码 {encoding} 失败: {e}")
                continue
        
        if content is None:
            # 最后的兜底方案：使用错误替换
            current_app.logger.warning("所有编码尝试失败，使用错误替换模式")
            with open(db_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            used_encoding = 'utf-8-with-errors'
        
        current_app.logger.info(f"成功使用编码 {used_encoding} 读取文件，内容长度: {len(content)}")
        
        # 增强的内容清理
        original_length = len(content)
        
        # 清理各种可能导致问题的字符
        content = content.replace('\u200b', '')  # 零宽空格
        content = content.replace('\ufeff', '')  # BOM
        content = content.replace('\u00a0', ' ')  # 非断空格 -> 普通空格
        content = content.replace('\r\n', '\n')  # 统一换行符
        content = content.replace('\r', '\n')    # Mac换行符
        
        # 清理SQLAlchemy可能误解的特殊字符组合
        # 这些组合可能被误认为是bind参数
        content = content.replace('::', '__DOUBLE_COLON__')  # 临时替换双冒号
        content = content.replace('%(', '__PERCENT_PAREN__')  # 临时替换%(
        
        # 清理多余的空白字符
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            # 去除行首行尾空白，但保留必要的缩进
            stripped = line.strip()
            if stripped:  # 只保留非空行
                cleaned_lines.append(stripped)
        
        content = '\n'.join(cleaned_lines)
        
        # 恢复临时替换的字符
        content = content.replace('__DOUBLE_COLON__', '::')
        content = content.replace('__PERCENT_PAREN__', '%(')
        
        current_app.logger.info(f"内容清理完成: {original_length} -> {len(content)} 字符")
        
        return content
    
    def _parse_sql_dump(self, sql_content: str) -> Dict[str, List[str]]:
        """解析SQL转储文件，提取表数据插入语句 - 增强版处理复杂SQL"""
        table_data = {}
        current_insert = ""
        in_insert_statement = False
        
        current_app.logger.info("开始解析SQL转储文件...")
        
        lines = sql_content.split('\n')
        total_lines = len(lines)
        processed_lines = 0
        
        for line in lines:
            processed_lines += 1
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('--') or line.startswith('/*'):
                continue
                
            # 跳过会锁表的语句 - 这是导致问题的关键
            if any(keyword in line.upper() for keyword in [
                'LOCK TABLES', 'UNLOCK TABLES', 'ALTER TABLE', 'DISABLE KEYS', 'ENABLE KEYS',
                'DROP TABLE', 'CREATE TABLE'  # 也跳过表结构语句，只恢复数据
            ]):
                current_app.logger.debug(f"跳过锁表语句: {line[:50]}...")
                continue
                
            # 跳过系统设置语句
            if (line.startswith('/*!') or 
                'SET ' in line.upper() or 
                line.upper().startswith('USE ') or
                line.upper().startswith('SOURCE ')):
                continue
                
            # 处理INSERT语句 - 可能跨多行
            if line.upper().startswith('INSERT INTO'):
                if in_insert_statement and current_insert:
                    # 前一个INSERT语句还没结束，先处理它
                    self._process_insert_statement(current_insert, table_data)
                
                current_insert = line
                in_insert_statement = True
                
                # 检查是否是单行INSERT语句
                if current_insert.rstrip().endswith(';'):
                    # 单行语句，立即处理
                    self._process_insert_statement(current_insert, table_data)
                    current_insert = ""
                    in_insert_statement = False
                    
            elif in_insert_statement:
                # 继续拼接多行INSERT语句
                current_insert += " " + line
                
                # 检查是否结束
                if line.rstrip().endswith(';'):
                    self._process_insert_statement(current_insert, table_data)
                    current_insert = ""
                    in_insert_statement = False
            
            # 每处理1000行记录进度
            if processed_lines % 1000 == 0:
                current_app.logger.debug(f"解析进度: {processed_lines}/{total_lines} 行")
        
        # 处理最后一个INSERT语句（如果存在）
        if current_insert and in_insert_statement:
            self._process_insert_statement(current_insert, table_data)
        
        current_app.logger.info(f"SQL解析完成，共解析出 {len(table_data)} 个表")
        for table_name, inserts in table_data.items():
            current_app.logger.info(f"表 {table_name}: {len(inserts)} 条INSERT语句")
        
        return table_data
    
    def _process_insert_statement(self, insert_sql: str, table_data: Dict[str, List[str]]):
        """处理单个INSERT语句，提取表名并存储"""
        try:
            # 清理INSERT语句，去除末尾分号
            insert_sql = insert_sql.rstrip().rstrip(';')
            
            # 提取表名 - 更健壮的方法
            table_name = self._extract_table_name(insert_sql)
            if table_name:
                if table_name not in table_data:
                    table_data[table_name] = []
                
                # 清理SQL语句，避免SQLAlchemy bind参数冲突
                cleaned_sql = self._clean_insert_sql_for_sqlalchemy(insert_sql)
                table_data[table_name].append(cleaned_sql)
            else:
                current_app.logger.warning(f"无法提取表名: {insert_sql[:100]}...")
                
        except Exception as e:
            current_app.logger.error(f"处理INSERT语句失败: {e}, SQL: {insert_sql[:100]}...")
    
    def _extract_table_name(self, insert_sql: str) -> Optional[str]:
        """从INSERT语句中提取表名"""
        import re
        
        # 匹配 INSERT INTO `table_name` 或 INSERT INTO table_name
        patterns = [
            r'INSERT\s+INTO\s+`([^`]+)`',  # 反引号包围的表名
            r'INSERT\s+INTO\s+([^\s(]+)',  # 无引号的表名
        ]
        
        for pattern in patterns:
            match = re.search(pattern, insert_sql, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _clean_insert_sql_for_sqlalchemy(self, insert_sql: str) -> str:
        """清理INSERT语句，避免SQLAlchemy误解bind参数"""
        # SQLAlchemy会将 %(xxx) 误认为是bind参数
        # 我们需要转义这些模式
        
        # 方法1: 将所有的 %(xxx) 模式替换为转义版本
        import re
        
        # 查找所有 %(变量名) 模式并转义
        def escape_bind_params(match):
            full_match = match.group(0)
            # 将 %(xxx) 替换为 %%(xxx) 来转义
            return full_match.replace('%', '%%')
        
        # 匹配 %(任何非)字符) 的模式
        pattern = r'%\([^)]+\)'
        cleaned_sql = re.sub(pattern, escape_bind_params, insert_sql)
        
        # 检查是否有其他可能的bind参数模式
        if ':' in cleaned_sql and not cleaned_sql.count('::'):
            # 如果有单独的冒号（不是::），可能是named参数，需要转义
            # 但要小心不要转义时间格式等合法用途
            pass  # 暂时不处理这种复杂情况
        
        return cleaned_sql
    
    def _split_sql_statements(self, sql_content: str) -> list:
        """智能分割SQL语句，处理字符串中的分号"""
        statements = []
        current_statement = ""
        in_string = False
        string_char = None
        i = 0
        
        while i < len(sql_content):
            char = sql_content[i]
            
            if not in_string:
                if char in ("'", '"'):
                    in_string = True
                    string_char = char
                elif char == ';':
                    statements.append(current_statement.strip())
                    current_statement = ""
                    i += 1
                    continue
            else:
                if char == string_char:
                    # 检查是否是转义的引号
                    if i > 0 and sql_content[i-1] != '\\':
                        in_string = False
                        string_char = None
            
            current_statement += char
            i += 1
        
        # 添加最后一个语句
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements
    
    def _restore_mysql_with_docker(self, db_file: Path, database_url: str, options: Dict[str, Any]):
        """使用Docker容器恢复MySQL数据库"""
        import urllib.parse
        import subprocess
        
        # 检测MySQL Docker容器
        container_name = self._detect_mysql_docker_container()
        if not container_name:
            raise Exception("未找到MySQL Docker容器")
        
        parsed = urllib.parse.urlparse(database_url)
        username = parsed.username or 'root'
        password = parsed.password
        database = parsed.path.lstrip('/')
        
        # 构建docker exec命令
        cmd = [
            'docker', 'exec', '-i', container_name,
            'mysql',
            f'--user={username}',
            f'--database={database}'
        ]
        
        if password:
            cmd.insert(-1, f'--password={password}')
        
        current_app.logger.info(f"使用Docker容器 {container_name} 恢复数据库")
        current_app.logger.info(f"SQL文件大小: {db_file.stat().st_size} 字节")
        
        try:
            current_app.logger.info("创建MySQL进程...")
            # 减小缓冲区以避免大文件阻塞
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # 行缓冲
            )
            
            current_app.logger.info(f"进程已启动 PID: {process.pid}")
            
            # 流式传输文件内容
            current_app.logger.info("开始流式传输SQL文件...")
            
            with open(db_file, 'r', encoding='utf-8') as f:
                # 分块传输，避免内存问题
                chunk_size = 4096  # 4KB块
                total_sent = 0
                
                try:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        process.stdin.write(chunk)
                        total_sent += len(chunk)
                        
                        # 每传输50KB记录进度
                        if total_sent % 51200 == 0:
                            current_app.logger.info(f"已传输: {total_sent // 1024}KB")
                    
                    process.stdin.close()
                    current_app.logger.info(f"传输完成: {total_sent // 1024}KB，等待MySQL处理...")
                    
                except Exception as e:
                    current_app.logger.error(f"文件传输失败: {e}")
                    process.kill()
                    raise
            
            # 等待处理完成
            stdout, stderr = process.communicate(timeout=240)  # 4分钟超时
            
            current_app.logger.info(f"MySQL处理完成，返回码: {process.returncode}")
            if stdout:
                current_app.logger.info(f"stdout: {stdout}")
            if stderr:
                current_app.logger.info(f"stderr: {stderr}")
                
            if process.returncode != 0:
                raise Exception(f"Docker MySQL恢复失败 (返回码: {process.returncode}): {stderr}")
                
            current_app.logger.info("✅ Docker MySQL恢复成功")
                
        except subprocess.TimeoutExpired:
            current_app.logger.error("Docker MySQL恢复超时，终止进程...")
            process.kill()
            raise Exception("Docker MySQL恢复超时 (4分钟)")
        except Exception as e:
            current_app.logger.error(f"Docker恢复异常: {e}")
            raise Exception(f"Docker MySQL恢复失败: {e}")
    
    def _detect_mysql_docker_container(self) -> str:
        """检测MySQL Docker容器"""
        import subprocess
        
        try:
            # 查找运行中的MySQL容器
            result = subprocess.run(
                ['docker', 'ps', '--filter', 'status=running', '--format', '{{.Names}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                containers = result.stdout.strip().split('\n')
                for container in containers:
                    if 'mysql' in container.lower():
                        current_app.logger.info(f"发现MySQL容器: {container}")
                        return container
                        
        except Exception as e:
            current_app.logger.debug(f"Docker容器检测失败: {e}")
        
        return None
    
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
        """更新恢复进度 - 事务隔离版本，避免与数据恢复操作冲突"""
        try:
            # 使用独立的数据库会话来更新恢复任务状态，避免与数据恢复操作的事务冲突
            from sqlalchemy.orm import sessionmaker
            from .. import db
            
            # 创建独立会话
            Session = sessionmaker(bind=db.engine)
            independent_session = Session()
            
            try:
                # 在独立会话中查询并更新恢复记录
                independent_record = independent_session.query(RestoreRecord).filter_by(id=restore_record.id).first()
                if independent_record:
                    independent_record.progress = progress
                    independent_record.status_message = message
                    independent_session.commit()
                    current_app.logger.info(f"Restore {restore_record.restore_id}: {progress}% - {message}")
                else:
                    current_app.logger.warning(f"无法找到恢复记录: {restore_record.id}")
            finally:
                independent_session.close()
                
        except Exception as e:
            current_app.logger.warning(f"更新恢复进度失败: {e}")
            # 不抛出异常，避免中断恢复过程
    
    def _complete_restore(self, restore_record: RestoreRecord):
        """完成恢复 - 事务隔离版本"""
        try:
            # 使用独立的数据库会话来更新恢复任务状态
            from sqlalchemy.orm import sessionmaker
            from .. import db
            
            # 创建独立会话
            Session = sessionmaker(bind=db.engine)
            independent_session = Session()
            
            try:
                # 在独立会话中查询并更新恢复记录
                independent_record = independent_session.query(RestoreRecord).filter_by(id=restore_record.id).first()
                if independent_record:
                    independent_record.status = 'completed'
                    independent_record.progress = 100
                    independent_record.completed_at = datetime.now(SHANGHAI_TZ)
                    independent_record.status_message = '恢复完成'
                    independent_session.commit()
                    current_app.logger.info(f"恢复记录已标记为完成: {restore_record.restore_id}")
                else:
                    current_app.logger.error(f"无法找到恢复记录: {restore_record.id}")
            finally:
                independent_session.close()
                
        except Exception as e:
            current_app.logger.error(f"更新恢复完成状态时出错: {e}")
    
    def _fail_restore(self, restore_record: RestoreRecord, error_message: str):
        """恢复失败 - 事务隔离修复版本，避免rollback影响恢复任务记录"""
        if restore_record:
            try:
                # 关键修复：使用独立的数据库会话来更新恢复任务状态
                # 避免与数据恢复操作的事务冲突
                from sqlalchemy.orm import sessionmaker
                from .. import db
                
                # 创建独立会话
                Session = sessionmaker(bind=db.engine)
                independent_session = Session()
                
                try:
                    # 在独立会话中查询并更新恢复记录
                    independent_record = independent_session.query(RestoreRecord).filter_by(id=restore_record.id).first()
                    if independent_record:
                        independent_record.status = 'failed'
                        independent_record.error_message = error_message[:500]  # 限制错误消息长度
                        independent_record.status_message = f'恢复失败: {error_message[:200]}'
                        independent_record.completed_at = datetime.now(SHANGHAI_TZ)
                        independent_session.commit()
                        current_app.logger.info(f"恢复记录已标记为失败: {restore_record.restore_id}")
                    else:
                        current_app.logger.error(f"无法找到恢复记录: {restore_record.id}")
                finally:
                    independent_session.close()
                    
            except Exception as e:
                current_app.logger.error(f"更新恢复失败状态时出错: {e}")
                # 确保不会抛出异常，不影响主流程
    
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
    
    def _test_mode_restore(self, restore_record: RestoreRecord, backup_record: BackupRecord, restore_options: Dict[str, Any]) -> Dict[str, Any]:
        """测试模式恢复 - 只验证不实际执行"""
        try:
            # 模拟恢复过程，提供详细的验证信息
            verification_results = []
            
            # 第1步：验证备份文件存在性
            self._update_progress(restore_record, 20, "测试模式: 验证备份文件...")
            backup_file = self.backup_root / 'snapshots' / f"{backup_record.backup_id}.tar.gz"
            if backup_file.exists():
                verification_results.append("✅ 备份文件存在且可访问")
                file_size = backup_file.stat().st_size
                verification_results.append(f"📁 备份文件大小: {file_size / (1024*1024):.1f} MB")
            else:
                verification_results.append("❌ 备份文件不存在或无法访问")
            
            # 第2步：验证备份文件完整性（快速检查）
            self._update_progress(restore_record, 40, "测试模式: 检查备份完整性...")
            try:
                import tarfile
                with tarfile.open(backup_file, 'r:gz') as tar:
                    members = tar.getnames()
                    verification_results.append(f"✅ 备份文件结构完整，包含 {len(members)} 个文件/目录")
                    
                    # 检查关键文件
                    db_files = [m for m in members if m.endswith('.sql')]
                    if db_files:
                        verification_results.append(f"🗄️ 发现 {len(db_files)} 个数据库备份文件")
                        
            except Exception as e:
                verification_results.append(f"❌ 备份文件损坏: {str(e)}")
            
            # 第3步：验证恢复目标
            self._update_progress(restore_record, 60, "测试模式: 验证恢复目标...")
            target_path = restore_options.get('target_path')
            if target_path:
                target = Path(target_path)
                try:
                    target.mkdir(parents=True, exist_ok=True)
                    # 测试写入权限
                    test_file = target / '.restore_test'
                    test_file.write_text('test')
                    test_file.unlink()
                    verification_results.append(f"✅ 目标目录可写: {target_path}")
                except Exception as e:
                    verification_results.append(f"❌ 目标目录无法写入: {str(e)}")
            else:
                verification_results.append("⚠️ 未指定目标路径，将恢复到原位置（高风险操作）")
            
            # 第4步：验证数据库连接（如果包含数据库恢复）
            self._update_progress(restore_record, 80, "测试模式: 验证数据库连接...")
            if restore_options.get('include_database', True):
                try:
                    # 简单的数据库连接测试
                    db.session.execute('SELECT 1')
                    verification_results.append("✅ 数据库连接正常")
                except Exception as e:
                    verification_results.append(f"❌ 数据库连接失败: {str(e)}")
            
            # 完成测试
            self._update_progress(restore_record, 100, "测试模式验证完成")
            
            # 更新恢复记录
            restore_record.status = 'completed'
            restore_record.completed_at = datetime.now(SHANGHAI_TZ)
            restore_record.status_message = '测试模式验证完成 - 未执行实际恢复'
            restore_record.error_message = '\n'.join(verification_results)
            db.session.commit()
            
            current_app.logger.info(f"Test mode restore completed for {restore_record.restore_id}")
            
            return {
                'status': 'success',
                'restore_id': restore_record.restore_id,
                'message': '测试模式验证完成',
                'test_results': verification_results
            }
            
        except Exception as e:
            current_app.logger.error(f"Test mode restore failed: {e}")
            self._fail_restore(restore_record, f"测试模式失败: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'message': f'测试模式失败: {str(e)}'
            }

    # ========== 智能表验证相关方法 ==========
    
    def _verify_database_table_completeness(self, db_file_path: Path) -> Dict[str, Any]:
        """验证数据库备份的表完整性"""
        try:
            current_app.logger.info("开始智能表完整性验证...")
            
            # 读取SQL文件内容
            with open(db_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 使用智能验证器验证
            validation_result = self.smart_validator.validate_backup_completeness(sql_content)
            
            current_app.logger.info(f"表完整性验证完成 - 完整性: {validation_result['complete']}")
            
            return validation_result
            
        except Exception as e:
            current_app.logger.error(f"智能表验证失败: {e}")
            # 返回保守的结果，假设验证失败意味着可能有问题
            return {
                'complete': False,
                'severity': 'unknown',
                'missing_tables': [],
                'error': str(e),
                'can_proceed_safely': False,
                'recommendations': ['验证过程出现异常，建议检查备份文件和系统状态']
            }
    
    def _verify_backup_checksum(self, extracted_path: Path, expected_checksum: str) -> bool:
        """验证备份文件的校验和"""
        try:
            import hashlib
            
            # 计算提取后文件的整体校验和
            actual_checksum = self._calculate_directory_checksum(extracted_path)
            
            if actual_checksum == expected_checksum:
                current_app.logger.info("✅ 备份校验和验证通过")
                return True
            else:
                current_app.logger.error(f"❌ 校验和不匹配 - 期望: {expected_checksum}, 实际: {actual_checksum}")
                return False
                
        except Exception as e:
            current_app.logger.error(f"校验和验证失败: {e}")
            return False
    
    def _calculate_directory_checksum(self, directory: Path) -> str:
        """计算目录的整体校验和"""
        import hashlib
        
        hasher = hashlib.md5()
        
        # 按文件名排序，确保结果一致
        for file_path in sorted(directory.rglob('*')):
            if file_path.is_file():
                # 添加文件名到hash
                hasher.update(str(file_path.relative_to(directory)).encode())
                
                # 添加文件内容到hash  
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def create_pre_restore_snapshot(self) -> Optional[str]:
        """在恢复前创建紧急快照"""
        try:
            from .backup_manager import BackupManager
            
            current_app.logger.info("正在创建恢复前安全快照...")
            
            backup_manager = BackupManager()
            snapshot_id = backup_manager.create_backup('snapshot', {
                'description': '恢复前安全快照 - 自动创建',
                'emergency_snapshot': True,
                'include_database': True,
                'include_files': False,  # 为了速度，只备份数据库
                'requested_by': 'restore_safety_system'
            })
            
            current_app.logger.info(f"✅ 安全快照创建完成: {snapshot_id}")
            return snapshot_id
            
        except Exception as e:
            current_app.logger.error(f"❌ 安全快照创建失败: {e}")
            return None
    
    def get_table_validation_report(self, backup_record: BackupRecord) -> Dict[str, Any]:
        """获取备份的表验证报告（供UI显示）"""
        try:
            # 提取备份文件
            with tempfile.TemporaryDirectory(prefix="validation_") as temp_dir:
                temp_path = Path(temp_dir)
                extracted_path = self._extract_backup(backup_record, temp_path)
                
                # 查找数据库文件
                db_files = list(extracted_path.glob("database_*.sql"))
                if not db_files:
                    return {
                        'status': 'error',
                        'message': '未找到数据库备份文件'
                    }
                
                # 执行验证
                validation_result = self._verify_database_table_completeness(db_files[0])
                
                # 格式化为报告格式
                return {
                    'status': 'success',
                    'validation_result': validation_result,
                    'summary': {
                        'complete': validation_result['complete'],
                        'severity': validation_result['severity'],
                        'total_expected': validation_result.get('total_expected', 0),
                        'total_in_backup': validation_result.get('total_in_backup', 0),
                        'missing_count': validation_result.get('missing_count', 0)
                    },
                    'recommendations': validation_result.get('recommendations', [])
                }
                
        except Exception as e:
            current_app.logger.error(f"获取验证报告失败: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }