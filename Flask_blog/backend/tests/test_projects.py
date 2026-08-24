"""Project 实体 API 测试(impl-P2 A1/A2)"""

from app import db
from app.models import Project
from tests.helpers import auth_header


def make_project(**overrides) -> Project:
    import random

    n = random.randint(1000, 9999)
    data = {
        "name": f"Proj {n}",
        "slug": f"proj-{n}",
        "description": "test project",
        "status": Project.STATUS_ACTIVE,
        "is_current": False,
        "tech_stack": '["Python"]',
    }
    data.update(overrides)
    p = Project(**data)
    db.session.add(p)
    db.session.commit()
    return p


class TestPublicList:
    def test_list_returns_projects_with_current_first(self, client):
        make_project(slug="normal-a", sort_order=1)
        make_project(slug="normal-b", sort_order=0)
        make_project(slug="the-current", is_current=True, sort_order=99)

        resp = client.get("/api/v1/projects/")
        assert resp.status_code == 200
        items = resp.json["data"]["list"]
        assert items[0]["slug"] == "the-current"  # current 永远置顶
        assert [i["slug"] for i in items[1:]] == [
            "normal-b",
            "normal-a",
        ]  # 再按 sort_order

    def test_archived_excluded_from_public_list(self, client):
        make_project(slug="visible")
        make_project(slug="hidden", status=Project.STATUS_ARCHIVED)
        resp = client.get("/api/v1/projects/")
        slugs = [i["slug"] for i in resp.json["data"]["list"]]
        assert "visible" in slugs
        assert "hidden" not in slugs

    def test_detail_by_slug_and_404(self, client):
        make_project(slug="hello", motivation="why", related_article_slugs='["a"]')
        resp = client.get("/api/v1/projects/hello")
        assert resp.status_code == 200
        data = resp.json["data"]
        assert data["motivation"] == "why"
        assert data["related_article_slugs"] == ["a"]  # JSON 列已反序列化

        assert client.get("/api/v1/projects/nope").status_code == 404

    def test_archived_detail_returns_404(self, client):
        make_project(slug="gone", status=Project.STATUS_ARCHIVED)
        assert client.get("/api/v1/projects/gone").status_code == 404


class TestAdminCrud:
    def test_write_requires_auth(self, client):
        assert (
            client.post(
                "/api/v1/projects/", json={"name": "x", "slug": "x"}
            ).status_code
            == 401
        )
        assert client.get("/api/v1/projects/admin/list").status_code == 401

    def test_create_and_current_exclusivity(self, client):
        h = auth_header(client, role="editor")
        r1 = client.post(
            "/api/v1/projects/",
            headers=h,
            json={
                "name": "First",
                "slug": "first",
                "is_current": True,
                "tech_stack": ["Vue"],
            },
        )
        assert r1.status_code == 201
        assert r1.json["data"]["is_current"] is True

        # 置第二个为 current → 第一个自动清除
        r2 = client.post(
            "/api/v1/projects/",
            headers=h,
            json={"name": "Second", "slug": "second", "is_current": True},
        )
        assert r2.status_code == 201
        assert Project.query.filter_by(slug="first").first().is_current is False
        assert Project.query.filter_by(slug="second").first().is_current is True

    def test_create_validates_slug_unique(self, client):
        h = auth_header(client, role="editor")
        make_project(slug="dup")
        resp = client.post(
            "/api/v1/projects/", headers=h, json={"name": "X", "slug": "dup"}
        )
        assert resp.status_code == 400

    def test_update_switches_current(self, client):
        h = auth_header(client, role="editor")
        a = make_project(slug="pa", is_current=True)
        b = make_project(slug="pb")
        resp = client.put(
            f"/api/v1/projects/{b.id}", headers=h, json={"is_current": True}
        )
        assert resp.status_code == 200
        assert Project.query.get(a.id).is_current is False
        assert Project.query.get(b.id).is_current is True

    def test_delete_admin_only(self, client):
        p = make_project(slug="doomed")
        # editor 不可删
        h_editor = auth_header(client, role="editor")
        assert (
            client.delete(f"/api/v1/projects/{p.id}", headers=h_editor).status_code
            == 403
        )
        h_admin = auth_header(client, role="admin")
        assert (
            client.delete(f"/api/v1/projects/{p.id}", headers=h_admin).status_code
            == 200
        )
        assert Project.query.get(p.id) is None

    def test_admin_list_includes_archived(self, client):
        h = auth_header(client, role="editor")
        make_project(slug="arch", status=Project.STATUS_ARCHIVED)
        resp = client.get("/api/v1/projects/admin/list", headers=h)
        assert resp.status_code == 200
        slugs = [i["slug"] for i in resp.json["data"]["list"]]
        assert "arch" in slugs
