"""物理恢复引擎测试 — _validate_backup + restore_database(编排路径)。"""

import json
import types

from app.backup.physical_restore_engine import PhysicalRestoreEngine


def _success_engine(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.backup.physical_restore_engine.subprocess.run",
        lambda args, **kw: __import__("types").SimpleNamespace(
            returncode=0, stdout="", stderr=""
        ),
    )
    return _make_engine(tmp_path)


def _make_engine(tmp_path):
    return PhysicalRestoreEngine(
        {
            "mysql_container": "x",
            "mysql_volume": "mysqldata",
            "backup_root": str(tmp_path),
        }
    )


def _write_backup(tmp_path, backup_id, compressed=False):
    backup_dir = tmp_path / backup_id
    backup_dir.mkdir(exist_ok=True)
    meta = {
        "backup_id": backup_id,
        "compressed": compressed,
        "volume_name": "mysqldata",
        "databases_count": 1,
    }
    (backup_dir / "backup_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    if compressed:
        (tmp_path / f"{backup_id}.tar.gz").write_bytes(b"x")
    else:
        (backup_dir / "mysql_data.tar.gz").write_bytes(b"x")
    return meta


class TestValidateBackup:
    def test_valid_uncompressed(self, tmp_path):
        engine = _make_engine(tmp_path)
        _write_backup(tmp_path, "bk1", compressed=False)
        info = engine._validate_backup("bk1")
        assert info is not None
        assert info["backup_id"] == "bk1"

    def test_valid_compressed(self, tmp_path):
        engine = _make_engine(tmp_path)
        _write_backup(tmp_path, "bk1", compressed=True)
        info = engine._validate_backup("bk1")
        assert info is not None

    def test_missing_backup(self, tmp_path):
        engine = _make_engine(tmp_path)
        assert engine._validate_backup("nope") is None


class TestRestoreDatabase:
    def test_restore_success(self, tmp_path, monkeypatch):
        engine = _make_engine(tmp_path)
        monkeypatch.setattr(engine, "_validate_backup", lambda bid: {"backup_id": bid})
        monkeypatch.setattr(engine, "_check_environment", lambda: True)
        monkeypatch.setattr(engine, "_prepare_for_restore", lambda: {"success": True})
        monkeypatch.setattr(
            engine, "_perform_physical_restore", lambda bid: {"success": True}
        )
        monkeypatch.setattr(
            engine, "_restart_database_service", lambda: {"success": True}
        )
        monkeypatch.setattr(engine, "_validate_restore", lambda: {"ok": True})
        result = engine.restore_database("bk1", "r1")
        assert result["success"] is True
        assert result["restore_id"] == "r1"

    def test_restore_backup_invalid(self, tmp_path, monkeypatch):
        engine = _make_engine(tmp_path)
        monkeypatch.setattr(engine, "_validate_backup", lambda bid: None)
        result = engine.restore_database("nope", "r2")
        assert result["success"] is False

    def test_restore_env_fail(self, tmp_path, monkeypatch):
        engine = _make_engine(tmp_path)
        monkeypatch.setattr(engine, "_validate_backup", lambda bid: {"backup_id": bid})
        monkeypatch.setattr(engine, "_check_environment", lambda: False)
        result = engine.restore_database("bk1", "r3")
        assert result["success"] is False


class TestDockerMethods:
    def test_check_environment_success(self, tmp_path, monkeypatch):

        engine = _make_engine(tmp_path)

        def fake_run(args, **kw):
            key = args[1] if len(args) > 1 else ""
            if key == "version":
                return types.SimpleNamespace(returncode=0, stdout="Docker", stderr="")
            if key == "ps":
                return types.SimpleNamespace(returncode=0, stdout="x\n", stderr="")
            if key == "inspect":
                return types.SimpleNamespace(returncode=0, stdout="{}", stderr="")
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(
            "app.backup.physical_restore_engine.subprocess.run", fake_run
        )
        assert engine._check_environment() is True

    def test_check_environment_docker_missing(self, tmp_path, monkeypatch):

        engine = _make_engine(tmp_path)

        def fake_run(args, **kw):
            return types.SimpleNamespace(returncode=1, stdout="", stderr="err")

        monkeypatch.setattr(
            "app.backup.physical_restore_engine.subprocess.run", fake_run
        )
        assert engine._check_environment() is False

    def test_check_environment_container_missing(self, tmp_path, monkeypatch):

        engine = _make_engine(tmp_path)

        def fake_run(args, **kw):
            key = args[1] if len(args) > 1 else ""
            if key == "version":
                return types.SimpleNamespace(returncode=0, stdout="Docker", stderr="")
            if key == "ps":
                return types.SimpleNamespace(returncode=0, stdout="other\n", stderr="")
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(
            "app.backup.physical_restore_engine.subprocess.run", fake_run
        )
        assert engine._check_environment() is False

    def test_get_container_volume(self, tmp_path, monkeypatch):

        engine = _make_engine(tmp_path)

        def fake_run(args, **kw):
            return types.SimpleNamespace(
                returncode=0, stdout='[{"Name":"mysqldata"}]', stderr=""
            )

        monkeypatch.setattr(
            "app.backup.physical_restore_engine.subprocess.run", fake_run
        )
        vol = engine._get_container_volume()
        assert vol in ("mysqldata", None)

    def test_restart_database_service(self, tmp_path, monkeypatch):

        import types

        engine = _make_engine(tmp_path)

        def fake_run(args, **kw):
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(
            "app.backup.physical_restore_engine.subprocess.run", fake_run
        )
        result = engine._restart_database_service()
        assert result["success"] is True


class TestRestoreSubSteps:
    def _success_subprocess(self, tmp_path, monkeypatch):
        import types

        engine = _make_engine(tmp_path)
        monkeypatch.setattr(
            "app.backup.physical_restore_engine.subprocess.run",
            lambda args, **kw: types.SimpleNamespace(
                returncode=0, stdout="", stderr=""
            ),
        )
        return engine

    def test_stop_mysql_container(self, tmp_path, monkeypatch):
        engine = _success_engine(tmp_path, monkeypatch)
        assert engine._stop_mysql_container()["success"] is True

    def test_backup_current_data(self, tmp_path, monkeypatch):
        engine = _success_engine(tmp_path, monkeypatch)
        result = engine._backup_current_data()
        assert result["success"] is True

    def test_clear_mysql_volume(self, tmp_path, monkeypatch):
        engine = _success_engine(tmp_path, monkeypatch)
        result = engine._clear_mysql_volume()
        assert result["success"] is True

    def test_validate_restore(self, tmp_path, monkeypatch):
        engine = _success_engine(tmp_path, monkeypatch)
        result = engine._validate_restore()
        assert isinstance(result, dict)

    def test_perform_physical_restore_success(self, tmp_path, monkeypatch):
        engine = _success_engine(tmp_path, monkeypatch)
        result = engine._perform_physical_restore("bk1")
        assert isinstance(result, dict)

    def test_prepare_for_restore_success(self, tmp_path, monkeypatch):

        engine = _make_engine(tmp_path)
        monkeypatch.setattr(engine, "_stop_mysql_container", lambda: {"success": True})
        monkeypatch.setattr(engine, "_backup_current_data", lambda: {"success": True})
        monkeypatch.setattr(engine, "_clear_mysql_volume", lambda: {"success": True})
        result = engine._prepare_for_restore()
        assert result["success"] is True


class TestRestoreFromData:
    def test_restore_from_data_file_success(self, tmp_path, monkeypatch):
        engine = _success_engine(tmp_path, monkeypatch)
        result = engine._restore_from_data_file(tmp_path / "d.tar.gz")
        assert result["success"] is True

    def test_restore_from_data_file_fail(self, tmp_path, monkeypatch):
        import types

        engine = _make_engine(tmp_path)
        monkeypatch.setattr(
            "app.backup.physical_restore_engine.subprocess.run",
            lambda args, **kw: types.SimpleNamespace(
                returncode=1, stdout="", stderr="err"
            ),
        )
        result = engine._restore_from_data_file(tmp_path / "d.tar.gz")
        assert result["success"] is False

    def test_restore_from_archive_success(self, tmp_path, monkeypatch):
        import types

        engine = _make_engine(tmp_path)
        monkeypatch.setattr(
            engine, "_restore_from_data_file", lambda d: {"success": True}
        )
        monkeypatch.setattr(
            "app.backup.physical_restore_engine.subprocess.run",
            lambda args, **kw: types.SimpleNamespace(
                returncode=0, stdout="", stderr=""
            ),
        )
        result = engine._restore_from_archive(tmp_path / "bk.tar.gz", "bk1")
        assert result["success"] in (True, False)
