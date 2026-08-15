"""系统设置 service 层与路由测试。"""

import pytest

from .helpers import (
    auth_header,
    create_article,
    create_category,
    create_tag,
    create_user,
)


@pytest.fixture()
def isolated_settings(monkeypatch, tmp_path):
    target = tmp_path / "settings.json"
    from app.settings import service as svc

    monkeypatch.setattr(svc, "SETTINGS_FILE", str(target))
    return svc


class TestService:
    def test_load_defaults(self, isolated_settings):
        svc = isolated_settings
        settings = svc.load_settings()
        assert settings["general"]["siteName"] == "Flask博客系统"
        assert "security" in settings

    def test_save_and_load_roundtrip(self, isolated_settings):
        import copy

        svc = isolated_settings
        # load_settings() 返回 DEFAULT_SETTINGS 的浅拷贝,直接改会污染模块级默认值
        settings = copy.deepcopy(svc.load_settings())
        settings["general"]["siteName"] = "Custom"
        assert svc.save_settings(settings) is True
        reloaded = svc.load_settings()
        assert reloaded["general"]["siteName"] == "Custom"

    def test_load_merges_defaults_into_partial(
        self, isolated_settings, tmp_path, monkeypatch
    ):
        import json

        svc = isolated_settings
        partial = {"general": {"siteName": "Partial"}}
        monkeypatch.setattr(svc, "SETTINGS_FILE", str(tmp_path / "partial.json"))
        with open(svc.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(partial, f)
        settings = svc.load_settings()
        assert settings["general"]["siteName"] == "Partial"
        # default keys merged in
        assert settings["general"]["siteSlogan"] == "分享知识，记录思考"

    def test_load_bad_json_falls_back(self, isolated_settings, monkeypatch, tmp_path):
        svc = isolated_settings
        bad = tmp_path / "bad.json"
        monkeypatch.setattr(svc, "SETTINGS_FILE", str(bad))
        with open(bad, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        settings = svc.load_settings()
        assert settings["general"]["siteName"] == "Flask博客系统"

    def test_system_info(self, app, isolated_settings):
        from app.settings.service import get_system_info_data
        from flask import current_app

        author = create_user()
        cat = create_category()
        create_tag()
        create_article(author_id=author, status="published", category_id=cat)
        info = get_system_info_data()
        assert info["totalArticles"] >= 1
        assert info["totalUsers"] >= 1
        assert info["version"] == current_app.config.get("VERSION")

    def test_optimize_non_sqlite(self, app, isolated_settings, monkeypatch):
        from app.settings.service import optimize_database_operation

        monkeypatch.setitem(
            app.config, "SQLALCHEMY_DATABASE_URI", "mysql://user@localhost/db"
        )
        res = optimize_database_operation()
        assert res["operation"] == "database_vacuum"

    def test_clear_cache(self, app, isolated_settings):
        from app.settings.service import clear_cache_operation

        res = clear_cache_operation()
        assert res["operation"] == "cache_clear"

    def test_cleanup_logs(self, app, isolated_settings):
        from app.settings.service import cleanup_logs_operation

        assert cleanup_logs_operation()["operation"] == "logs_cleanup"

    def test_generate_sitemap(self, app, isolated_settings, monkeypatch, tmp_path):
        from app.settings.service import generate_sitemap_operation

        monkeypatch.setattr("app.settings.service.os.getcwd", lambda: str(tmp_path))
        author = create_user()
        create_article(author_id=author, status="published")
        res = generate_sitemap_operation()
        assert res["articles_count"] >= 1
        assert "sitemap.xml" in res["sitemap_path"]

    def test_create_backup(self, app, isolated_settings):
        from app.settings.service import create_backup_operation

        res = create_backup_operation()
        assert res["filename"].startswith("backup_")

    def test_backup_history(self, app, isolated_settings):
        from app.settings.service import get_backup_history_data

        assert len(get_backup_history_data()) == 2


class TestRoutes:
    def test_get_all(self, client):
        h = auth_header(client, role="admin")
        r = client.get("/api/v1/settings/all", headers=h)
        assert r.status_code == 200
        assert "general" in r.get_json()["data"]

    def test_get_general(self, client):
        h = auth_header(client, role="admin")
        r = client.get("/api/v1/settings/general", headers=h)
        assert r.status_code == 200

    def test_update_general(self, client, isolated_settings):
        # isolated_settings fixture 已把 SETTINGS_FILE 指向临时文件,避免污染真实配置
        h = auth_header(client, role="admin")
        r = client.put("/api/v1/settings/general", json={"siteName": "X"}, headers=h)
        assert r.status_code == 200

    def test_update_general_no_data(self, client):
        h = auth_header(client, role="admin")
        r = client.put("/api/v1/settings/general", json={}, headers=h)
        assert r.status_code == 400

    def test_get_content(self, client):
        h = auth_header(client, role="admin")
        r = client.get("/api/v1/settings/content", headers=h)
        assert r.status_code == 200

    def test_get_security(self, client):
        h = auth_header(client, role="admin")
        r = client.get("/api/v1/settings/security", headers=h)
        assert r.status_code == 200

    def test_system_endpoints(self, client):
        h = auth_header(client, role="admin")
        r = client.post("/api/v1/settings/system/optimize-database", headers=h)
        assert r.status_code in (200, 500)
        r2 = client.post("/api/v1/settings/system/clear-cache", headers=h)
        assert r2.status_code == 200
        r3 = client.post("/api/v1/settings/system/cleanup-logs", headers=h)
        assert r3.status_code == 200
        r4 = client.post("/api/v1/settings/system/backup", headers=h)
        assert r4.status_code == 200
        r5 = client.get("/api/v1/settings/backup/history", headers=h)
        assert r5.status_code == 200
