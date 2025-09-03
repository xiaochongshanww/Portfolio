#!/usr/bin/env python3
"""
物理备份引擎 - 全新架构
基于Docker Volume的MySQL物理备份，彻底解决SQL依赖问题
"""

import os
import sys
import subprocess
import tempfile
import tarfile
import json
import time
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
import psutil


class PhysicalBackupEngine:
    """物理备份引擎 - 无SQL解析，无依赖问题"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = self._setup_logger()
        self.container_name = config.get('mysql_container', 'blog-mysql')
        self.volume_name = config.get('mysql_volume', 'mysqldata')
        
        # 支持自动检测卷名
        if self.volume_name == 'auto-detect':
            self.logger.info("启用MySQL卷自动检测")
            detected_volume = self._get_container_volume()
            if detected_volume:
                self.volume_name = detected_volume
                self.logger.info(f"自动检测到MySQL卷: {self.volume_name}")
            else:
                self.logger.warning("自动检测卷失败，使用默认值 mysqldata")
                self.volume_name = 'mysqldata'
        
        self.backup_root = Path(config.get('backup_root', './backups/physical'))
        self.backup_root.mkdir(parents=True, exist_ok=True)
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志系统"""
        logger = logging.getLogger('PhysicalBackupEngine')
        logger.setLevel(logging.DEBUG)
        
        log_file_path = Path(__file__).parent.parent.parent / 'logs' / 'physical_backup' / 'physical_backup.log'
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file_path),
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8',
            utc=True
        )
        formatter = logging.Formatter('%(asctime)s [PHYSICAL] %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 控制台输出
        if not logger.handlers or len([h for h in logger.handlers if isinstance(h, logging.StreamHandler)]) == 0:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
        return logger

    def create_backup(self, backup_id: str = None) -> Dict[str, Any]:
        """创建物理备份"""
        # 记录开始时间
        start_time = time.time()
        start_datetime = datetime.now(timezone.utc)
        
        if not backup_id:
            backup_id = f"physical_{start_datetime.strftime('%Y%m%d_%H%M%S')}"
            
        self.logger.info(f"开始创建物理备份: {backup_id}")
        
        try:
            # 检查Docker环境
            if not self._check_docker_environment():
                return {"success": False, "error": "Docker环境检查失败"}
                
            # 创建备份目录
            backup_dir = self.backup_root / backup_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 获取数据库状态信息
            db_info_start = time.time()
            db_info = self._get_database_info()
            db_info_duration = time.time() - db_info_start
            
            # 执行物理备份
            backup_start = time.time()
            backup_result = self._perform_physical_backup(backup_dir)
            backup_duration = time.time() - backup_start
            
            if not backup_result['success']:
                return backup_result
                
            # 计算备份文件大小
            size_calc_start = time.time()
            raw_backup_size = self._calculate_backup_size(backup_dir)
            size_calc_duration = time.time() - size_calc_start
            
            # 创建压缩包（可选）
            compressed_size = None
            compression_duration = 0
            archive_path = None
            
            if self.config.get('compress_backup', True):
                compress_start = time.time()
                archive_path = self._create_compressed_archive(backup_dir, backup_id)
                compression_duration = time.time() - compress_start
                
                # 获取压缩文件大小
                if archive_path and archive_path.exists():
                    compressed_size = archive_path.stat().st_size
            
            # 计算总耗时
            end_time = time.time()
            total_duration = end_time - start_time
            
            # 创建详细的备份元数据
            metadata = {
                "backup_id": backup_id,
                "backup_type": "physical",
                "created_at": start_datetime.isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "database_info": db_info,
                
                # 文件大小信息
                "backup_size": raw_backup_size,
                "compressed_size": compressed_size,
                "compression_ratio": round(compressed_size / raw_backup_size, 3) if compressed_size and raw_backup_size > 0 else None,
                
                # 时间统计信息（秒）
                "timing": {
                    "total_duration": round(total_duration, 3),
                    "database_info_duration": round(db_info_duration, 3),
                    "backup_duration": round(backup_duration, 3),
                    "size_calculation_duration": round(size_calc_duration, 3),
                    "compression_duration": round(compression_duration, 3)
                },
                
                # 性能统计
                "performance": {
                    "backup_speed_mbps": round((raw_backup_size / 1024 / 1024) / backup_duration, 2) if backup_duration > 0 else 0,
                    "total_speed_mbps": round((raw_backup_size / 1024 / 1024) / total_duration, 2) if total_duration > 0 else 0
                },
                
                "mysql_version": db_info.get('version'),
                "container_name": self.container_name,
                "volume_name": self.volume_name,
                "compressed": compressed_size is not None,
                "archive_path": str(archive_path) if archive_path else None
            }
            
            # 保存元数据
            metadata_file = backup_dir / "backup_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
            # 记录详细日志
            self.logger.info(f"物理备份创建成功: {backup_id}")
            self.logger.info(f"备份大小: {raw_backup_size:,} bytes ({raw_backup_size/1024/1024:.1f} MB)")
            if compressed_size:
                self.logger.info(f"压缩后大小: {compressed_size:,} bytes ({compressed_size/1024/1024:.1f} MB)")
                self.logger.info(f"压缩比: {metadata['compression_ratio']:.1%}")
            self.logger.info(f"总耗时: {total_duration:.2f}秒, 备份速度: {metadata['performance']['total_speed_mbps']:.1f} MB/s")
            
            return {
                "success": True,
                "backup_id": backup_id,
                "metadata": metadata,
                "message": "物理备份创建成功",
                
                # 前端需要的关键信息
                "summary": {
                    "backup_id": backup_id,
                    "duration": total_duration,
                    "duration_text": self._format_duration(total_duration),
                    "backup_size": compressed_size if compressed_size else raw_backup_size,
                    "backup_size_text": self._format_file_size(compressed_size if compressed_size else raw_backup_size),
                    "raw_size": raw_backup_size,
                    "compressed_size": compressed_size,
                    "compression_ratio": metadata.get('compression_ratio'),
                    "backup_speed": metadata['performance']['total_speed_mbps']
                }
            }
            
        except Exception as e:
            error_msg = f"物理备份创建失败: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _check_docker_environment(self) -> bool:
        """检查Docker环境"""
        try:
            # 检查Docker是否运行
            result = subprocess.run(['docker', 'version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.logger.error("Docker未运行或无法访问")
                return False
                
            # 检查MySQL容器是否存在
            result = subprocess.run(['docker', 'ps', '--filter', f'name={self.container_name}', '--format', '{{.Names}}'],
                                  capture_output=True, text=True, timeout=10)
            if self.container_name not in result.stdout:
                self.logger.error(f"MySQL容器 {self.container_name} 未找到")
                return False
                
            # 动态获取容器实际使用的卷
            actual_volume = self._get_container_volume()
            if actual_volume and actual_volume != self.volume_name:
                self.logger.info(f"检测到实际卷名: {actual_volume}，更新配置")
                self.volume_name = actual_volume
                
            # 检查Docker volume是否存在
            result = subprocess.run(['docker', 'volume', 'ls', '--filter', f'name={self.volume_name}', '--format', '{{.Name}}'],
                                  capture_output=True, text=True, timeout=10)
            if self.volume_name not in result.stdout:
                self.logger.error(f"Docker volume {self.volume_name} 未找到")
                return False
                
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("Docker命令执行超时")
            return False
        except Exception as e:
            self.logger.error(f"Docker环境检查异常: {e}")
            return False
    
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

    def _get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        try:
            # 获取MySQL版本
            version_cmd = ['docker', 'exec', self.container_name, 
                          'mysql', '--version']
            version_result = subprocess.run(version_cmd, capture_output=True, text=True)
            
            # 获取数据库大小
            size_cmd = ['docker', 'exec', self.container_name,
                       'du', '-sh', '/var/lib/mysql']
            size_result = subprocess.run(size_cmd, capture_output=True, text=True)
            
            return {
                "version": version_result.stdout.strip() if version_result.returncode == 0 else "unknown",
                "data_size": size_result.stdout.strip() if size_result.returncode == 0 else "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.warning(f"获取数据库信息失败: {e}")
            return {"version": "unknown", "data_size": "unknown"}

    def _perform_physical_backup(self, backup_dir: Path) -> Dict[str, Any]:
        """执行物理备份"""
        try:
            self.logger.info("开始执行物理备份...")
            
            # 方法1: 热备份（推荐）- 使用tar直接备份Docker volume
            if self.config.get('hot_backup', True):
                return self._hot_backup_via_docker(backup_dir)
            else:
                # 方法2: 冷备份 - 需要短暂停止写入
                return self._cold_backup_with_lock(backup_dir)
                
        except Exception as e:
            return {"success": False, "error": f"物理备份执行失败: {e}"}

    def _hot_backup_via_docker(self, backup_dir: Path) -> Dict[str, Any]:
        """通过Docker执行热备份"""
        try:
            self.logger.info("执行Docker volume热备份...")
            
            # 使用临时容器备份Docker volume
            backup_cmd = [
                'docker', 'run', '--rm',
                '-v', f'{self.volume_name}:/source:ro',  # 只读挂载源volume
                '-v', f'{backup_dir.absolute()}:/backup',  # 挂载备份目录
                'alpine:latest',
                'sh', '-c', 
                'cd /source && tar czf /backup/mysql_data.tar.gz .'
            ]
            
            self.logger.info(f"执行备份命令: {' '.join(backup_cmd)}")
            
            result = subprocess.run(
                backup_cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30分钟超时
            )
            
            if result.returncode == 0:
                self.logger.info("Docker volume热备份成功")
                return {"success": True, "method": "docker_hot_backup"}
            else:
                error_msg = f"Docker volume备份失败: {result.stderr}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Docker volume备份超时"}
        except Exception as e:
            return {"success": False, "error": f"Docker volume备份异常: {e}"}

    def _cold_backup_with_lock(self, backup_dir: Path) -> Dict[str, Any]:
        """冷备份（带锁）"""
        try:
            self.logger.info("执行带锁的冷备份...")
            
            # 1. 刷新并锁定表
            flush_cmd = ['docker', 'exec', self.container_name,
                        'mysql', '-u', 'root', '-proot', '-e', 
                        'FLUSH TABLES WITH READ LOCK; SYSTEM sleep 3;']
            
            # 2. 在另一个进程中执行备份
            backup_cmd = [
                'docker', 'run', '--rm',
                '-v', f'{self.volume_name}:/source:ro',
                '-v', f'{backup_dir.absolute()}:/backup',
                'alpine:latest',
                'sh', '-c', 
                'cd /source && tar czf /backup/mysql_data.tar.gz .'
            ]
            
            # 3. 解锁表
            unlock_cmd = ['docker', 'exec', self.container_name,
                         'mysql', '-u', 'root', '-proot', '-e', 'UNLOCK TABLES;']
            
            # 执行锁定
            flush_result = subprocess.run(flush_cmd, capture_output=True, text=True)
            if flush_result.returncode != 0:
                self.logger.warning(f"表锁定失败，继续热备份: {flush_result.stderr}")
                return self._hot_backup_via_docker(backup_dir)
            
            try:
                # 执行备份
                backup_result = subprocess.run(backup_cmd, capture_output=True, text=True, timeout=300)
                
                if backup_result.returncode == 0:
                    self.logger.info("冷备份成功")
                    return {"success": True, "method": "cold_backup_with_lock"}
                else:
                    self.logger.error(f"冷备份失败: {backup_result.stderr}")
                    return {"success": False, "error": backup_result.stderr}
                    
            finally:
                # 确保解锁
                unlock_result = subprocess.run(unlock_cmd, capture_output=True, text=True)
                if unlock_result.returncode != 0:
                    self.logger.warning(f"表解锁失败: {unlock_result.stderr}")
                    
        except Exception as e:
            return {"success": False, "error": f"冷备份异常: {e}"}

    def _calculate_backup_size(self, backup_dir: Path) -> int:
        """计算备份大小"""
        try:
            total_size = 0
            for file_path in backup_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except Exception as e:
            self.logger.warning(f"计算备份大小失败: {e}")
            return 0

    def _create_compressed_archive(self, backup_dir: Path, backup_id: str) -> Path:
        """创建压缩归档"""
        archive_path = self.backup_root / f"{backup_id}.tar.gz"
        
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(backup_dir, arcname=backup_id)
            
        self.logger.info(f"创建压缩归档: {archive_path}")
        return archive_path

    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有物理备份"""
        backups = []
        
        try:
            for backup_dir in self.backup_root.iterdir():
                if backup_dir.is_dir():
                    metadata_file = backup_dir / "backup_metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                                backups.append(metadata)
                        except Exception as e:
                            self.logger.warning(f"读取备份元数据失败 {backup_dir}: {e}")
                            
            # 按创建时间排序
            backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return backups
            
        except Exception as e:
            self.logger.error(f"列出备份失败: {e}")
            return []

    def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """获取特定备份的详细信息"""
        try:
            backup_dir = self.backup_root / backup_id
            metadata_file = backup_dir / "backup_metadata.json"
            
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"获取备份信息失败: {e}")
            return None

    def delete_backup(self, backup_id: str) -> Dict[str, Any]:
        """删除物理备份"""
        try:
            backup_dir = self.backup_root / backup_id
            archive_path = self.backup_root / f"{backup_id}.tar.gz"
            
            # 删除备份目录
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
                self.logger.info(f"删除备份目录: {backup_dir}")
                
            # 删除压缩文件
            if archive_path.exists():
                archive_path.unlink()
                self.logger.info(f"删除备份归档: {archive_path}")
                
            return {"success": True, "message": f"备份 {backup_id} 删除成功"}
            
        except Exception as e:
            error_msg = f"删除备份失败: {e}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _format_duration(self, seconds: float) -> str:
        """格式化持续时间为人类可读格式"""
        if seconds < 1:
            return f"{seconds * 1000:.0f} 毫秒"
        elif seconds < 60:
            return f"{seconds:.1f} 秒"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes:.0f} 分 {remaining_seconds:.0f} 秒"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            return f"{hours:.0f} 小时 {remaining_minutes:.0f} 分"

    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小为人类可读格式"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        if i == 0:
            return f"{int(size)} {size_names[i]}"
        else:
            return f"{size:.1f} {size_names[i]}"

    def get_storage_statistics(self) -> Dict[str, Any]:
        """获取存储空间统计信息"""
        try:
            backups = self.list_backups()
            
            # 基本统计
            total_backups = len(backups)
            total_raw_size = 0
            total_compressed_size = 0
            total_archive_size = 0
            
            # 分类统计
            compressed_count = 0
            uncompressed_count = 0
            
            # 时间统计
            from collections import defaultdict
            monthly_size = defaultdict(int)
            daily_size = defaultdict(int)
            
            # 大小分布统计
            size_ranges = {
                'tiny': 0,      # < 10MB
                'small': 0,     # 10MB - 100MB
                'medium': 0,    # 100MB - 1GB
                'large': 0,     # 1GB - 10GB
                'huge': 0       # > 10GB
            }
            
            for backup in backups:
                raw_size = backup.get('backup_size', 0)
                compressed_size = backup.get('compressed_size', 0)
                
                total_raw_size += raw_size
                
                if compressed_size:
                    total_compressed_size += compressed_size
                    compressed_count += 1
                    final_size = compressed_size
                else:
                    uncompressed_count += 1
                    final_size = raw_size
                
                # 计算归档文件实际大小
                backup_id = backup.get('backup_id')
                archive_path = self.backup_root / f"{backup_id}.tar.gz"
                if archive_path.exists():
                    archive_size = archive_path.stat().st_size
                    total_archive_size += archive_size
                else:
                    # 如果没有归档文件，使用目录大小
                    backup_dir = self.backup_root / backup_id
                    if backup_dir.exists():
                        dir_size = self._calculate_backup_size(backup_dir)
                        total_archive_size += dir_size
                
                # 按时间分组
                created_at = backup.get('created_at', '')
                if created_at:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        monthly_key = dt.strftime('%Y-%m')
                        daily_key = dt.strftime('%Y-%m-%d')
                        monthly_size[monthly_key] += final_size
                        daily_size[daily_key] += final_size
                    except:
                        pass
                
                # 大小分布
                mb_size = final_size / 1024 / 1024
                if mb_size < 10:
                    size_ranges['tiny'] += 1
                elif mb_size < 100:
                    size_ranges['small'] += 1
                elif mb_size < 1024:
                    size_ranges['medium'] += 1
                elif mb_size < 10240:
                    size_ranges['large'] += 1
                else:
                    size_ranges['huge'] += 1
            
            # 计算压缩效率
            overall_compression_ratio = 0
            if total_raw_size > 0 and total_compressed_size > 0:
                overall_compression_ratio = total_compressed_size / total_raw_size
            
            # 存储效率分析
            average_backup_size = total_archive_size // total_backups if total_backups > 0 else 0
            
            # 获取备份目录总大小（仅包括实际备份文件）
            backup_root_size = self._calculate_actual_backup_storage_size()
            
            statistics = {
                # 基本统计
                "total_backups": total_backups,
                "total_storage_used": backup_root_size,
                "total_storage_used_text": self._format_file_size(backup_root_size),
                
                # 大小统计
                "total_raw_size": total_raw_size,
                "total_raw_size_text": self._format_file_size(total_raw_size),
                "total_compressed_size": total_compressed_size,
                "total_compressed_size_text": self._format_file_size(total_compressed_size),
                "total_archive_size": total_archive_size,
                "total_archive_size_text": self._format_file_size(total_archive_size),
                
                # 压缩统计
                "compressed_backups": compressed_count,
                "uncompressed_backups": uncompressed_count,
                "overall_compression_ratio": round(overall_compression_ratio, 3),
                "compression_savings": total_raw_size - total_compressed_size,
                "compression_savings_text": self._format_file_size(total_raw_size - total_compressed_size),
                
                # 平均值
                "average_backup_size": average_backup_size,
                "average_backup_size_text": self._format_file_size(average_backup_size),
                "average_raw_size": total_raw_size // total_backups if total_backups > 0 else 0,
                
                # 大小分布
                "size_distribution": size_ranges,
                
                # 时间分布
                "monthly_storage": dict(monthly_size),
                "daily_storage": dict(daily_size),
                "monthly_storage_formatted": {
                    k: self._format_file_size(v) for k, v in monthly_size.items()
                },
                
                # 存储效率
                "storage_efficiency": {
                    "files_vs_raw_ratio": round(backup_root_size / total_raw_size, 3) if total_raw_size > 0 else 0,
                    "compression_effectiveness": round((total_raw_size - total_compressed_size) / total_raw_size * 100, 1) if total_raw_size > 0 else 0
                },
                
                # 统计时间
                "calculated_at": datetime.now(timezone.utc).isoformat()
            }
            
            self.logger.info(f"存储统计完成 - 总备份: {total_backups}, 总存储: {self._format_file_size(backup_root_size)}")
            return statistics
            
        except Exception as e:
            self.logger.error(f"获取存储统计失败: {e}")
            return {}

    def _get_directory_size(self, directory: Path) -> int:
        """递归计算目录总大小"""
        try:
            total_size = 0
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except Exception as e:
            self.logger.warning(f"计算目录大小失败: {e}")
            return 0
    
    def _calculate_actual_backup_storage_size(self) -> int:
        """计算实际备份存储大小，排除恢复临时目录"""
        try:
            total_size = 0
            excluded_dirs = {'pre_restore_backup', 'temp', 'tmp', '.temp'}
            
            for item in self.backup_root.iterdir():
                # 跳过恢复相关的临时目录
                if item.name in excluded_dirs:
                    self.logger.debug(f"跳过非备份目录: {item.name}")
                    continue
                
                if item.is_file():
                    # 直接在备份根目录的文件（如 .tar.gz 归档文件）
                    total_size += item.stat().st_size
                elif item.is_dir() and item.name.startswith('physical_'):
                    # 只包含以 physical_ 开头的备份目录
                    dir_size = self._get_directory_size(item)
                    total_size += dir_size
                    self.logger.debug(f"包含备份目录 {item.name}: {self._format_file_size(dir_size)}")
            
            self.logger.debug(f"实际备份存储大小: {self._format_file_size(total_size)}")
            return total_size
        except Exception as e:
            self.logger.error(f"计算实际备份存储大小失败: {e}")
            # 降级到原始方法
            return self._get_directory_size(self.backup_root)


def main():
    """独立执行的主函数"""
    if len(sys.argv) < 2:
        print("用法: python physical_backup_engine.py <create|list|info|delete> [backup_id]")
        sys.exit(1)
        
    command = sys.argv[1]
    
    # 配置
    config = {
        "mysql_container": "blog-mysql",
        "mysql_volume": "auto-detect", 
        "backup_root": "./backups/physical",
        "hot_backup": True,
        "compress_backup": True
    }
    
    engine = PhysicalBackupEngine(config)
    
    if command == "create":
        backup_id = sys.argv[2] if len(sys.argv) > 2 else None
        result = engine.create_backup(backup_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "list":
        backups = engine.list_backups()
        print(json.dumps(backups, ensure_ascii=False, indent=2))
        
    elif command == "info":
        if len(sys.argv) < 3:
            print("错误: 需要提供backup_id")
            sys.exit(1)
        backup_id = sys.argv[2]
        info = engine.get_backup_info(backup_id)
        print(json.dumps(info, ensure_ascii=False, indent=2))
        
    elif command == "delete":
        if len(sys.argv) < 3:
            print("错误: 需要提供backup_id")
            sys.exit(1)
        backup_id = sys.argv[2]
        result = engine.delete_backup(backup_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()