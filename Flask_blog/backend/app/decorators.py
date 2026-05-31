"""认证与权限装饰器。"""

from functools import wraps

import jwt
from flask import current_app, g, jsonify, request


def _get_user():
    """从 JWT Authorization header 提取用户信息。"""
    try:
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1]
            payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            return payload
    except Exception:
        pass
    return None


def require_auth(fn):
    """要求有效 JWT Access Token。失败返回 401。"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        payload = _get_user()
        if payload is None or payload.get('type') != 'access':
            return jsonify({'code': 2001, 'message': 'Authentication required'}), 401
        # 注入用户信息到 request
        setattr(request, 'user_id', int(payload['sub']))
        setattr(request, 'user_role', payload.get('role'))
        return fn(*args, **kwargs)
    return wrapper


def require_roles(*roles):
    """要求用户拥有指定角色之一。需先经过 @require_auth。"""
    def deco(fn):
        @wraps(fn)
        @require_auth
        def wrapper(*args, **kwargs):
            user_role = getattr(request, 'user_role', None)
            if user_role not in roles:
                return jsonify({'code': 2003, 'message': 'Insufficient permissions'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return deco
