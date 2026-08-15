"""备份引擎纯函数测试:backup_manager / restore_manager / smart_table_validator 等。"""

import tarfile

from app import db
from app.backup.backup_manager import BackupManager
from app.backup.physical_backup_engine import PhysicalBackupEngine
from app.backup.restore_manager import RestoreManager
from app.backup.smart_table_validator import SmartTableValidator
from app.models import BackupRecord


def _make_backup_manager(app):
    return BackupManager()


class TestBackupManagerCancellation:
    def test_create_and_check_flag(self, app):
        mgr = _make_backup_manager(app)
        evt = mgr._create_cancellation_flag("b1")
        assert isinstance(evt, object)
        assert mgr._is_cancelled("b1") is False

    def test_set_cancelled_in_memory(self, app):
        mgr = _make_backup_manager(app)
        mgr._create_cancellation_flag("b1")
        mgr._set_cancelled("b1")
        assert mgr._is_cancelled("b1") is True

    def test_set_cancelled_persists_db(self, app):
        mgr = _make_backup_manager(app)
        db.session.add(
            BackupRecord(backup_id="b-db", backup_type="full", status="running")
        )
        db.session.commit()
        mgr._set_cancelled("b-db")
        rec = BackupRecord.query.filter_by(backup_id="b-db").first()
        assert rec.status == "cancelled"

    def test_is_cancelled_from_db_status(self, app):
        mgr = _make_backup_manager(app)
        db.session.add(
            BackupRecord(backup_id="b-cancel", backup_type="full", status="cancelled")
        )
        db.session.commit()
        assert mgr._is_cancelled("b-cancel") is True

    def test_cleanup_flag(self, app):
        mgr = _make_backup_manager(app)
        mgr._create_cancellation_flag("b1")
        mgr._cleanup_cancellation_flag("b1")
        assert mgr._is_cancelled("b1") is False

    def test_cancel_backup_missing_record(self, app):
        mgr = _make_backup_manager(app)
        assert mgr.cancel_backup("does-not-exist") is False

    def test_cancel_backup_completed(self, app):
        mgr = _make_backup_manager(app)
        db.session.add(
            BackupRecord(backup_id="b-done", backup_type="full", status="completed")
        )
        db.session.commit()
        assert mgr.cancel_backup("b-done") is False

    def test_cancel_backup_running(self, app):
        mgr = _make_backup_manager(app)
        db.session.add(
            BackupRecord(backup_id="b-run", backup_type="full", status="running")
        )
        db.session.commit()
        assert mgr.cancel_backup("b-run") is True
        assert mgr._is_cancelled("b-run") is True


class TestBackupManagerFileOps:
    def test_should_exclude_fnmatch(self, app):
        from pathlib import Path

        mgr = _make_backup_manager(app)
        src = Path("source")
        assert (
            mgr._should_exclude(Path("source/__pycache__/x.py"), ["__pycache__/*"], src)
            is True
        )
        assert (
            mgr._should_exclude(Path("source/main.py"), ["__pycache__/*"], src) is False
        )
        assert mgr._should_exclude(Path("source/secret.txt"), ["*.txt"], src) is True

    def test_calculate_file_hash(self, app, tmp_path):
        mgr = _make_backup_manager(app)
        f = tmp_path / "data.txt"
        f.write_bytes(b"hello world")
        import hashlib

        expected = hashlib.md5(b"hello world").hexdigest()
        assert mgr._calculate_file_hash(f) == expected

    def test_calculate_checksum(self, app, tmp_path):
        mgr = _make_backup_manager(app)
        f = tmp_path / "data.txt"
        f.write_bytes(b"hello world")
        import hashlib

        expected = hashlib.sha256(b"hello world").hexdigest()
        assert mgr._calculate_checksum(f) == expected

    def test_calculate_original_size(self, app, tmp_path):
        mgr = _make_backup_manager(app)
        (tmp_path / "a.txt").write_bytes(b"12345")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.txt").write_bytes(b"1234567")
        assert mgr._calculate_original_size(tmp_path) == 12

    def test_create_archive(self, app, tmp_path):
        mgr = _make_backup_manager(app)
        (tmp_path / "f.txt").write_bytes(b"x")
        archive = mgr._create_archive(tmp_path)
        assert archive.exists()
        with tarfile.open(archive, "r:gz") as tar:
            names = tar.getnames()
        assert any(n.endswith("f.txt") for n in names)

    def test_manifest_roundtrip(self, app, tmp_path, monkeypatch):
        mgr = _make_backup_manager(app)
        monkeypatch.setattr(mgr, "backup_base_dir", tmp_path)
        mgr._save_backup_manifest({"a": 1, "b": [1, 2]})
        assert mgr._get_last_backup_manifest() == {"a": 1, "b": [1, 2]}


class TestPhysicalBackupEngineFormatters:
    def test_format_duration(self, app):
        engine = PhysicalBackupEngine(
            {
                "mysql_container": "x",
                "mysql_volume": "mysqldata",
                "backup_root": "backups/physical",
            }
        )
        assert "毫秒" in engine._format_duration(0.5)
        assert "秒" in engine._format_duration(30)
        assert "分" in engine._format_duration(120)
        assert "小时" in engine._format_duration(7200)

    def test_format_file_size(self, app):
        engine = PhysicalBackupEngine(
            {
                "mysql_container": "x",
                "mysql_volume": "mysqldata",
                "backup_root": "backups/physical",
            }
        )
        assert engine._format_file_size(0) == "0 B"
        assert engine._format_file_size(512) == "512 B"
        assert "KB" in engine._format_file_size(2048)
        assert "MB" in engine._format_file_size(2048 * 1024)
        assert "GB" in engine._format_file_size(2048 * 1024 * 1024)


class TestRestoreManagerParsing:
    def test_extract_table_name_backtick(self, app):
        rm = RestoreManager()
        assert rm._extract_table_name("INSERT INTO `users` VALUES (1)") == "users"

    def test_extract_table_name_plain(self, app):
        rm = RestoreManager()
        assert (
            rm._extract_table_name("INSERT INTO articles (id) VALUES (1)") == "articles"
        )

    def test_extract_table_name_none(self, app):
        rm = RestoreManager()
        assert rm._extract_table_name("SELECT * FROM users") is None

    def test_clean_insert_sql_escapes_bind(self, app):
        rm = RestoreManager()
        cleaned = rm._clean_insert_sql_for_sqlalchemy(
            "INSERT INTO t VALUES (100.5, %(price)s)"
        )
        assert "%%(price)s" in cleaned

    def test_split_sql_statements(self, app):
        rm = RestoreManager()
        stmts = rm._split_sql_statements(
            "INSERT INTO t VALUES ('a;b'); INSERT INTO t VALUES ('c');"
        )
        assert len(stmts) == 2

    def test_parse_sql_dump(self, app):
        rm = RestoreManager()
        sql = (
            "-- comment\n"
            "LOCK TABLES users WRITE;\n"
            "INSERT INTO `users` (id, name) VALUES (1, 'a');\n"
            "INSERT INTO `articles` (id) VALUES (10);\n"
        )
        result = rm._parse_sql_dump(sql)
        assert "users" in result
        assert "articles" in result

    def test_process_insert_statement_unknown_table(self, app):
        rm = RestoreManager()
        data = {}
        rm._process_insert_statement("SELECT 1", data)
        assert data == {}


class TestSmartTableValidator:
    def _validator(self):
        v = SmartTableValidator()
        return v

    def test_parse_backup_tables(self, app):
        v = self._validator()
        sql = (
            "CREATE TABLE users (id INT);\n" "INSERT INTO `articles` (id) VALUES (1);\n"
        )
        tables = v.parse_backup_tables(sql)
        assert "users" in tables
        assert "articles" in tables

    def test_heuristic_classify(self, app):
        v = self._validator()
        assert v._heuristic_classify_table("articles") == "critical"
        assert v._heuristic_classify_table("comments") == "important"
        assert v._heuristic_classify_table("audit_logs") == "system"
        assert v._heuristic_classify_table("parent_id") == "relationship"
        assert v._heuristic_classify_table("random_stuff_here") == "optional"

    def test_analyze_missing_severity_empty(self, app):
        v = self._validator()
        result = v._analyze_missing_severity(set(), {})
        assert result["severity"] == "none"
        assert result["can_proceed"] is True

    def test_analyze_missing_severity_critical(self, app):
        v = self._validator()
        result = v._analyze_missing_severity({"users"}, {})
        assert result["severity"] == "critical"
        assert result["can_proceed"] is False

    def test_analyze_missing_severity_important(self, app):
        v = self._validator()
        result = v._analyze_missing_severity({"comments"}, {})
        assert result["severity"] == "high"
        assert result["can_proceed"] is False

    def test_analyze_missing_severity_system(self, app):
        v = self._validator()
        result = v._analyze_missing_severity({"backup_records"}, {})
        assert result["severity"] == "medium"
        assert result["can_proceed"] is True


class TestLocalStorageProvider:
    def test_upload_and_exists(self, tmp_path):
        from app.backup.storage_manager import LocalStorageProvider

        store = tmp_path / "store"
        src = tmp_path / "src.tar.gz"
        src.write_bytes(b"backup-data")
        provider = LocalStorageProvider(base_dir=str(store))
        result = provider.upload(src, "b1")
        assert result["provider"] == "local"
        assert provider.exists("b1")
        assert (store / "b1.tar.gz").exists()

    def test_download_roundtrip(self, tmp_path):
        from app.backup.storage_manager import LocalStorageProvider

        store = tmp_path / "store"
        src = tmp_path / "src.tar.gz"
        src.write_bytes(b"backup-data")
        provider = LocalStorageProvider(base_dir=str(store))
        provider.upload(src, "b1")
        target = tmp_path / "out.tar.gz"
        assert provider.download("b1", target) is True
        assert target.read_bytes() == b"backup-data"

    def test_download_missing(self, tmp_path):
        from app.backup.storage_manager import LocalStorageProvider

        provider = LocalStorageProvider(base_dir=str(tmp_path / "store"))
        assert provider.download("nope", tmp_path / "out.tar.gz") is False

    def test_delete(self, tmp_path):
        from app.backup.storage_manager import LocalStorageProvider

        store = tmp_path / "store"
        src = tmp_path / "src.tar.gz"
        src.write_bytes(b"data")
        provider = LocalStorageProvider(base_dir=str(store))
        provider.upload(src, "b1")
        assert provider.delete("b1") is True
        assert provider.exists("b1") is False
        assert provider.delete("b1") is False


class TestBackupEncryption:
    def test_encrypt_decrypt_roundtrip(self, app, tmp_path):
        from app.backup.storage_manager import BackupEncryption
        from cryptography.fernet import Fernet

        crypto = BackupEncryption(key=Fernet.generate_key())
        plain = tmp_path / "plain.txt"
        enc = tmp_path / "enc.bin"
        dec = tmp_path / "dec.txt"
        plain.write_bytes(b"secret content")
        assert crypto.enabled is True
        assert crypto.encrypt_file(plain, enc) is True
        assert enc.read_bytes() != b"secret content"
        assert crypto.decrypt_file(enc, dec) is True
        assert dec.read_bytes() == b"secret content"

    def test_get_key_string(self, app):
        from app.backup.storage_manager import BackupEncryption
        from cryptography.fernet import Fernet

        crypto = BackupEncryption(key=Fernet.generate_key())
        key_str = crypto.get_key_string()
        assert isinstance(key_str, str)
        assert key_str != ""
