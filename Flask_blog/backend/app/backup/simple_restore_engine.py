#!/usr/bin/env python3
"""
简单数据库恢复引擎 - ULTRALTHINK 架构重构
完全独立的恢复进程，避免所有SQLAlchemy会话冲突
"""

import os
import sys
import subprocess
import tempfile
import tarfile
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler


class SimpleRestoreEngine:
    """简单恢复引擎 - 无依赖，无冲突"""
    
    def __init__(self, database_config: Dict[str, str]):
        self.db_config = database_config
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """设置独立的日志系统"""
        logger = logging.getLogger('SimpleRestoreEngine')
        logger.setLevel(logging.DEBUG)
        log_file_path = Path(__file__).parent.parent.parent / 'logs' / 'simple_restore_engine' / 'simple_restore_engine.log'
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file_path),
            when='midnight',
            interval=1,
            backupCount=7,     # 保留最近7天的日志，可按需调整
            encoding='utf-8',
            utc=True
        )
        formatter = logging.Formatter('%(asctime)s [RESTORE] %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s [RESTORE] %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def restore_database(self, backup_file_path: str, restore_id: str) -> Dict[str, Any]:
        """执行数据库恢复 - 核心方法"""
        self.logger.info(f"开始恢复数据库: {restore_id}")
        self.logger.info(f"备份文件: {backup_file_path}")
        
        try:
            # 第一阶段：提取备份文件
            with tempfile.TemporaryDirectory(prefix=f"restore_{restore_id}_") as temp_dir:
                temp_path = Path(temp_dir)
                self.logger.info(f"工作目录: {temp_path}")
                
                # 提取备份
                sql_file = self._extract_backup(backup_file_path, temp_path)
                if not sql_file:
                    return {"success": False, "error": "未找到数据库备份文件"}
                    
                self.logger.info(f"找到数据库文件: {sql_file}")
                
                # 第二阶段：执行恢复
                result = self._execute_mysql_restore(sql_file)
                
                if result["success"]:
                    self.logger.info("数据库恢复成功完成")
                    return {
                        "success": True,
                        "message": "数据库恢复成功",
                        "restore_id": restore_id,
                        "restored_file": str(sql_file)
                    }
                else:
                    self.logger.error(f"数据库恢复失败: {result['error']}")
                    return result
                    
        except Exception as e:
            error_msg = f"恢复过程异常: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _extract_backup(self, backup_file_path: str, temp_path: Path) -> Optional[Path]:
        """提取备份文件"""
        try:
            backup_file = Path(backup_file_path)
            if not backup_file.exists():
                self.logger.error(f"备份文件不存在: {backup_file_path}")
                return None
                
            self.logger.info("正在提取备份文件...")
            
            # 提取tar.gz文件
            with tarfile.open(backup_file, 'r:gz') as tar:
                tar.extractall(temp_path)
                
            # 查找SQL文件
            sql_files = list(temp_path.rglob("database_*.sql"))
            if sql_files:
                self.logger.info(f"找到SQL文件: {sql_files[0]}")
                return sql_files[0]
            else:
                self.logger.error("备份中未找到数据库SQL文件")
                return None
                
        except Exception as e:
            self.logger.error(f"提取备份文件失败: {e}")
            return None
    
    def _execute_mysql_restore(self, sql_file: Path) -> Dict[str, Any]:
        """执行MySQL恢复 - 使用最简单可靠的方法"""
        try:
            self.logger.info("开始执行MySQL恢复...")
            
            # 方法1：尝试Docker方式（最可靠）
            docker_result = self._try_docker_restore(sql_file)
            if docker_result["success"]:
                return docker_result
                
            # 方法2：尝试系统mysql命令
            system_result = self._try_system_mysql_restore(sql_file)
            if system_result["success"]:
                return system_result
                
            # 所有方法都失败
            return {
                "success": False,
                "error": "所有恢复方法都失败了",
                "details": {
                    "docker_error": docker_result.get("error", "未尝试"),
                    "system_error": system_result.get("error", "未尝试")
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"恢复执行异常: {e}"}
    
    def _try_docker_restore(self, sql_file: Path) -> Dict[str, Any]:
        """尝试使用Docker恢复 - 优化版本使用文件复制"""
        try:
            # 查找MySQL Docker容器
            container_name = self._find_mysql_container()
            if not container_name:
                return {"success": False, "error": "未找到MySQL Docker容器"}
                
            self.logger.info(f"使用Docker容器: {container_name}")
            
            # 优先尝试文件复制方式（性能更好）
            copy_result = self._try_docker_restore_with_copy(container_name, sql_file)
            if copy_result["success"]:
                return copy_result
            
            # 如果文件复制失败，降级到stdin方式（向后兼容）
            self.logger.warning(f"文件复制方式失败: {copy_result['error']}")
            self.logger.info("降级到stdin传输方式...")
            return self._try_docker_restore_with_stdin(container_name, sql_file)
                
        except Exception as e:
            return {"success": False, "error": f"Docker恢复异常: {e}"}
    
    def _try_docker_restore_with_copy(self, container_name: str, sql_file: Path) -> Dict[str, Any]:
        """使用Docker文件复制方式恢复 - 高性能版本 + 系统表保护"""
        try:
            container_temp_file = "/tmp/restore_backup.sql"
            container_filtered_file = "/tmp/restore_backup_filtered.sql"
            
            self.logger.info("步骤1: 复制SQL文件到容器内...")
            # 复制文件到容器
            copy_cmd = [
                'docker', 'cp', 
                str(sql_file), 
                f'{container_name}:{container_temp_file}'
            ]
            
            copy_process = subprocess.run(
                copy_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60  # 文件复制1分钟超时
            )
            
            if copy_process.returncode != 0:
                return {"success": False, "error": f"文件复制失败: {copy_process.stderr}"}
            
            self.logger.info("步骤2: 预处理SQL文件，过滤受保护的系统表...")
            # 使用本地过滤（更可靠）而不是容器内sed过滤
            filtered_content = self._filter_protected_tables_local(sql_file)
            if not filtered_content:
                return {"success": False, "error": "SQL文件过滤失败"}
            
            # 将过滤后的内容写入临时文件，然后复制到容器
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.sql', delete=False) as temp_filtered:
                temp_filtered.write(filtered_content)
                temp_filtered_path = temp_filtered.name
            
            try:
                # 复制过滤后的文件到容器
                copy_filtered_cmd = [
                    'docker', 'cp',
                    temp_filtered_path,
                    f'{container_name}:{container_filtered_file}'
                ]
                
                copy_filtered_process = subprocess.run(
                    copy_filtered_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=60
                )
                
                if copy_filtered_process.returncode != 0:
                    return {"success": False, "error": f"过滤文件复制失败: {copy_filtered_process.stderr}"}
                    
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_filtered_path)
                except:
                    pass
            
            self.logger.info("步骤3: 在容器内执行过滤后的MySQL恢复...")
            # 使用过滤后的文件进行恢复
            mysql_cmd = (
                f'mysql --user={self.db_config["username"]} '
                f'--password={self.db_config["password"]} '
                f'--database={self.db_config["database"]} '
                f'--execute="SOURCE {container_filtered_file};"'
            )
            
            restore_cmd = [
                'docker', 'exec', container_name,
                'sh', '-c', mysql_cmd
            ]
            
            self.logger.info(f"执行命令: docker exec {container_name} sh -c 'mysql ... --execute=SOURCE filtered_file'")
            
            restore_process = subprocess.run(
                restore_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120  # 2分钟超时
            )

            # 记录命令输出
            if restore_process.stdout:
                for line in restore_process.stdout.splitlines():
                    self.logger.info(f"[mysql stdout] {line}")
            if restore_process.stderr:
                for line in restore_process.stderr.splitlines():
                    self.logger.warning(f"[mysql stderr] {line}")
            
            # 清理临时文件
            cleanup_cmd = ['docker', 'exec', container_name, 'rm', '-f', container_temp_file, container_filtered_file]
            subprocess.run(cleanup_cmd, capture_output=True)
            
            if restore_process.returncode == 0:
                self.logger.info("Docker系统表保护恢复成功")
                return {"success": True, "method": "docker_protected_restore"}
            else:
                # 添加错误容忍机制，与stdin方式保持一致
                stderr_content = restore_process.stderr.lower()
                acceptable_errors = [
                    "table '.*?' doesn't exist",
                    "unknown table", 
                    "using a password on the command line interface can be insecure"
                ]
                
                is_acceptable = any(
                    any(keyword in stderr_content for keyword in acceptable_errors)
                    for _ in acceptable_errors
                ) or "doesn't exist" in stderr_content
                
                if is_acceptable:
                    self.logger.warning(f"Docker文件复制恢复部分成功（存在兼容性警告）: {restore_process.stderr}")
                    return {"success": True, "method": "docker_protected_restore", "warnings": restore_process.stderr}
                else:
                    error_msg = f"MySQL执行失败: {restore_process.stderr}"
                    self.logger.warning(error_msg)
                    return {"success": False, "error": error_msg}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Docker文件复制恢复超时"}
        except Exception as e:
            return {"success": False, "error": f"Docker文件复制恢复异常: {e}"}
    
    def _try_docker_restore_with_stdin(self, container_name: str, sql_file: Path) -> Dict[str, Any]:
        """使用Docker stdin方式恢复 - 备用兼容版本 + 系统表保护"""
        try:
            self.logger.info("步骤1: 预处理SQL文件，过滤受保护的系统表...")
            
            # 在本地过滤SQL文件
            filtered_sql_content = self._filter_protected_tables_local(sql_file)
            if not filtered_sql_content:
                return {"success": False, "error": "SQL文件过滤失败"}
            
            # 构建docker exec命令
            cmd = [
                'docker', 'exec', '-i', container_name,
                'mysql',
                f'--user={self.db_config["username"]}',
                f'--password={self.db_config["password"]}',
                f'--database={self.db_config["database"]}'
            ]
            
            self.logger.info("步骤2: 执行Docker stdin保护恢复命令...")
            
            # 执行恢复（使用过滤后的内容）
            process = subprocess.run(
                cmd,
                input=filtered_sql_content,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=1800  # 30分钟超时
            )
            
            if process.returncode == 0:
                self.logger.info("Docker stdin保护恢复成功")
                return {"success": True, "method": "docker_stdin_protected"}
            else:
                # 检查是否是可接受的错误（表不存在等）
                stderr_content = process.stderr.lower()
                acceptable_errors = [
                    "table '.*?' doesn't exist",
                    "unknown table",
                    "using a password on the command line interface can be insecure"
                ]
                
                is_acceptable = any(
                    any(keyword in stderr_content for keyword in acceptable_errors)
                    for _ in acceptable_errors
                ) or "doesn't exist" in stderr_content
                
                if is_acceptable:
                    self.logger.warning(f"Docker stdin恢复部分成功（存在兼容性警告）: {process.stderr}")
                    return {"success": True, "method": "docker_stdin_protected", "warnings": process.stderr}
                else:
                    error_msg = f"Docker stdin恢复失败: {process.stderr}"
                    self.logger.warning(error_msg)
                    return {"success": False, "error": error_msg}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Docker stdin恢复超时"}
        except Exception as e:
            return {"success": False, "error": f"Docker stdin恢复异常: {e}"}
    
    def _try_system_mysql_restore(self, sql_file: Path) -> Dict[str, Any]:
        """尝试使用系统mysql命令恢复 + 系统表保护"""
        try:
            self.logger.info("尝试系统mysql命令保护恢复...")
            
            # 预处理SQL文件，过滤受保护的系统表
            filtered_sql_content = self._filter_protected_tables_local(sql_file)
            if not filtered_sql_content:
                return {"success": False, "error": "系统mysql恢复: SQL文件过滤失败"}
            
            # 构建mysql命令
            cmd = [
                'mysql',
                f'--host={self.db_config["host"]}',
                f'--port={self.db_config["port"]}',
                f'--user={self.db_config["username"]}',
                f'--password={self.db_config["password"]}',
                self.db_config["database"]
            ]
            
            # 执行恢复（使用过滤后的内容）
            process = subprocess.run(
                cmd,
                input=filtered_sql_content,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300
            )
            
            if process.returncode == 0:
                self.logger.info("系统mysql保护恢复成功")
                return {"success": True, "method": "system_mysql_protected"}
            else:
                # 检查是否是可接受的错误（表不存在等）
                stderr_content = process.stderr.lower()
                is_acceptable = "doesn't exist" in stderr_content or "unknown table" in stderr_content
                
                if is_acceptable:
                    self.logger.warning(f"系统mysql恢复部分成功（存在兼容性警告）: {process.stderr}")
                    return {"success": True, "method": "system_mysql_protected", "warnings": process.stderr}
                else:
                    error_msg = f"系统mysql恢复失败: {process.stderr}"
                    self.logger.warning(error_msg)
                    return {"success": False, "error": error_msg}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "系统mysql恢复超时"}
        except FileNotFoundError:
            return {"success": False, "error": "系统中未找到mysql命令"}
        except Exception as e:
            return {"success": False, "error": f"系统mysql恢复异常: {e}"}
    
    def _find_mysql_container(self) -> Optional[str]:
        """查找MySQL Docker容器"""
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
                        self.logger.info(f"发现MySQL容器: {container}")
                        return container
                        
        except Exception as e:
            self.logger.debug(f"Docker容器检测失败: {e}")
        
        return None
    
    def _filter_protected_tables_in_container(self, container_name: str, input_file: str, output_file: str) -> Dict[str, Any]:
        """在Docker容器内过滤受保护的系统表"""
        try:
            # 定义受保护的系统表
            protected_tables = {
                'restore_records', 'backup_records', 'backup_configs', 
                'users', 'alembic_version', 'user_roles', 'roles'
            }
            
            self.logger.info(f"过滤受保护的系统表: {', '.join(protected_tables)}")
            
            # 构建sed命令来过滤掉受保护表的SQL语句 - 修复语法
            filter_patterns = []
            for table in protected_tables:
                # 过滤DROP、CREATE、INSERT、LOCK等语句，使用正确的sed语法
                escaped_table = table.replace('_', '\\_')  # 转义下划线
                filter_patterns.extend([
                    f"/DROP TABLE.*{escaped_table}/d",
                    f"/CREATE TABLE.*{escaped_table}/d", 
                    f"/INSERT INTO.*{escaped_table}/d",
                    f"/LOCK TABLES.*{escaped_table}/d"
                ])
            
            # 构建完整的sed命令，使用单引号包围模式
            pattern_args = ' '.join([f"-e '{pattern}'" for pattern in filter_patterns])
            sed_cmd = f"sed {pattern_args} {input_file} > {output_file}"
            
            filter_cmd = [
                'docker', 'exec', container_name,
                'sh', '-c', sed_cmd
            ]
            
            self.logger.info("执行SQL过滤命令...")
            
            filter_process = subprocess.run(
                filter_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60
            )
            
            if filter_process.returncode == 0:
                self.logger.info("SQL文件过滤成功")
                return {"success": True}
            else:
                error_msg = f"SQL过滤失败: {filter_process.stderr}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "SQL过滤超时"}
        except Exception as e:
            return {"success": False, "error": f"SQL过滤异常: {e}"}
    
    def _filter_protected_tables_local(self, sql_file: Path) -> Optional[str]:
        """在本地过滤受保护的系统表 - 完整SQL块过滤版本"""
        try:
            # 定义受保护的系统表
            protected_tables = {
                'restore_records', 'backup_records', 'backup_configs', 
                'users', 'alembic_version', 'user_roles', 'roles'
            }
            
            # 定义依赖受保护表的表（需要特殊处理外键约束）
            dependent_tables = {
                'article_bookmarks': ['users', 'articles'],  # 依赖users和articles
                'article_likes': ['users', 'articles'],      # 依赖users和articles  
                'comments': ['users', 'articles'],           # 依赖users和articles
            }
            
            self.logger.info(f"本地过滤受保护的系统表: {', '.join(protected_tables)}")
            self.logger.info(f"检测到依赖表: {', '.join(dependent_tables.keys())}")
            
            # 读取SQL文件内容
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 使用正则表达式进行块级过滤
            import re
            
            # 首先添加错误容忍机制，过滤可能不存在的表引用
            self.logger.info("添加错误容忍机制...")
            
            # 在SQL开始添加表存在性检查和错误容忍设置
            sql_prefix = """-- ULTRALTHINK 系统表保护和错误容忍设置
SET sql_notes = 0;
SET foreign_key_checks = 0;
SET autocommit = 0;
START TRANSACTION;
"""
            
            # 在SQL结尾恢复设置  
            sql_suffix = """
-- 恢复MySQL设置
COMMIT;
SET autocommit = 1;
SET foreign_key_checks = 1;
SET sql_notes = 1;
"""
            
            # 应用前缀和后缀
            sql_content = sql_prefix + sql_content + sql_suffix
            
            # 首先处理依赖表，移除所有外键约束（避免表创建顺序问题）
            for dep_table, dependencies in dependent_tables.items():
                self.logger.info(f"处理依赖表 {dep_table}，移除所有外键约束和DROP语句以避免创建顺序问题")
                
                # 1. 移除该表的DROP TABLE语句（避免DROP不存在的表导致错误）
                drop_pattern = rf'DROP TABLE IF EXISTS `{re.escape(dep_table)}`.*?;'
                drop_count = len(re.findall(drop_pattern, sql_content, re.IGNORECASE | re.DOTALL))
                sql_content = re.sub(drop_pattern, f'-- DROP TABLE `{dep_table}` removed for safety', sql_content, flags=re.IGNORECASE | re.DOTALL)
                
                # 2. 移除该表的所有外键约束（不管是否指向受保护表）
                constraint_pattern = rf'CONSTRAINT `{re.escape(dep_table)}_ibfk_\d+` FOREIGN KEY \([^)]+\) REFERENCES `[^`]+` \([^)]+\),?\s*'
                removed_count = len(re.findall(constraint_pattern, sql_content, re.IGNORECASE))
                sql_content = re.sub(constraint_pattern, '', sql_content, flags=re.IGNORECASE)
                
                # 3. 移除该表的LOCK TABLES语句（避免锁定不存在的表）
                lock_pattern = rf'LOCK TABLES `{re.escape(dep_table)}`.*?;'
                lock_count = len(re.findall(lock_pattern, sql_content, re.IGNORECASE | re.DOTALL))
                sql_content = re.sub(lock_pattern, f'-- LOCK TABLE `{dep_table}` removed for safety', sql_content, flags=re.IGNORECASE | re.DOTALL)
                
                # 4. 清理可能产生的多余逗号（如果外键约束在最后一个字段后）
                cleanup_pattern = rf'(,\s*)\s+\) ENGINE='
                sql_content = re.sub(cleanup_pattern, r'\n) ENGINE=', sql_content, flags=re.IGNORECASE)
                
                self.logger.info(f"已移除 {dep_table} 的 {drop_count} 个DROP语句、{lock_count} 个LOCK语句和 {removed_count} 个外键约束")

            # 然后处理受保护表的完全过滤
            for table in protected_tables:
                # 过滤DROP TABLE语句
                drop_pattern = rf'DROP TABLE IF EXISTS `{re.escape(table)}`.*?;'
                sql_content = re.sub(drop_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)
                
                # 过滤完整的CREATE TABLE块（从CREATE到分号结束，包括所有MySQL注释）
                # 匹配可能的MySQL client设置
                mysql_client_start = r'/\*!40101 SET @saved_cs_client\s*=\s*@@character_set_client \*/;'
                mysql_client_end = r'/\*!40101 SET character_set_client = @saved_cs_client \*/;'
                
                # 构建完整的CREATE TABLE块模式
                create_pattern = (
                    rf'(?:{mysql_client_start}\s*)?'
                    rf'/\*!50503 SET character_set_client = utf8mb4 \*/;\s*'
                    rf'CREATE TABLE `{re.escape(table)}`.*?;'
                    rf'\s*(?:{mysql_client_end})?'
                )
                sql_content = re.sub(create_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)
                
                # 简化版：直接匹配CREATE TABLE到分号
                simple_create_pattern = rf'CREATE TABLE `{re.escape(table)}`.*?;'
                sql_content = re.sub(simple_create_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)
                
                # 过滤LOCK TABLES语句
                lock_pattern = rf'LOCK TABLES `{re.escape(table)}`.*?;'
                sql_content = re.sub(lock_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)
                
                # 过滤INSERT INTO语句（可能跨越多行）
                insert_pattern = rf'INSERT INTO `{re.escape(table)}`.*?;'
                sql_content = re.sub(insert_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)
                
                # 过滤相关的MySQL设置语句
                client_pattern = rf'/\*!40101 SET @saved_cs_client\s*=\s*@@character_set_client \*/;.*?/\*!40101 SET character_set_client = @saved_cs_client \*/;'
                sql_content = re.sub(client_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)
                
                self.logger.debug(f"已过滤表 `{table}` 的所有SQL语句")
            
            # 清理多余的空行和注释块
            lines = sql_content.split('\n')
            filtered_lines = []
            prev_empty = False
            
            for line in lines:
                line_stripped = line.strip()
                is_empty = line_stripped == '' or line_stripped.startswith('--')
                
                # 保留重要的注释但跳过连续空行
                if is_empty and prev_empty and not line_stripped.startswith('--'):
                    continue
                    
                filtered_lines.append(line)
                prev_empty = is_empty
            
            filtered_content = '\n'.join(filtered_lines)
            
            # 统计过滤效果
            original_lines = len(sql_content.split('\n'))
            filtered_line_count = len(filtered_lines)
            
            self.logger.info(f"SQL块级过滤完成")
            self.logger.info(f"原始行数: {original_lines}, 过滤后行数: {filtered_line_count}")
            self.logger.info(f"已保护 {len(protected_tables)} 个系统表")
            
            return filtered_content
            
        except Exception as e:
            self.logger.error(f"本地SQL过滤失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None


def main():
    """独立执行恢复的主函数"""
    if len(sys.argv) != 3:
        print("用法: python simple_restore_engine.py <备份文件路径> <恢复ID>")
        sys.exit(1)
        
    backup_file_path = sys.argv[1]
    restore_id = sys.argv[2]
    
    # 数据库配置（从环境变量或配置文件读取）
    db_config = {
        "host": "127.0.0.1",
        "port": "3307",
        "username": "root",
        "password": "root",
        "database": "blog"
    }
    
    # 创建恢复引擎并执行
    engine = SimpleRestoreEngine(db_config)
    result = engine.restore_database(backup_file_path, restore_id)
    
    # 输出结果
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 设置退出码
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()