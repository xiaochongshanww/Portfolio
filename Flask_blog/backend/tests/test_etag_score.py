def test_search_etag_and_score(client, monkeypatch):
    class DummyIdx:
        def search(self, q, params=None):
            return {
                'estimatedTotalHits': 2,
                'hits': [
                    {'id':1,'title':'Hello','content':'Hello World','slug':'hello','status':'published','published_at':'2024-01-01T00:00:00Z','created_at':'2024-01-01T00:00:00Z','tags':['t1'],'likes_count':0,'_rankingScore': 12.34,'_formatted': {'title':'<mark>Hello</mark>','content':'<mark>Hello</mark> World'}},
                    {'id':2,'title':'World','content':'World Text','slug':'world','status':'published','published_at':'2024-01-02T00:00:00Z','created_at':'2024-01-02T00:00:00Z','tags':['t2'],'likes_count':0,'_rankingScore': 5.6,'_formatted': {'title':'World','content':'World'}}
                ]
            }
    monkeypatch.setattr('app.search.client.ensure_index', lambda: DummyIdx(), raising=False)
    monkeypatch.setattr('app.search.indexer.ensure_index', lambda: DummyIdx(), raising=False)
    monkeypatch.setattr('app.search.routes.ensure_index', lambda: DummyIdx(), raising=False)

    r1 = client.get('/api/v1/search/', query_string={'q':'Hello'})
    assert r1.status_code == 200
    etag = r1.headers.get('ETag')
    assert etag
    data = r1.get_json()['data']
    assert len(data['list']) == 2
    assert 'score' in data['list'][0]
    # second conditional request
    r2 = client.get('/api/v1/search/', query_string={'q':'Hello'}, headers={'If-None-Match': etag})
    assert r2.status_code == 304


def test_public_article_list_etag(client):
    # create user & article then publish
    client.post('/api/v1/auth/register', json={'email':'pa@test.com','password':'pass123'})
    login = client.post('/api/v1/auth/login', json={'email':'pa@test.com','password':'pass123'})
    token = login.get_json()['data']['access_token']
    create = client.post('/api/v1/articles/', json={'title':'公开文章','content_md':'正文'}, headers={'Authorization':'Bearer '+token})
    art_id = create.get_json()['data']['id']
    # publish directly
    from app import db
    from app.models import Article
    with client.application.app_context():
        a = Article.query.get(art_id)
        a.status = 'published'
        db.session.commit()
    r1 = client.get('/api/v1/articles/public/')
    assert r1.status_code == 200
    etag = r1.headers.get('ETag')
    assert etag
    r2 = client.get('/api/v1/articles/public/', headers={'If-None-Match': etag})
    assert r2.status_code == 304


def test_internal_articles_list_etag(client):
    # create article (draft)
    client.post('/api/v1/auth/register', json={'email':'in@test.com','password':'pass123'})
    login = client.post('/api/v1/auth/login', json={'email':'in@test.com','password':'pass123'})
    token = login.get_json()['data']['access_token']
    client.post('/api/v1/articles/', json={'title':'内部文章','content_md':'正文'}, headers={'Authorization':'Bearer '+token})
    r1 = client.get('/api/v1/articles/')
    assert r1.status_code == 200
    etag = r1.headers.get('ETag')
    assert etag
    r2 = client.get('/api/v1/articles/', headers={'If-None-Match': etag})
    assert r2.status_code == 304


def test_admin_users_list_etag(client):
    # register & promote to admin
    client.post('/api/v1/auth/register', json={'email':'admin@test.com','password':'pass123'})
    login = client.post('/api/v1/auth/login', json={'email':'admin@test.com','password':'pass123'})
    token = login.get_json()['data']['access_token']
    from app import db
    from app.models import User
    with client.application.app_context():
        u = User.query.filter_by(email='admin@test.com').first()
        u.role = 'admin'
        db.session.commit()
    r1 = client.get('/api/v1/users/', headers={'Authorization':'Bearer '+token})
    assert r1.status_code == 200
    etag = r1.headers.get('ETag')
    assert etag
    r2 = client.get('/api/v1/users/', headers={'Authorization':'Bearer '+token, 'If-None-Match': etag})
    assert r2.status_code == 304


def test_public_author_profile_etag(client):
    # create author & publish article to update count
    client.post('/api/v1/auth/register', json={'email':'authorp@test.com','password':'pass123'})
    login = client.post('/api/v1/auth/login', json={'email':'authorp@test.com','password':'pass123'})
    token = login.get_json()['data']['access_token']
    create = client.post('/api/v1/articles/', json={'title':'A1','content_md':'正文'}, headers={'Authorization':'Bearer '+token})
    art_id = create.get_json()['data']['id']
    from app import db
    from app.models import Article, User
    with client.application.app_context():
        a = Article.query.get(art_id)
        a.status = 'published'
        db.session.commit()
        uid = User.query.filter_by(email='authorp@test.com').first().id
    r1 = client.get(f'/api/v1/users/public/{uid}')
    assert r1.status_code == 200
    etag = r1.headers.get('ETag')
    assert etag
    r2 = client.get(f'/api/v1/users/public/{uid}', headers={'If-None-Match': etag})
    assert r2.status_code == 304
