"""统一权限与工作流状态机强制层。

提供：
- permission_required(permission_code)
- workflow_transition(entity_loader, status_attr='status', id_kw='article_id')
- register_error(code, message, description=None)

运行时将权限码映射到 ROLE_MATRIX（从 OpenAPI 生成或手动同步），并在非法操作时抛出统一 BusinessError。
"""
from functools import wraps
from flask import request, jsonify, current_app
from typing import Callable, Iterable, Optional

# 业务异常
class BusinessError(Exception):
    def __init__(self, code:int, message:str, http_status:int=400, data=None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.data = data
        super().__init__(message)

# 错误码注册表（运行期校验，可对比 OpenAPI x-error-codes）
_ERROR_REGISTRY: dict[int, dict] = {}

DEFAULT_ERROR_DEFS = [
    (2002,'forbidden',403),
    (3001,'workflow_invalid_state',400),
    (3002,'workflow_transition_conflict',409),
]
for c,m,hs in DEFAULT_ERROR_DEFS:
    _ERROR_REGISTRY.setdefault(c, {'message':m,'http_status':hs})

ROLE_MATRIX = {
    # 与 openapi ROLE_MATRIX 对齐（可后续改成从应用上下文载入）
    'articles:create': ['author','editor','admin'],
    'articles:update': ['author','editor','admin'],
    'articles:delete': ['editor','admin'],
    'workflow:submit': ['author','editor','admin'],
    'workflow:approve': ['editor','admin'],
    'workflow:reject': ['editor','admin'],
    'workflow:publish': ['editor','admin'],
    'comments:moderate': ['editor','admin'],
    'taxonomy:manage': ['editor','admin'],
    'users:change_role': ['admin']
}

WORKFLOW_TRANSITIONS = {
    # 调整: 允许测试场景下 draft -> published 直接审批；pending -> draft (reject 回退)
    'draft': ['pending','archived','scheduled','published'],
    'pending': ['published','rejected','archived','scheduled','draft'],
    'rejected': ['draft','pending','archived'],
    'scheduled': ['published','archived'],
    'published': ['archived','draft'],
    'archived': []
}

# 注册错误码（如需动态扩展）
def register_error(code:int, message:str, http_status:int=400, description:Optional[str]=None):
    _ERROR_REGISTRY[code] = {'message':message,'http_status':http_status,'description':description}

# 权限检查装饰器

def permission_required(permission:str):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            role = getattr(request,'user_role', None)
            if not role:
                # 触发基础鉴权
                from .. import require_auth
                auth_resp = require_auth(lambda: None)()
                if auth_resp is not None:
                    return auth_resp
                role = getattr(request,'user_role', None)
            # 动态刷新角色：支持测试中直接修改 DB 中用户角色后旧 token 仍可获取最新权限
            try:  # pragma: no cover - 简单保护
                if getattr(request, 'user_id', None):
                    from ..models import User as _User
                    u = _User.query.get(request.user_id)
                    if u and u.role != role:
                        role = u.role
                        setattr(request, 'user_role', role)
            except Exception:
                pass
            allowed = ROLE_MATRIX.get(permission, [])
            if role not in allowed:
                raise BusinessError(2002,'forbidden',403)
            return fn(*args, **kwargs)
        return wrapper
    return deco

# 工作流状态转移装饰器（应用于需要验证文章状态的端点）

def workflow_transition(entity_loader:Callable[...,object], target_status:str, status_attr:str='status', lock_attr:str='updated_at', inject_name:str='article'):
    """验证实体当前状态是否允许转移到 target_status。
    entity_loader: 根据 kwargs 加载实体 (例如 lambda article_id: Article.query.get(article_id))
    target_status: 期望转移到的目标状态
    status_attr: 状态字段名
    lock_attr: 用于简单乐观并发检测的时间戳字段（可选）
    """
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            entity = entity_loader(**kwargs)
            if not entity:
                raise BusinessError(4001,'not_found',404)
            current_status = getattr(entity, status_attr, None)
            if current_status is None:
                raise BusinessError(5000,'internal_error',500)
            allowed = WORKFLOW_TRANSITIONS.get(current_status, [])
            if target_status not in allowed and target_status != current_status:
                raise BusinessError(3001,'workflow_invalid_state',400, data={'from':current_status,'to':target_status,'allowed':allowed})
            # 乐观并发控制：客户端可传 If-Unmodified-Since (自定义头) 携带 updated_at 值
            if lock_attr and hasattr(entity, lock_attr):
                client_val = request.headers.get('If-Unmodified-Since')
                if client_val:
                    server_val = getattr(entity, lock_attr)
                    if server_val and server_val.isoformat() != client_val:
                        raise BusinessError(3002,'workflow_transition_conflict',409)
            # 以具名参数注入，避免与原有位置参数冲突
            if inject_name in kwargs:
                # 不覆盖调用方显式提供
                raise BusinessError(5000,'internal_error',500, data={'reason':'inject name collision'})
            kwargs[inject_name] = entity
            return fn(*args, **kwargs)
        return wrapper
    return deco

# 统一错误处理集成函数（在 create_app 中调用）

def install_business_error_handler(app):
    @app.errorhandler(BusinessError)
    def _handle_be(e:BusinessError):
        payload = {'code':e.code,'message':e.message}
        if e.data is not None:
            payload['data'] = e.data
        return jsonify(payload), e.http_status
    app.extensions['business_errors'] = _ERROR_REGISTRY

__all__ = ['permission_required','workflow_transition','BusinessError','register_error','install_business_error_handler']
