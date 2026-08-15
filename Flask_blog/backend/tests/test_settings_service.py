"""系统设置业务逻辑测试 — 覆盖 settings/service.py。"""

from app import db
from app.models import Article, User
from app.settings import service as settings_svc


def _user():
    u = User(email="st@test.com", password_hash="x", role="admin")
    db.session.add(u)
    db.session.commit()
    return u


class TestLoadSave:
    def test_load_defaults_when_missing(self, app, monkeypatch, tmp_path):
        monkeypatch.setattr(settings_svc, "SETTINGS_FILE", str(tmp_path / "none.json"))
        s = settings_svc.load_settings()
        assert s["general"]["siteName"] == "Flask博客系统"
        assert s["content"]["articlesPerPage"] == 10

    def test_save_and_load(self, app, monkeypatch, tmp_path):
        f = tmp_path / "settings.json"
        monkeypatch.setattr(settings_svc, "SETTINGS_FILE", str(f))
        assert settings_svc.save_settings(
            {"general": {"siteName": "X"}, "content": {}, "security": {}}
        )
        s = settings_svc.load_settings()
        assert s["general"]["siteName"] == "X"


class TestSystemInfo:
    def test_get_system_info(self, app):
        u = _user()
        db.session.add(
            Article(
                title="t", slug="s", content_md="x", author_id=u.id, status="published"
            )
        )
        db.session.commit()
        info = settings_svc.get_system_info_data()
        assert info["totalUsers"] >= 1
        assert info["totalArticles"] >= 1
        assert "dbSize" in info


class TestOperations:
    def test_optimize_database(self, app):
        result = settings_svc.optimize_database_operation()
        assert result["operation"] == "database_vacuum"

    def test_clear_cache(self, app):
        result = settings_svc.clear_cache_operation()
        assert result["operation"] == "cache_clear"

    def test_cleanup_logs(self, app):
        result = settings_svc.cleanup_logs_operation()
        assert result["operation"] == "logs_cleanup"

    def test_create_backup(self, app):
        result = settings_svc.create_backup_operation()
        assert result["filename"].startswith("backup_")
        assert "database" in result["includes"]

    def test_backup_history(self, app):
        history = settings_svc.get_backup_history_data()
        assert len(history) >= 1

    def test_generate_sitemap(self, app, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        u = _user()
        db.session.add(
            Article(
                title="t2",
                slug="s2",
                content_md="x",
                author_id=u.id,
                status="published",
            )
        )
        db.session.commit()
        result = settings_svc.generate_sitemap_operation()
        assert result["articles_count"] >= 1
        assert "sitemap.xml" in result["sitemap_path"]
