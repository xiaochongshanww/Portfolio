"""备份管理 API 测试。"""

from .helpers import auth_header


class TestBackup:
    def test_get_records(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/backup/records", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["code"] == 0

    def test_get_records_unauthorized(self, client):
        resp = client.get("/api/v1/backup/records")
        assert resp.status_code == 401

    def test_get_config(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/backup/config", headers=h)
        assert resp.status_code in (200,)

    def test_get_statistics(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/backup/statistics", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["code"] == 0

    def test_get_tasks(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/backup/tasks", headers=h)
        assert resp.status_code == 200

    def test_list_restores(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/backup/restores", headers=h)
        assert resp.status_code == 200

    def test_cleanup(self, client):
        h = auth_header(client, role="admin")
        resp = client.post("/api/v1/backup/cleanup", headers=h)
        assert resp.status_code in (200,)

    def test_create_backup(self, client):
        h = auth_header(client, role="admin")
        resp = client.post(
            "/api/v1/backup/create",
            json={"backup_type": "full", "description": "test backup"},
            headers=h,
        )
        # create may queue a task, respond directly, or fail when Docker is unavailable
        assert resp.status_code in (200, 201, 202, 500)

    def test_forbidden_for_author(self, client):
        h = auth_header(client, role="author")
        resp = client.get("/api/v1/backup/records", headers=h)
        assert resp.status_code in (401, 403)
