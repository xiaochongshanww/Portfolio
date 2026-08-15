"""备份在线引擎测试 — PhysicalBackupEngine 格式化等纯函数。"""

from app.backup.physical_backup_engine import PhysicalBackupEngine


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
