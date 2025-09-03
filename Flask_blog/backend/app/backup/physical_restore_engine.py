#!/usr/bin/env python3
"""
物理恢复引擎 - 彻底解决SQL依赖问题
基于Docker Volume的MySQL物理恢复，无需处理任何SQL语法
"""

import os
import sys
import subprocess
import json
import time
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler


class PhysicalRestoreEngine:
    """物理恢复引擎 - 直接操作文件系统，避免所有SQL问题"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = self._setup_logger()
        self.container_name = config.get('mysql_container', 'blog-mysql')
        # volume_name 将从备份元数据中动态获取，而不是配置中硬编码
        self.volume_name = None
        self.backup_root = Path(config.get('backup_root', './backups/physical'))
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志系统"""
        logger = logging.getLogger('PhysicalRestoreEngine')
        logger.setLevel(logging.DEBUG)
        
        log_file_path = Path(__file__).parent.parent.parent / 'logs' / 'physical_restore' / 'physical_restore.log'
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file_path),
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8',
            utc=True
        )
        formatter = logging.Formatter('%(asctime)s [PHYSICAL_RESTORE] %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 控制台输出
        if not logger.handlers or len([h for h in logger.handlers if isinstance(h, logging.StreamHandler)]) == 0:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
        return logger
    
    def _get_container_volume(self) -> Optional[str]:
        """动态获取容器使用的MySQL数据卷"""
        try:
            # 检查容器的挂载信息
            result = subprocess.run([
                'docker', 'inspect', self.container_name,
                '--format', '{{json .Mounts}}'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                import json
                mounts = json.loads(result.stdout)
                for mount in mounts:
                    if mount.get('Destination') == '/var/lib/mysql' and mount.get('Type') == 'volume':
                        volume_name = mount.get('Name')
                        self.logger.info(f"检测到MySQL数据卷: {volume_name}")
                        return volume_name
            
            return None
        except Exception as e:
            self.logger.warning(f"获取容器卷信息失败: {e}")
            return None

    def restore_database(self, backup_id: str, restore_id: str = None) -> Dict[str, Any]:
        """执行物理恢复"""
        if not restore_id:
            restore_id = f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        self.logger.info(f"开始物理恢复: 备份ID={backup_id}, 恢复ID={restore_id}")
        
        try:
            # 1. 验证备份存在
            backup_info = self._validate_backup(backup_id)
            if not backup_info:
                return {"success": False, "error": f"备份 {backup_id} 不存在或无效"}
                
            # 2. 检查环境
            if not self._check_environment():
                return {"success": False, "error": "环境检查失败"}
                
            # 3. 创建数据库服务前的准备工作
            preparation_result = self._prepare_for_restore()
            if not preparation_result['success']:
                return preparation_result
                
            # 4. 执行物理恢复
            restore_result = self._perform_physical_restore(backup_id)
            if not restore_result['success']:
                return restore_result
                
            # 5. 重启数据库服务
            restart_result = self._restart_database_service()
            if not restart_result['success']:
                return restart_result
                
            # 6. 验证恢复结果
            validation_result = self._validate_restore()
            
            self.logger.info(f"物理恢复完成: {restore_id}")
            
            return {
                "success": True,
                "restore_id": restore_id,
                "backup_id": backup_id,
                "backup_info": backup_info,
                "validation": validation_result,
                "message": "数据库物理恢复成功"
            }
            
        except Exception as e:
            error_msg = f"物理恢复失败: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _validate_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """验证备份文件"""
        try:
            backup_dir = self.backup_root / backup_id
            metadata_file = backup_dir / "backup_metadata.json"
            
            # 检查元数据文件
            if not metadata_file.exists():
                self.logger.error(f"备份元数据文件不存在: {metadata_file}")
                return None
                
            # 读取元数据
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                
            # 从备份元数据中获取原始的 volume 信息
            original_volume_name = metadata.get('volume_name')
            if original_volume_name:
                self.volume_name = original_volume_name
                self.logger.info(f"从备份元数据中获取 volume: {self.volume_name}")
            else:
                self.logger.warning(f"备份元数据中缺少 volume_name 信息，将使用自动检测")
                # 降级使用自动检测
                configured_volume = self.config.get('mysql_volume', 'auto-detect')
                if configured_volume == 'auto-detect':
                    self.volume_name = self._get_container_volume()
                    if self.volume_name:
                        self.logger.info(f"自动检测到 volume: {self.volume_name}")
                    else:
                        self.logger.error("自动检测volume失败，使用默认值 mysqldata")
                        self.volume_name = 'mysqldata'
                else:
                    self.volume_name = configured_volume
                
            # 检查备份数据文件
            if metadata.get('compressed', False):
                # 检查压缩文件
                archive_path = self.backup_root / f"{backup_id}.tar.gz"
                if not archive_path.exists():
                    self.logger.error(f"压缩备份文件不存在: {archive_path}")
                    return None
            else:
                # 检查解压后的数据文件
                data_file = backup_dir / "mysql_data.tar.gz"
                if not data_file.exists():
                    self.logger.error(f"备份数据文件不存在: {data_file}")
                    return None
                    
            self.logger.info(f"备份验证成功: {backup_id}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"备份验证失败: {e}")
            return None

    def _check_environment(self) -> bool:
        """检查恢复环境"""
        try:
            # 检查Docker环境
            result = subprocess.run(['docker', 'version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.logger.error("Docker未运行")
                return False
                
            # 检查MySQL容器状态
            result = subprocess.run(['docker', 'ps', '-a', '--filter', f'name={self.container_name}', '--format', '{{.Names}} {{.Status}}'],
                                  capture_output=True, text=True, timeout=10)
            
            if self.container_name not in result.stdout:
                self.logger.error(f"MySQL容器 {self.container_name} 不存在")
                return False
                
            # 检查Docker volume
            result = subprocess.run(['docker', 'volume', 'inspect', self.volume_name],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.logger.error(f"Docker volume [{self.volume_name}] 不存在")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"环境检查失败: {e}")
            return False

    def _prepare_for_restore(self) -> Dict[str, Any]:
        """准备恢复环境"""
        try:
            self.logger.info("准备恢复环境...")
            
            # 1. 停止MySQL容器（如果正在运行）
            stop_result = self._stop_mysql_container()
            if not stop_result['success']:
                self.logger.warning(f"停止MySQL容器警告: {stop_result.get('error', '')}")
                
            # 2. 创建数据备份（安全措施）
            backup_current_result = self._backup_current_data()
            if not backup_current_result['success']:
                self.logger.warning(f"当前数据备份警告: {backup_current_result.get('error', '')}")
                
            # 3. 清空目标volume（准备恢复）
            clear_result = self._clear_mysql_volume()
            if not clear_result['success']:
                return clear_result
                
            self.logger.info("恢复环境准备完成")
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": f"准备恢复环境失败: {e}"}

    def _stop_mysql_container(self) -> Dict[str, Any]:
        """停止MySQL容器"""
        try:
            self.logger.info("停止MySQL容器...")
            
            result = subprocess.run(['docker', 'stop', self.container_name],
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.logger.info("MySQL容器停止成功")
                return {"success": True}
            else:
                # 容器可能已经停止
                self.logger.info(f"MySQL容器停止命令返回: {result.stderr}")
                return {"success": True, "warning": "容器可能已停止"}
                
        except Exception as e:
            return {"success": False, "error": f"停止MySQL容器失败: {e}"}

    def _backup_current_data(self) -> Dict[str, Any]:
        """备份当前数据（安全措施）"""
        try:
            self.logger.info("备份当前数据作为安全措施...")
            
            current_backup_dir = self.backup_root / "pre_restore_backup"
            current_backup_dir.mkdir(exist_ok=True)
            
            backup_cmd = [
                'docker', 'run', '--rm',
                '-v', f'{self.volume_name}:/source:ro',
                '-v', f'{current_backup_dir.absolute()}:/backup',
                'alpine:latest',
                'sh', '-c', 
                f'cd /source && tar czf /backup/pre_restore_{int(time.time())}.tar.gz . || echo "No data to backup"'
            ]
            
            result = subprocess.run(backup_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info("当前数据备份成功")
                return {"success": True}
            else:
                self.logger.warning(f"当前数据备份失败: {result.stderr}")
                return {"success": True, "warning": "当前数据备份失败，但继续恢复"}
                
        except Exception as e:
            return {"success": True, "warning": f"当前数据备份异常: {e}"}

    def _clear_mysql_volume(self) -> Dict[str, Any]:
        """清空MySQL volume"""
        try:
            self.logger.info("清空MySQL数据volume...")
            
            clear_cmd = [
                'docker', 'run', '--rm',
                '-v', f'{self.volume_name}:/target',
                'alpine:latest',
                'sh', '-c', 'rm -rf /target/* /target/.[!.]* 2>/dev/null || true'
            ]
            
            result = subprocess.run(clear_cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                self.logger.info("MySQL volume清空成功")
                return {"success": True}
            else:
                error_msg = f"MySQL volume清空失败: {result.stderr}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            return {"success": False, "error": f"清空MySQL volume异常: {e}"}

    def _perform_physical_restore(self, backup_id: str) -> Dict[str, Any]:
        """执行物理恢复"""
        try:
            self.logger.info(f"开始执行物理恢复: {backup_id}")
            
            backup_dir = self.backup_root / backup_id
            
            # 检查是否存在压缩归档
            archive_path = self.backup_root / f"{backup_id}.tar.gz"
            if archive_path.exists():
                # 从压缩归档恢复
                return self._restore_from_archive(archive_path, backup_id)
            else:
                # 从解压的备份目录恢复
                data_file = backup_dir / "mysql_data.tar.gz"
                if data_file.exists():
                    return self._restore_from_data_file(data_file)
                else:
                    return {"success": False, "error": "未找到有效的备份数据文件"}
                    
        except Exception as e:
            return {"success": False, "error": f"物理恢复执行失败: {e}"}

    def _restore_from_archive(self, archive_path: Path, backup_id: str) -> Dict[str, Any]:
        """从压缩归档恢复"""
        try:
            self.logger.info(f"从压缩归档恢复: {archive_path}")
            
            # 先解压归档到临时目录（Windows兼容）
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / f"restore_temp_{int(time.time())}"
            temp_dir.mkdir(exist_ok=True)
            
            try:
                # 解压归档
                extract_cmd = ['tar', 'xzf', str(archive_path), '-C', str(temp_dir)]
                extract_result = subprocess.run(extract_cmd, capture_output=True, text=True, timeout=300)
                
                if extract_result.returncode != 0:
                    return {"success": False, "error": f"解压归档失败: {extract_result.stderr}"}
                
                # 找到数据文件
                data_file = temp_dir / backup_id / "mysql_data.tar.gz"
                if not data_file.exists():
                    return {"success": False, "error": "归档中未找到数据文件"}
                    
                # 恢复数据
                return self._restore_from_data_file(data_file)
                
            finally:
                # 清理临时目录
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            return {"success": False, "error": f"从压缩归档恢复失败: {e}"}

    def _restore_from_data_file(self, data_file: Path) -> Dict[str, Any]:
        """从数据文件恢复"""
        try:
            self.logger.info(f"从数据文件恢复: {data_file}")
            
            # 将备份数据恢复到MySQL volume
            restore_cmd = [
                'docker', 'run', '--rm',
                '-v', f'{data_file.absolute()}:/backup.tar.gz:ro',
                '-v', f'{self.volume_name}:/target',
                'alpine:latest',
                'sh', '-c', 'cd /target && tar xzf /backup.tar.gz'
            ]
            
            self.logger.info(f"执行恢复命令: {' '.join(restore_cmd)}")
            
            result = subprocess.run(restore_cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                self.logger.info("数据文件恢复成功")
                return {"success": True, "method": "data_file_restore"}
            else:
                error_msg = f"数据文件恢复失败: {result.stderr}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            return {"success": False, "error": f"数据文件恢复异常: {e}"}

    def _restart_database_service(self) -> Dict[str, Any]:
        """重启数据库服务"""
        try:
            self.logger.info("重启MySQL数据库服务...")
            
            # 启动MySQL容器
            start_result = subprocess.run(['docker', 'start', self.container_name],
                                        capture_output=True, text=True, timeout=30)
            
            if start_result.returncode != 0:
                error_msg = f"启动MySQL容器失败: {start_result.stderr}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
            # 等待MySQL服务就绪
            max_wait = 60  # 最多等待60秒
            wait_interval = 2
            waited = 0
            
            while waited < max_wait:
                try:
                    # 检查MySQL是否就绪
                    check_cmd = ['docker', 'exec', self.container_name, 'mysqladmin', 'ping', '-h', 'localhost']
                    check_result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=5)
                    
                    if check_result.returncode == 0:
                        self.logger.info(f"MySQL服务就绪 (等待了 {waited} 秒)")
                        return {"success": True, "startup_time": waited}
                        
                except subprocess.TimeoutExpired:
                    pass
                    
                time.sleep(wait_interval)
                waited += wait_interval
                
            # 超时
            error_msg = f"MySQL服务启动超时 (等待了 {max_wait} 秒)"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            return {"success": False, "error": f"重启数据库服务异常: {e}"}

    def _validate_restore(self) -> Dict[str, Any]:
        """验证恢复结果"""
        try:
            self.logger.info("验证恢复结果...")
            
            validation_results = {}
            
            # 1. 检查数据库连接
            try:
                connect_cmd = ['docker', 'exec', self.container_name, 
                             'mysql', '-u', 'root', '-proot', '-e', 'SELECT 1;']
                connect_result = subprocess.run(connect_cmd, capture_output=True, text=True, timeout=10)
                validation_results['database_connection'] = connect_result.returncode == 0
            except Exception as e:
                validation_results['database_connection'] = False
                validation_results['connection_error'] = str(e)
            
            # 2. 检查表数量
            try:
                tables_cmd = ['docker', 'exec', self.container_name,
                            'mysql', '-u', 'root', '-proot', 'blog', '-e', 
                            'SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema="blog";']
                tables_result = subprocess.run(tables_cmd, capture_output=True, text=True, timeout=10)
                if tables_result.returncode == 0:
                    # 解析表数量 (简单方式)
                    output = tables_result.stdout
                    if 'table_count' in output:
                        lines = output.strip().split('\n')
                        if len(lines) >= 2:
                            validation_results['table_count'] = lines[1].strip()
                    validation_results['tables_check'] = True
                else:
                    validation_results['tables_check'] = False
            except Exception as e:
                validation_results['tables_check'] = False
                validation_results['tables_error'] = str(e)
            
            # 3. 检查数据完整性（示例）
            try:
                integrity_cmd = ['docker', 'exec', self.container_name,
                               'mysql', '-u', 'root', '-proot', 'blog', '-e',
                               'SELECT COUNT(*) FROM articles;']
                integrity_result = subprocess.run(integrity_cmd, capture_output=True, text=True, timeout=10)
                validation_results['data_integrity_check'] = integrity_result.returncode == 0
                if integrity_result.returncode == 0:
                    # 简单解析文章数量
                    output = integrity_result.stdout.strip()
                    lines = output.split('\n')
                    if len(lines) >= 2:
                        validation_results['articles_count'] = lines[1].strip()
            except Exception as e:
                validation_results['data_integrity_check'] = False
                validation_results['integrity_error'] = str(e)
                
            # 4. 整体健康状态
            validation_results['overall_health'] = (
                validation_results.get('database_connection', False) and
                validation_results.get('tables_check', False) and
                validation_results.get('data_integrity_check', False)
            )
            
            if validation_results['overall_health']:
                self.logger.info("恢复结果验证通过")
            else:
                self.logger.warning("恢复结果验证存在问题")
                
            return validation_results
            
        except Exception as e:
            self.logger.error(f"验证恢复结果失败: {e}")
            return {"validation_failed": True, "error": str(e)}


def main():
    """独立执行的主函数"""
    if len(sys.argv) != 3:
        print("用法: python physical_restore_engine.py <backup_id> <restore_id>")
        sys.exit(1)
        
    backup_id = sys.argv[1]
    restore_id = sys.argv[2]
    
    # 配置
    config = {
        "mysql_container": "blog-mysql",
        "mysql_volume": "auto-detect",
        "backup_root": "./backups/physical"
    }
    
    engine = PhysicalRestoreEngine(config)
    result = engine.restore_database(backup_id, restore_id)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()