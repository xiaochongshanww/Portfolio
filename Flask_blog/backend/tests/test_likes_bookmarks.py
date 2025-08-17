def test_like_bookmark_flow(client):
    # 注册并登录
    client.post('/api/v1/auth/register', json={'email':'lb@test.com','password':'pass123'})
    login = client.post('/api/v1/auth/login', json={'email':'lb@test.com','password':'pass123'})
    token = login.get_json()['data']['access_token']

    # 创建文章
    create = client.post('/api/v1/articles/', json={'title':'Like文章','content_md':'内容'}, headers={'Authorization':'Bearer '+token})
    slug = create.get_json()['data']['slug']
    art_detail = client.get(f'/api/v1/articles/slug/{slug}')
    art_id = art_detail.get_json()['data']['id']

    # 发布模拟
    from app import db
    from app.models import Article
    with client.application.app_context():
        art = Article.query.get(art_id)
        art.status = 'published'
        db.session.commit()

    # 点赞
    r = client.post(f'/api/v1/articles/{art_id}/like', headers={'Authorization':'Bearer '+token})
    assert r.status_code == 200
    assert r.get_json()['data']['action'] == 'liked'
    # 取消点赞
    r2 = client.post(f'/api/v1/articles/{art_id}/like', headers={'Authorization':'Bearer '+token})
    assert r2.get_json()['data']['action'] == 'unliked'

    # 收藏
    b1 = client.post(f'/api/v1/articles/{art_id}/bookmark', headers={'Authorization':'Bearer '+token})
    assert b1.get_json()['data']['action'] == 'bookmarked'
    # 取消收藏
    b2 = client.post(f'/api/v1/articles/{art_id}/bookmark', headers={'Authorization':'Bearer '+token})
    assert b2.get_json()['data']['action'] == 'removed'
