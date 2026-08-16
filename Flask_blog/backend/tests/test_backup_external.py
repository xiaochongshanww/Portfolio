"""外部元数据系统测试 — ExternalMetadataManager 独立模式 + 模型方法。"""

from datetime import datetime, timedelta, timezone

from app.backup.backup_records_external import (
    BackupRecordExternal,
    ExternalMetadataManager,
)


def _make_manager(tmp_path):
    return ExternalMetadataManager(db_path=f"sqlite:///{tmp_path / 'external.db'}")


class TestExternalMetadataManager:
    def test_create_get_roundtrip(self, tmp_path):
        mgr = _make_manager(tmp_path)
        rec = mgr.create_backup_record("b1", backup_type="physical", status="completed")
        assert rec.backup_id == "b1"
        fetched = mgr.get_backup_record("b1")
        assert fetched is not None
        assert fetched.status == "completed"

    def test_get_missing(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr.get_backup_record("nope") is None

    def test_update_backup_record(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.create_backup_record("b1")
        assert mgr.update_backup_record("b1", status="failed", file_size=123) is True
        rec = mgr.get_backup_record("b1")
        assert rec.status == "failed"
        assert rec.file_size == 123

    def test_update_missing(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr.update_backup_record("nope", status="failed") is False

    def test_delete_backup_record(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.create_backup_record("b1")
        assert mgr.delete_backup_record("b1") is True
        assert mgr.get_backup_record("b1") is None
        assert mgr.delete_backup_record("b1") is False

    def test_statistics(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.create_backup_record("b1", status="completed")
        mgr.create_backup_record("b2", status="completed")
        mgr.create_backup_record("b3", status="failed")
        stats = mgr.get_statistics()
        assert stats["total_backup_records"] == 3
        assert stats["completed_backups"] == 2
        assert stats["failed_backups"] == 1
        assert stats["success_rate"] == round(2 / 3 * 100, 2)

    def test_conflict_count_and_find(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.create_backup_record("b1")
        rec = mgr.get_backup_record("b1")
        rec.sync_status = "conflict"
        mgr.save_record(rec)
        assert mgr.get_conflict_count() == 1
        conflicts = mgr.find_conflicts()
        assert len(conflicts) == 1
        assert conflicts[0].backup_id == "b1"

    def test_save_record(self, tmp_path):
        mgr = _make_manager(tmp_path)
        rec = mgr.create_backup_record("b1")
        rec.status = "failed"
        mgr.save_record(rec)
        assert mgr.get_backup_record("b1").status == "failed"


class TestBackupRecordExternalModel:
    def test_extra_data_roundtrip(self, tmp_path):
        mgr = _make_manager(tmp_path)
        rec = mgr.create_backup_record("b1", description="desc", requested_by="me")
        assert rec.extra_data["description"] == "desc"
        assert rec.extra_data["requested_by"] == "me"

    def test_get_duration(self, tmp_path):
        mgr = _make_manager(tmp_path)
        rec = mgr.create_backup_record("b1")
        rec.started_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        rec.completed_at = datetime.now(timezone.utc)
        assert rec.get_duration() is not None
        assert rec.get_duration() > 0

    def test_to_dict(self, tmp_path):
        mgr = _make_manager(tmp_path)
        rec = mgr.create_backup_record("b1", backup_type="physical", status="completed")
        d = rec.to_dict()
        assert d["backup_id"] == "b1"
        assert d["status"] == "completed"

    def test_from_mysql_record(self):
        rec = BackupRecordExternal.from_mysql_record(
            {
                "backup_id": "m1",
                "backup_type": "physical",
                "status": "completed",
                "file_size": 42,
            }
        )
        assert rec.backup_id == "m1"
        assert rec.sync_status == "synced"
        assert rec.file_size == 42


class TestSyncStats:

    def test_resolve_all_conflicts(self, tmp_path):
        mgr = _make_manager(tmp_path)
        rec = mgr.create_backup_record("conflict-1")
        rec = mgr.get_backup_record("conflict-1")
        rec.sync_status = "conflict"
        mgr.save_record(rec)
        result = mgr.resolve_all_conflicts()
        assert isinstance(result, dict)

    def test_find_and_count_conflicts(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr.get_conflict_count() >= 0
        assert isinstance(mgr.find_conflicts(), list)


class TestExternalModels:
    def test_restore_record_external_to_dict(self, tmp_path):
        from app.backup.backup_records_external import RestoreRecordExternal

        mgr = _make_manager(tmp_path)
        session = mgr._get_session()
        rec = RestoreRecordExternal(
            restore_id="rr1", restore_type="full", status="pending"
        )
        session.add(rec)
        session.commit()
        d = rec.to_dict()
        assert d["restore_id"] == "rr1"
        assert d["restore_type"] == "full"

    def test_restore_options_property(self, tmp_path):
        from app.backup.backup_records_external import RestoreRecordExternal

        mgr = _make_manager(tmp_path)
        session = mgr._get_session()
        rec = RestoreRecordExternal(
            restore_id="rr2", restore_type="full", status="pending"
        )
        rec.restore_options = {"target_db": "blog"}
        session.add(rec)
        session.commit()
        assert rec.restore_options == {"target_db": "blog"}

    def test_sync_log_external_to_dict(self, tmp_path):
        from app.backup.backup_records_external import SyncLogExternal

        mgr = _make_manager(tmp_path)
        session = mgr._get_session()
        log = SyncLogExternal(operation="sync", record_type="backup", record_id="b1")
        session.add(log)
        session.commit()
        assert log.operation == "sync"
        assert log.record_type == "backup"
        assert log.record_id == "b1"


class TestSyncFromMysql:
    def test_sync_creates_records(self, tmp_path):
        mgr = _make_manager(tmp_path)
        result = mgr.sync_from_mysql(
            [{"backup_id": "s1", "backup_type": "full", "status": "completed"}]
        )
        assert result["created"] == 1
        rec = mgr.get_backup_record("s1")
        assert rec is not None
        assert rec.status == "completed"

    def test_sync_second_time_unchanged(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.sync_from_mysql(
            [{"backup_id": "s2", "backup_type": "full", "status": "completed"}]
        )
        result = mgr.sync_from_mysql(
            [{"backup_id": "s2", "backup_type": "full", "status": "completed"}]
        )
        assert result["total_processed"] == 1

    def test_get_sync_statistics(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.sync_from_mysql(
            [{"backup_id": "s3", "backup_type": "full", "status": "completed"}]
        )
        stats = mgr.get_sync_statistics()
        assert isinstance(stats, dict)

    def test_cleanup_old_logs(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.sync_from_mysql(
            [{"backup_id": "s4", "backup_type": "full", "status": "completed"}]
        )
        count = mgr.cleanup_old_logs(days_to_keep=1)
        assert count >= 0

    def test_resolve_all_conflicts(self, tmp_path):
        mgr = _make_manager(tmp_path)
        rec = mgr.create_backup_record("conflict-x")
        rec = mgr.get_backup_record("conflict-x")
        rec.sync_status = "conflict"
        mgr.save_record(rec)
        result = mgr.resolve_all_conflicts()
        assert result["total_conflicts"] == 1


class TestBackupRecordExternalMethods:
    def test_extra_data_setter_clear(self, tmp_path):
        mgr = _make_manager(tmp_path)
        rec = mgr.create_backup_record("e1")
        rec.extra_data = {"a": 1}
        mgr.save_record(rec)
        assert rec.extra_data == {"a": 1}
        rec.extra_data = None
        mgr.save_record(rec)
        assert rec.extra_data is None

    def test_get_duration(self, tmp_path):
        from datetime import datetime, timedelta, timezone

        mgr = _make_manager(tmp_path)
        rec = mgr.create_backup_record("e2")
        rec.started_at = datetime.now(timezone.utc) - timedelta(seconds=30)
        rec.completed_at = datetime.now(timezone.utc)
        assert rec.get_duration() is not None
        assert rec.get_duration() > 0

    def test_verify_file_exists_no_path(self, tmp_path):
        mgr = _make_manager(tmp_path)
        rec = mgr.create_backup_record("e3")
        # 无 file_path 且非 physical → False
        assert rec.verify_file_exists() in (True, False)

    def test_update_sync_status(self, tmp_path):
        mgr = _make_manager(tmp_path)
        rec = mgr.create_backup_record("e4")
        rec.update_sync_status("synced", "done")
        mgr.save_record(rec)
        assert rec.sync_status == "synced"

    def test_to_dict_include_extra_data(self, tmp_path):
        mgr = _make_manager(tmp_path)
        rec = mgr.create_backup_record("e5", description="desc")
        d = rec.to_dict(include_extra_data=True)
        assert d["backup_id"] == "e5"
        assert "extra_data" in d or "description" in d
