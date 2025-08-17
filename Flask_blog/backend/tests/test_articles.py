import json

def test_create_article_flow(client):
    # 先注册并登录
    client.post('/api/v1/auth/register', json={'email':'a@test.com','password':'pass123'})
    login_resp = client.post('/api/v1/auth/login', json={'email':'a@test.com','password':'pass123'})
    access = login_resp.get_json()['data']['access_token']

    # 创建文章
    r = client.post('/api/v1/articles/', json={'title':'测试标题','content_md':'内容','tags':['测试','示例']}, headers={'Authorization':'Bearer '+access})
    assert r.status_code == 201
    slug = r.get_json()['data']['slug']

    # 获取文章（通过 slug）
    r2 = client.get(f'/api/v1/articles/slug/{slug}')
    assert r2.status_code == 200
    body = r2.get_json()['data']
    assert body['title'] == '测试标题'
    assert '测试' in body['tags']
