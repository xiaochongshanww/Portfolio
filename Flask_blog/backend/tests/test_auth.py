from app import db
from app.models import User
from flask_bcrypt import Bcrypt
import json


def _xsrf_header(client):
    """从 login 响应 Set-Cookie 中取 XSRF-TOKEN 并构造请求头（双提交 CSRF）。

    Werkzeug test client 的 cookie_jar 结构随版本变化，直接从响应头解析最稳定。
    """
    xsrf = None
    for c in getattr(client, '_xsrf', None) or []:
        xsrf = c
        break
    assert xsrf, 'XSRF-TOKEN not available (call _capture_xsrf after login)'
    return {'X-XSRF-TOKEN': xsrf}


def _capture_xsrf(client, resp):
    """解析 login 响应的 Set-Cookie 头并记录 XSRF-TOKEN 供后续请求使用。"""
    tokens = []
    for cookie in resp.headers.getlist('Set-Cookie'):
        if cookie.startswith('XSRF-TOKEN='):
            tokens.append(cookie.split('XSRF-TOKEN=', 1)[1].split(';', 1)[0])
    if tokens:
        client._xsrf = tokens


def test_register_login(client, app):
    # register
    resp = client.post('/api/v1/auth/register', json={'email':'u1@test.com','password':'pass123'})
    assert resp.status_code == 201
    # login
    resp = client.post('/api/v1/auth/login', json={'email':'u1@test.com','password':'pass123'})
    if resp.status_code != 200:
        print('login fail payload:', resp.get_json())
    print('login Set-Cookie headers:', resp.headers.getlist('Set-Cookie'))
    assert resp.status_code == 200
    _capture_xsrf(client, resp)
    data = resp.get_json()
    assert data['code'] == 0
    # refresh (双提交 CSRF：需携带 XSRF cookie + 头)
    refresh_resp = client.post('/api/v1/auth/refresh', headers=_xsrf_header(client))
    print('refresh status:', refresh_resp.status_code, 'body:', refresh_resp.get_json())
    assert refresh_resp.status_code == 200
    assert 'access_token' in refresh_resp.get_json()['data']
    # logout (需要 Bearer token)
    access_token = refresh_resp.get_json()['data']['access_token']
    logout_resp = client.post('/api/v1/auth/logout', headers={'Authorization': f'Bearer {access_token}'})
    assert logout_resp.status_code == 200
