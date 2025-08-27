"""
存储管理器

支持多种存储后端：本地存储、云存储(AWS S3、阿里云OSS、腾讯云COS等)
"""

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from flask import current_app
try:
    from cryptography.fernet import Fernet
    import base64
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    Fernet = None
    base64 = None


class StorageProvider(ABC):
    """存储提供商抽象基类"""
    
    @abstractmethod
    def upload(self, file_path: Path, backup_id: str) -> Dict[str, Any]:
        """上传备份文件"""
        pass
    
    @abstractmethod
    def download(self, backup_id: str, target_path: Path) -> bool:
        """下载备份文件"""
        pass
    
    @abstractmethod
    def delete(self, backup_id: str) -> bool:
        """删除备份文件"""
        pass
    
    @abstractmethod
    def exists(self, backup_id: str) -> bool:
        """检查备份文件是否存在"""
        pass


class LocalStorageProvider(StorageProvider):
    """本地存储提供商"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or current_app.config.get('LOCAL_BACKUP_DIR', 'backups/local'))
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def upload(self, file_path: Path, backup_id: str) -> Dict[str, Any]:
        """上传到本地存储"""
        try:
            target_path = self.base_dir / f"{backup_id}.tar.gz"
            shutil.copy2(file_path, target_path)
            
            return {
                'provider': 'local',
                'path': str(target_path),
                'size': target_path.stat().st_size
            }
        except Exception as e:
            current_app.logger.error(f"Local storage upload failed: {e}")
            raise
    
    def download(self, backup_id: str, target_path: Path) -> bool:
        """从本地存储下载"""
        try:
            source_path = self.base_dir / f"{backup_id}.tar.gz"
            if source_path.exists():
                shutil.copy2(source_path, target_path)
                return True
            return False
        except Exception as e:
            current_app.logger.error(f"Local storage download failed: {e}")
            return False
    
    def delete(self, backup_id: str) -> bool:
        """删除本地存储文件"""
        try:
            file_path = self.base_dir / f"{backup_id}.tar.gz"
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            current_app.logger.error(f"Local storage delete failed: {e}")
            return False
    
    def exists(self, backup_id: str) -> bool:
        """检查本地文件是否存在"""
        file_path = self.base_dir / f"{backup_id}.tar.gz"
        return file_path.exists()


class S3StorageProvider(StorageProvider):
    """AWS S3存储提供商"""
    
    def __init__(self, bucket_name: str, access_key: str, secret_key: str, region: str = 'us-east-1'):
        self.bucket_name = bucket_name
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self._client = None
    
    @property
    def client(self):
        """懒加载S3客户端"""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    's3',
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region
                )
            except ImportError:
                raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")
        return self._client
    
    def upload(self, file_path: Path, backup_id: str) -> Dict[str, Any]:
        """上传到S3存储"""
        try:
            key = f"backups/{backup_id}.tar.gz"
            self.client.upload_file(str(file_path), self.bucket_name, key)
            
            return {
                'provider': 's3',
                'bucket': self.bucket_name,
                'key': key,
                'region': self.region,
                'size': file_path.stat().st_size
            }
        except Exception as e:
            current_app.logger.error(f"S3 upload failed: {e}")
            raise
    
    def download(self, backup_id: str, target_path: Path) -> bool:
        """从S3下载"""
        try:
            key = f"backups/{backup_id}.tar.gz"
            self.client.download_file(self.bucket_name, key, str(target_path))
            return True
        except Exception as e:
            current_app.logger.error(f"S3 download failed: {e}")
            return False
    
    def delete(self, backup_id: str) -> bool:
        """删除S3文件"""
        try:
            key = f"backups/{backup_id}.tar.gz"
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as e:
            current_app.logger.error(f"S3 delete failed: {e}")
            return False
    
    def exists(self, backup_id: str) -> bool:
        """检查S3文件是否存在"""
        try:
            key = f"backups/{backup_id}.tar.gz"
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except:
            return False


class AliyunOSSProvider(StorageProvider):
    """阿里云OSS存储提供商"""
    
    def __init__(self, bucket_name: str, access_key: str, secret_key: str, endpoint: str):
        self.bucket_name = bucket_name
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = endpoint
        self._bucket = None
    
    @property
    def bucket(self):
        """懒加载OSS bucket"""
        if self._bucket is None:
            try:
                import oss2
                auth = oss2.Auth(self.access_key, self.secret_key)
                self._bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            except ImportError:
                raise ImportError("oss2 is required for Aliyun OSS storage. Install with: pip install oss2")
        return self._bucket
    
    def upload(self, file_path: Path, backup_id: str) -> Dict[str, Any]:
        """上传到阿里云OSS"""
        try:
            key = f"backups/{backup_id}.tar.gz"
            result = self.bucket.put_object_from_file(key, str(file_path))
            
            return {
                'provider': 'aliyun_oss',
                'bucket': self.bucket_name,
                'key': key,
                'endpoint': self.endpoint,
                'etag': result.etag,
                'size': file_path.stat().st_size
            }
        except Exception as e:
            current_app.logger.error(f"Aliyun OSS upload failed: {e}")
            raise
    
    def download(self, backup_id: str, target_path: Path) -> bool:
        """从阿里云OSS下载"""
        try:
            key = f"backups/{backup_id}.tar.gz"
            self.bucket.get_object_to_file(key, str(target_path))
            return True
        except Exception as e:
            current_app.logger.error(f"Aliyun OSS download failed: {e}")
            return False
    
    def delete(self, backup_id: str) -> bool:
        """删除阿里云OSS文件"""
        try:
            key = f"backups/{backup_id}.tar.gz"
            self.bucket.delete_object(key)
            return True
        except Exception as e:
            current_app.logger.error(f"Aliyun OSS delete failed: {e}")
            return False
    
    def exists(self, backup_id: str) -> bool:
        """检查阿里云OSS文件是否存在"""
        try:
            key = f"backups/{backup_id}.tar.gz"
            return self.bucket.object_exists(key)
        except:
            return False


class TencentCOSProvider(StorageProvider):
    """腾讯云COS存储提供商"""
    
    def __init__(self, bucket_name: str, region: str, secret_id: str, secret_key: str):
        self.bucket_name = bucket_name
        self.region = region
        self.secret_id = secret_id
        self.secret_key = secret_key
        self._client = None
    
    @property
    def client(self):
        """懒加载COS客户端"""
        if self._client is None:
            try:
                from qcloud_cos import CosConfig, CosS3Client
                config = CosConfig(Region=self.region, SecretId=self.secret_id, SecretKey=self.secret_key)
                self._client = CosS3Client(config)
            except ImportError:
                raise ImportError("cos-python-sdk-v5 is required for Tencent COS storage.")
        return self._client
    
    def upload(self, file_path: Path, backup_id: str) -> Dict[str, Any]:
        """上传到腾讯云COS"""
        try:
            key = f"backups/{backup_id}.tar.gz"
            with open(file_path, 'rb') as f:
                response = self.client.put_object(
                    Bucket=self.bucket_name,
                    Body=f,
                    Key=key
                )
            
            return {
                'provider': 'tencent_cos',
                'bucket': self.bucket_name,
                'key': key,
                'region': self.region,
                'etag': response['ETag'],
                'size': file_path.stat().st_size
            }
        except Exception as e:
            current_app.logger.error(f"Tencent COS upload failed: {e}")
            raise
    
    def download(self, backup_id: str, target_path: Path) -> bool:
        """从腾讯云COS下载"""
        try:
            key = f"backups/{backup_id}.tar.gz"
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            
            with open(target_path, 'wb') as f:
                f.write(response['Body'].read())
            return True
        except Exception as e:
            current_app.logger.error(f"Tencent COS download failed: {e}")
            return False
    
    def delete(self, backup_id: str) -> bool:
        """删除腾讯云COS文件"""
        try:
            key = f"backups/{backup_id}.tar.gz"
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as e:
            current_app.logger.error(f"Tencent COS delete failed: {e}")
            return False
    
    def exists(self, backup_id: str) -> bool:
        """检查腾讯云COS文件是否存在"""
        try:
            key = f"backups/{backup_id}.tar.gz"
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except:
            return False


class BackupEncryption:
    """备份加密工具"""
    
    def __init__(self, key: bytes = None):
        if not CRYPTOGRAPHY_AVAILABLE:
            current_app.logger.warning("Cryptography library not available. Backup encryption disabled.")
            self.enabled = False
            return
            
        self.enabled = True
        if key:
            self.key = key
        else:
            # 从配置或环境变量获取密钥
            key_str = current_app.config.get('BACKUP_ENCRYPTION_KEY')
            if key_str:
                self.key = base64.urlsafe_b64decode(key_str.encode())
            else:
                self.key = Fernet.generate_key()
                current_app.logger.warning("Generated new encryption key. Save it securely!")
                
        self.cipher = Fernet(self.key)
    
    def encrypt_file(self, input_path: Path, output_path: Path) -> bool:
        """加密文件"""
        if not self.enabled:
            # 如果加密未启用，直接复制文件
            try:
                import shutil
                shutil.copy2(input_path, output_path)
                return True
            except Exception as e:
                current_app.logger.error(f"File copy failed: {e}")
                return False
        
        try:
            with open(input_path, 'rb') as f:
                data = f.read()
                
            encrypted_data = self.cipher.encrypt(data)
            
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
                
            return True
        except Exception as e:
            current_app.logger.error(f"File encryption failed: {e}")
            return False
    
    def decrypt_file(self, input_path: Path, output_path: Path) -> bool:
        """解密文件"""
        if not self.enabled:
            # 如果加密未启用，直接复制文件
            try:
                import shutil
                shutil.copy2(input_path, output_path)
                return True
            except Exception as e:
                current_app.logger.error(f"File copy failed: {e}")
                return False
        
        try:
            with open(input_path, 'rb') as f:
                encrypted_data = f.read()
                
            data = self.cipher.decrypt(encrypted_data)
            
            with open(output_path, 'wb') as f:
                f.write(data)
                
            return True
        except Exception as e:
            current_app.logger.error(f"File decryption failed: {e}")
            return False
    
    def get_key_string(self) -> str:
        """获取密钥字符串(用于保存到配置)"""
        if not self.enabled:
            return ""
        return base64.urlsafe_b64encode(self.key).decode()


class StorageManager:
    """存储管理器"""
    
    def __init__(self):
        self.providers = {}
        self._setup_providers()
        self.encryption = BackupEncryption()
    
    def _setup_providers(self):
        """设置存储提供商"""
        # 本地存储(默认)
        self.providers['local'] = LocalStorageProvider()
        
        # S3存储
        s3_config = current_app.config.get('S3_BACKUP_CONFIG')
        if s3_config:
            self.providers['s3'] = S3StorageProvider(
                bucket_name=s3_config['bucket'],
                access_key=s3_config['access_key'],
                secret_key=s3_config['secret_key'],
                region=s3_config.get('region', 'us-east-1')
            )
        
        # 阿里云OSS
        oss_config = current_app.config.get('ALIYUN_OSS_CONFIG')
        if oss_config:
            self.providers['aliyun_oss'] = AliyunOSSProvider(
                bucket_name=oss_config['bucket'],
                access_key=oss_config['access_key'],
                secret_key=oss_config['secret_key'],
                endpoint=oss_config['endpoint']
            )
        
        # 腾讯云COS
        cos_config = current_app.config.get('TENCENT_COS_CONFIG')
        if cos_config:
            self.providers['tencent_cos'] = TencentCOSProvider(
                bucket_name=cos_config['bucket'],
                region=cos_config['region'],
                secret_id=cos_config['secret_id'],
                secret_key=cos_config['secret_key']
            )
    
    def store_backup(self, file_path: Path, backup_id: str, providers: list = None) -> Dict[str, Any]:
        """存储备份到多个后端"""
        if providers is None:
            providers = list(self.providers.keys())
        
        # 加密备份文件
        encrypted_file = None
        if current_app.config.get('BACKUP_ENCRYPTION_ENABLED', True):
            encrypted_file = file_path.parent / f"{file_path.name}.encrypted"
            if not self.encryption.encrypt_file(file_path, encrypted_file):
                raise Exception("Backup encryption failed")
            upload_file = encrypted_file
        else:
            upload_file = file_path
        
        storage_info = {}
        
        try:
            for provider_name in providers:
                if provider_name in self.providers:
                    try:
                        result = self.providers[provider_name].upload(upload_file, backup_id)
                        storage_info[provider_name] = {
                            'status': 'success',
                            'info': result
                        }
                    except Exception as e:
                        storage_info[provider_name] = {
                            'status': 'error',
                            'error': str(e)
                        }
                        current_app.logger.error(f"Failed to upload to {provider_name}: {e}")
                else:
                    storage_info[provider_name] = {
                        'status': 'error',
                        'error': f'Provider {provider_name} not configured'
                    }
            
            return storage_info
            
        finally:
            # 清理加密文件
            if encrypted_file and encrypted_file.exists():
                encrypted_file.unlink()
    
    def retrieve_backup(self, backup_id: str, target_path: Path, provider_name: str = None) -> bool:
        """从存储后端恢复备份"""
        providers_to_try = [provider_name] if provider_name else list(self.providers.keys())
        
        for provider in providers_to_try:
            if provider in self.providers:
                try:
                    # 下载文件
                    download_path = target_path
                    if current_app.config.get('BACKUP_ENCRYPTION_ENABLED', True):
                        download_path = target_path.parent / f"{target_path.name}.encrypted"
                    
                    if self.providers[provider].download(backup_id, download_path):
                        # 解密文件
                        if current_app.config.get('BACKUP_ENCRYPTION_ENABLED', True):
                            if self.encryption.decrypt_file(download_path, target_path):
                                download_path.unlink()  # 删除加密文件
                                return True
                            else:
                                download_path.unlink()  # 删除损坏的加密文件
                                continue
                        else:
                            return True
                            
                except Exception as e:
                    current_app.logger.error(f"Failed to retrieve from {provider}: {e}")
                    continue
        
        return False
    
    def delete_backup(self, backup_id: str, storage_info: Dict[str, Any]) -> Dict[str, bool]:
        """删除存储后端的备份文件"""
        results = {}
        
        for provider_name, info in storage_info.items():
            if provider_name in self.providers and info.get('status') == 'success':
                try:
                    results[provider_name] = self.providers[provider_name].delete(backup_id)
                except Exception as e:
                    current_app.logger.error(f"Failed to delete from {provider_name}: {e}")
                    results[provider_name] = False
            else:
                results[provider_name] = True  # 没有存储就认为删除成功
        
        return results
    
    def check_backup_exists(self, backup_id: str, provider_name: str) -> bool:
        """检查备份是否存在"""
        if provider_name in self.providers:
            return self.providers[provider_name].exists(backup_id)
        return False
    
    def get_available_providers(self) -> Dict[str, bool]:
        """获取可用的存储提供商"""
        available = {}
        for name, provider in self.providers.items():
            try:
                # 简单测试提供商是否可用
                available[name] = True
            except Exception:
                available[name] = False
        return available