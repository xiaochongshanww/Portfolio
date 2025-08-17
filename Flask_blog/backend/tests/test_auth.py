from app import db
from app.models import User
from flask_bcrypt import Bcrypt
import json

def test_register_login(client, app):
    # register
    resp = client.post('/api/v1/auth/register', json={'email':'u1@test.com','password':'pass123'})
    assert resp.status_code == 201
    # login
    resp = client.post('/api/v1/auth/login', json={'email':'u1@test.com','password':'pass123'})
    if resp.status_code != 200:
        print('login fail payload:', resp.get_json())
    print('login Set-Cookie headers:', resp.headers.getlist('Set-Cookie'))
    # inspect client stored cookies
    try:
        jar = getattr(client, 'cookie_jar', None)
        if jar:
            print('client cookies after login:', [(c.name, c.value, c.domain, c.path) for c in jar])
    except Exception as e:
        print('cookie jar inspect error', e)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['code'] == 0
    # refresh
    refresh_resp = client.post('/api/v1/auth/refresh')
    print('refresh status:', refresh_resp.status_code, 'body:', refresh_resp.get_json())
    assert refresh_resp.status_code == 200
    assert 'access_token' in refresh_resp.get_json()['data']
    # logout
    logout_resp = client.post('/api/v1/auth/logout')
    assert logout_resp.status_code == 200
