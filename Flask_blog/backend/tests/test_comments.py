def test_comment_flow(client):
    # 注册并登录用户A (作者)
    client.post('/api/v1/auth/register', json={'email':'c1@test.com','password':'pass123'})
    login = client.post('/api/v1/auth/login', json={'email':'c1@test.com','password':'pass123'})
    token_a = login.get_json()['data']['access_token']

    # 创建并发布文章（直接插入状态模拟，简化测试）
    create = client.post('/api/v1/articles/', json={'title':'评论文章','content_md':'x'}, headers={'Authorization':'Bearer '+token_a})
    slug = create.get_json()['data']['slug']
    # 获取文章 id（草稿需带授权才能访问内部接口）
    article_detail = client.get(f'/api/v1/articles/slug/{slug}', headers={'Authorization':'Bearer '+token_a})
    article_id = article_detail.get_json()['data']['id']

    # 直接修改数据库状态为 published（测试环境简单处理）
    from app import db
    from app.models import Article
    with client.application.app_context():
        art = Article.query.get(article_id)
        art.status = 'published'
        db.session.commit()

    # 添加评论
    r = client.post('/api/v1/comments/', json={'article_id':article_id,'content':'第一条评论'}, headers={'Authorization':'Bearer '+token_a})
    assert r.status_code == 201
