def test_internal_article_detail_etag(client):
    # 注册并登录
    client.post('/api/v1/auth/register', json={'email':'d1@test.com','password':'pass123'})
    login = client.post('/api/v1/auth/login', json={'email':'d1@test.com','password':'pass123'})
    assert login.status_code == 200, f"login failed: {login.status_code} {login.get_json()}"
    token = login.get_json()['data']['access_token']
    # 创建文章
    create = client.post('/api/v1/articles/', json={'title':'细节文章','content_md':'正文'}, headers={'Authorization':'Bearer '+token})
    art_id = create.get_json()['data']['id']
    # 第一次获取
    r1 = client.get(f'/api/v1/articles/{art_id}')
    assert r1.status_code == 200
    etag = r1.headers.get('ETag')
    assert etag
    # 条件请求
    r2 = client.get(f'/api/v1/articles/{art_id}', headers={'If-None-Match': etag})
    assert r2.status_code == 304


def test_internal_article_slug_detail_etag(client):
    client.post('/api/v1/auth/register', json={'email':'d2@test.com','password':'pass123'})
    login = client.post('/api/v1/auth/login', json={'email':'d2@test.com','password':'pass123'})
    assert login.status_code == 200, f"login failed: {login.status_code} {login.get_json()}"
    token = login.get_json()['data']['access_token']
    create = client.post('/api/v1/articles/', json={'title':'Slug细节','content_md':'正文'}, headers={'Authorization':'Bearer '+token})
    slug = create.get_json()['data']['slug']
    r1 = client.get(f'/api/v1/articles/slug/{slug}')
    assert r1.status_code == 200
    etag = r1.headers.get('ETag')
    assert etag
    r2 = client.get(f'/api/v1/articles/slug/{slug}', headers={'If-None-Match': etag})
    assert r2.status_code == 304
