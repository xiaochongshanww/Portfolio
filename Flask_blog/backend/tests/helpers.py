"""
测试辅助工具：认证头、模型工厂、数据构建器。

用法:
    from helpers import auth_header, create_article

    def test_something(client, app):
        token = auth_header(client, role='admin')
        article = create_article(author_id=1)
        resp = client.get('/api/v1/articles/', headers=token)
"""

import json
from datetime import datetime, timezone


def register_and_login(client, email='test@example.com', password='test123456'):
    """注册并登录，返回 access_token。"""
    resp = client.post('/api/v1/auth/register', json={'email': email, 'password': password})
    if resp.status_code not in (201, 409):  # 409 = already exists
        raise RuntimeError(f'Registration failed: {resp.json}')
    resp = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert resp.status_code == 200, f'Login failed: {resp.json}'
    return resp.json['data']['access_token']


def auth_header(client, role='admin', email=None):
    """返回带有 Authorization 头的 dict，供 client.get/post 的 headers= 使用。
    根据 role 创建/登录对应用户（admin/editor/author）。
    """
    import random
    suffix = random.randint(10000, 99999)
    if email is None:
        email = f'{role}_{suffix}@test.com'
    # 注册
    client.post('/api/v1/auth/register', json={'email': email, 'password': 'test123456'})
    # 如果需要 admin 角色，直接改数据库
    if role != 'author':
        from app import db
        from app.models import User
        user = User.query.filter_by(email=email).first()
        if user:
            user.role = role
            db.session.commit()
    token = register_and_login(client, email=email, password='test123456')
    return {'Authorization': f'Bearer {token}'}


# ─── 模型工厂 ─────────────────────────────────────────────

def create_user(**overrides) -> int:
    """创建用户并返回 id。"""
    from app import bcrypt, db
    from app.models import User
    import random
    data = {
        'email': f'user_{random.randint(10000, 99999)}@test.com',
        'password_hash': bcrypt.generate_password_hash('test123456').decode('utf-8'),
        'role': 'author',
    }
    data.update(overrides)
    user = User(**data)
    db.session.add(user)
    db.session.commit()
    return user.id


def create_article(author_id: int = None, **overrides) -> int:
    """创建文章并返回 id。"""
    from app import db
    from app.models import Article
    import random
    if author_id is None:
        author_id = create_user()
    data = {
        'title': f'Test Article {random.randint(1000, 9999)}',
        'slug': f'test-article-{random.randint(1000, 9999)}',
        'content_md': '# Hello\nThis is a test article.',
        'content_html': '<h1>Hello</h1><p>This is a test article.</p>',
        'author_id': author_id,
        'status': 'published',
        'summary': 'Test summary',
        'published_at': datetime.now(timezone.utc),
    }
    data.update(overrides)
    article = Article(**data)
    db.session.add(article)
    db.session.commit()
    return article.id


def create_comment(article_id: int, user_id: int = None, **overrides) -> int:
    """创建评论并返回 id。"""
    from app import db
    from app.models import Comment
    if user_id is None:
        user_id = create_user()
    data = {
        'article_id': article_id,
        'user_id': user_id,
        'content': 'Test comment',
        'status': 'approved',
    }
    data.update(overrides)
    comment = Comment(**data)
    db.session.add(comment)
    db.session.commit()
    return comment.id


def create_category(**overrides) -> int:
    """创建分类并返回 id。"""
    from app import db
    from app.models import Category
    import random
    data = {
        'name': f'Category {random.randint(1000, 9999)}',
        'slug': f'cat-{random.randint(1000, 9999)}',
    }
    data.update(overrides)
    cat = Category(**data)
    db.session.add(cat)
    db.session.commit()
    return cat.id


def create_tag(**overrides) -> int:
    """创建标签并返回 id。"""
    from app import db
    from app.models import Tag
    import random
    data = {
        'name': f'Tag {random.randint(1000, 9999)}',
        'slug': f'tag-{random.randint(1000, 9999)}',
    }
    data.update(overrides)
    tag = Tag(**data)
    db.session.add(tag)
    db.session.commit()
    return tag.id
