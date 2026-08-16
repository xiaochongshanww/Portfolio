"""备份业务逻辑层测试 — 覆盖 service.py / task_cleaner.py 的纯 DB 逻辑。"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app import db
from app.backup import service as backup_service
from app.backup.task_cleaner import TaskCleaner
from app.models import BackupRecord, RestoreRecord


def _make_record(**overrides):
    data = {
        "backup_id": "backup-test",
        "backup_type": "full",
        "status": "completed",
    }
    data.update(overrides)
    rec = BackupRecord(**data)
    db.session.add(rec)
    db.session.commit()
    return rec


class TestShouldResolveConflict:
    def test_mysql_running_and_external_completed(self):
        c = SimpleNamespace(
            conflict_reason="MySQL=running, 外部=completed",
            completed_at=None,
            status="pending",
        )
        assert backup_service.should_resolve_conflict(c) is True

    def test_mysql_completed_and_external_pending(self):
        c = SimpleNamespace(
            conflict_reason="MySQL=completed, 外部=pending",
            completed_at=None,
            status="pending",
        )
        assert backup_service.should_resolve_conflict(c) is True

    def test_completed_at_with_pending_status(self):
        c = SimpleNamespace(
            conflict_reason="",
            completed_at=datetime.now(timezone.utc),
            status="running",
        )
        assert backup_service.should_resolve_conflict(c) is True

    def test_no_match_returns_false(self):
        c = SimpleNamespace(
            conflict_reason="MySQL=running, 外部=running",
            completed_at=None,
            status="running",
        )
        assert backup_service.should_resolve_conflict(c) is False

    def test_malformed_returns_false(self):
        assert backup_service.should_resolve_conflict(None) is False


class TestBackupConfig:
    def test_get_config_defaults(self, app):
        result = backup_service.get_config()
        assert result["auto_backup"] is False
        assert result["backup_interval_hours"] == 24
        assert result["retention_days"] == 30
        assert result["backup_type"] == "full"

    def test_update_and_get_roundtrip(self, app):
        backup_service.update_config(
            {
                "auto_backup": True,
                "backup_interval_hours": 6,
                "retention_days": 14,
                "backup_time": "03:30",
                "backup_type": "incremental",
            }
        )
        result = backup_service.get_config()
        assert result["auto_backup"] is True
        assert result["backup_interval_hours"] == 6
        assert result["retention_days"] == 14
        assert result["backup_time"] == "03:30"
        assert result["backup_type"] == "incremental"

    def test_update_overwrites_existing(self, app):
        backup_service.update_config({"retention_days": 7})
        backup_service.update_config({"retention_days": 45})
        assert backup_service.get_config()["retention_days"] == 45


class TestListBackupRecords:
    def test_pagination_and_filter(self, app):
        _make_record(backup_id="r1", status="completed", backup_type="full")
        _make_record(backup_id="r2", status="failed", backup_type="incremental")
        total, items = backup_service.list_backup_records(
            page=1,
            size=10,
            status="completed",
            backup_type="full",
            sort_by="created_at",
            sort_order="desc",
        )
        assert total == 1
        assert items[0].backup_id == "r1"

    def test_default_sort_asc(self, app):
        _make_record(backup_id="a1")
        _make_record(backup_id="a2")
        total, items = backup_service.list_backup_records(
            page=1,
            size=10,
            status=None,
            backup_type=None,
            sort_by="backup_id",
            sort_order="asc",
        )
        assert total == 2
        assert [r.backup_id for r in items] == ["a1", "a2"]


class TestCleanupExpired:
    def test_force_removes_expired(self, app):
        old = datetime.now(timezone.utc) - timedelta(days=200)
        _make_record(
            backup_id="old1", status="completed", backup_type="full", created_at=old
        )
        _make_record(backup_id="fresh", status="completed", backup_type="full")
        count = backup_service.cleanup_expired(force=True)
        assert count == 1
        assert BackupRecord.query.filter_by(backup_id="old1").first() is None
        assert BackupRecord.query.filter_by(backup_id="fresh").first() is not None

    def test_non_force_keeps_physical(self, app):
        old = datetime.now(timezone.utc) - timedelta(days=200)
        _make_record(
            backup_id="phys", status="completed", backup_type="physical", created_at=old
        )
        _make_record(
            backup_id="full", status="completed", backup_type="full", created_at=old
        )
        count = backup_service.cleanup_expired(force=False)
        assert count == 1
        assert BackupRecord.query.filter_by(backup_id="phys").first() is not None
        assert BackupRecord.query.filter_by(backup_id="full").first() is None


class TestSyncPhysicalBackups:
    def test_sync_inserts_missing(self, app, monkeypatch):
        fake_engine = SimpleNamespace(
            list_backups=lambda: [
                {"backup_id": "phys-1"},
                {"backup_id": "phys-2"},
            ]
        )
        monkeypatch.setattr(
            backup_service, "get_physical_backup_engine", lambda: fake_engine
        )
        synced = backup_service.sync_physical_backups_to_database()
        assert synced == 2
        assert BackupRecord.query.filter_by(backup_id="phys-1").first() is not None

    def test_sync_skips_existing(self, app, monkeypatch):
        _make_record(backup_id="phys-1", backup_type="physical")
        fake_engine = SimpleNamespace(list_backups=lambda: [{"backup_id": "phys-1"}])
        monkeypatch.setattr(
            backup_service, "get_physical_backup_engine", lambda: fake_engine
        )
        assert backup_service.sync_physical_backups_to_database() == 0


class TestTaskCleaner:
    def test_cleanup_stuck_backup_no_file_path(self, app):
        old = datetime.now(timezone.utc) - timedelta(minutes=120)
        _make_record(
            backup_id="stuck", status="running", file_path=None, created_at=old
        )
        cleaner = TaskCleaner()
        result = cleaner.cleanup_stuck_tasks()
        assert result["backup_cleaned"] == 1
        rec = BackupRecord.query.filter_by(backup_id="stuck").first()
        assert rec.status == "failed"

    def test_cleanup_stuck_backup_file_exists(self, app, tmp_path, monkeypatch):
        import os

        old = datetime.now(timezone.utc) - timedelta(minutes=120)
        monkeypatch.setattr(os.path, "exists", lambda p: True)
        monkeypatch.setattr(os.path, "getsize", lambda p: 5)
        _make_record(
            backup_id="stuck2",
            status="pending",
            file_path="backups/x.bak",
            created_at=old,
        )
        cleaner = TaskCleaner()
        result = cleaner.cleanup_stuck_tasks()
        assert result["backup_cleaned"] == 1
        rec = BackupRecord.query.filter_by(backup_id="stuck2").first()
        assert rec.status == "completed"
        assert rec.file_size == 5

    def test_cleanup_stuck_restore(self, app):
        old = datetime.now(timezone.utc) - timedelta(minutes=120)
        db.session.add(
            RestoreRecord(
                restore_id="r-stuck",
                restore_type="full",
                status="running",
                created_at=old,
            )
        )
        db.session.commit()
        cleaner = TaskCleaner()
        result = cleaner.cleanup_stuck_tasks()
        assert result["restore_cleaned"] == 1
        rec = RestoreRecord.query.filter_by(restore_id="r-stuck").first()
        assert rec.status == "failed"

    def test_cleanup_nothing_stuck(self, app):
        cleaner = TaskCleaner()
        result = cleaner.cleanup_stuck_tasks()
        assert result["total_cleaned"] == 0

    def test_safe_operation_success(self, app):
        cleaner = TaskCleaner()
        result = cleaner._safe_database_operation(lambda: 42, "test")
        assert result == {"success": True, "result": 42}

    def test_safe_operation_exception(self, app):
        cleaner = TaskCleaner()

        def boom():
            raise RuntimeError("boom")

        result = cleaner._safe_database_operation(boom, "test")
        assert result["success"] is False
        assert "boom" in result["error"]

    def test_get_cleanup_status(self, app):
        cleaner = TaskCleaner()
        status = cleaner.get_cleanup_status()
        assert not status["daemon_running"]
        assert "config" in status

    def test_init_app_registers_extension(self, app):
        cleaner = TaskCleaner()
        cleaner.init_app(app)
        assert app.extensions["task_cleaner"] is cleaner
        assert cleaner.config["enable_auto_cleanup"] is True

    def test_start_daemon_disabled(self, app):
        cleaner = TaskCleaner()
        cleaner.config["enable_auto_cleanup"] = False
        cleaner.start_cleanup_daemon()
        assert cleaner.cleaning_thread is None


class TestTaskCleanerMore:
    def test_check_database_connection(self, app):
        cleaner = TaskCleaner()
        assert cleaner._check_database_connection() is True

    def test_daemon_worker_exits_when_stopped(self, app):
        cleaner = TaskCleaner()
        cleaner.app = app
        cleaner.config["cleanup_interval_minutes"] = 0
        cleaner.stop_event.set()
        cleaner._cleanup_daemon_worker()  # 应立刻退出,不挂起

    def test_cleanup_stuck_backups_returns_errors(self, app):
        cleaner = TaskCleaner()
        # 直接调用内部方法,模拟无卡死任务
        result = cleaner._cleanup_stuck_backups()
        assert result["cleaned_count"] == 0


class TestSafeOperationRetry:
    def test_retry_after_operational_error(self, app, monkeypatch):
        from sqlalchemy.exc import OperationalError

        cleaner = TaskCleaner()
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 2:
                raise OperationalError("stmt", {}, Exception("conn down"))
            return "ok"

        # 减少 sleep 避免测试慢
        monkeypatch.setattr(cleaner, "_safe_database_operation", None)
        result = TaskCleaner()._safe_database_operation(flaky, "test", max_retries=1)
        # 首次失败后重试成功
        assert result["success"] is True
        assert result["result"] == "ok"
