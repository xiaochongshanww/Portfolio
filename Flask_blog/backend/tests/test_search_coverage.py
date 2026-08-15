"""搜索模块:索引器、同义词路由、ensure_index 真实逻辑测试。"""

from datetime import datetime, timezone

from app import db
from app.models import Article, Tag

from .helpers import auth_header, create_article, create_tag, create_user


class FakeSynonymsIdx:
    """带 get_synonyms/update_synonyms 的假索引。"""

    def __init__(self, syns=None):
        self.syns = syns or {}

    def get_synonyms(self):
        return self.syns

    def update_synonyms(self, syns):
        self.syns = syns


def _published_article():
    author = create_user()
    return create_article(
        author_id=author, status="published", published_at=datetime.now(timezone.utc)
    )


class TestIndexer:
    def test_article_to_doc(self, app):
        from app.search.indexer import article_to_doc

        tag = create_tag(slug="py")
        art_id = _published_article()
        a = db.session.get(Article, art_id)
        a.tags.append(db.session.get(Tag, tag))
        db.session.commit()
        doc = article_to_doc(a)
        assert doc["id"] == art_id
        assert doc["status"] == "published"
        assert "py" in doc["tags"]

    def test_index_article_published_adds(self, app):
        from app.search.indexer import index_article

        art_id = _published_article()
        a = db.session.get(Article, art_id)
        index_article(a)  # DummyIdx.add_documents

    def test_index_article_draft_deletes(self, app):
        from app.search.indexer import index_article

        author = create_user()
        art_id = create_article(author_id=author, status="draft")
        index_article(db.session.get(Article, art_id))

    def test_delete_article(self, app):
        from app.search.indexer import delete_article

        delete_article(999)

    def test_reindex_all(self, app):
        from app.search.indexer import reindex_all

        _published_article()
        _published_article()
        author = create_user()
        create_article(author_id=author, status="draft")  # excluded
        reindex_all(published_only=True)
        reindex_all(published_only=False)


class TestSynonymsRoutes:
    def test_list_synonyms(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.search.client.ensure_index",
            lambda: FakeSynonymsIdx({"ai": ["人工智能"]}),
        )
        h = auth_header(client, role="admin")
        r = client.get("/api/v1/search/synonyms/", headers=h)
        assert r.status_code == 200
        assert r.get_json()["data"][0]["term"] == "ai"

    def test_list_synonyms_editor(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.search.client.ensure_index", lambda: FakeSynonymsIdx({})
        )
        h = auth_header(client, role="editor")
        r = client.get("/api/v1/search/synonyms/", headers=h)
        assert r.status_code == 200

    def test_list_forbidden_author(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.search.client.ensure_index", lambda: FakeSynonymsIdx({})
        )
        h = auth_header(client, role="author")
        r = client.get("/api/v1/search/synonyms/", headers=h)
        assert r.status_code in (401, 403)

    def test_add_synonym(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.search.client.ensure_index", lambda: FakeSynonymsIdx({})
        )
        h = auth_header(client, role="admin")
        r = client.post(
            "/api/v1/search/synonyms/",
            json={"term": "js", "synonyms": ["javascript"]},
            headers=h,
        )
        assert r.status_code == 200

    def test_add_synonym_invalid(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.search.client.ensure_index", lambda: FakeSynonymsIdx({})
        )
        h = auth_header(client, role="admin")
        r = client.post("/api/v1/search/synonyms/", json={"term": ""}, headers=h)
        assert r.status_code == 400

    def test_delete_synonym(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.search.client.ensure_index",
            lambda: FakeSynonymsIdx({"js": ["javascript"]}),
        )
        h = auth_header(client, role="admin")
        r = client.delete("/api/v1/search/synonyms/js", headers=h)
        assert r.status_code == 200


class TestEnsureIndexReal:
    def test_creates_index_when_missing(self, app):
        import importlib

        from app.search import client as sc

        importlib.reload(sc)  # 恢复源码级 ensure_index(conftest 打过桩)

        class FakeMeili:
            def __init__(self):
                self.log = []

            def get_index(self, name):
                if "create" not in self.log:
                    raise Exception("index not found")
                return self

            def create_index(self, name, opts=None):
                self.log.append("create")
                return self

            def update_searchable_attributes(self, x):
                self.log.append("searchable")

            def update_filterable_attributes(self, x):
                self.log.append("filterable")

            def update_faceting(self, x):
                self.log.append("faceting")

            def update_sortable_attributes(self, x):
                self.log.append("sortable")

            def get_settings(self):
                return {"rankingRules": []}

            def update_ranking_rules(self, x):
                self.log.append("ranking")

            def update_synonyms(self, x):
                self.log.append("synonyms")

            def update_typo_tolerance(self, x):
                self.log.append("typo")

        fake = FakeMeili()
        sc.client = fake
        idx = sc.ensure_index()
        assert idx is fake
        assert "create" in fake.log
        assert "searchable" in fake.log
        assert "ranking" in fake.log
        assert "synonyms" in fake.log

    def test_ensure_index_existing(self, app):
        import importlib

        from app.search import client as sc

        importlib.reload(sc)

        class Existing:
            def __init__(self):
                self.log = []

            def get_index(self, name):
                return self

            def update_searchable_attributes(self, x):
                self.log.append("s")

            def update_filterable_attributes(self, x):
                self.log.append("f")

            def update_faceting(self, x):
                self.log.append("fa")

            def update_sortable_attributes(self, x):
                self.log.append("so")

            def get_settings(self):
                return {"rankingRules": []}

            def update_ranking_rules(self, x):
                self.log.append("r")

            def update_synonyms(self, x):
                self.log.append("sy")

            def update_typo_tolerance(self, x):
                self.log.append("t")

        fake = Existing()
        sc.client = fake
        idx = sc.ensure_index()
        assert idx is fake
        assert "create" not in fake.log
