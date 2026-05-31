"""应用配置类。"""

import os


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
    ENABLE_SCHEDULER = os.getenv('ENABLE_SCHEDULER', 'true').lower() == 'true'
    SCHEDULE_CHECK_INTERVAL = int(os.getenv('SCHEDULE_CHECK_INTERVAL', '60'))
    UPLOAD_DIR = os.getenv('UPLOAD_DIR', 'uploads')
    MAX_IMAGE_SIZE = int(os.getenv('MAX_IMAGE_SIZE', '2097152'))  # 2MB
    ALLOWED_IMAGE_TYPES = os.getenv('ALLOWED_IMAGE_TYPES', 'image/jpeg,image/png,image/webp').split(',')
    SUPPORTED_LOCALES = os.getenv('SUPPORTED_LOCALES', 'en,zh').split(',')
    DEFAULT_LOCALE = os.getenv('DEFAULT_LOCALE', 'zh')
    AUTH_LOG_DETAIL = os.getenv('AUTH_LOG_DETAIL', 'true').lower() == 'true'

    # 缓存 TTL（秒）
    CACHE_ARTICLE_DETAIL_TTL = int(os.getenv('CACHE_ARTICLE_DETAIL_TTL', '300'))
    CACHE_ARTICLE_LIST_TTL = int(os.getenv('CACHE_ARTICLE_LIST_TTL', '120'))
    CACHE_SEARCH_TTL = int(os.getenv('CACHE_SEARCH_TTL', '60'))
    CACHE_PUBLIC_LIST_TTL = int(os.getenv('CACHE_PUBLIC_LIST_TTL', '120'))
    CACHE_PUBLIC_ARTICLE_TTL = int(os.getenv('CACHE_PUBLIC_ARTICLE_TTL', '120'))
    # 分页默认值
    DEFAULT_PAGE_SIZE = int(os.getenv('DEFAULT_PAGE_SIZE', '10'))
    MAX_PAGE_SIZE = int(os.getenv('MAX_PAGE_SIZE', '50'))
    # 公开接口 CDN 缓存
    PUBLIC_CACHE_MAX_AGE = int(os.getenv('PUBLIC_CACHE_MAX_AGE', '60'))


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


CONFIG_MAP = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
