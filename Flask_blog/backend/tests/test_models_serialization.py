"""模型序列化测试 — 覆盖 models.py 中有 to_dict 的模型。"""

from app import db
from app.models import (
    BackupConfig,
    BackupRecord,
    BackupTask,
    LogEntry,
    Media,
    MediaFolder,
    MediaUsage,
    RestoreRecord,
)


class TestBackupModels:
    def test_backup_record_to_dict(self, app):
        rec = BackupRecord(backup_id="b1", backup_type="full", status="completed")
        db.session.add(rec)
        db.session.commit()
        d = rec.to_dict()
        assert d["backup_id"] == "b1"
        assert d["status"] == "completed"

    def test_restore_record_to_dict(self, app):
        rec = RestoreRecord(restore_id="r1", restore_type="full", status="completed")
        db.session.add(rec)
        db.session.commit()
        d = rec.to_dict()
        assert d["restore_id"] == "r1"

    def test_backup_config_to_dict(self, app):
        cfg = BackupConfig(config_key="auto_backup", config_value="false")
        db.session.add(cfg)
        db.session.commit()
        d = cfg.to_dict()
        assert d["config_key"] == "auto_backup"

    def test_backup_task_to_dict(self, app):
        t = BackupTask(task_id="t1", task_name="backup", task_type="manual")
        db.session.add(t)
        db.session.commit()
        d = t.to_dict()
        assert d["task_type"] == "manual"


class TestMediaModels:
    def test_media_folder_to_dict(self, app):
        from app.models import User

        u = User(email="mf@test.com", password_hash="x", role="author")
        db.session.add(u)
        db.session.commit()
        folder = MediaFolder(name="f1", owner_id=u.id)
        db.session.add(folder)
        db.session.commit()
        d = folder.to_dict()
        assert d["name"] == "f1"

    def test_media_to_dict(self, app):
        from app.models import User

        u = User(email="mm@test.com", password_hash="x", role="author")
        db.session.add(u)
        db.session.commit()
        m = Media(
            filename="m.jpg",
            mime_type="image/jpeg",
            media_type="image",
            file_path="u/m.jpg",
            original_name="m.jpg",
            file_size=10,
            owner_id=u.id,
        )
        db.session.add(m)
        db.session.commit()
        d = m.to_dict()
        assert d["filename"] == "m.jpg"

    def test_media_usage_to_dict(self, app):
        from app.models import User

        u = User(email="mu@test.com", password_hash="x", role="author")
        db.session.add(u)
        db.session.commit()
        m = Media(
            filename="x.png",
            mime_type="image/png",
            media_type="image",
            file_path="u/x.png",
            original_name="x.png",
            file_size=1,
            owner_id=u.id,
        )
        db.session.add(m)
        db.session.commit()
        usage = MediaUsage(media_id=m.id, usage_type="other")
        db.session.add(usage)
        db.session.commit()
        d = usage.to_dict()
        assert d["media_id"] == m.id


class TestLogModel:
    def test_log_entry_to_dict(self, app):
        e = LogEntry(level="INFO", source="S", message="m")
        db.session.add(e)
        db.session.commit()
        d = e.to_dict()
        assert d["message"] == "m"
        assert d["level"] == "INFO"
