"""物理恢复引擎测试 — _validate_backup + restore_database(编排路径)。"""

import json

from app.backup.physical_restore_engine import PhysicalRestoreEngine


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
