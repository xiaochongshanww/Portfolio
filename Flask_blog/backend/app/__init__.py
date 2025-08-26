import os
# Load environment variables at module import time
from dotenv import load_dotenv
load_dotenv()

# 添加 PyMySQL 兼容层
try:
    import pymysql  # type: ignore
    pymysql.install_as_MySQLdb()
except Exception:
    pass
from functools import wraps
from flask import Flask, request, jsonify, current_app, g, Response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import jwt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
import redis
import sqlalchemy
import time, uuid, logging, json
try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:
    BackgroundScheduler = None
# i18n
try:
    from flask_babel import Babel, gettext as _
except Exception:
    Babel = None
    _ = lambda x: x

# 配置类
class BaseConfig:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///dev.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret')
    CORS_SUPPORTS_CREDENTIALS = True
    JWT_ACCESS_MINUTES = int(os.getenv('JWT_ACCESS_MINUTES', '30'))
    JWT_REFRESH_DAYS = int(os.getenv('JWT_REFRESH_DAYS', '14'))
    REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
    RATE_LIMIT_DEFAULT_MINUTE = os.getenv('RATE_LIMIT_DEFAULT_MINUTE', '200')
    RATE_LIMIT_DEFAULT_DAY = os.getenv('RATE_LIMIT_DEFAULT_DAY', '2000')
    MEILISEARCH_URL = os.getenv('MEILISEARCH_URL', 'http://localhost:7700')
    VERSION = os.getenv('APP_VERSION', '0.6.9')
    ENABLE_SCHEDULER = os.getenv('ENABLE_SCHEDULER','true').lower() == 'true'
    SCHEDULE_CHECK_INTERVAL = int(os.getenv('SCHEDULE_CHECK_INTERVAL','60'))
    UPLOAD_DIR = os.getenv('UPLOAD_DIR','uploads')
    MAX_IMAGE_SIZE = int(os.getenv('MAX_IMAGE_SIZE','2097152'))  # 2MB
    ALLOWED_IMAGE_TYPES = os.getenv('ALLOWED_IMAGE_TYPES','image/jpeg,image/png,image/webp').split(',')
    SUPPORTED_LOCALES = os.getenv('SUPPORTED_LOCALES','en,zh').split(',')
    DEFAULT_LOCALE = os.getenv('DEFAULT_LOCALE','zh')
    AUTH_LOG_DETAIL = os.getenv('AUTH_LOG_DETAIL','true').lower() == 'true'

class DevelopmentConfig(BaseConfig):
    DEBUG = True

class ProductionConfig(BaseConfig):
    DEBUG = False

CONFIG_MAP = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
redis_client = None
limiter = None
babel = None


def create_app(config_name=None):
    global redis_client, limiter, babel
    if not config_name:
        config_name = os.getenv('FLASK_CONFIG', 'development')
    cfg_cls = CONFIG_MAP.get(config_name, DevelopmentConfig)
    app = Flask(__name__)
    app.config.from_object(cfg_cls)
    # 允许带/不带/ 都直接命中，避免 301/308 重定向导致某些环境下 Authorization 丢失
    try:
        app.url_map.strict_slashes = False
    except Exception:
        pass

    # 日志
    log_level = os.getenv('LOG_LEVEL','INFO').upper()
    handler = logging.StreamHandler()
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            base = {
                'level': record.levelname,
                'msg': record.getMessage(),
                'logger': record.name,
                'time': self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            }
            if hasattr(record, 'extra_data'):
                base.update(record.extra_data)
            return json.dumps(base, ensure_ascii=False)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(handler)
    root.setLevel(log_level)

    CORS(app, resources={
        r"/api/*": {
            "origins": os.getenv('CORS_ORIGINS', '*'),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "X-XSRF-TOKEN"],
            "supports_credentials": True
        },
        r"/uploads/*": {
            "origins": os.getenv('CORS_ORIGINS', '*'),
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": False
        },
        r"/public/*": {
            "origins": os.getenv('CORS_ORIGINS', '*'),
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": False
        }
    })

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)

    # Redis
    redis_client = None
    redis_url_for_limiter = None
    try:
        redis_client = redis.from_url(app.config['REDIS_URL'])
        # 主动探测，失败直接进入降级
        redis_client.ping()
        app.extensions['redis_client'] = redis_client
        redis_url_for_limiter = app.config['REDIS_URL']
        logging.info('Redis connected for limiter')
    except Exception as e:
        logging.warning('Redis unavailable, fallback to in-memory limiter: %s', e)
        redis_client = None
        app.extensions['redis_client'] = None
        # 内存限流（进程级，非分布式）
        redis_url_for_limiter = 'memory://'

    # Limiter (允许在没有 Redis 时回退内存)
    try:
        limiter = Limiter(
            get_remote_address,
            storage_uri=redis_url_for_limiter,
            default_limits=[f"{app.config['RATE_LIMIT_DEFAULT_MINUTE']}/minute", f"{app.config['RATE_LIMIT_DEFAULT_DAY']}/day"]
        )
        limiter.init_app(app)
        app.extensions['limiter'] = limiter
    except Exception as e:
        logging.error('Limiter init failed, disable rate limiting: %s', e)
        class _DummyLimiter:
            def limit(self, *_a, **_kw):
                def deco(f):
                    return f
                return deco
        limiter = _DummyLimiter()
        app.extensions['limiter'] = limiter

    # Babel
    if Babel:
        def select_locale():
            # 优先顺序: URL 查询 ?lang= / Header Accept-Language / 默认
            q = request.args.get('lang')
            if q and q in app.config['SUPPORTED_LOCALES']:
                return q
            header = request.headers.get('Accept-Language','')
            if header:
                # 简单解析, 取第一个匹配
                parts = [p.split(';')[0].strip() for p in header.split(',') if p]
                for p in parts:
                    if p in app.config['SUPPORTED_LOCALES']:
                        return p
                    # zh-CN -> zh
                    if '-' in p:
                        base = p.split('-',1)[0]
                        if base in app.config['SUPPORTED_LOCALES']:
                            return base
            return app.config['DEFAULT_LOCALE']
        babel = Babel(app, locale_selector=select_locale)

    # 蓝图
    from .auth.routes import auth_bp
    from .articles.routes import articles_bp
    from .comments.routes import comments_bp
    from .search.routes import search_bp
    from .search.synonyms import synonyms_bp
    from .docs.openapi import openapi_bp
    from .users.routes import users_bp
    from .taxonomy.routes import taxonomy_bp
    from .uploads.routes import uploads_bp
    from .metrics.routes import metrics_bp
    from .security.routes import security_bp
    from .settings.routes import settings_bp
    from .logs.routes import logs_bp
    from .simple_logs import simple_logs_bp
    from .public_api import public_bp
    from .middlewares import VisitorTrackingMiddleware

    # 初始化访客追踪中间件
    visitor_middleware = VisitorTrackingMiddleware(app)

    # OpenAPI 只注册一次 (根路径 /spec)
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
    # Public read-only namespace (versioned separately for stability)
    app.register_blueprint(public_bp, url_prefix='/public/v1')

    # 安装业务错误统一处理
    try:
        from .security.enforcer import install_business_error_handler
        install_business_error_handler(app)
    except Exception:
        pass

    # 确保上传目录存在
    up_dir = app.config['UPLOAD_DIR']
    try: os.makedirs(up_dir, exist_ok=True)
    except Exception: pass

    @app.route('/uploads/<path:filename>')
    @limiter.exempt  # 静态资源豁免rate limiting
    def serve_upload(filename):
        from flask import send_from_directory
        return send_from_directory(app.config['UPLOAD_DIR'], filename)

    # 启动定时发布调度器
    if getattr(app.config,'ENABLE_SCHEDULER', False) and BackgroundScheduler:
        scheduler = BackgroundScheduler(timezone='UTC')
        def publish_scheduled():
            from datetime import datetime, timezone
            from .models import Article
            from .search.indexer import index_article
            with app.app_context():
                now = datetime.now(timezone.utc)
                # 选出到期未发布
                due = Article.query.filter(Article.deleted==False, Article.status=='scheduled', Article.scheduled_at!=None, Article.scheduled_at <= now).all()
                changed = 0
                for a in due:
                    a.status = 'published'
                    if not a.published_at:
                        a.published_at = now
                    changed += 1
                if changed:
                    try:
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
                        return
                    for a in due:
                        try: index_article(a)
                        except Exception: pass
        scheduler.add_job(publish_scheduled, 'interval', seconds=app.config['SCHEDULE_CHECK_INTERVAL'], id='publish_scheduled', replace_existing=True)
        scheduler.start()
        app.extensions['scheduler'] = scheduler

    @app.before_request
    def _start_timer():
        g._start = time.time()
        g.request_id = request.headers.get('X-Request-ID') or uuid.uuid4().hex
        # （已解决 401 问题）去除针对 /admin/logs 的高频调试日志，仅保留轻量追踪
        if '/admin/logs' in request.path:
            auth = request.headers.get('Authorization','')
            current_app.logger.debug(f"logs_access {request.method} auth_present={bool(auth)}")
        if METRICS_ENABLED:
            g._hist_timer = HTTP_REQUEST_DURATION.labels(request.method, request.path).time()

    @app.after_request
    def add_security_headers(resp):
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('X-Frame-Options', 'DENY')
        resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        resp.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        resp.headers.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        csp = "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'"
        resp.headers.setdefault('Content-Security-Policy', csp)
        resp.headers.setdefault('X-Request-ID', getattr(g,'request_id',''))
        try:
            duration = int((time.time() - getattr(g,'_start', time.time()))*1000)
            logging.getLogger('request').info(
                f"{request.method} {request.path} {resp.status_code} {duration}ms",
                extra={
                    'extra_data': {
                        'request_id': getattr(g,'request_id', None),
                        'method': request.method,
                        'path': request.path,
                        'status': resp.status_code,
                        'duration_ms': duration,
                        'ip': request.remote_addr,
                        'user_id': getattr(request,'user_id', None),
                        'user_role': getattr(request,'user_role', None)
                    }
                }
            )
        except Exception:
            pass
        if METRICS_ENABLED:
            try:
                HTTP_REQUESTS_TOTAL.labels(request.method, request.path, str(resp.status_code)).inc()
                if hasattr(g,'_hist_timer'):
                    g._hist_timer.observe_duration()
            except Exception:
                pass
        return resp

    if METRICS_ENABLED:
        @app.route('/metrics')
        def metrics():
            return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({'code':4040,'message':_('not found')}), 404

    @app.errorhandler(405)
    def handle_405(e):
        return jsonify({'code':4050,'message':_('method not allowed')}), 405

    @app.errorhandler(RateLimitExceeded)
    def handle_ratelimit(e):
        return jsonify({'code':4290,'message':_('rate limit exceeded')}), 429

    @app.errorhandler(Exception)
    def handle_exception(e):
        if app.config.get('DEBUG') or app.config.get('TESTING'):
            return jsonify({'code':5000,'message':_('server error'),'detail':str(e)}), 500
        return jsonify({'code':5000,'message':_('server error')}), 500

    @app.route('/api/v1/ping')
    @limiter.limit('10/second')
    def ping():
        return {'code':0,'message':'pong'}

    @app.route('/api/v1/rum/metrics', methods=['POST'])
    def rum_metrics():
        if not METRICS_ENABLED:
            return {'code':0,'message':'disabled'}
        try:
            data = request.get_json() or {}
            metrics = data.get('metrics') or []
            for m in metrics:
                name = str(m.get('name','unknown'))[:32]
                val = m.get('value')
                try:
                    val = float(val)
                except Exception:
                    continue
                try:
                    RUM_WEB_VITALS.labels(name).observe(val/1000.0 if name not in ('CLS','TTFB') and val>10 else val/1000.0 if name=='TTFB' else val)
                except Exception:
                    pass
        except Exception:
            return {'code':400,'message':'bad metrics'}, 400
        return {'code':0,'message':'ok'}

    @app.route('/api/v1/health')
    def health():
        db_ok = True
        redis_ok = True
        search_ok = True
        try:
            with app.app_context():
                db.session.execute(sqlalchemy.text('SELECT 1'))
        except Exception:
            db_ok = False
        try:
            if not app.extensions.get('redis_client'):
                redis_ok = False
            else:
                app.extensions['redis_client'].ping()
        except Exception:
            redis_ok = False
        import requests
        try:
            url = app.config.get('MEILISEARCH_URL')
            if url:
                r = requests.get(f"{url}/health", timeout=0.5)
                if r.status_code >= 400:
                    search_ok = False
        except Exception:
            search_ok = False
        overall = db_ok and redis_ok and search_ok
        return jsonify({'code':0 if overall else 5001,'message':'ok' if overall else 'degraded','data':{
            'db': db_ok,
            'redis': redis_ok,
            'search': search_ok,
            'version': app.config.get('VERSION')
        }})

    @app.route('/api/v1/meta/version')
    def meta_version():
        return jsonify({'code':0,'message':'ok','data':{
            'version': app.config.get('VERSION'),
            'git_commit': os.getenv('GIT_COMMIT','unknown'),
            'build_time': os.getenv('BUILD_TIME','unknown')
        }})
    @app.route('/api/v1/meta/error-codes')
    def meta_error_codes():
        catalog = [
            {'code':0,'message':'ok','description':_('success')},
            {'code':4001,'message':'validation error','description':_('parameter validation failed')},
            {'code':4010,'message':'unauthorized','description':_('authentication failed or token invalid')},
            {'code':4030,'message':'forbidden','description':_('operation not permitted')},
            {'code':4040,'message':'not found','description':_('resource not found')},
            {'code':4050,'message':'method not allowed','description':_('http method not allowed')},
            {'code':4090,'message':'conflict','description':_('resource conflict (email/slug/concurrent)')},
            {'code':4290,'message':'rate limit exceeded','description':_('too many requests')},
            {'code':4401,'message':'upload invalid file','description':_('file missing or filename empty')},
            {'code':4402,'message':'upload type not allowed','description':_('unsupported mime type')},
            {'code':4403,'message':'upload too large','description':_('file size exceeds limit')},
            {'code':5000,'message':'server error','description':_('internal server error')},
            {'code':5001,'message':'degraded','description':_('service degraded')}
        ]
        return jsonify({'code':0,'message':'ok','data':catalog})

    @app.route('/sitemap.xml')
    def sitemap_xml():
        from datetime import datetime
        from .models import Article
        cache_key = 'sitemap:xml'
        xml = None
        if redis_client:
            try: xml = redis_client.get(cache_key)
            except Exception: xml = None
        if not xml:
            items = Article.query.filter_by(status='published', deleted=False).order_by(Article.published_at.desc()).limit(5000).all()
            base_url = request.url_root.rstrip('/')
            lines = ["<?xml version='1.0' encoding='UTF-8'?>", "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"]
            lines.append(f"<url><loc>{base_url}/</loc><priority>0.8</priority></url>")
            for a in items:
                loc = f"{base_url}/articles/{a.slug or a.id}"
                lastmod_dt = (a.updated_at or a.published_at or a.created_at)
                lastmod = lastmod_dt.strftime('%Y-%m-%dT%H:%M:%SZ') if lastmod_dt else ''
                lines.append(f"<url><loc>{loc}</loc>" + (f"<lastmod>{lastmod}</lastmod>" if lastmod else '') + "<changefreq>daily</changefreq><priority>0.6</priority></url>")
            lines.append("</urlset>")
            xml = "".join(lines)
            if redis_client:
                try: redis_client.setex(cache_key, 600, xml)
                except Exception: pass
        resp = Response(xml, mimetype='application/xml')
        resp.headers['Cache-Control'] = 'public, max-age=600'
        return resp

    @app.route('/robots.txt')
    def robots_txt():
        base_url = request.url_root.rstrip('/')
        content = f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n"
        resp = Response(content, mimetype='text/plain; charset=utf-8')
        resp.headers['Cache-Control'] = 'public, max-age=3600'
        return resp

    return app

# 鉴权工具

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization','')
        origin = request.headers.get('Origin', 'NO_ORIGIN')
        host = request.headers.get('Host', 'NO_HOST')
        referer = request.headers.get('Referer', 'NO_REFERER')
        current_app.logger.warning(f"[AUTH] 收到认证请求 - Origin:{origin}, Host:{host}, Referer:{referer}")
        current_app.logger.warning(f"[AUTH] Authorization头: {auth[:50]}..." if auth else "[AUTH] 无Authorization头")
        
        if not auth.startswith('Bearer '):
            current_app.logger.warning("[AUTH] 失败: 缺少Bearer token")
            return jsonify({'code':4010,'message':_('missing token')}), 401
        
        token = auth.split(' ',1)[1]
        current_app.logger.warning(f"[AUTH] 提取到token: {token[:50]}...")
        
        try:
            # 细分异常类型，便于定位 401 来源
            from jwt import ExpiredSignatureError, InvalidSignatureError, DecodeError, InvalidTokenError
            start_decode = time.time()
            payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            decode_ms = int((time.time()-start_decode)*1000)
            sub_val = payload.get('sub')
            raw_role = payload.get('role')
            token_type = payload.get('type')
            issued_at = payload.get('iat')
            exp_at = payload.get('exp')
            now_epoch = int(time.time())
            # 记录时间偏差（本地时钟 vs token）
            drift_iat = now_epoch - int(issued_at) if issued_at else None
            ttl_left = int(exp_at - now_epoch) if exp_at else None
            try:
                sub_val = int(sub_val)
            except Exception:
                pass
            request.user_id = sub_val
            request.user_role = raw_role
            if current_app.config.get('AUTH_LOG_DETAIL'):
                current_app.logger.warning(
                    json.dumps({
                        'auth_event':'success',
                        'user_id': sub_val,
                        'role': raw_role,
                        'token_type': token_type,
                        'decode_ms': decode_ms,
                        'drift_iat_s': drift_iat,
                        'ttl_left_s': ttl_left,
                        'path': request.path,
                        'method': request.method
                    }, ensure_ascii=False)
                )
        except Exception as e:  # 保持兼容，统一处理
            et = e.__class__.__name__
            msg = str(e)
            if current_app.config.get('AUTH_LOG_DETAIL'):
                current_app.logger.warning(json.dumps({
                    'auth_event':'failure',
                    'error_type': et,
                    'error_msg': msg,
                    'path': request.path,
                    'method': request.method,
                    'has_token': bool(token),
                    'token_prefix': token[:16] if auth.startswith('Bearer ') else None
                }, ensure_ascii=False))
            else:
                current_app.logger.warning(f"[AUTH] 失败: JWT解码错误 {et}: {msg}")
            return jsonify({'code':4010,'message':_('invalid token')}), 401
        return fn(*args, **kwargs)
    return wrapper

def require_roles(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not getattr(request, 'user_id', None):
                auth_resp = require_auth(lambda: None)()
                if auth_resp is not None:
                    return auth_resp
            if request.user_role not in roles:
                # 延迟导入避免循环依赖：只有在需要回源校验角色时才导入
                try:
                    from .models import User as _User  # 局部导入
                    u = _User.query.get(request.user_id)
                    if u and u.role in roles:
                        request.user_role = u.role
                    else:
                        return jsonify({'code':4030,'message':_('forbidden')}), 403
                except Exception:
                    return jsonify({'code':4030,'message':_('forbidden')}), 403
            return fn(*args, **kwargs)
        return wrapper
    return deco

# 指标
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    METRICS_ENABLED = True
    HTTP_REQUESTS_TOTAL = Counter('app_http_requests_total', 'Total HTTP requests', ['method','path','status'])
    HTTP_REQUEST_DURATION = Histogram('app_http_request_duration_seconds', 'Request duration seconds', ['method','path'])
    ARTICLE_PUBLISHED_TOTAL = Counter('app_article_published_total','Total articles published',['source'])
    SEARCH_QUERIES_TOTAL = Counter('app_search_queries_total','Total search queries')
    SEARCH_ZERO_RESULT_TOTAL = Counter('app_search_zero_result_total','Search queries resulting in zero hits')
    PUBLIC_AUTHOR_PROFILE_REQUESTS_TOTAL = Counter('app_public_author_profile_requests_total','Public author profile requests')
    PUBLIC_AUTHOR_ARTICLES_REQUESTS_TOTAL = Counter('app_public_author_articles_requests_total','Public author articles list requests')
    PUBLIC_AUTHOR_ARTICLES_ZERO_RESULT_TOTAL = Counter('app_public_author_articles_zero_result_total','Public author articles list zero result')
    CACHE_HIT_TOTAL = Counter('app_cache_hit_total','Cache hit total',['resource_type'])
    CACHE_MISS_TOTAL = Counter('app_cache_miss_total','Cache miss total',['resource_type'])
    RUM_WEB_VITALS = Histogram('app_rum_web_vitals','RUM Web Vitals values',['name'])
except Exception:
    METRICS_ENABLED = False
    ARTICLE_PUBLISHED_TOTAL = SEARCH_QUERIES_TOTAL = SEARCH_ZERO_RESULT_TOTAL = None
    PUBLIC_AUTHOR_PROFILE_REQUESTS_TOTAL = PUBLIC_AUTHOR_ARTICLES_REQUESTS_TOTAL = PUBLIC_AUTHOR_ARTICLES_ZERO_RESULT_TOTAL = None
    CACHE_HIT_TOTAL = CACHE_MISS_TOTAL = None

__all__ = ['db','bcrypt','redis_client','limiter','require_auth','require_roles','create_app',
           'METRICS_ENABLED','ARTICLE_PUBLISHED_TOTAL','SEARCH_QUERIES_TOTAL','SEARCH_ZERO_RESULT_TOTAL',
           'PUBLIC_AUTHOR_PROFILE_REQUESTS_TOTAL','PUBLIC_AUTHOR_ARTICLES_REQUESTS_TOTAL','PUBLIC_AUTHOR_ARTICLES_ZERO_RESULT_TOTAL',
           'CACHE_HIT_TOTAL','CACHE_MISS_TOTAL','RUM_WEB_VITALS']
