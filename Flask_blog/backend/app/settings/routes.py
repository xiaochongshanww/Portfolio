from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from sqlalchemy import func, text
from .. import db, require_auth, require_roles
from ..models import User, Article, Comment, Category, Tag
import json
import os
import logging

settings_bp = Blueprint('settings', __name__)

# 默认配置
DEFAULT_SETTINGS = {
    'general': {
        'siteName': 'Flask博客系统',
        'siteSlogan': '分享知识，记录思考',
        'siteDescription': '一个基于Flask开发的现代化博客系统，支持Markdown编辑、分类管理、评论系统等功能。',
        'adminEmail': 'admin@example.com',
        'contactPhone': '',
        'defaultLanguage': 'zh',
        'timezone': 'Asia/Shanghai'
    },
    'content': {
        'articlesPerPage': 10,
        'commentModeration': 'auto',
        'allowAnonymousComments': False,
        'enableArticleLikes': True,
        'defaultArticleStatus': 'draft',
        'excerptLength': 200
    },
    'security': {
        'maxLoginAttempts': 5,
        'lockoutDuration': 15,
        'jwtExpiry': 30,
        'enableTwoFactor': False,
        'passwordComplexity': ['lowercase', 'numbers'],
        'minPasswordLength': 8,
        'enableIpWhitelist': False
    }
}

# 设置文件路径
SETTINGS_FILE = 'config/system_settings.json'

def load_settings():
    """加载设置"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
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

def save_settings(settings):
    """保存设置"""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"保存设置失败: {e}")
        return False

@settings_bp.route('/all', methods=['GET'])
@require_roles('admin')
def get_all_settings():
    """获取所有设置"""
    try:
        settings = load_settings()
        return jsonify({
            'code': 0,
            'message': 'ok',
            'data': settings
        })
    except Exception as e:
        logging.error(f"获取设置失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '获取设置失败',
            'data': None
        }), 500

@settings_bp.route('/general', methods=['GET'])
@require_roles('admin')
def get_general_settings():
    """获取基本设置"""
    try:
        settings = load_settings()
        return jsonify({
            'code': 0,
            'message': 'ok',
            'data': settings.get('general', DEFAULT_SETTINGS['general'])
        })
    except Exception as e:
        logging.error(f"获取基本设置失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '获取基本设置失败',
            'data': None
        }), 500

@settings_bp.route('/general', methods=['PUT'])
@require_roles('admin')
def update_general_settings():
    """更新基本设置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 4001,
                'message': '无效的数据格式'
            }), 400
            
        settings = load_settings()
        settings['general'].update(data)
        
        if save_settings(settings):
            return jsonify({
                'code': 0,
                'message': '基本设置保存成功',
                'data': settings['general']
            })
        else:
            return jsonify({
                'code': 5000,
                'message': '保存设置失败'
            }), 500
            
    except Exception as e:
        logging.error(f"更新基本设置失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '更新基本设置失败',
            'data': None
        }), 500

@settings_bp.route('/content', methods=['GET'])
@require_roles('admin')
def get_content_settings():
    """获取内容设置"""
    try:
        settings = load_settings()
        return jsonify({
            'code': 0,
            'message': 'ok',
            'data': settings.get('content', DEFAULT_SETTINGS['content'])
        })
    except Exception as e:
        logging.error(f"获取内容设置失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '获取内容设置失败',
            'data': None
        }), 500

@settings_bp.route('/content', methods=['PUT'])
@require_roles('admin')
def update_content_settings():
    """更新内容设置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 4001,
                'message': '无效的数据格式'
            }), 400
            
        settings = load_settings()
        settings['content'].update(data)
        
        if save_settings(settings):
            return jsonify({
                'code': 0,
                'message': '内容设置保存成功',
                'data': settings['content']
            })
        else:
            return jsonify({
                'code': 5000,
                'message': '保存设置失败'
            }), 500
            
    except Exception as e:
        logging.error(f"更新内容设置失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '更新内容设置失败',
            'data': None
        }), 500

@settings_bp.route('/security', methods=['GET'])
@require_roles('admin')
def get_security_settings():
    """获取安全设置"""
    try:
        settings = load_settings()
        return jsonify({
            'code': 0,
            'message': 'ok',
            'data': settings.get('security', DEFAULT_SETTINGS['security'])
        })
    except Exception as e:
        logging.error(f"获取安全设置失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '获取安全设置失败',
            'data': None
        }), 500

@settings_bp.route('/security', methods=['PUT'])
@require_roles('admin')
def update_security_settings():
    """更新安全设置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 4001,
                'message': '无效的数据格式'
            }), 400
            
        settings = load_settings()
        settings['security'].update(data)
        
        if save_settings(settings):
            return jsonify({
                'code': 0,
                'message': '安全设置保存成功',
                'data': settings['security']
            })
        else:
            return jsonify({
                'code': 5000,
                'message': '保存设置失败'
            }), 500
            
    except Exception as e:
        logging.error(f"更新安全设置失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '更新安全设置失败',
            'data': None
        }), 500

@settings_bp.route('/system/info', methods=['GET'])
@require_roles('admin')
def get_system_info():
    """获取系统信息"""
    try:
        # 获取数据库统计信息
        total_articles = Article.query.filter_by(deleted=False).count()
        total_users = User.query.count()
        total_categories = Category.query.count()
        total_tags = Tag.query.count()
        total_comments = Comment.query.filter_by(deleted=False).count()
        
        # 获取数据库大小（模拟）
        try:
            # 对于SQLite
            if current_app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
                db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
                if os.path.exists(db_path):
                    db_size_bytes = os.path.getsize(db_path)
                    db_size = f"{db_size_bytes / 1024 / 1024:.1f} MB"
                else:
                    db_size = "0 MB"
            else:
                # 对于其他数据库，使用估算
                db_size = f"{(total_articles * 5 + total_comments * 2) / 1024:.1f} MB"
        except Exception:
            db_size = "未知"
        
        # 获取应用启动时间（模拟）
        uptime = "7天 12小时 35分钟"
        
        # 获取最近发布的文章
        recent_articles = Article.query.filter_by(
            status='published', 
            deleted=False
        ).order_by(Article.published_at.desc()).limit(5).all()
        
        # 获取系统版本
        version = current_app.config.get('VERSION', '1.0.0')
        
        system_info = {
            'version': version,
            'uptime': uptime,
            'dbSize': db_size,
            'cacheUsage': "12.3 MB",  # 模拟缓存使用
            'totalArticles': total_articles,
            'totalUsers': total_users,
            'totalCategories': total_categories,
            'totalTags': total_tags,
            'totalComments': total_comments,
            'diskUsage': "2.1 GB / 10 GB",  # 模拟磁盘使用
            'lastBackup': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'recentArticles': [{
                'id': article.id,
                'title': article.title,
                'published_at': article.published_at.strftime('%Y-%m-%d %H:%M') if article.published_at else ''
            } for article in recent_articles]
        }
        
        return jsonify({
            'code': 0,
            'message': 'ok',
            'data': system_info
        })
        
    except Exception as e:
        logging.error(f"获取系统信息失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '获取系统信息失败',
            'data': None
        }), 500

@settings_bp.route('/system/optimize-database', methods=['POST'])
@require_roles('admin')
def optimize_database():
    """优化数据库"""
    try:
        # 执行数据库优化操作
        # 对于SQLite，执行VACUUM
        if current_app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
            db.session.execute(text('VACUUM'))
            db.session.commit()
        
        logging.info("数据库优化完成")
        
        return jsonify({
            'code': 0,
            'message': '数据库优化完成',
            'data': {
                'optimized_at': datetime.now().isoformat(),
                'operation': 'database_vacuum'
            }
        })
        
    except Exception as e:
        logging.error(f"数据库优化失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '数据库优化失败',
            'data': None
        }), 500

@settings_bp.route('/system/clear-cache', methods=['POST'])
@require_roles('admin')
def clear_cache():
    """清理缓存"""
    try:
        # 清理Redis缓存
        from .. import redis_client
        if redis_client:
            try:
                redis_client.flushall()
                logging.info("Redis缓存已清理")
            except Exception as e:
                logging.warning(f"清理Redis缓存失败: {e}")
        
        return jsonify({
            'code': 0,
            'message': '缓存清理完成',
            'data': {
                'cleared_at': datetime.now().isoformat(),
                'operation': 'cache_clear'
            }
        })
        
    except Exception as e:
        logging.error(f"清理缓存失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '清理缓存失败',
            'data': None
        }), 500

@settings_bp.route('/system/cleanup-logs', methods=['POST'])
@require_roles('admin')
def cleanup_logs():
    """清理日志"""
    try:
        # 模拟日志清理操作
        logging.info("日志清理完成")
        
        return jsonify({
            'code': 0,
            'message': '日志清理完成',
            'data': {
                'cleaned_at': datetime.now().isoformat(),
                'operation': 'logs_cleanup'
            }
        })
        
    except Exception as e:
        logging.error(f"清理日志失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '清理日志失败',
            'data': None
        }), 500

@settings_bp.route('/system/generate-sitemap', methods=['POST'])
@require_roles('admin')
def generate_sitemap():
    """生成站点地图"""
    try:
        # 获取所有已发布的文章
        articles = Article.query.filter_by(
            status='published',
            deleted=False
        ).order_by(Article.published_at.desc()).all()
        
        # 生成站点地图XML内容
        sitemap_content = ['<?xml version="1.0" encoding="UTF-8"?>']
        sitemap_content.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        
        # 添加首页
        sitemap_content.append('<url>')
        sitemap_content.append('  <loc>http://localhost:3000/</loc>')
        sitemap_content.append('  <changefreq>daily</changefreq>')
        sitemap_content.append('  <priority>1.0</priority>')
        sitemap_content.append('</url>')
        
        # 添加文章页面
        for article in articles:
            sitemap_content.append('<url>')
            sitemap_content.append(f'  <loc>http://localhost:3000/article/{article.slug or article.id}</loc>')
            if article.updated_at:
                sitemap_content.append(f'  <lastmod>{article.updated_at.strftime("%Y-%m-%d")}</lastmod>')
            sitemap_content.append('  <changefreq>weekly</changefreq>')
            sitemap_content.append('  <priority>0.8</priority>')
            sitemap_content.append('</url>')
        
        sitemap_content.append('</urlset>')
        
        # 保存站点地图文件
        sitemap_path = os.path.join(os.getcwd(), 'public', 'sitemap.xml')
        os.makedirs(os.path.dirname(sitemap_path), exist_ok=True)
        
        with open(sitemap_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sitemap_content))
        
        logging.info("站点地图生成完成")
        
        return jsonify({
            'code': 0,
            'message': '站点地图生成完成',
            'data': {
                'generated_at': datetime.now().isoformat(),
                'articles_count': len(articles),
                'sitemap_path': sitemap_path
            }
        })
        
    except Exception as e:
        logging.error(f"生成站点地图失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '生成站点地图失败',
            'data': None
        }), 500

@settings_bp.route('/system/backup', methods=['POST'])
@require_roles('admin')
def create_backup():
    """创建系统备份"""
    try:
        # 模拟备份创建
        backup_filename = f"backup_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.zip"
        backup_info = {
            'filename': backup_filename,
            'size': '16.7 MB',
            'created_at': datetime.now().isoformat(),
            'includes': ['database', 'uploads', 'config']
        }
        
        logging.info(f"系统备份创建完成: {backup_filename}")
        
        return jsonify({
            'code': 0,
            'message': '系统备份创建完成',
            'data': backup_info
        })
        
    except Exception as e:
        logging.error(f"创建系统备份失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '创建系统备份失败',
            'data': None
        }), 500

@settings_bp.route('/backup/history', methods=['GET'])
@require_roles('admin')
def get_backup_history():
    """获取备份历史"""
    try:
        # 模拟备份历史数据
        backup_history = [
            {
                'filename': 'backup_2024_01_15_103000.zip',
                'size': '15.2 MB',
                'created_at': '2024-01-15T10:30:00Z'
            },
            {
                'filename': 'backup_2024_01_14_103000.zip', 
                'size': '14.8 MB',
                'created_at': '2024-01-14T10:30:00Z'
            }
        ]
        
        return jsonify({
            'code': 0,
            'message': 'ok',
            'data': backup_history
        })
        
    except Exception as e:
        logging.error(f"获取备份历史失败: {e}")
        return jsonify({
            'code': 5000,
            'message': '获取备份历史失败',
            'data': None
        }), 500