"""认证路由 — 仅负责 HTTP 编排，业务逻辑委托给 service.py"""

import secrets
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, make_response, request

from .. import bcrypt, db, limiter, require_auth
from ..models import User
from .service import (
    authenticate,
    change_password,
    check_brute_force,
    clear_brute_force,
    generate_tokens,
    record_login_failure,
    refresh_tokens,
    register_user,
    revoke_refresh,
)

# pydantic 验证
try:
    from pydantic import BaseModel, EmailStr, ValidationError, field_validator
    HAS_PYDANTIC = True
except Exception:
    HAS_PYDANTIC = False
    class BaseModel: pass
    class EmailStr(str): pass
    def ValidationError(*a, **k): return Exception('validation error')
    def field_validator(*a, **k):
        def deco(fn): return fn
        return deco

auth_bp = Blueprint('auth', __name__)

if HAS_PYDANTIC:
    class RegisterModel(BaseModel):
        email: EmailStr
        password: str
        @field_validator('password')
        @classmethod
        def pwd_len(cls, v):
            if not (6 <= len(v) <= 128):
                raise ValueError('password length 6-128')
            return v
    class LoginModel(BaseModel):
        email: EmailStr
        password: str
        @field_validator('password')
        @classmethod
        def pwd_len(cls, v):
            if not (6 <= len(v) <= 128):
                raise ValueError('password length 6-128')
            return v
    class ChangePasswordModel(BaseModel):
        email: EmailStr
        old_password: str
        new_password: str
        @field_validator('old_password','new_password')
        @classmethod
        def pwd_len(cls, v):
            if not (6 <= len(v) <= 128):
                raise ValueError('password length 6-128')
            return v
else:
    class RegisterModel: pass
    class LoginModel: pass
    class ChangePasswordModel: pass


def _make_security_event(event_type, description, user_id=None, severity='low', source_ip=None, extra=None):
    """记录安全事件（容错）。"""
    try:
        from ..security import log_security_event
        log_security_event(
            event_type=event_type,
            description=description,
            source_ip=source_ip or request.remote_addr or '0.0.0.0',
            user_id=user_id,
            severity=severity,
            additional_data=extra or {},
        )
    except Exception:
        pass


def _issue_csrf(resp):
    """生成/刷新简易 CSRF Token (双提交 cookie 模式)。"""
    token = secrets.token_hex(16)
    resp.set_cookie('XSRF-TOKEN', token, httponly=False, samesite='Lax')
    return token


@auth_bp.route('/register', methods=['POST'])
@limiter.limit('5/minute')
def register():
    data = request.get_json() or {}
    try:
        parsed = RegisterModel(**data)
    except ValidationError as ve:
        return jsonify({'code': 4001, 'message': 'validation error', 'data': ve.errors()}), 400
    try:
        user = register_user(parsed.email, parsed.password)
        return jsonify({'code': 0, 'data': {'id': user.id, 'email': user.email}, 'message': 'ok'}), 201
    except ValueError as e:
        if str(e) == 'email_exists':
            return jsonify({'code': 4090, 'message': 'Email already exists'}), 409
        return jsonify({'code': 4001, 'message': str(e)}), 400


@auth_bp.route('/login', methods=['POST'])
@limiter.limit('10/minute')
def login():
    data = request.get_json() or {}
    try:
        parsed = LoginModel(**data)
    except ValidationError as ve:
        return jsonify({'code': 4001, 'message': 'validation error', 'data': ve.errors()}), 400

    email = parsed.email
    password = parsed.password
    ip = request.remote_addr or '0.0.0.0'

    # 暴力破解防护
    fails = check_brute_force(email, ip)
    if fails >= 5:
        return jsonify({'code': 4290, 'message': 'too many failed attempts'}), 429

    result = authenticate(email, password)
    if not result:
        new_fails = record_login_failure(email, ip)
        _make_security_event(
            'login_failure', f'登录失败: {email}',
            severity='low', extra={'email': email},
        )
        if new_fails >= 3:
            _make_security_event(
                'brute_force_attack',
                f'检测到暴力破解: {email}, 失败: {new_fails}次',
                severity='high' if new_fails >= 5 else 'medium',
                extra={'email': email, 'failed_attempts': new_fails},
            )
        return jsonify({'code': 4010, 'message': 'Invalid credentials'}), 401

    user, access, refresh = result
    clear_brute_force(email, ip)
    _make_security_event(
        'login_success', f'用户登录成功: {email}',
        severity='info', user_id=user.id,
        extra={'role': user.role, 'user_agent': (request.headers.get('User-Agent', '')[:100] or '')},
    )

    resp = make_response(jsonify({'code': 0, 'data': {'access_token': access, 'role': user.role}, 'message': 'ok'}))
    resp.set_cookie('refresh_token', refresh, httponly=True, samesite='Lax')
    _issue_csrf(resp)
    return resp


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    result = refresh_tokens(
        request.cookies.get('refresh_token'),
        request.cookies.get('XSRF-TOKEN'),
        request.headers.get('X-XSRF-TOKEN'),
    )
    if not result:
        return jsonify({'code': 4010, 'message': 'refresh failed'}), 401
    new_access, new_refresh = result
    resp = make_response(jsonify({'code': 0, 'data': {'access_token': new_access}, 'message': 'ok'}))
    resp.set_cookie('refresh_token', new_refresh, httponly=True, samesite='Lax')
    _issue_csrf(resp)
    return resp


@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    revoke_refresh(request.cookies.get('refresh_token'))
    resp = jsonify({'code': 0, 'message': 'ok'})
    resp.delete_cookie('refresh_token')
    return resp


@auth_bp.route('/change_password', methods=['POST'])
@require_auth
@limiter.limit('5/minute')
def change_password_route():
    data = request.get_json() or {}
    try:
        parsed = ChangePasswordModel(**data)
    except ValidationError as ve:
        return jsonify({'code': 4001, 'message': 'validation error', 'data': ve.errors()}), 400
    ok, msg = change_password(parsed.email, parsed.old_password, parsed.new_password)
    if not ok:
        return jsonify({'code': 4010, 'message': msg}), 401
    return jsonify({'code': 0, 'message': 'ok'})
