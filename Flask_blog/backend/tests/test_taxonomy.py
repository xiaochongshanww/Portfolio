"""分类与标签 API 测试。"""

from .helpers import auth_header, create_category, create_tag


class TestCategories:
    def test_create_category(self, client):
        h = auth_header(client, role='admin')
        resp = client.post('/api/v1/taxonomy/categories/', json={
            'name': 'Technology', 'slug': 'tech',
        }, headers=h)
        assert resp.status_code == 201
        assert resp.json['data']['name'] == 'Technology'
        assert resp.json['data']['slug'] == 'tech'

    def test_create_category_unauthorized(self, client):
        resp = client.post('/api/v1/taxonomy/categories/', json={'name': 'Tech'})
        assert resp.status_code == 401

    def test_create_category_forbidden_author(self, client):
        h = auth_header(client, role='author')
        resp = client.post('/api/v1/taxonomy/categories/', json={'name': 'Tech'}, headers=h)
        assert resp.status_code == 403

    def test_create_category_duplicate_slug(self, client):
        h = auth_header(client, role='admin')
        client.post('/api/v1/taxonomy/categories/', json={
            'name': 'Tech', 'slug': 'tech',
        }, headers=h)
        resp = client.post('/api/v1/taxonomy/categories/', json={
            'name': 'Tech Again', 'slug': 'tech',
        }, headers=h)
        assert resp.status_code == 409

    def test_list_categories(self, client, app):
        from app import db
        from app.models import Category
        for i in range(3):
            db.session.add(Category(name=f'Cat {i}', slug=f'cat-{i}'))
        db.session.commit()
        h = auth_header(client, role='author')
        resp = client.get('/api/v1/taxonomy/categories/', headers=h)
        assert resp.status_code == 200
        assert len(resp.json['data']) == 3

    def test_update_category(self, client, app):
        from app import db
        from app.models import Category
        c = Category(name='Old', slug='old')
        db.session.add(c)
        db.session.commit()
        h = auth_header(client, role='admin')
        resp = client.patch(f'/api/v1/taxonomy/categories/{c.id}', json={
            'name': 'Updated',
        }, headers=h)
        assert resp.status_code == 200
        assert resp.json['data']['name'] == 'Updated'

    def test_delete_category(self, client, app):
        from app import db
        from app.models import Category
        c = Category(name='To Delete', slug='to-delete')
        db.session.add(c)
        db.session.commit()
        cid = c.id
        h = auth_header(client, role='admin')
        resp = client.delete(f'/api/v1/taxonomy/categories/{cid}', headers=h)
        assert resp.status_code == 200
        assert Category.query.get(cid) is None

    def test_public_categories(self, client, app):
        from app import db
        from app.models import Category
        db.session.add(Category(name='Public', slug='public'))
        db.session.commit()
        resp = client.get('/api/v1/taxonomy/categories/public')
        assert resp.status_code == 200
        assert len(resp.json['data']) >= 1


class TestTags:
    def test_create_tag(self, client):
        h = auth_header(client, role='admin')
        resp = client.post('/api/v1/taxonomy/tags/', json={
            'name': 'python', 'slug': 'python',
        }, headers=h)
        assert resp.status_code == 201
        assert resp.json['data']['name'] == 'python'

    def test_create_tag_unauthorized(self, client):
        resp = client.post('/api/v1/taxonomy/tags/', json={'name': 'python'})
        assert resp.status_code == 401

    def test_list_tags(self, client, app):
        from app import db
        from app.models import Tag
        for i in range(3):
            db.session.add(Tag(name=f'Tag {i}', slug=f'tag-{i}'))
        db.session.commit()
        h = auth_header(client, role='author')
        resp = client.get('/api/v1/taxonomy/tags/', headers=h)
        assert resp.status_code == 200
        assert len(resp.json['data']) == 3

    def test_delete_tag_in_use(self, client, app):
        from app import db
        from app.models import Article, Tag, ArticleTag
        tag = Tag(name='inuse', slug='inuse')
        db.session.add(tag)
        db.session.commit()
        article = Article(title='Test', slug='test-tag-del', author_id=1,
                          content_md='x', content_html='<p>x</p>', status='draft')
        db.session.add(article)
        db.session.commit()
        db.session.execute(ArticleTag.__table__.insert().values(article_id=article.id, tag_id=tag.id))
        db.session.commit()
        h = auth_header(client, role='admin')
        resp = client.delete(f'/api/v1/taxonomy/tags/{tag.id}', headers=h)
        assert resp.status_code == 400  # tag in use
