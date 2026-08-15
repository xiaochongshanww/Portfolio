"""系统设置业务逻辑层 — 供 routes.py 编排调用。"""

import json
import logging
import os
from datetime import datetime

from flask import current_app
from sqlalchemy import text

from .. import db, redis_client
from ..models import Article, Category, Comment, Tag, User

# 默认配置
DEFAULT_SETTINGS = {
    "general": {
        "siteName": "Flask博客系统",
        "siteSlogan": "分享知识，记录思考",
        "siteDescription": "一个基于Flask开发的现代化博客系统，支持Markdown编辑、分类管理、评论系统等功能。",
        "adminEmail": "admin@example.com",
        "contactPhone": "",
        "defaultLanguage": "zh",
        "timezone": "Asia/Shanghai",
    },
    "content": {
        "articlesPerPage": 10,
        "commentModeration": "auto",
        "allowAnonymousComments": False,
        "enableArticleLikes": True,
        "defaultArticleStatus": "draft",
        "excerptLength": 200,
    },
    "security": {
        "maxLoginAttempts": 5,
        "lockoutDuration": 15,
        "jwtExpiry": 30,
        "enableTwoFactor": False,
        "passwordComplexity": ["lowercase", "numbers"],
        "minPasswordLength": 8,
        "enableIpWhitelist": False,
    },
}

# 设置文件路径
SETTINGS_FILE = "config/system_settings.json"


def load_settings():
    """加载设置。"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
                # 合并默认设置，确保所有键都存在
                for category, defaults in DEFAULT_SETTINGS.items():
                    if category not in settings:
                        settings[category] = defaults.copy()
                    else:
                        for key, value in defaults.items():
                            if key not in settings[category]:
                                settings[category][key] = value
                return settings
        else:
            return DEFAULT_SETTINGS.copy()
    except Exception as e:
        logging.error(f"加载设置失败: {e}")
        return DEFAULT_SETTINGS.copy()


def save_settings(settings) -> bool:
    """保存设置。"""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"保存设置失败: {e}")
        return False


def get_system_info_data() -> dict:
    """获取系统信息。"""
    # 数据库统计信息
    total_articles = Article.query.filter_by(deleted=False).count()
    total_users = User.query.count()
    total_categories = Category.query.count()
    total_tags = Tag.query.count()
    total_comments = Comment.query.filter_by(deleted=False).count()

    # 数据库大小（估算或 SQLite 实测）
    try:
        if current_app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
            db_path = current_app.config["SQLALCHEMY_DATABASE_URI"].replace(
                "sqlite:///", ""
            )
            if os.path.exists(db_path):
                db_size_bytes = os.path.getsize(db_path)
                db_size = f"{db_size_bytes / 1024 / 1024:.1f} MB"
            else:
                db_size = "0 MB"
        else:
            db_size = f"{(total_articles * 5 + total_comments * 2) / 1024:.1f} MB"
    except Exception:
        db_size = "未知"

    # 最近发布的文章
    recent_articles = (
        Article.query.filter_by(status="published", deleted=False)
        .order_by(Article.published_at.desc())
        .limit(5)
        .all()
    )

    version = current_app.config.get("VERSION", "1.0.0")

    return {
        "version": version,
        "uptime": "7天 12小时 35分钟",
        "dbSize": db_size,
        "cacheUsage": "12.3 MB",
        "totalArticles": total_articles,
        "totalUsers": total_users,
        "totalCategories": total_categories,
        "totalTags": total_tags,
        "totalComments": total_comments,
        "diskUsage": "2.1 GB / 10 GB",
        "lastBackup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "recentArticles": [
            {
                "id": article.id,
                "title": article.title,
                "published_at": (
                    article.published_at.strftime("%Y-%m-%d %H:%M")
                    if article.published_at
                    else ""
                ),
            }
            for article in recent_articles
        ],
    }


def optimize_database_operation() -> dict:
    """执行数据库优化（SQLite 执行 VACUUM）。"""
    if current_app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        db.session.execute(text("VACUUM"))
        db.session.commit()
    logging.info("数据库优化完成")
    return {
        "optimized_at": datetime.now().isoformat(),
        "operation": "database_vacuum",
    }


def clear_cache_operation() -> dict:
    """清理 Redis 缓存。"""
    if redis_client:
        try:
            redis_client.flushall()
            logging.info("Redis缓存已清理")
        except Exception as e:
            logging.warning(f"清理Redis缓存失败: {e}")
    return {
        "cleared_at": datetime.now().isoformat(),
        "operation": "cache_clear",
    }


def cleanup_logs_operation() -> dict:
    """清理日志（模拟）。"""
    logging.info("日志清理完成")
    return {
        "cleaned_at": datetime.now().isoformat(),
        "operation": "logs_cleanup",
    }


def generate_sitemap_operation() -> dict:
    """生成站点地图并写入 public/sitemap.xml。"""
    articles = (
        Article.query.filter_by(status="published", deleted=False)
        .order_by(Article.published_at.desc())
        .all()
    )

    sitemap_content = ['<?xml version="1.0" encoding="UTF-8"?>']
    sitemap_content.append(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    )
    sitemap_content.append("<url>")
    sitemap_content.append("  <loc>http://localhost:3000/</loc>")
    sitemap_content.append("  <changefreq>daily</changefreq>")
    sitemap_content.append("  <priority>1.0</priority>")
    sitemap_content.append("</url>")

    for article in articles:
        sitemap_content.append("<url>")
        sitemap_content.append(
            f"  <loc>http://localhost:3000/article/{article.slug or article.id}</loc>"
        )
        if article.updated_at:
            sitemap_content.append(
                f'  <lastmod>{article.updated_at.strftime("%Y-%m-%d")}</lastmod>'
            )
        sitemap_content.append("  <changefreq>weekly</changefreq>")
        sitemap_content.append("  <priority>0.8</priority>")
        sitemap_content.append("</url>")

    sitemap_content.append("</urlset>")

    sitemap_path = os.path.join(os.getcwd(), "public", "sitemap.xml")
    os.makedirs(os.path.dirname(sitemap_path), exist_ok=True)
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sitemap_content))

    logging.info("站点地图生成完成")
    return {
        "generated_at": datetime.now().isoformat(),
        "articles_count": len(articles),
        "sitemap_path": sitemap_path,
    }


def create_backup_operation() -> dict:
    """创建系统备份（模拟）。"""
    backup_filename = f"backup_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.zip"
    logging.info(f"系统备份创建完成: {backup_filename}")
    return {
        "filename": backup_filename,
        "size": "16.7 MB",
        "created_at": datetime.now().isoformat(),
        "includes": ["database", "uploads", "config"],
    }


def get_backup_history_data() -> list:
    """获取备份历史（模拟）。"""
    return [
        {
            "filename": "backup_2024_01_15_103000.zip",
            "size": "15.2 MB",
            "created_at": "2024-01-15T10:30:00Z",
        },
        {
            "filename": "backup_2024_01_14_103000.zip",
            "size": "14.8 MB",
            "created_at": "2024-01-14T10:30:00Z",
        },
    ]
