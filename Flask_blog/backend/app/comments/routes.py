from flask import Blueprint, request, jsonify
from .. import db, require_auth, require_roles, limiter
from ..models import Comment, Article
# pydantic 校验
try:
    from pydantic import BaseModel, ValidationError, field_validator
    HAS_PY = True
except Exception:
    HAS_PY = False
    class BaseModel: pass
    def ValidationError(*a, **k): return Exception('validation error')
    def field_validator(*a, **k):
        def deco(fn): return fn
        return deco

comments_bp = Blueprint('comments', __name__)

if HAS_PY:
    class CommentCreate(BaseModel):
        article_id: int
        content: str
        parent_id: int | None = None
        @field_validator('content')
        @classmethod
        def content_len(cls, v):
            if not v or len(v.strip()) < 2:
                raise ValueError('content too short')
            return v.strip()

    class CommentModerate(BaseModel):
        action: str
        @field_validator('action')
        @classmethod
        def action_ok(cls, v):
            if v not in ('approve','reject'):
                raise ValueError('invalid action')
            return v
else:
    class CommentCreate: pass
    class CommentModerate: pass

@comments_bp.route('/', methods=['POST'])
@require_auth
@limiter.limit('20/minute')  # 评论发表限速
def add_comment():
    data = request.get_json() or {}
    if HAS_PY:
        try:
            parsed = CommentCreate(**data)
        except ValidationError as ve:
            return jsonify({'code':4001,'message':'validation error','data':ve.errors()}), 400
        article_id = parsed.article_id
        content = parsed.content
        parent_id = parsed.parent_id
    else:
        article_id = data.get('article_id')
        content = (data.get('content') or '').strip()
        parent_id = data.get('parent_id')
    if not article_id or not content:
        return jsonify({'code':4001,'message':'article_id & content required'}), 400
    art = Article.query.get(article_id)
    if not art or art.deleted or art.status != 'published':
        return jsonify({'code':4040,'message':'article not found'}), 404
    # 层级限制
    level = 1
    if parent_id:
        parent = Comment.query.get(parent_id)
        if not parent or parent.article_id != article_id:
            return jsonify({'code':4001,'message':'invalid parent'}), 400
        tmp = parent
        while tmp.parent_id:
            level += 1
            tmp = Comment.query.get(tmp.parent_id)
            if level >= 3:
                return jsonify({'code':4001,'message':'max depth reached'}), 400
    comment = Comment(article_id=article_id, parent_id=parent_id, user_id=request.user_id, content=content)
    db.session.add(comment)
    db.session.commit()
    return jsonify({'code':0,'data':{'id':comment.id,'status':comment.status},'message':'ok'}), 201

@comments_bp.route('/article/<int:article_id>', methods=['GET'])
def list_comments(article_id):
    comments = Comment.query.filter_by(article_id=article_id, status='approved').order_by(Comment.created_at.asc()).all()
    def ser(c):
        return {'id':c.id,'parent_id':c.parent_id,'content':c.content,'created_at':c.created_at.isoformat(),'user_id':c.user_id}
    return jsonify({'code':0,'data':[ser(c) for c in comments],'message':'ok'})

@comments_bp.route('/article/<int:article_id>/tree', methods=['GET'])
def list_comments_tree(article_id):
    """评论树。默认仅返回 approved；传 include=all 且登录作者本人或 editor/admin 时返回其余状态。"""
    include = request.args.get('include')
    q = Comment.query.filter_by(article_id=article_id).order_by(Comment.created_at.asc())
    allowed_all = False
    try:
        # 复用认证: 如果带 Authorization 头则尝试鉴权
        from .. import require_auth as _rq
        if 'Authorization' in request.headers:
            auth_resp = _rq(lambda: None)()
            if auth_resp is None:
                from ..models import Article
                art = Article.query.get(article_id)
                if art and (art.author_id == request.user_id or request.user_role in ('editor','admin')):
                    allowed_all = True
    except Exception:
        pass
    if include != 'all' or not allowed_all:
        q = q.filter_by(status='approved')
    comments = q.all()
    nodes = {c.id: {'id':c.id,'parent_id':c.parent_id,'content':c.content,'created_at':c.created_at.isoformat(),'user_id':c.user_id,'status':c.status,'children':[]} for c in comments}
    roots = []
    for c in comments:
        if c.parent_id and c.parent_id in nodes:
            nodes[c.parent_id]['children'].append(nodes[c.id])
        else:
            roots.append(nodes[c.id])
    return jsonify({'code':0,'data':roots,'message':'ok'})

@comments_bp.route('/pending', methods=['GET'])
@require_roles('editor','admin')
def list_pending():
    # 分页列出待审核评论，可按文章过滤
    try:
        page = int(request.args.get('page',1)); size = int(request.args.get('page_size',10))
    except Exception:
        page, size = 1, 10
    size = max(1, min(size, 50))
    q = Comment.query.filter_by(status='pending')
    article_id = request.args.get('article_id')
    if article_id and article_id.isdigit():
        q = q.filter_by(article_id=int(article_id))
    total = q.count()
    items = q.order_by(Comment.created_at.asc()).offset((page-1)*size).limit(size).all()
    data = [{ 'id':c.id,'article_id':c.article_id,'parent_id':c.parent_id,'content':c.content,'user_id':c.user_id,'created_at':c.created_at.isoformat()} for c in items]
    return jsonify({'code':0,'data':{'total':total,'page':page,'page_size':size,'has_next': page*size < total,'list':data},'message':'ok'})

@comments_bp.route('/admin/list', methods=['GET'])
@require_roles('editor','admin')
def admin_list_comments():
    """管理员评论列表，支持状态筛选、内容搜索等"""
    try:
        page = int(request.args.get('page', 1))
        size = int(request.args.get('page_size', 20))
    except Exception:
        page, size = 1, 20
    size = max(1, min(size, 100))
    
    # 构建查询
    q = Comment.query
    
    # 状态筛选
    status = request.args.get('status')
    if status and status in ('pending', 'approved', 'rejected'):
        q = q.filter_by(status=status)
    
    # 文章ID筛选
    article_id = request.args.get('article_id')
    if article_id and article_id.isdigit():
        q = q.filter_by(article_id=int(article_id))
    
    # 内容搜索
    content = request.args.get('content')
    if content:
        q = q.filter(Comment.content.contains(content))
    
    # 排序：最新的在前
    q = q.order_by(Comment.created_at.desc())
    
    # 分页
    total = q.count()
    items = q.offset((page-1)*size).limit(size).all()
    
    # 序列化
    data = [{
        'id': c.id,
        'article_id': c.article_id,
        'parent_id': c.parent_id,
        'content': c.content,
        'user_id': c.user_id,
        'status': c.status,
        'created_at': c.created_at.isoformat()
    } for c in items]
    
    return jsonify({
        'code': 0,
        'data': {
            'total': total,
            'page': page,
            'page_size': size,
            'has_next': page * size < total,
            'list': data
        },
        'message': 'ok'
    })

@comments_bp.route('/admin/stats', methods=['GET'])
@require_roles('editor','admin')
def admin_stats():
    """管理员统计数据"""
    from datetime import datetime, timezone, timedelta
    
    # 待审核数量
    pending_count = Comment.query.filter_by(status='pending').count()
    
    # 今日评论数量
    today = datetime.now(timezone.utc).date()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    today_count = Comment.query.filter(Comment.created_at >= today_start).count()
    
    # 总评论数量
    total_count = Comment.query.count()
    
    return jsonify({
        'code': 0,
        'data': {
            'pending': pending_count,
            'today': today_count,
            'total': total_count
        },
        'message': 'ok'
    })

@comments_bp.route('/moderate/<int:comment_id>', methods=['POST'])
@require_roles('editor','admin')
@limiter.limit('60/minute')  # 审核操作限速
def moderate(comment_id):
    data = request.get_json() or {}
    if HAS_PY:
        try:
            parsed = CommentModerate(**data)
        except ValidationError as ve:
            return jsonify({'code':4001,'message':'validation error','data':ve.errors()}), 400
        action = parsed.action
    else:
        action = data.get('action')
    c = Comment.query.get_or_404(comment_id)
    if action == 'approve':
        c.status = 'approved'
    elif action == 'reject':
        c.status = 'rejected'
    else:
        return jsonify({'code':4001,'message':'invalid action'}), 400
    db.session.commit()
    return jsonify({'code':0,'data':{'id':c.id,'status':c.status},'message':'ok'})

@comments_bp.route('/moderate/batch', methods=['POST'])
@require_roles('editor','admin')
@limiter.limit('30/minute')  # 批量操作限速
def moderate_batch():
    """批量审核评论"""
    data = request.get_json() or {}
    ids = data.get('ids', [])
    action = data.get('action')
    
    if not ids or not isinstance(ids, list):
        return jsonify({'code': 4001, 'message': 'ids required as array'}), 400
    
    if action not in ('approve', 'reject'):
        return jsonify({'code': 4001, 'message': 'invalid action'}), 400
    
    if len(ids) > 50:  # 限制批量操作数量
        return jsonify({'code': 4001, 'message': 'too many items, max 50'}), 400
    
    # 查找所有评论
    comments = Comment.query.filter(Comment.id.in_(ids)).all()
    
    if len(comments) != len(ids):
        return jsonify({'code': 4001, 'message': 'some comments not found'}), 400
    
    # 批量更新状态
    new_status = 'approved' if action == 'approve' else 'rejected'
    for comment in comments:
        comment.status = new_status
    
    db.session.commit()
    
    return jsonify({
        'code': 0,
        'data': {
            'updated_count': len(comments),
            'status': new_status
        },
        'message': 'ok'
    })
