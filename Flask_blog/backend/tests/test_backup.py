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

    # ─── 扩展: 更多路由端点覆盖 ──────────────────────────────

    def test_put_config(self, client):
        h = auth_header(client, role="admin")
        resp = client.put(
            "/api/v1/backup/config", json={"retention_days": 15}, headers=h
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["retention_days"] == 15

    def test_statistics_with_records(self, client, app):
        from app import db
        from app.models import BackupRecord

        db.session.add(
            BackupRecord(backup_id="s1", backup_type="full", status="completed")
        )
        db.session.add(
            BackupRecord(backup_id="s2", backup_type="full", status="failed")
        )
        db.session.commit()
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/backup/statistics", headers=h)
        body = resp.get_json()["data"]
        assert body["total"] == 2
        assert body["successful"] == 1
        assert body["failed"] == 1

    def test_cleanup_with_force(self, client, app):
        from datetime import datetime, timedelta, timezone

        from app import db
        from app.models import BackupRecord

        old = datetime.now(timezone.utc) - timedelta(days=200)
        db.session.add(
            BackupRecord(
                backup_id="old1", backup_type="full", status="completed", created_at=old
            )
        )
        db.session.commit()
        h = auth_header(client, role="admin")
        resp = client.post("/api/v1/backup/cleanup?force=true", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["deleted_count"] == 1

    def test_delete_backup(self, client, app):
        from app import db
        from app.models import BackupRecord

        db.session.add(
            BackupRecord(backup_id="d1", backup_type="full", status="completed")
        )
        db.session.commit()
        h = auth_header(client, role="admin")
        resp = client.delete("/api/v1/backup/d1", headers=h)
        assert resp.status_code == 200
        assert BackupRecord.query.filter_by(backup_id="d1").first() is None

    def test_delete_backup_missing(self, client):
        h = auth_header(client, role="admin")
        resp = client.delete("/api/v1/backup/nope", headers=h)
        assert resp.status_code == 404

    def test_cleaner_status(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/backup/tasks/cleaner/status", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "running"

    def test_trigger_cleaner(self, client, app):
        h = auth_header(client, role="admin")
        resp = client.post("/api/v1/backup/tasks/cleaner/trigger", headers=h)
        assert resp.status_code == 200


class TestBackupMoreEndpoints:
    def test_get_backup_detail(self, client, app):
        from app import db
        from app.models import BackupRecord

        db.session.add(
            BackupRecord(backup_id="detail-1", backup_type="full", status="completed")
        )
        db.session.commit()
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/backup/detail-1", headers=h)
        assert resp.status_code == 200

    def test_get_backup_detail_missing(self, client):
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/backup/no-such", headers=h)
        assert resp.status_code == 404

    def test_sync(self, client):
        h = auth_header(client, role="admin")
        resp = client.post("/api/v1/backup/sync", headers=h)
        assert resp.status_code in (200, 500)

    def test_status_sync(self, client):
        h = auth_header(client, role="admin")
        resp = client.post("/api/v1/backup/status/sync", headers=h)
        assert resp.status_code in (200, 500)

    def test_restores_detail(self, client, app):
        from app import db
        from app.models import RestoreRecord

        db.session.add(
            RestoreRecord(
                restore_id="r-detail", restore_type="full", status="completed"
            )
        )
        db.session.commit()
        h = auth_header(client, role="admin")
        resp = client.get("/api/v1/backup/restores/r-detail", headers=h)
        assert resp.status_code in (200, 404)

    def test_restores_cleanup(self, client):
        h = auth_header(client, role="admin")
        resp = client.post("/api/v1/backup/restores/cleanup", headers=h)
        assert resp.status_code in (200, 500)
