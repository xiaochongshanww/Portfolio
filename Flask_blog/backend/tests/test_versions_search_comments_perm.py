from datetime import datetime, timezone

def login_token(client, email, role=None):
    client.post('/api/v1/auth/register', json={'email':email,'password':'pass123'})
    if role and role != 'author':
        from app import db
        from app.models import User
        with client.application.app_context():
            u = User.query.filter_by(email=email).first(); u.role = role; db.session.commit()
    r = client.post('/api/v1/auth/login', json={'email':email,'password':'pass123'})
    return r.get_json()['data']['access_token']

def create_article(client, token, title='A1'):
    r = client.post('/api/v1/articles/', json={'title':title,'content_md':'Hello'}, headers={'Authorization':'Bearer '+token})
    data = r.get_json()['data']; return data['id'], data['slug']

def publish_article(client, aid, author_token, editor_token):
    client.post(f'/api/v1/articles/{aid}/submit', headers={'Authorization':'Bearer '+author_token})
    client.post(f'/api/v1/articles/{aid}/approve', headers={'Authorization':'Bearer '+editor_token})

def test_article_versions_flow(client):
    author = login_token(client,'v_author@test.com')
    editor = login_token(client,'v_editor@test.com', role='editor')
    aid, _ = create_article(client, author, 'Versioned')
    # 修改文章内容并创建多个版本
    for content in ['First body','Second body']:
        # 更新产生自动版本 (n)
        client.put(f'/api/v1/articles/{aid}', json={'content_md':content}, headers={'Authorization':'Bearer '+author})
        # 显式再创建一个快照 (n+1)
        client.post(f'/api/v1/articles/{aid}/versions', headers={'Authorization':'Bearer '+author})
    # 列出版本
    lst = client.get(f'/api/v1/articles/{aid}/versions', headers={'Authorization':'Bearer '+author}).get_json()['data']
    # 两轮：每轮更新自动 + 手动 -> 4 个版本号 1..4
    assert {v['version_no'] for v in lst} == {1,2,3,4}
    # 回滚到版本1
    rb = client.post(f'/api/v1/articles/{aid}/versions/1/rollback', headers={'Authorization':'Bearer '+author})
    assert rb.status_code == 200
    # 回滚生成新版本号 (5)
    get_v5 = client.get(f'/api/v1/articles/{aid}/versions/5', headers={'Authorization':'Bearer '+author})
    assert get_v5.status_code == 200

def test_search_fallback_and_tag_filter(client, app):
    author = login_token(client,'s_author@test.com')
    editor = login_token(client,'s_editor@test.com', role='editor')
    # 创建三篇文章：两篇含 tag x, 一篇含 tag y
    ids = []
    for i, tags in enumerate((['x'], ['x','y'], ['y'])):
        r = client.post('/api/v1/articles/', json={'title':f'SE{i}','content_md':'c','tags':tags}, headers={'Authorization':'Bearer '+author})
        ids.append(r.get_json()['data']['id'])
    # 全部发布
    for aid in ids:
        publish_article(client, aid, author, editor)
    # 强制 fallback (测试配置)
    app.config['SEARCH_FORCE_FALLBACK'] = True
    r = client.get('/api/v1/search/?q=SE&tags=x&match_mode=and&page=1&page_size=10')
    data = r.get_json()['data']
    assert data['total'] == 2
    titles = {item['title'] for item in data['list']}
    assert titles == {'SE0','SE1'}
    # OR 模式
    r2 = client.get('/api/v1/search/?q=SE&tags=x,y&match_mode=or')
    t2 = {i['title'] for i in r2.get_json()['data']['list']}
    assert t2 == {'SE0','SE1','SE2'}

def test_comment_visibility_permissions(client):
    author1 = login_token(client,'c_auth1@test.com')
    author2 = login_token(client,'c_auth2@test.com')
    editor = login_token(client,'c_editor@test.com', role='editor')
    # 文章属于 author1
    aid, slug = create_article(client, author1, 'CommentPerm')
    # 发布文章
    publish_article(client, aid, author1, editor)
    # 添加两条评论（均 pending）
    for content in ('P1','P2'):
        client.post('/api/v1/comments/', json={'article_id':aid,'content':'PENDING:'+content}, headers={'Authorization':'Bearer '+author1})
    # 普通另一作者访问树：只应看到 approved (此时为 0)
    tree_other = client.get(f'/api/v1/comments/article/{aid}/tree').get_json()['data']
    assert tree_other == []
    # 作者本人带 include=all 应该看到 pending
    tree_author_all = client.get(f'/api/v1/comments/article/{aid}/tree?include=all', headers={'Authorization':'Bearer '+author1}).get_json()['data']
    assert len(tree_author_all) == 2
    # 编辑也能看到 pending
    tree_editor_all = client.get(f'/api/v1/comments/article/{aid}/tree?include=all', headers={'Authorization':'Bearer '+editor}).get_json()['data']
    assert len(tree_editor_all) == 2
    # 审核其中一条
    first_id = tree_author_all[0]['id']
    client.post(f'/api/v1/comments/moderate/{first_id}', json={'action':'approve'}, headers={'Authorization':'Bearer '+editor})
    # 公共再次获取应只出现已审核 1 条
    public_tree = client.get(f'/api/v1/comments/article/{aid}/tree').get_json()['data']
    assert len(public_tree) == 1 and public_tree[0]['id'] == first_id
