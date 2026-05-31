"""认证业务逻辑层 — 供 routes.py 编排调用"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app

from .. import bcrypt, db, redis_client
from ..models import User


def _get_redis():
    """获取 Redis 客户端（支持 FakeRedis monkeypatch）。"""
    try:
        from .. import redis_client as global_rc
    except Exception:
        global_rc = None
    module_rc = globals().get('redis_client')
    for candidate in (module_rc, global_rc):
        if candidate is not None:
            if candidate.__class__.__name__.lower().startswith('fake'):
                return candidate
    if module_rc is not None:
        return module_rc
    if global_rc is not None:
        return global_rc
    if current_app:
        return current_app.extensions.get('redis_client')
    return None


def generate_tokens(user_id: int, role: str) -> tuple[str, str]:
    """生成 access + refresh JWT 令牌对，并注册到 Redis。"""
    secret = current_app.config['JWT_SECRET_KEY']
    now = datetime.now(timezone.utc)
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())
    user_sub = str(user_id)

    access_payload = {
        'sub': user_sub, 'role': role, 'type': 'access', 'jti': access_jti,
        'exp': now + timedelta(minutes=current_app.config['JWT_ACCESS_MINUTES']),
        'iat': now,
    }
    refresh_payload = {
        'sub': user_sub, 'role': role, 'type': 'refresh', 'jti': refresh_jti,
        'exp': now + timedelta(days=current_app.config['JWT_REFRESH_DAYS']),
        'iat': now,
    }

    access = jwt.encode(access_payload, secret, algorithm='HS256')
    refresh = jwt.encode(refresh_payload, secret, algorithm='HS256')

    rc = _get_redis()
    if rc:
        ttl = int((refresh_payload['exp'] - now).total_seconds())
        try:
            rc.setex(f'refresh:allow:{refresh_jti}', ttl, '1')
            rc.setex(f'refresh:user:{user_sub}:{refresh_jti}', ttl, '1')
            rc.setex(f'refresh:current:{user_sub}', ttl, refresh_jti)
        except Exception:
            pass
    return access, refresh


def register_user(email: str, password: str) -> User:
    """注册新用户。"""
    if User.query.filter_by(email=email).first():
        raise ValueError('email_exists')
    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password_hash=pw_hash, role='author')
    db.session.add(user)
    db.session.commit()
    return user


def authenticate(email: str, password: str) -> tuple[User, str, str] | None:
    """验证登录，成功返回 (user, access, refresh)。"""
    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return None
    access, refresh = generate_tokens(user.id, user.role)
    return user, access, refresh


def check_brute_force(email: str, ip: str) -> int:
    """检查暴力破解计数，返回当前失败次数。"""
    rc = _get_redis()
    if not rc:
        return 0
    bf_key = f"login:bf:{email}:{ip}"
    try:
        fails = int(rc.get(bf_key) or 0)
        return fails
    except Exception:
        return 0


def record_login_failure(email: str, ip: str, user_id: int | None = None) -> int:
    """记录登录失败并返回当前失败次数。"""
    rc = _get_redis()
    if not rc:
        return 0
    bf_key = f"login:bf:{email}:{ip}"
    try:
        new_fails = rc.incr(bf_key)
        if new_fails == 1:
            rc.expire(bf_key, 900)
        return new_fails
    except Exception:
        return 0


def clear_brute_force(email: str, ip: str):
    """清除暴力破解计数。"""
    rc = _get_redis()
    if not rc:
        return
    bf_key = f"login:bf:{email}:{ip}"
    try:
        rc.delete(bf_key)
    except Exception:
        pass


def refresh_tokens(refresh_token: str, xsrf_cookie: str, xsrf_header: str) -> tuple[str, str] | None:
    """刷新令牌对。返回 (new_access, new_refresh) 或 None。"""
    if not xsrf_cookie or not xsrf_header or xsrf_cookie != xsrf_header:
        return None
    if not refresh_token:
        return None
    try:
        payload = jwt.decode(refresh_token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        if payload.get('type') != 'refresh':
            return None
        jti = payload.get('jti')
        sub = payload.get('sub')
        rc = _get_redis()
        if rc:
            current_jti = rc.get(f'refresh:current:{sub}') if hasattr(rc, 'get') else None
            if rc.get(f'refresh:blacklist:{jti}') or not rc.get(f'refresh:allow:{jti}') or (current_jti and current_jti != jti):
                return None
    except Exception:
        return None

    new_access, new_refresh = generate_tokens(payload['sub'], payload.get('role'))

    rc = _get_redis()
    if rc and payload.get('jti'):
        ttl = int(payload['exp'] - datetime.now(timezone.utc).timestamp())
        if ttl > 0:
            try:
                rc.setex(f"refresh:blacklist:{payload['jti']}", ttl, '1')
            except Exception:
                pass
            try:
                rc.delete(f"refresh:allow:{payload.get('jti')}")
            except Exception:
                pass

    return new_access, new_refresh


def revoke_refresh(refresh_token: str):
    """吊销 refresh token（登出）。"""
    if not refresh_token:
        return
    rc = _get_redis()
    if not rc:
        return
    try:
        payload = jwt.decode(refresh_token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        if payload.get('type') == 'refresh':
            ttl = int(payload['exp'] - datetime.now(timezone.utc).timestamp())
            if ttl > 0:
                try:
                    rc.setex(f"refresh:blacklist:{payload.get('jti')}", ttl, '1')
                except Exception:
                    pass
    except Exception:
        pass


def change_password(email: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """修改密码。成功返回 (True, 'ok')，失败返回 (False, 错误消息)。"""
    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, old_password):
        return False, 'invalid_credentials'

    user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()

    # 吊销该用户的所有 refresh token
    rc = _get_redis() or redis_client
    if rc:
        try:
            allow_keys = []
            user_keys = []
            try:
                for k in rc.scan_iter(match='refresh:allow:*'):
                    allow_keys.append(k)
            except Exception:
                store = getattr(rc, 'store', {})
                allow_keys = [k for k in store.keys() if k.startswith('refresh:allow:')]
            try:
                for k in rc.scan_iter(match=f'refresh:user:{user.id}:*'):
                    user_keys.append(k)
            except Exception:
                store = getattr(rc, 'store', {})
                user_keys = [k for k in store.keys() if k.startswith(f'refresh:user:{user.id}:')]
            for k in allow_keys + user_keys:
                jti = k.split(':')[-1]
                try:
                    rc.setex(f'refresh:blacklist:{jti}', 3600, '1')
                except Exception:
                    pass
                try:
                    rc.delete(k)
                except Exception:
                    pass
        except Exception:
            pass
    return True, 'ok'
