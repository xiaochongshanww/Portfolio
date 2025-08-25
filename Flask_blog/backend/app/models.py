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
