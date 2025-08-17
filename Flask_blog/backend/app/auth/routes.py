from flask import Blueprint, request, jsonify, current_app, make_response
from datetime import datetime, timedelta, timezone
import jwt, uuid
import secrets

# 仅使用正式 PyJWT，不再包含最小 fallback 实现

from .. import db, bcrypt, limiter, redis_client  # 添加 redis_client 方便 monkeypatch
from ..models import User
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

def _redis():
    # 优先使用测试 monkeypatch 的模块级 redis_client（FakeRedis），否则再取 app.extensions
    try:
        from .. import redis_client as global_rc
    except Exception:
        global_rc = None
    # 模块内（本文件）可能也被 monkeypatch
    module_rc = globals().get('redis_client')
    for candidate in (module_rc, global_rc):
        if candidate is not None:
            # 若是 Fake* 实例直接使用
            if candidate.__class__.__name__.lower().startswith('fake'):
                return candidate
    if module_rc is not None:
        return module_rc
    if global_rc is not None:
        return global_rc
    if current_app:
        return current_app.extensions.get('redis_client')
    return None

def generate_tokens(user_id, role):
    secret = current_app.config['JWT_SECRET_KEY']
    now = datetime.now(timezone.utc)
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())
    user_sub = str(user_id)  # PyJWT 要求 sub 为字符串
    access_payload = {
        'sub': user_sub,
        'role': role,
        'type': 'access',
        'jti': access_jti,
        'exp': now + timedelta(minutes=current_app.config['JWT_ACCESS_MINUTES']),
        'iat': now
    }
    refresh_payload = {
        'sub': user_sub,
        'role': role,
        'type': 'refresh',
        'jti': refresh_jti,
        'exp': now + timedelta(days=current_app.config['JWT_REFRESH_DAYS']),
        'iat': now
    }
    access = jwt.encode(access_payload, secret, algorithm='HS256')
    refresh = jwt.encode(refresh_payload, secret, algorithm='HS256')
    rc = _redis()
    if rc:
        ttl = int((refresh_payload['exp'] - now).total_seconds())
        try:
            rc.setex(f'refresh:allow:{refresh_jti}', ttl, '1')
            rc.setex(f'refresh:user:{user_sub}:{refresh_jti}', ttl, '1')
            # 记录当前最新 refresh jti
            rc.setex(f'refresh:current:{user_sub}', ttl, refresh_jti)
        except Exception:
            pass
    return access, refresh

@auth_bp.route('/register', methods=['POST'])
@limiter.limit('5/minute')
def register():
    data = request.get_json() or {}
    try:
        parsed = RegisterModel(**data)
    except ValidationError as ve:
        return jsonify({'code':4001,'message':'validation error','data':ve.errors()}), 400
    if not getattr(parsed,'email', None) or not getattr(parsed,'password', None):
        return jsonify({'code':4001,'message':'validation error'}), 400
    if User.query.filter_by(email=parsed.email).first():
        return jsonify({'code':4090,'message':'Email already exists'}), 409
    pw_hash = bcrypt.generate_password_hash(parsed.password).decode('utf-8')
    user = User(email=parsed.email, password_hash=pw_hash, role='author')
    db.session.add(user)
    db.session.commit()
    return jsonify({'code':0,'data':{'id':user.id,'email':user.email},'message':'ok'}), 201

def _issue_csrf(resp):
    """生成/刷新简易 CSRF Token (双提交 cookie 模式)。前端提交变更请求时可通过 header X-XSRF-TOKEN 回传。"""
    token = secrets.token_hex(16)
    resp.set_cookie('XSRF-TOKEN', token, httponly=False, samesite='Lax')
    return token

@auth_bp.route('/login', methods=['POST'])
@limiter.limit('10/minute')
def login():
    data = request.get_json() or {}
    try:
        parsed = LoginModel(**data)
    except ValidationError as ve:
        return jsonify({'code':4001,'message':'validation error','data':ve.errors()}), 400
    # 暴力破解防护：Redis 计数 (email+ip)
    rc = _redis()
    ip = request.remote_addr or '0.0.0.0'
    bf_key = f"login:bf:{getattr(parsed,'email','')}:{ip}"
    if rc:
        try:
            fails = int(rc.get(bf_key) or 0)
            if fails >= 5:
                return jsonify({'code':4290,'message':'too many failed attempts'}), 429
        except Exception:
            pass
    user = User.query.filter_by(email=getattr(parsed,'email', None)).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, getattr(parsed,'password','')):
        if rc:
            try:
                new_fails = rc.incr(bf_key)
                if new_fails == 1:
                    rc.expire(bf_key, 900)  # 15 分钟窗口
            except Exception:
                pass
        return jsonify({'code':4010,'message':'Invalid credentials'}), 401
    access, refresh = generate_tokens(user.id, user.role)
    resp = make_response(jsonify({'code':0,'data':{'access_token':access,'role':user.role},'message':'ok'}))
    resp.set_cookie('refresh_token', refresh, httponly=True, samesite='Lax')
    _issue_csrf(resp)
    if rc:
        try: rc.delete(bf_key)
        except Exception: pass
    return resp

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    token = request.cookies.get('refresh_token')
    # CSRF: 校验 header 与 cookie；前端需在刷新时附带
    xsrf_cookie = request.cookies.get('XSRF-TOKEN')
    xsrf_header = request.headers.get('X-XSRF-TOKEN')
    if not xsrf_cookie or not xsrf_header or xsrf_cookie != xsrf_header:
        return jsonify({'code':4010,'message':'csrf check failed'}), 401
    if not token:
        return jsonify({'code':4010,'message':'missing refresh token'}), 401
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        if payload.get('type') != 'refresh':
            raise ValueError('not refresh')
        jti = payload.get('jti')
        sub = payload.get('sub')
        rc = _redis()
        if rc:
            current_jti = rc.get(f'refresh:current:{sub}') if hasattr(rc, 'get') else None
            if rc.get(f'refresh:blacklist:{jti}') or not rc.get(f'refresh:allow:{jti}') or (current_jti and current_jti != jti):
                return jsonify({'code':4010,'message':'refresh token revoked'}), 401
    except Exception:
        return jsonify({'code':4010,'message':'invalid refresh token'}), 401
    new_access, new_refresh = generate_tokens(payload['sub'], payload.get('role'))
    rc = _redis()
    if rc and payload.get('jti'):
        ttl = int(payload['exp'] - datetime.now(timezone.utc).timestamp())
        if ttl > 0:
            try: rc.setex(f"refresh:blacklist:{payload['jti']}", ttl, '1')
            except Exception: pass
        try: rc.delete(f"refresh:allow:{payload.get('jti')}")
        except Exception: pass
    resp = make_response(jsonify({'code':0,'data':{'access_token':new_access},'message':'ok'}))
    resp.set_cookie('refresh_token', new_refresh, httponly=True, samesite='Lax')
    _issue_csrf(resp)
    return resp

@auth_bp.route('/logout', methods=['POST'])
def logout():
    token = request.cookies.get('refresh_token')
    rc = _redis()
    if token and rc:
        try:
            payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            if payload.get('type') == 'refresh':
                ttl = int(payload['exp'] - datetime.now(timezone.utc).timestamp())
                if ttl > 0:
                    try:
                        rc.setex(f"refresh:blacklist:{payload.get('jti')}", ttl, '1')
                    except Exception:
                        pass
        except Exception:
            pass
    resp = jsonify({'code':0,'message':'ok'})
    # 删除根路径 cookie
    resp.delete_cookie('refresh_token')
    return resp

@auth_bp.route('/change_password', methods=['POST'])
@limiter.limit('5/minute')
def change_password():
    data = request.get_json() or {}
    try:
        parsed = ChangePasswordModel(**data)
    except ValidationError as ve:
        return jsonify({'code':4001,'message':'validation error','data':ve.errors()}), 400
    user = User.query.filter_by(email=getattr(parsed,'email', None)).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, getattr(parsed,'old_password','')):
        return jsonify({'code':4010,'message':'invalid credentials'}), 401
    user.password_hash = bcrypt.generate_password_hash(parsed.new_password).decode('utf-8')
    db.session.commit()
    rc = _redis() or redis_client
    if rc:
        try:
            allow_keys = []
            user_keys = []
            # 扫描 allow
            try:
                for k in rc.scan_iter(match='refresh:allow:*'):
                    allow_keys.append(k)
            except Exception:
                store = getattr(rc, 'store', {})
                allow_keys = [k for k in store.keys() if k.startswith('refresh:allow:')]
            # 扫描 user
            try:
                for k in rc.scan_iter(match=f'refresh:user:{user.id}:*'):
                    user_keys.append(k)
            except Exception:
                store = getattr(rc, 'store', {})
                user_keys = [k for k in store.keys() if k.startswith(f'refresh:user:{user.id}:')]
            # 将所有 allow/user 关联的 jti 加入黑名单并删除 key
            for k in allow_keys + user_keys:
                parts = k.split(':')
                jti = parts[-1]
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
    return jsonify({'code':0,'message':'ok'})

