from datetime import datetime, timezone, timedelta
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy import Text
from sqlalchemy.dialects import mysql
from . import db

# 定义上海时区 (UTC+8)
SHANGHAI_TZ = timezone(timedelta(hours=8))

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default='author', index=True)
    nickname = db.Column(db.String(80))
    bio = db.Column(db.Text)
    avatar = db.Column(db.String(255))
    social_links = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    articles = db.relationship('Article', backref='author', lazy='dynamic')

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(150), unique=True, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(120), unique=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class ArticleTag(db.Model):
    __tablename__ = 'article_tags'
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), primary_key=True)

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, index=True)
    content_md = db.Column(Text().with_variant(mysql.LONGTEXT(), 'mysql'))
    content_html = db.Column(Text().with_variant(mysql.LONGTEXT(), 'mysql'))
    status = db.Column(db.String(32), index=True, default='draft')
    seo_title = db.Column(db.String(255))
    seo_desc = db.Column(db.String(255))
    summary = db.Column(db.String(500))
    featured_image = db.Column(db.String(255))
    featured_focal_x = db.Column(db.Float)  # 0-1 之间，表示裁剪焦点横向相对位置
    featured_focal_y = db.Column(db.Float)  # 0-1 之间
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), index=True)
    scheduled_at = db.Column(db.DateTime)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted = db.Column(db.Boolean, default=False, index=True)
    reject_reason = db.Column(db.String(500))  # 新增：最近一次拒绝原因
    views_count = db.Column(db.Integer, default=0, index=True)

    versions = db.relationship('ArticleVersion', backref='article', lazy='dynamic')
    tags = db.relationship('Tag', secondary='article_tags', backref=db.backref('articles', lazy='dynamic'))

class ArticleVersion(db.Model):
    __tablename__ = 'article_versions'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=False, index=True)
    version_no = db.Column(db.Integer, nullable=False)
    # 使用通用 Text，并为 MySQL 指定 LONGTEXT 变体
    content_md = db.Column(Text().with_variant(mysql.LONGTEXT(), 'mysql'))
    content_html = db.Column(Text().with_variant(mysql.LONGTEXT(), 'mysql'))
    editor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), index=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), default='pending', index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class ArticleLike(db.Model):
    __tablename__ = 'article_likes'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(SHANGHAI_TZ))

class ArticleBookmark(db.Model):
    __tablename__ = 'article_bookmarks'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(SHANGHAI_TZ))

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), index=True, nullable=False)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False)  # submit/approve/reject/unpublish/schedule/unschedule/delete/rollback
    note = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

# 访客统计相关模型
class VisitorStats(db.Model):
    """网站访客统计表"""
    __tablename__ = 'visitor_stats'
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)  # 支持IPv6
    user_agent_hash = db.Column(db.String(64), nullable=False, index=True)  # User-Agent的哈希值
    visited_date = db.Column(db.Date, nullable=False, index=True)  # 访问日期
    first_visit_time = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(SHANGHAI_TZ))
    last_visit_time = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(SHANGHAI_TZ), onupdate=lambda: datetime.now(SHANGHAI_TZ))
    page_views = db.Column(db.Integer, default=1)  # 当天的页面浏览量
    
    # 唯一约束：同一IP+User-Agent哈希+日期只能有一条记录
    __table_args__ = (
        db.UniqueConstraint('ip_address', 'user_agent_hash', 'visited_date', name='unique_visitor_per_day'),
        db.Index('idx_visitor_date', 'visited_date'),
        db.Index('idx_visitor_ip', 'ip_address'),
    )

class DailyStats(db.Model):
    """每日统计汇总表"""
    __tablename__ = 'daily_stats'
    id = db.Column(db.Integer, primary_key=True)
    stat_date = db.Column(db.Date, nullable=False, unique=True, index=True)
    unique_visitors = db.Column(db.Integer, default=0)  # 独立访客数
    total_page_views = db.Column(db.Integer, default=0)  # 总页面浏览量
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(SHANGHAI_TZ))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(SHANGHAI_TZ), onupdate=lambda: datetime.now(SHANGHAI_TZ))


class LogEntry(db.Model):
    """系统日志条目"""
    __tablename__ = 'log_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, nullable=False, default=lambda: datetime.now(SHANGHAI_TZ))
    level = db.Column(db.String(10), index=True, nullable=False)  # ERROR, WARNING, INFO, DEBUG
    source = db.Column(db.String(50), index=True, nullable=False)  # 日志来源模块
    message = db.Column(Text().with_variant(mysql.LONGTEXT(), 'mysql'), nullable=False)  # 日志消息
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4/IPv6
    user_agent = db.Column(db.String(500), nullable=True)
    request_id = db.Column(db.String(36), index=True, nullable=True)  # 请求链路追踪
    endpoint = db.Column(db.String(200), nullable=True)  # API端点
    method = db.Column(db.String(10), nullable=True)  # HTTP方法
    status_code = db.Column(db.Integer, nullable=True)  # HTTP状态码
    duration_ms = db.Column(db.Integer, nullable=True)  # 请求耗时(毫秒)
    extra_data = db.Column(db.JSON, nullable=True)  # 额外元数据
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(SHANGHAI_TZ))
    
    # 关联用户对象
    user = db.relationship('User', backref='logs', lazy='select')
    
    # 复合索引优化查询性能
    __table_args__ = (
        db.Index('idx_level_timestamp', 'level', 'timestamp'),
        db.Index('idx_source_timestamp', 'source', 'timestamp'),
        db.Index('idx_user_timestamp', 'user_id', 'timestamp'),
        db.Index('idx_request_id', 'request_id'),
        db.Index('idx_endpoint_timestamp', 'endpoint', 'timestamp'),
    )

    def to_dict(self):
        """序列化为字典"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.level,
            'source': self.source,
            'message': self.message,
            'user_id': self.user_id,
            'user_name': self.user.nickname if self.user else None,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_id': self.request_id,
            'endpoint': self.endpoint,
            'method': self.method,
            'status_code': self.status_code,
            'duration_ms': self.duration_ms,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class LogConfig(db.Model):
    """日志配置表"""
    __tablename__ = 'log_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(50), unique=True, nullable=False, index=True)
    config_value = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(SHANGHAI_TZ))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(SHANGHAI_TZ), onupdate=lambda: datetime.now(SHANGHAI_TZ))


# ========== 备份系统模型 ==========

class BackupRecord(db.Model):
    """备份记录模型"""
    __tablename__ = 'backup_records'
    
    id = db.Column(db.Integer, primary_key=True)
    backup_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    backup_type = db.Column(db.String(20), nullable=False, index=True)  # full, incremental, snapshot
    status = db.Column(db.String(20), default='pending', index=True)    # pending, running, completed, failed
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # 文件信息
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.BigInteger)  # 字节数
    compressed_size = db.Column(db.BigInteger)  # 压缩后字节数
    compression_ratio = db.Column(db.Float)  # 压缩比
    
    # 安全信息
    encryption_enabled = db.Column(db.Boolean, default=True, nullable=False)
    checksum = db.Column(db.String(64))  # SHA-256校验和
    
    # 存储信息
    storage_providers = db.Column(db.Text)  # JSON字符串存储提供商信息
    
    # 备份元数据
    extra_data = db.Column(db.Text)  # JSON字符串存储元数据信息
    
    # 错误信息
    error_message = db.Column(db.Text)
    
    # 统计信息
    files_count = db.Column(db.Integer, default=0)  # 备份的文件数量
    databases_count = db.Column(db.Integer, default=0)  # 备份的数据库数量
    
    def __repr__(self):
        return f'<BackupRecord {self.backup_id}: {self.backup_type} - {self.status}>'
    
    def get_storage_providers(self):
        """获取存储提供商信息"""
        if self.storage_providers:
            import json
            try:
                return json.loads(self.storage_providers)
            except:
                return {}
        return {}
    
    def set_storage_providers(self, providers_dict):
        """设置存储提供商信息"""
        import json
        self.storage_providers = json.dumps(providers_dict)
    
    def get_extra_data(self):
        """获取元数据"""
        if self.extra_data:
            import json
            try:
                return json.loads(self.extra_data)
            except:
                return {}
        return {}
    
    def set_extra_data(self, metadata_dict):
        """设置元数据"""
        import json
        self.extra_data = json.dumps(metadata_dict)
    
    def get_duration(self):
        """获取备份耗时(秒)"""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None
    
    def to_dict(self):
        """转换为字典格式"""
        from datetime import timezone, timedelta
        shanghai_tz = timezone(timedelta(hours=8))
        
        def format_datetime(dt):
            if dt is None:
                return None
            # 确保datetime有timezone信息，如果没有则假设是UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # 转换为上海时间
            shanghai_dt = dt.astimezone(shanghai_tz)
            return shanghai_dt.isoformat()
        
        return {
            'id': self.id,
            'backup_id': self.backup_id,
            'backup_type': self.backup_type,
            'status': self.status,
            'created_at': format_datetime(self.created_at),
            'started_at': format_datetime(self.started_at),
            'completed_at': format_datetime(self.completed_at),
            'file_path': self.file_path,
            'file_size': self.file_size,
            'compressed_size': self.compressed_size,
            'compression_ratio': self.compression_ratio,
            'encryption_enabled': self.encryption_enabled,
            'checksum': self.checksum,
            'storage_providers': self.get_storage_providers(),
            'extra_data': self.get_extra_data(),
            'error_message': self.error_message,
            'files_count': self.files_count,
            'databases_count': self.databases_count,
            'duration': self.get_duration()
        }


class BackupConfig(db.Model):
    """备份配置模型"""
    __tablename__ = 'backup_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    config_value = db.Column(db.Text)
    config_type = db.Column(db.String(20), default='string')  # string, int, float, bool, json
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='general', index=True)  # general, storage, schedule, security
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    updated_by = db.Column(db.String(100))  # 更新者
    
    def __repr__(self):
        return f'<BackupConfig {self.config_key}: {self.config_value}>'
    
    def get_typed_value(self):
        """根据类型返回正确的值"""
        if not self.config_value:
            return None
            
        if self.config_type == 'int':
            return int(self.config_value)
        elif self.config_type == 'float':
            return float(self.config_value)
        elif self.config_type == 'bool':
            return self.config_value.lower() in ('true', '1', 'yes', 'on')
        elif self.config_type == 'json':
            import json
            return json.loads(self.config_value)
        else:
            return self.config_value
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'typed_value': self.get_typed_value(),
            'config_type': self.config_type,
            'description': self.description,
            'category': self.category,
            'is_active': self.is_active,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by
        }


class BackupTask(db.Model):
    """备份任务模型"""
    __tablename__ = 'backup_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    task_name = db.Column(db.String(100), nullable=False)
    task_type = db.Column(db.String(20), nullable=False)  # scheduled, manual, triggered
    
    # 调度信息
    schedule_expression = db.Column(db.String(100))  # cron表达式
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    
    # 备份配置
    backup_type = db.Column(db.String(20), default='incremental')  # full, incremental, snapshot
    include_database = db.Column(db.Boolean, default=True, nullable=False)
    include_files = db.Column(db.Boolean, default=True, nullable=False)
    include_patterns = db.Column(db.Text)  # JSON字符串
    exclude_patterns = db.Column(db.Text)  # JSON字符串
    
    # 存储配置
    storage_config = db.Column(db.Text)  # JSON字符串
    retention_days = db.Column(db.Integer, default=30)  # 保留天数
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_run_at = db.Column(db.DateTime)
    next_run_at = db.Column(db.DateTime)
    
    # 统计信息
    total_runs = db.Column(db.Integer, default=0)
    successful_runs = db.Column(db.Integer, default=0)
    failed_runs = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<BackupTask {self.task_name}: {self.task_type}>'
    
    def get_include_patterns(self):
        """获取包含模式"""
        if self.include_patterns:
            import json
            try:
                return json.loads(self.include_patterns)
            except:
                return []
        return []
    
    def set_include_patterns(self, patterns):
        """设置包含模式"""
        import json
        self.include_patterns = json.dumps(patterns)
    
    def get_exclude_patterns(self):
        """获取排除模式"""
        if self.exclude_patterns:
            import json
            try:
                return json.loads(self.exclude_patterns)
            except:
                return []
        return []
    
    def set_exclude_patterns(self, patterns):
        """设置排除模式"""
        import json
        self.exclude_patterns = json.dumps(patterns)
    
    def get_storage_config(self):
        """获取存储配置"""
        if self.storage_config:
            import json
            try:
                return json.loads(self.storage_config)
            except:
                return {}
        return {}
    
    def set_storage_config(self, config):
        """设置存储配置"""
        import json
        self.storage_config = json.dumps(config)
    
    def get_success_rate(self):
        """获取成功率"""
        if self.total_runs == 0:
            return 0
        return round(self.successful_runs / self.total_runs * 100, 2)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'task_name': self.task_name,
            'task_type': self.task_type,
            'schedule_expression': self.schedule_expression,
            'is_enabled': self.is_enabled,
            'backup_type': self.backup_type,
            'include_database': self.include_database,
            'include_files': self.include_files,
            'include_patterns': self.get_include_patterns(),
            'exclude_patterns': self.get_exclude_patterns(),
            'storage_config': self.get_storage_config(),
            'retention_days': self.retention_days,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'next_run_at': self.next_run_at.isoformat() if self.next_run_at else None,
            'total_runs': self.total_runs,
            'successful_runs': self.successful_runs,
            'failed_runs': self.failed_runs,
            'success_rate': self.get_success_rate()
        }


class RestoreRecord(db.Model):
    """恢复记录模型"""
    __tablename__ = 'restore_records'
    
    id = db.Column(db.Integer, primary_key=True)
    restore_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    backup_record_id = db.Column(db.Integer, db.ForeignKey('backup_records.id'), nullable=False)
    
    # 恢复配置
    restore_type = db.Column(db.String(20), nullable=False)  # full, partial, database_only, files_only
    target_path = db.Column(db.String(500))  # 恢复目标路径
    restore_options = db.Column(db.Text)  # JSON字符串
    
    # 状态信息
    status = db.Column(db.String(20), default='pending', index=True)  # pending, running, completed, failed, cancelled
    progress = db.Column(db.Integer, default=0)  # 恢复进度 (0-100)
    status_message = db.Column(db.String(200))  # 状态描述信息
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # 结果信息
    restored_files_count = db.Column(db.Integer, default=0)
    restored_databases_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    
    # 操作者信息
    requested_by = db.Column(db.String(100))  # 请求恢复的用户
    
    # 关联关系
    backup_record = db.relationship('BackupRecord', backref='restore_records')
    
    def __repr__(self):
        return f'<RestoreRecord {self.restore_id}: {self.status}>'
    
    def get_restore_options(self):
        """获取恢复选项"""
        if self.restore_options:
            import json
            try:
                return json.loads(self.restore_options)
            except:
                return {}
        return {}
    
    def set_restore_options(self, options):
        """设置恢复选项"""
        import json
        self.restore_options = json.dumps(options)
    
    def get_duration(self):
        """获取恢复耗时(秒)"""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'restore_id': self.restore_id,
            'backup_record_id': self.backup_record_id,
            'restore_type': self.restore_type,
            'target_path': self.target_path,
            'restore_options': self.get_restore_options(),
            'status': self.status,
            'progress': self.progress,
            'status_message': self.status_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'restored_files_count': self.restored_files_count,
            'restored_databases_count': self.restored_databases_count,
            'error_message': self.error_message,
            'requested_by': self.requested_by,
            'duration': self.get_duration()
        }
