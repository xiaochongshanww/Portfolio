from datetime import datetime, timezone
import json

def register_and_login(client, email, password='pass123', role=None):
    """注册并登录。若需要升级角色，使用应用上下文修改数据库。"""
    client.post('/api/v1/auth/register', json={'email':email,'password':password})
    if role and role != 'author':
        from app import db
        from app.models import User
        # 在测试 client 中获取 application 对象
        app = client.application
        with app.app_context():
            u = User.query.filter_by(email=email).first()
            u.role = role
            db.session.commit()
    login = client.post('/api/v1/auth/login', json={'email':email,'password':password})
    payload = login.get_json() or {}
    assert login.status_code == 200 and payload.get('data'), f"login failed: {login.status_code} {payload}"
    return payload['data']['access_token']

def create_article_api(client, token, status='draft'):
    r = client.post('/api/v1/articles/', json={'title':f'T-{status}','content_md':'x'}, headers={'Authorization':'Bearer '+token})
    payload = r.get_json() or {}
    assert r.status_code == 201 and payload.get('data'), f"create article failed: {r.status_code} {payload}"
    aid = payload['data']['id']
    return aid

def _get_slug(client, token, article_id):
    r = client.get(f'/api/v1/articles/{article_id}', headers={'Authorization':'Bearer '+token})
    payload = r.get_json() or {}
    assert r.status_code == 200, f"detail failed: {r.status_code} {payload}"
    return payload['data']['slug']

def test_slug_anonymous_and_published_visibility(client):
    token_author = register_and_login(client, 's1@example.com')
    draft_pub_id = create_article_api(client, token_author)
    draft_hidden_id = create_article_api(client, token_author)
    slug_pub = _get_slug(client, token_author, draft_pub_id)
    slug_hidden = _get_slug(client, token_author, draft_hidden_id)
    token_editor = register_and_login(client, 's_editor@example.com', role='editor')
    # publish first draft
    client.post(f'/api/v1/articles/{draft_pub_id}/submit', headers={'Authorization':'Bearer '+token_author})
    client.post(f'/api/v1/articles/{draft_pub_id}/approve', headers={'Authorization':'Bearer '+token_editor})
    r_ok = client.get(f'/api/v1/articles/slug/{slug_pub}')
    r_hidden = client.get(f'/api/v1/articles/slug/{slug_hidden}')
    assert r_ok.status_code == 200
    assert r_hidden.status_code == 404

def test_slug_author_can_view_own_draft(client):
    token_author = register_and_login(client, 's2@example.com')
    draft_id = create_article_api(client, token_author)
    slug = _get_slug(client, token_author, draft_id)
    r = client.get(f'/api/v1/articles/slug/{slug}', headers={'Authorization':'Bearer '+token_author})
    assert r.status_code == 200

def test_slug_other_author_cannot_view_draft(client):
    token_a1 = register_and_login(client, 's3@example.com')
    token_a2 = register_and_login(client, 's4@example.com')
    draft_id = create_article_api(client, token_a1)
    slug = _get_slug(client, token_a1, draft_id)
    r = client.get(f'/api/v1/articles/slug/{slug}', headers={'Authorization':'Bearer '+token_a2})
    assert r.status_code == 404

def test_slug_editor_can_view_draft(client):
    token_author = register_and_login(client, 's5@example.com')
    token_editor = register_and_login(client, 's6@example.com', role='editor')
    draft_id = create_article_api(client, token_author)
    slug = _get_slug(client, token_author, draft_id)
    r = client.get(f'/api/v1/articles/slug/{slug}', headers={'Authorization':'Bearer '+token_editor})
    assert r.status_code == 200


def test_anonymous_only_sees_published(client, app):
    # 一个作者创建 draft 与 published（published 通过 approve 流程）
    token_author = register_and_login(client, 'a1@example.com')
    draft_id = create_article_api(client, token_author, 'draft')
    # 额外创建一个仍为 draft 的文章用于列表过滤验证
    another_draft_id = create_article_api(client, token_author, 'draft')
    # 为模拟 published：提交 + 用编辑账号审核
    token_editor = register_and_login(client, 'ed1@example.com', role='editor')
    submit = client.post(f'/api/v1/articles/{draft_id}/submit', headers={'Authorization':'Bearer '+token_author})
    submit_payload = submit.get_json()
    assert submit.status_code == 200, f"submit failed: {submit.status_code} {submit_payload}"
    approve = client.post(f'/api/v1/articles/{draft_id}/approve', headers={'Authorization':'Bearer '+token_editor})
    approve_payload = approve.get_json()
    assert approve.status_code == 200, f"approve failed: {approve.status_code} {approve_payload}"
    pub_id = draft_id  # now published
    r = client.get('/api/v1/articles/?page=1&page_size=10')
    data = r.get_json()['data']
    ids = [i['id'] for i in data['list']]
    assert pub_id in ids
    assert another_draft_id not in ids
    r2 = client.get(f'/api/v1/articles/{another_draft_id}')
    assert r2.status_code == 404


def test_author_can_view_own_draft(app, client):
    token = register_and_login(client, 'a2@example.com')
    draft_id = create_article_api(client, token, 'draft')
    r = client.get(f'/api/v1/articles/{draft_id}', headers={'Authorization':'Bearer '+token})
    assert r.status_code == 200


def test_other_author_cannot_view_draft(app, client):
    token_a1 = register_and_login(client, 'a3@example.com')
    token_a2 = register_and_login(client, 'a4@example.com')
    draft_id = create_article_api(client, token_a1, 'draft')
    r = client.get(f'/api/v1/articles/{draft_id}', headers={'Authorization':'Bearer '+token_a2})
    assert r.status_code == 404


def test_editor_can_view_draft(app, client):
    token_author = register_and_login(client, 'a5@example.com')
    token_editor = register_and_login(client, 'ed2@example.com', role='editor')
    draft_id = create_article_api(client, token_author, 'draft')
    r = client.get(f'/api/v1/articles/{draft_id}', headers={'Authorization':'Bearer '+token_editor})
    assert r.status_code == 200
