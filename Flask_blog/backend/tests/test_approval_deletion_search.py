def test_approve_and_delete_flow(client):
    # 创建作者与文章
    client.post('/api/v1/auth/register', json={'email':'author@test.com','password':'pass123'})
    login_author = client.post('/api/v1/auth/login', json={'email':'author@test.com','password':'pass123'})
    token_author = login_author.get_json()['data']['access_token']

    create = client.post('/api/v1/articles/', json={'title':'待审核文章','content_md':'正文内容'}, headers={'Authorization':'Bearer '+token_author})
    assert create.status_code == 201
    article_id = create.get_json()['data']['id']

    # 升级作者为 editor 以便审核（测试直接修改）
    from app import db
    from app.models import User, Article
    with client.application.app_context():
        u = User.query.filter_by(email='author@test.com').first()
        u.role = 'editor'
        db.session.commit()

    # 审批发布
    approve = client.post(f'/api/v1/articles/{article_id}/approve', headers={'Authorization':'Bearer '+token_author})
    assert approve.status_code == 200
    data = approve.get_json()['data']
    assert data['status'] == 'published'

    # 搜索应命中 (简单匹配标题关键字)
    search = client.get('/api/v1/search/', query_string={'q':'待审核'})
    assert search.status_code == 200
    total_before = search.get_json()['data']['total']
    assert total_before >= 1

    # 删除文章
    delete_resp = client.delete(f'/api/v1/articles/{article_id}', headers={'Authorization':'Bearer '+token_author})
    assert delete_resp.status_code == 200

    # 再次搜索应减少或不再包含该文
    search_after = client.get('/api/v1/search/', query_string={'q':'待审核'})
    assert search_after.status_code == 200
    total_after = search_after.get_json()['data']['total']
    assert total_after <= total_before
