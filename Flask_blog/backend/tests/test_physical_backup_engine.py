"""物理备份引擎文件系统方法测试 — list/get/delete/stats 不依赖 Docker。"""

import json

from app.backup.physical_backup_engine import PhysicalBackupEngine


def _make_engine(tmp_path):
    return PhysicalBackupEngine(
        {
            "mysql_container": "x",
            "mysql_volume": "mysqldata",
            "backup_root": str(tmp_path),
        }
    )


def _write_backup(tmp_path, backup_id, **overrides):
    meta = {
        "backup_id": backup_id,
        "backup_type": "full",
        "status": "completed",
        "backup_size": 100,
        "compressed_size": 50,
        "created_at": "2025-09-01T00:00:00Z",
        "databases_count": 1,
        "files_count": 2,
    }
    meta.update(overrides)
    backup_dir = tmp_path / backup_id
    backup_dir.mkdir(exist_ok=True)
    (backup_dir / "backup_metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8"
    )
    return meta


class TestListBackups:
    def test_empty_root(self, tmp_path):
        engine = _make_engine(tmp_path)
        assert engine.list_backups() == []

    def test_list_with_metadata(self, tmp_path):
        engine = _make_engine(tmp_path)
        _write_backup(tmp_path, "bk1")
        _write_backup(tmp_path, "bk2", backup_size=200, compressed_size=100)
        backups = engine.list_backups()
        assert len(backups) == 2
        ids = {b["backup_id"] for b in backups}
        assert ids == {"bk1", "bk2"}

    def test_ignores_dirs_without_metadata(self, tmp_path):
        engine = _make_engine(tmp_path)
        _write_backup(tmp_path, "bk1")
        (tmp_path / "no_meta").mkdir()
        assert len(engine.list_backups()) == 1


class TestGetBackupInfo:
    def test_existing(self, tmp_path):
        engine = _make_engine(tmp_path)
        _write_backup(tmp_path, "bk1")
        info = engine.get_backup_info("bk1")
        assert info is not None
        assert info["backup_id"] == "bk1"

    def test_missing(self, tmp_path):
        engine = _make_engine(tmp_path)
        assert engine.get_backup_info("nope") is None


class TestDeleteBackup:
    def test_delete_dir_and_archive(self, tmp_path):
        engine = _make_engine(tmp_path)
        _write_backup(tmp_path, "bk1")
        (tmp_path / "bk1.tar.gz").write_bytes(b"archive")
        result = engine.delete_backup("bk1")
        assert result["success"] is True
        assert not (tmp_path / "bk1").exists()
        assert not (tmp_path / "bk1.tar.gz").exists()

    def test_delete_missing_is_success(self, tmp_path):
        engine = _make_engine(tmp_path)
        result = engine.delete_backup("nope")
        assert result["success"] is True


class TestStorageStatistics:
    def test_statistics(self, tmp_path):
        engine = _make_engine(tmp_path)
        _write_backup(tmp_path, "bk1")
        _write_backup(tmp_path, "bk2", backup_size=200, compressed_size=100)
        stats = engine.get_storage_statistics()
        assert stats["total_backups"] == 2
        assert stats["total_raw_size"] == 300
        assert stats["total_compressed_size"] == 150
        assert stats["compressed_backups"] == 2

    def test_statistics_empty(self, tmp_path):
        engine = _make_engine(tmp_path)
        stats = engine.get_storage_statistics()
        assert stats["total_backups"] == 0


class TestDirectorySize:
    def test_get_directory_size(self, tmp_path):
        engine = _make_engine(tmp_path)
        d = tmp_path / "physical_bk1"
        d.mkdir()
        (d / "a.bin").write_bytes(b"12345")
        (d / "sub").mkdir()
        (d / "sub" / "b.bin").write_bytes(b"1234567")
        assert engine._get_directory_size(d) == 12

    def test_calculate_actual_storage_size(self, tmp_path):
        engine = _make_engine(tmp_path)
        (tmp_path / "physical_bk1").mkdir()
        (tmp_path / "physical_bk1" / "data.bin").write_bytes(b"0123456789")
        (tmp_path / "bk1.tar.gz").write_bytes(b"012345")
        (tmp_path / "pre_restore_backup").mkdir()
        (tmp_path / "pre_restore_backup" / "tmp.bin").write_bytes(b"0" * 100)
        size = engine._calculate_actual_backup_storage_size()
        # 只统计 physical_ 目录(10) + 根目录归档文件(6),排除 pre_restore_backup
        assert size == 16
