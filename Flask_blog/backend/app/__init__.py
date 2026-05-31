"""
Flask 博客应用工厂。

保持在此的全局实例:
  db, migrate, bcrypt, redis_client, limiter, babel
"""

import json
import logging
import os
import time
import uuid
from functools import wraps
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

import jwt
import redis
import sqlalchemy
from dotenv import load_dotenv
from flask import Flask, Response, current_app, g, jsonify, request
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.errors import RateLimitExceeded
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:
    BackgroundScheduler = None
try:
    from flask_babel import Babel
    from flask_babel import gettext as _
except Exception:
    Babel = None
    _ = lambda x: x
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except Exception:
    pass

load_dotenv()

from .config import CONFIG_MAP, DevelopmentConfig  # noqa: E402
from .decorators import require_auth, require_roles  # noqa: E402 — re-exported for existing imports

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
redis_client = None
limiter = None
babel = None


def create_app(config_name=None):
    """Flask 应用工厂。"""
    global redis_client, limiter, babel
    if not config_name:
        config_name = os.getenv('FLASK_CONFIG', 'development')
    cfg_cls = CONFIG_MAP.get(config_name, DevelopmentConfig)
    app = Flask(__name__)
    app.config.from_object(cfg_cls)
    try:
        app.url_map.strict_slashes = False
    except Exception:
        pass

    _setup_logging(app)
    _setup_cors(app)
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    _setup_redis(app)
    _setup_limiter(app)
    _setup_babel(app)
    _register_blueprints(app)
    _install_error_handlers(app)
    _setup_upload_dir(app)
    _setup_static_route(app)
    _setup_scheduler(app)
    _setup_metrics(app)

    return app


# ─── 各初始化步骤 ─────────────────────────────────────────


def _setup_logging(app):
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_format = os.getenv('LOG_FORMAT', 'human').lower()
    handler = logging.StreamHandler()

    if log_format == 'json':
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                base = {
                    'level': record.levelname, 'msg': record.getMessage(),
                    'logger': record.name,
                    'time': self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                }
                if hasattr(record, 'extra_data'):
                    base.update(record.extra_data)
                return json.dumps(base, ensure_ascii=False)
        handler.setFormatter(JsonFormatter())
    elif log_format == 'simple':
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S'))
    else:
        class HumanFormatter(logging.Formatter):
            COLORS = {
                'DEBUG': '\033[36m', 'INFO': '\033[32m', 'WARNING': '\033[33m',
                'ERROR': '\033[31m', 'CRITICAL': '\033[35m', 'RESET': '\033[0m',
            }
            def format(self, record):
                level_color = self.COLORS.get(record.levelname, '')
                reset_color = self.COLORS['RESET']
                colored_level = f"{level_color}{record.levelname:<8}{reset_color}"
                time_str = self.formatTime(record, "%H:%M:%S")
                message = record.getMessage()
                extra_info = ""
                if hasattr(record, 'extra_data') and record.extra_data:
                    parts = []
                    for k in ('request_id', 'user_id', 'method', 'path', 'status', 'duration_ms'):
                        v = record.extra_data.get(k)
                        if v:
                            parts.append(f"{k}={v}")
                    if parts:
                        extra_info = f" [{', '.join(parts)}]"
                logger_name = record.name
                if logger_name.startswith('app.'):
                    logger_name = logger_name[4:]
                if len(logger_name) > 20:
                    logger_name = logger_name[:17] + '...'
                return f"{time_str} {colored_level} {logger_name:<20} {message}{extra_info}"
        handler.setFormatter(HumanFormatter())

    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(handler)
    root.setLevel(log_level)

    try:
        if os.getenv('LOG_FILE_ENABLED', 'true').lower() == 'true':
            log_dir = os.getenv('LOG_DIR', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, os.getenv('LOG_FILE_NAME', 'app.log'))
            has_file_handler = any(isinstance(h, (TimedRotatingFileHandler, RotatingFileHandler)) for h in root.handlers)
            if not has_file_handler:
                max_bytes = int(os.getenv('LOG_MAX_BYTES', '10485760'))
                retention_days = int(os.getenv('LOG_RETENTION_DAYS', '7'))
                file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=retention_days, encoding='utf-8')
                file_log_format = os.getenv('LOG_FILE_FORMAT', 'simple').lower()
                if file_log_format == 'json':
                    file_handler.setFormatter(JsonFormatter())
                else:
                    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
                root.addHandler(file_handler)
    except Exception as e:
        logging.warning('file logging init failed: %s', e)


def _setup_cors(app):
    cors_origins = os.getenv('CORS_ORIGINS', '*')
    if cors_origins == '*' and app.config.get('ENV') == 'production':
        app.logger.warning("CORS_ORIGINS='*' in production — restricting to same-origin")
        cors_origins = []
    CORS(app, resources={
        r"/api/*": {
            "origins": cors_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "X-XSRF-TOKEN"],
            "supports_credentials": True,
        },
        r"/uploads/*": {
            "origins": cors_origins if cors_origins != [] else [],
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": False,
        },
        r"/public/*": {
            "origins": cors_origins if cors_origins != [] else [],
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": False,
        },
    })


def _setup_redis(app):
    global redis_client
    try:
        redis_url = app.config.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
    except Exception:
        redis_client = None
    app.extensions['redis_client'] = redis_client


def _setup_limiter(app):
    global limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[
            f"{app.config.get('RATE_LIMIT_DEFAULT_MINUTE', 200)}/minute",
            f"{app.config.get('RATE_LIMIT_DEFAULT_DAY', 2000)}/day",
        ],
        storage_uri=app.config.get('REDIS_URL', 'redis://127.0.0.1:6379/0'),
    )

    @app.errorhandler(RateLimitExceeded)
    def _ratelimit_handler(e):
        return jsonify({'code': 4290, 'message': 'rate limit exceeded'}), 429

    @app.after_request
    def _inject_security_headers(resp):
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('X-Frame-Options', 'DENY')
        csp = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' cdnjs.cloudflare.com cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdnjs.cloudflare.com cdn.jsdelivr.net; img-src 'self' data: blob: https:; font-src 'self' data: cdnjs.cloudflare.com; connect-src 'self' https:; media-src 'self'; frame-src 'self' https://www.youtube.com https://www.bilibili.com; object-src 'none'"
        resp.headers.setdefault('Content-Security-Policy', csp)
        return resp

    @app.before_request
    def _before_request():
        g.start_time = time.time()
        g.request_id = str(uuid.uuid4())[:8]


def _setup_babel(app):
    global babel
    if Babel:
        try:
            babel = Babel(app)
        except Exception:
            pass


def _register_blueprints(app):
    from .articles.routes import articles_bp
    from .auth.routes import auth_bp
    from .backup.routes import backup_bp
    from .comments.routes import comments_bp
    from .logs.routes import logs_bp
    from .media.routes import media_bp
    from .metrics.routes import metrics_bp
    from .search.routes import search_bp
    from .search.synonyms import synonyms_bp
    from .security.routes import security_bp
    from .settings.routes import settings_bp
    from .taxonomy.routes import taxonomy_bp
    from .uploads.routes import uploads_bp
    from .users.routes import users_bp
    from .docs.openapi import openapi_bp
    from .public_api import public_bp
    from .simple_logs import simple_logs_bp

    app.register_blueprint(openapi_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(articles_bp, url_prefix='/api/v1/articles')
    app.register_blueprint(comments_bp, url_prefix='/api/v1/comments')
    app.register_blueprint(search_bp, url_prefix='/api/v1/search')
    app.register_blueprint(synonyms_bp, url_prefix='/api/v1/search/synonyms')
    app.register_blueprint(users_bp, url_prefix='/api/v1/users')
    app.register_blueprint(taxonomy_bp, url_prefix='/api/v1/taxonomy')
    app.register_blueprint(uploads_bp, url_prefix='/api/v1/uploads')
    app.register_blueprint(metrics_bp, url_prefix='/api/v1/metrics')
    app.register_blueprint(security_bp, url_prefix='/api/v1/security')
    app.register_blueprint(settings_bp, url_prefix='/api/v1/settings')
    app.register_blueprint(logs_bp, url_prefix='/api/v1/admin/logs')
    app.register_blueprint(simple_logs_bp, url_prefix='/api/v1/simple')
    app.register_blueprint(backup_bp, url_prefix='/api/v1/backup')
    app.register_blueprint(media_bp, url_prefix='/api/v1/media')
    app.register_blueprint(public_bp, url_prefix='/public/v1')


def _install_error_handlers(app):
    try:
        from .security.enforcer import install_business_error_handler
        install_business_error_handler(app)
    except Exception:
        pass


def _setup_upload_dir(app):
    up_dir = app.config['UPLOAD_DIR']
    try:
        os.makedirs(up_dir, exist_ok=True)
    except Exception:
        pass


def _setup_static_route(app):
    @app.route('/uploads/<path:filename>')
    @limiter.exempt
    def serve_upload(filename):
        from flask import send_file, send_from_directory
        import os
        filename = filename.replace('/', os.sep)
        upload_dir = os.path.abspath(app.config['UPLOAD_DIR'])
        full_path = os.path.join(upload_dir, filename)
        if os.path.exists(full_path):
            try:
                return send_file(full_path)
            except Exception:
                return send_from_directory(upload_dir, filename)
        return jsonify({'error': 'File not found', 'path': filename}), 404


def _setup_scheduler(app):
    if getattr(app.config, 'ENABLE_SCHEDULER', False) and BackgroundScheduler:
        scheduler = BackgroundScheduler(timezone='UTC')

        def publish_scheduled():
            from datetime import datetime, timezone
            from .models import Article
            from .search.indexer import index_article
            with app.app_context():
                now = datetime.now(timezone.utc)
                due = Article.query.filter(
                    Article.deleted == False, Article.status == 'scheduled',
                    Article.scheduled_at != None, Article.scheduled_at <= now
                ).all()
                changed = 0
                for a in due:
                    a.status = 'published'
                    if not a.published_at:
                        a.published_at = now
                    changed += 1
                if changed:
                    try:
                        db.session.commit()
                        for a in due:
                            try:
                                index_article(a)
                            except Exception:
                                pass
                    except Exception:
                        db.session.rollback()
                from .articles.service import invalidate_article_cache
                if due:
                    invalidate_article_cache()

        scheduler.add_job(publish_scheduled, 'interval', seconds=app.config.get('SCHEDULE_CHECK_INTERVAL', 60), id='publish_scheduled')
        scheduler.start()
        app.extensions['scheduler'] = scheduler


# 指标注册（容错）
METRICS_ENABLED = False

try:
    from prometheus_client import Counter, Histogram, Gauge
    METRICS_ENABLED = True
except Exception:
    Counter = Histogram = Gauge = None


def _setup_metrics(app):
    global METRICS_ENABLED
    if not METRICS_ENABLED or not os.getenv('PROMETHEUS_ENABLED', 'true').lower() == 'true':
        METRICS_ENABLED = False
        return
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        @app.route('/metrics', methods=['GET'])
        def prometheus_metrics():
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            resp = Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
            return resp
    except Exception:
        pass


# 指标计数器（供各模块导入）
ARTICLE_PUBLISHED_TOTAL = Counter('article_published_total', 'Articles published', ['method']) if Counter else None
SEARCH_QUERIES_TOTAL = Counter('search_queries_total', 'Search queries') if Counter else None
SEARCH_ZERO_RESULT_TOTAL = Counter('search_zero_result_total', 'Search queries with zero results') if Counter else None
CACHE_HIT_TOTAL = Counter('cache_hit_total', 'Cache hits', ['endpoint']) if Counter else None
CACHE_MISS_TOTAL = Counter('cache_miss_total', 'Cache misses', ['endpoint']) if Counter else None
PUBLIC_AUTHOR_PROFILE_REQUESTS_TOTAL = Counter('public_author_profile_requests_total', 'Public author profile requests') if Counter else None
PUBLIC_AUTHOR_ARTICLES_REQUESTS_TOTAL = Counter('public_author_articles_requests_total', 'Public author articles requests') if Counter else None
PUBLIC_AUTHOR_ARTICLES_ZERO_RESULT_TOTAL = Counter('public_author_articles_zero_result_total', 'Public author articles zero results') if Counter else None
