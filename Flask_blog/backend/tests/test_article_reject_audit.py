def test_reject_and_audit_logs(client):
    # 注册作者 & 编辑
    client.post('/api/v1/auth/register', json={'email':'author2@test.com','password':'pass123'})
    client.post('/api/v1/auth/register', json={'email':'editor2@test.com','password':'pass123'})

    # 登录作者创建文章
    login_author = client.post('/api/v1/auth/login', json={'email':'author2@test.com','password':'pass123'})
    token_author = login_author.get_json()['data']['access_token']
    create = client.post('/api/v1/articles/', json={'title':'审核文章','content_md':'内容'}, headers={'Authorization':'Bearer '+token_author})
    art_id = create.get_json()['data']['id']

    # 作者提交
    submit = client.post(f'/api/v1/articles/{art_id}/submit', headers={'Authorization':'Bearer '+token_author})
    assert submit.status_code == 200

    # 升级第二个用户为 editor
    from app import db
    from app.models import User
    with client.application.app_context():
        e = User.query.filter_by(email='editor2@test.com').first()
        e.role = 'editor'
        db.session.commit()

    # 登录编辑
    login_editor = client.post('/api/v1/auth/login', json={'email':'editor2@test.com','password':'pass123'})
    token_editor = login_editor.get_json()['data']['access_token']

    # 编辑拒绝
    reject = client.post(f'/api/v1/articles/{art_id}/reject', json={'reason':'质量不达标'}, headers={'Authorization':'Bearer '+token_editor})
    assert reject.status_code == 200
    assert reject.get_json()['data']['status'] == 'draft'

    # 查询审计日志
    logs = client.get(f'/api/v1/articles/{art_id}/audit_logs', headers={'Authorization':'Bearer '+token_editor})
    assert logs.status_code == 200
    arr = logs.get_json()['data']
    actions = [l['action'] for l in arr]
    assert 'submit' in actions and 'reject' in actions
