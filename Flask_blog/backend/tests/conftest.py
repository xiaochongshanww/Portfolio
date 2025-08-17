import sys, os
import types

# 在导入 app 之前处理依赖
from importlib import import_module

# 先将 backend 加入路径
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# 提前替换 flask_limiter.Limiter 为 no-op 版本，避免使用不支持的 storage uri
import flask_limiter
class _NoopLimiter:
    def __init__(self, *a, **k):
        pass
    def limit(self, *a, **k):
        def deco(fn):
            return fn
        return deco
    def init_app(self, app):
        pass
flask_limiter.Limiter = _NoopLimiter  # noqa

# 导入应用模块
import app as app_module

# FakeRedis 提供最小接口
class FakeRedis:
    def __init__(self):
        self.store = {}
    def get(self, key):
        return self.store.get(key)
    def setex(self, key, ttl, value):
        self.store[key] = value
    def delete(self, key):
        self.store.pop(key, None)
    def scan_iter(self, match=None):
        return iter([])
    def ping(self):
        return True

# patch redis.from_url 返回 FakeRedis
import redis as _redis_pkg
_orig_from_url = _redis_pkg.from_url

def _patched_from_url(url, *a, **k):
    return FakeRedis()
_redis_pkg.from_url = _patched_from_url  # noqa
app_module.redis.from_url = _patched_from_url  # 双重保障

# 强制使用内存 fake redis url（实际被 patched 函数忽略）
app_module.BaseConfig.REDIS_URL = 'redis://unused'
app_module.DevelopmentConfig.REDIS_URL = 'redis://unused'
app_module.ProductionConfig.REDIS_URL = 'redis://unused'

import pytest
from app import create_app, db

# Dummy 搜索索引
class DummyIdx:
    def search(self, q, params=None):
        return {'estimatedTotalHits': 0, 'hits': []}
    def add_documents(self, docs):
        pass
    def delete_document(self, doc_id):
        pass
    def delete_all_documents(self):
        pass

@pytest.fixture()
def app(monkeypatch):
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
    })

    # 搜索 ensure_index 替换
    def fake_ensure_index():
        return DummyIdx()
    monkeypatch.setattr('app.search.client.ensure_index', fake_ensure_index, raising=False)
    monkeypatch.setattr('app.search.indexer.ensure_index', fake_ensure_index, raising=False)
    monkeypatch.setattr('app.search.routes.ensure_index', fake_ensure_index, raising=False)

    with app.app_context():
        db.create_all()
    yield app

@pytest.fixture(autouse=True)
def _clean_db(app):
    # 每个测试前后清理，保持隔离
    with app.app_context():
        db.drop_all()
        db.create_all()
        # 清理 FakeRedis 缓存（避免跨测试缓存影响访问控制）
        try:
            from app import redis_client as _rc
            if _rc and hasattr(_rc, 'store'):
                _rc.store.clear()
        except Exception:
            pass
    yield

@pytest.fixture()
def client(app):
    return app.test_client()
