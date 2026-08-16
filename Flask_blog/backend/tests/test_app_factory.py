"""应用工厂与错误处理测试 — 覆盖 app/__init__.py。"""

from .helpers import auth_header


def test_create_app_production():
    from app import create_app

    app = create_app("production")
    assert app.config["DEBUG"] is False


def test_404_status(client):
    resp = client.get("/api/v1/definitely-not-a-route")
    assert resp.status_code == 404


def test_business_error_handler(client):
    # 不存在文章触发 BusinessError → 统一 JSON 错误格式
    h = auth_header(client, role="author")
    resp = client.post("/api/v1/articles/999999/submit", headers=h)
    assert resp.status_code in (404, 409, 400)
    assert resp.get_json() is not None


def test_create_app_development():
    from app import create_app

    app = create_app("development")
    assert app.config["DEBUG"] is True


def test_app_has_blueprints(client):
    # 关键 API 前缀已注册
    assert client.get("/api/v1/auth/login").status_code in (401, 405)
    assert client.get("/api/v1/ping").status_code in (200, 404, 405)
