import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Patch limiter BEFORE importing app
import flask_limiter
class _NoopLimiter:
    def __init__(self,*a,**k): pass
    def limit(self,*a,**k):
        def deco(fn): return fn
        return deco
    def init_app(self, app): pass
flask_limiter.Limiter = _NoopLimiter

# Patch redis.from_url BEFORE importing app
import redis as _r
class FakeRedis:
    def __init__(self): self.store={}
    def get(self,k): return self.store.get(k)
    def setex(self,k,t,v): self.store[k]=v
    def delete(self,k): self.store.pop(k, None)
    def scan_iter(self, match=None): return iter([])
    def ping(self): return True
_r.from_url = lambda *a, **k: FakeRedis()

from app import create_app, db

app = create_app()
app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://')

# Patch search ensure_index similar to conftest
from app.search import client as sc_client, indexer as sc_indexer, routes as sc_routes
class DummyIdx:
    def search(self,q,params=None): return {'estimatedTotalHits':0,'hits':[]}
    def add_documents(self,docs): pass
    def delete_document(self,doc_id): pass
    def delete_all_documents(self): pass
sc_client.ensure_index = lambda : DummyIdx()
sc_indexer.ensure_index = lambda : DummyIdx()
sc_routes.ensure_index = lambda : DummyIdx()

with app.app_context():
    db.create_all()
    c = app.test_client()
    r1 = c.post('/api/v1/auth/register', json={'email':'dbg@test.com','password':'pass123'})
    print('REGISTER STATUS', r1.status_code, 'BODY', r1.get_data(as_text=True))
    r2 = c.post('/api/v1/auth/login', json={'email':'dbg@test.com','password':'pass123'})
    print('LOGIN STATUS', r2.status_code, 'BODY', r2.get_data(as_text=True))
    if r2.status_code == 200:
        access = r2.get_json()['data']['access_token']
        r3 = c.post('/api/v1/articles/', json={'title':'测试标题','content_md':'内容','tags':['测试','示例']}, headers={'Authorization':'Bearer '+access})
        print('ARTICLE STATUS', r3.status_code, 'BODY', r3.get_data(as_text=True))
    else:
        print('Skip article create due to login failure')
