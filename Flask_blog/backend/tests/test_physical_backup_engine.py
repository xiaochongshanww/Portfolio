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


class TestCreateBackup:
    def test_create_backup_success(self, tmp_path, monkeypatch):
        engine = PhysicalBackupEngine(
            {
                "mysql_container": "x",
                "mysql_volume": "mysqldata",
                "backup_root": str(tmp_path),
                "compress_backup": True,
            }
        )
        monkeypatch.setattr(engine, "_check_docker_environment", lambda: True)
        monkeypatch.setattr(engine, "_get_database_info", lambda: {"mysql": "ok"})

        def fake_backup(d):
            (d / "data.sql").write_bytes(b"x" * 100)
            return {"success": True}

        monkeypatch.setattr(engine, "_perform_physical_backup", fake_backup)
        result = engine.create_backup("bk-test")
        assert result["success"] is True
        assert (tmp_path / "bk-test").exists()
        assert result["backup_id"] == "bk-test"
        assert result["summary"]["backup_size"] > 0
        assert result["metadata"]["backup_size"] == 100

    def test_create_backup_docker_fail(self, tmp_path, monkeypatch):
        engine = PhysicalBackupEngine(
            {
                "mysql_container": "x",
                "mysql_volume": "mysqldata",
                "backup_root": str(tmp_path),
            }
        )
        monkeypatch.setattr(engine, "_check_docker_environment", lambda: False)
        result = engine.create_backup("bk-fail")
        assert result["success"] is False


class TestDockerMethods:
    def _fake_run(self, results):
        def fake_run(args, **kw):
            key = args[1] if len(args) > 1 else ""
            return results.get(
                key,
                __import__("types").SimpleNamespace(returncode=0, stdout="", stderr=""),
            )

        return fake_run

    def test_check_docker_success(self, tmp_path, monkeypatch):
        engine = PhysicalBackupEngine(
            {
                "mysql_container": "blog-mysql",
                "mysql_volume": "mysqldata",
                "backup_root": str(tmp_path),
            }
        )
        import types

        def fake_run(args, **kw):
            key = args[1] if len(args) > 1 else ""
            if key == "version":
                return types.SimpleNamespace(
                    returncode=0, stdout="Docker version", stderr=""
                )
            if key == "ps":
                return types.SimpleNamespace(
                    returncode=0, stdout="blog-mysql\n", stderr=""
                )
            if key == "volume":
                return types.SimpleNamespace(
                    returncode=0, stdout="mysqldata\n", stderr=""
                )
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(engine, "_get_container_volume", lambda: "mysqldata")
        monkeypatch.setattr(
            "app.backup.physical_backup_engine.subprocess.run", fake_run
        )
        assert engine._check_docker_environment() is True

    def test_check_docker_missing_container(self, tmp_path, monkeypatch):
        engine = PhysicalBackupEngine(
            {
                "mysql_container": "blog-mysql",
                "mysql_volume": "mysqldata",
                "backup_root": str(tmp_path),
            }
        )
        import types

        def fake_run(args, **kw):
            key = args[1] if len(args) > 1 else ""
            if key == "version":
                return types.SimpleNamespace(returncode=0, stdout="Docker", stderr="")
            if key == "ps":
                return types.SimpleNamespace(returncode=0, stdout="other\n", stderr="")
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(
            "app.backup.physical_backup_engine.subprocess.run", fake_run
        )
        assert engine._check_docker_environment() is False


class TestPhysicalBackupExecution:
    def test_hot_backup_success(self, tmp_path, monkeypatch):
        import types

        engine = PhysicalBackupEngine(
            {
                "mysql_container": "x",
                "mysql_volume": "mysqldata",
                "backup_root": str(tmp_path),
            }
        )
        monkeypatch.setattr(
            "app.backup.physical_backup_engine.subprocess.run",
            lambda args, **kw: types.SimpleNamespace(
                returncode=0, stdout="", stderr=""
            ),
        )
        result = engine._hot_backup_via_docker(tmp_path / "bk")
        assert result["success"] is True

    def test_hot_backup_fail(self, tmp_path, monkeypatch):
        import types

        engine = PhysicalBackupEngine(
            {
                "mysql_container": "x",
                "mysql_volume": "mysqldata",
                "backup_root": str(tmp_path),
            }
        )
        monkeypatch.setattr(
            "app.backup.physical_backup_engine.subprocess.run",
            lambda args, **kw: types.SimpleNamespace(
                returncode=1, stdout="", stderr="err"
            ),
        )
        result = engine._hot_backup_via_docker(tmp_path / "bk")
        assert result["success"] is False

    def test_perform_physical_backup_hot(self, tmp_path, monkeypatch):
        import types

        engine = PhysicalBackupEngine(
            {
                "mysql_container": "x",
                "mysql_volume": "mysqldata",
                "backup_root": str(tmp_path),
                "hot_backup": True,
            }
        )
        monkeypatch.setattr(
            "app.backup.physical_backup_engine.subprocess.run",
            lambda args, **kw: types.SimpleNamespace(
                returncode=0, stdout="", stderr=""
            ),
        )
        result = engine._perform_physical_backup(tmp_path / "bk")
        assert result["success"] is True

    def test_perform_physical_backup_cold(self, tmp_path, monkeypatch):
        import types

        engine = PhysicalBackupEngine(
            {
                "mysql_container": "x",
                "mysql_volume": "mysqldata",
                "backup_root": str(tmp_path),
                "hot_backup": False,
            }
        )
        monkeypatch.setattr(
            "app.backup.physical_backup_engine.subprocess.run",
            lambda args, **kw: types.SimpleNamespace(
                returncode=0, stdout="", stderr=""
            ),
        )
        result = engine._perform_physical_backup(tmp_path / "bk")
        assert result["success"] is True


class TestMoreMethods:
    def test_get_database_info(self, tmp_path, monkeypatch):
        import types

        engine = PhysicalBackupEngine(
            {
                "mysql_container": "x",
                "mysql_volume": "mysqldata",
                "backup_root": str(tmp_path),
            }
        )

        def fake_run(args, **kw):
            return types.SimpleNamespace(returncode=0, stdout="5.7\n", stderr="")

        monkeypatch.setattr(
            "app.backup.physical_backup_engine.subprocess.run", fake_run
        )
        info = engine._get_database_info()
        assert isinstance(info, dict)

    def test_calculate_backup_size(self, tmp_path):
        engine = PhysicalBackupEngine(
            {
                "mysql_container": "x",
                "mysql_volume": "mysqldata",
                "backup_root": str(tmp_path),
            }
        )
        d = tmp_path / "bk"
        d.mkdir()
        (d / "a").write_bytes(b"12345")
        assert engine._calculate_backup_size(d) == 5

    def test_create_compressed_archive(self, tmp_path):
        engine = PhysicalBackupEngine(
            {
                "mysql_container": "x",
                "mysql_volume": "mysqldata",
                "backup_root": str(tmp_path),
            }
        )
        d = tmp_path / "bk"
        d.mkdir()
        (d / "a").write_bytes(b"x")
        archive = engine._create_compressed_archive(d, "bk")
        assert archive.exists()
        assert archive.name == "bk.tar.gz"
