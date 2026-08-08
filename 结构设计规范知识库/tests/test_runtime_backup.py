import json
import os
import shutil
import stat
import subprocess
import sys
import warnings
import zipfile
from pathlib import Path

import pytest

from src.pipeline import runtime_backup
from src.pipeline.runtime_backup import (
    BACKUP_MANIFEST_NAME,
    RuntimeBackupError,
    create_runtime_backup,
    restore_runtime_backup,
    validate_runtime_backup,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _runtime_data(tmp_path: Path) -> Path:
    data = tmp_path / "source-data"
    (data / "raw").mkdir(parents=True)
    source_pdf = data / "raw" / "GB 50009-2012_荷载规范.pdf"
    source_pdf.write_bytes(b"%PDF-runtime-backup")
    os.utime(source_pdf, ns=(1_700_000_000_123_456_700,) * 2)
    _write_json(
        data / "jobs" / "completed.json",
        {"job_id": "completed", "status": "succeeded", "outputs": {}},
    )
    _write_json(
        data / "corrections" / "approved" / "规范.json",
        {"corrections": [{"id": "fix-1", "value": "修正文"}]},
    )
    (data / "audit" / "reports").mkdir(parents=True)
    (data / "audit" / "events.jsonl").write_text('{"event":"verified"}\n', encoding="utf-8")
    (data / "manual_structuring" / "drafts" / "空目录").mkdir(parents=True)
    return data


def _manifest(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(BACKUP_MANIFEST_NAME).decode("utf-8"))


def _rewrite_archive(source: Path, destination: Path, mutate) -> None:
    with zipfile.ZipFile(source) as archive:
        members = {info.filename: archive.read(info.filename) for info in archive.infolist()}
    mutate(members)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "src.pipeline", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )


def test_backup_round_trip_preserves_complete_inventory_and_metadata(tmp_path: Path):
    source = _runtime_data(tmp_path)
    backup = tmp_path / "runtime-backup.zip"

    created = create_runtime_backup(
        backup,
        data_dir=source,
        actor="operator",
        maintenance_window=True,
    )
    validated = validate_runtime_backup(backup)
    target = tmp_path / "restored-data"
    restored = restore_runtime_backup(
        backup,
        data_dir=target,
        actor="recovery-operator",
        maintenance_window=True,
    )

    assert created["backup_id"] == validated["backup_id"] == restored["backup_id"]
    assert created["file_count"] == 4
    assert (target / "manual_structuring" / "drafts" / "空目录").is_dir()
    assert (target / "raw" / "GB 50009-2012_荷载规范.pdf").read_bytes() == b"%PDF-runtime-backup"
    assert (target / "raw" / "GB 50009-2012_荷载规范.pdf").stat().st_mtime_ns == 1_700_000_000_123_456_700
    source_inventory, _ = runtime_backup._scan_inventory(source)
    target_inventory, _ = runtime_backup._scan_inventory(target)
    assert target_inventory == source_inventory
    assert restored["restart_required"] is True
    assert "GET /ready" in restored["post_restore_checks"]


def test_backup_id_is_deterministic_across_archive_metadata(tmp_path: Path):
    source = _runtime_data(tmp_path)
    first = create_runtime_backup(
        tmp_path / "first.zip",
        data_dir=source,
        actor="first-operator",
        maintenance_window=True,
    )
    second = create_runtime_backup(
        tmp_path / "second.zip",
        data_dir=source,
        actor="second-operator",
        maintenance_window=True,
    )

    assert first["backup_id"] == second["backup_id"]
    assert _manifest(tmp_path / "first.zip")["actor"] == "first-operator"
    assert _manifest(tmp_path / "second.zip")["actor"] == "second-operator"


def test_backup_requires_maintenance_window_and_external_output(tmp_path: Path):
    source = _runtime_data(tmp_path)
    with pytest.raises(RuntimeBackupError, match="维护窗口"):
        create_runtime_backup(tmp_path / "backup.zip", data_dir=source)
    with pytest.raises(RuntimeBackupError, match="不能位于 DATA_DIR"):
        create_runtime_backup(
            source / "backup.zip",
            data_dir=source,
            maintenance_window=True,
        )


@pytest.mark.parametrize("status_value", ["queued", "running"])
def test_backup_rejects_active_jobs(tmp_path: Path, status_value: str):
    source = _runtime_data(tmp_path)
    _write_json(source / "jobs" / "active.json", {"status": status_value})

    with pytest.raises(RuntimeBackupError, match="存在活动任务"):
        create_runtime_backup(
            tmp_path / "backup.zip",
            data_dir=source,
            maintenance_window=True,
        )


def test_backup_rejects_corrupt_job_records(tmp_path: Path):
    source = _runtime_data(tmp_path)
    (source / "jobs" / "corrupt.json").write_text("{", encoding="utf-8")

    with pytest.raises(RuntimeBackupError, match="无法解析任务记录"):
        create_runtime_backup(
            tmp_path / "backup.zip",
            data_dir=source,
            maintenance_window=True,
        )


def test_backup_rejects_symlinks_when_supported(tmp_path: Path):
    source = _runtime_data(tmp_path)
    try:
        (source / "link").symlink_to(source / "raw", target_is_directory=True)
    except OSError:
        pytest.skip("当前环境不允许创建符号链接")

    with pytest.raises(RuntimeBackupError, match="符号链接"):
        create_runtime_backup(
            tmp_path / "backup.zip",
            data_dir=source,
            maintenance_window=True,
        )


def test_backup_discards_output_when_source_changes(tmp_path: Path, monkeypatch):
    source = _runtime_data(tmp_path)
    backup = tmp_path / "backup.zip"
    original_scan = runtime_backup._scan_inventory
    calls = 0

    def mutate_before_second_scan(data_dir: Path):
        nonlocal calls
        calls += 1
        if calls == 2:
            (source / "audit" / "events.jsonl").write_text("changed\n", encoding="utf-8")
        return original_scan(data_dir)

    monkeypatch.setattr(runtime_backup, "_scan_inventory", mutate_before_second_scan)

    with pytest.raises(RuntimeBackupError, match="发生变化"):
        create_runtime_backup(backup, data_dir=source, maintenance_window=True)
    assert not backup.exists()
    assert not list(tmp_path.glob(".backup.zip.*.tmp"))


def test_validation_rejects_tampered_payload_and_size_limit(tmp_path: Path):
    source = _runtime_data(tmp_path)
    backup = tmp_path / "backup.zip"
    create_runtime_backup(backup, data_dir=source, maintenance_window=True)
    tampered = tmp_path / "tampered.zip"

    def mutate(members: dict[str, bytes]) -> None:
        payload_name = next(name for name in members if name.startswith("data/raw/"))
        members[payload_name] = b"tampered"

    _rewrite_archive(backup, tampered, mutate)

    with pytest.raises(RuntimeBackupError, match="大小不匹配|SHA-256"):
        validate_runtime_backup(tampered)
    with pytest.raises(RuntimeBackupError, match="超过限制"):
        validate_runtime_backup(backup, max_uncompressed_bytes=1)


def test_validation_rejects_path_traversal_and_identity_tampering(tmp_path: Path):
    source = _runtime_data(tmp_path)
    backup = tmp_path / "backup.zip"
    create_runtime_backup(backup, data_dir=source, maintenance_window=True)
    traversal = tmp_path / "traversal.zip"
    identity = tmp_path / "identity.zip"

    def mutate_path(members: dict[str, bytes]) -> None:
        manifest = json.loads(members[BACKUP_MANIFEST_NAME].decode("utf-8"))
        manifest["files"][0]["path"] = "../escape"
        members[BACKUP_MANIFEST_NAME] = json.dumps(manifest).encode("utf-8")

    def mutate_identity(members: dict[str, bytes]) -> None:
        manifest = json.loads(members[BACKUP_MANIFEST_NAME].decode("utf-8"))
        manifest["backup_id"] = "rb-" + "0" * 24
        members[BACKUP_MANIFEST_NAME] = json.dumps(manifest).encode("utf-8")

    _rewrite_archive(backup, traversal, mutate_path)
    _rewrite_archive(backup, identity, mutate_identity)

    with pytest.raises(RuntimeBackupError, match="不安全路径"):
        validate_runtime_backup(traversal)
    with pytest.raises(RuntimeBackupError, match="backup_id 与清单不一致"):
        validate_runtime_backup(identity)


def test_validation_rejects_noncanonical_or_incomplete_directory_topology(tmp_path: Path):
    source = _runtime_data(tmp_path)
    backup = tmp_path / "backup.zip"
    create_runtime_backup(backup, data_dir=source, maintenance_window=True)
    unsorted = tmp_path / "unsorted.zip"
    missing_parent = tmp_path / "missing-parent.zip"

    def reverse_files(members: dict[str, bytes]) -> None:
        manifest = json.loads(members[BACKUP_MANIFEST_NAME].decode("utf-8"))
        manifest["files"].reverse()
        members[BACKUP_MANIFEST_NAME] = json.dumps(manifest).encode("utf-8")

    def remove_parent(members: dict[str, bytes]) -> None:
        manifest = json.loads(members[BACKUP_MANIFEST_NAME].decode("utf-8"))
        manifest["directories"] = [
            entry for entry in manifest["directories"] if entry["path"] != "data/audit"
        ]
        members[BACKUP_MANIFEST_NAME] = json.dumps(manifest).encode("utf-8")

    _rewrite_archive(backup, unsorted, reverse_files)
    _rewrite_archive(backup, missing_parent, remove_parent)

    with pytest.raises(RuntimeBackupError, match="必须按路径排序"):
        validate_runtime_backup(unsorted)
    with pytest.raises(RuntimeBackupError, match="缺少父目录声明"):
        validate_runtime_backup(missing_parent)


def test_validation_rejects_duplicate_and_zip_symlink_members(tmp_path: Path):
    source = _runtime_data(tmp_path)
    backup = tmp_path / "backup.zip"
    create_runtime_backup(backup, data_dir=source, maintenance_window=True)
    duplicate = tmp_path / "duplicate.zip"
    symlink = tmp_path / "symlink.zip"
    with zipfile.ZipFile(backup) as archive:
        members = [(info.filename, archive.read(info.filename)) for info in archive.infolist()]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(duplicate, "w") as archive:
            for name, content in members:
                archive.writestr(name, content)
            archive.writestr(members[0][0], members[0][1])

    with zipfile.ZipFile(symlink, "w") as archive:
        for name, content in members:
            archive.writestr(name, content)
        info = zipfile.ZipInfo("data/unsafe-link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "target")

    with pytest.raises(RuntimeBackupError, match="重复 ZIP 成员"):
        validate_runtime_backup(duplicate)
    with pytest.raises(RuntimeBackupError, match="ZIP 符号链接"):
        validate_runtime_backup(symlink)


def test_restore_requires_replace_and_rejects_backup_inside_target(tmp_path: Path):
    source = _runtime_data(tmp_path)
    backup = tmp_path / "backup.zip"
    create_runtime_backup(backup, data_dir=source, maintenance_window=True)
    target = tmp_path / "target"
    target.mkdir()
    (target / "old.txt").write_text("old", encoding="utf-8")

    with pytest.raises(RuntimeBackupError, match="--replace"):
        restore_runtime_backup(backup, data_dir=target, maintenance_window=True)
    nested_backup = target / "nested.zip"
    shutil.copy2(backup, nested_backup)
    with pytest.raises(RuntimeBackupError, match="不能位于目标 DATA_DIR"):
        restore_runtime_backup(
            nested_backup,
            data_dir=target,
            replace=True,
            maintenance_window=True,
        )


def test_restore_replaces_existing_target_only_after_validation(tmp_path: Path):
    source = _runtime_data(tmp_path)
    backup = tmp_path / "backup.zip"
    create_runtime_backup(backup, data_dir=source, maintenance_window=True)
    target = tmp_path / "target"
    target.mkdir()
    (target / "old.txt").write_text("old", encoding="utf-8")

    result = restore_runtime_backup(
        backup,
        data_dir=target,
        replace=True,
        actor="operator",
        maintenance_window=True,
    )

    assert result["replaced_existing"] is True
    assert not (target / "old.txt").exists()
    assert (target / "raw" / "GB 50009-2012_荷载规范.pdf").is_file()


def test_restore_rejects_active_jobs_in_target_or_backup(tmp_path: Path, monkeypatch):
    source = _runtime_data(tmp_path)
    clean_backup = tmp_path / "clean.zip"
    create_runtime_backup(clean_backup, data_dir=source, maintenance_window=True)
    target = tmp_path / "target"
    target.mkdir()
    _write_json(target / "jobs" / "active.json", {"status": "running"})

    with pytest.raises(RuntimeBackupError, match="存在活动任务"):
        restore_runtime_backup(
            clean_backup,
            data_dir=target,
            replace=True,
            maintenance_window=True,
        )
    assert (target / "jobs" / "active.json").is_file()

    _write_json(source / "jobs" / "active.json", {"status": "queued"})
    unsafe_backup = tmp_path / "unsafe.zip"
    with monkeypatch.context() as patcher:
        patcher.setattr(runtime_backup, "_assert_no_active_jobs", lambda _: None)
        create_runtime_backup(unsafe_backup, data_dir=source, maintenance_window=True)
    empty_target = tmp_path / "empty-target"

    with pytest.raises(RuntimeBackupError, match="存在活动任务"):
        restore_runtime_backup(
            unsafe_backup,
            data_dir=empty_target,
            maintenance_window=True,
        )
    assert not empty_target.exists()


def test_restore_failure_rolls_back_complete_previous_target(tmp_path: Path, monkeypatch):
    source = _runtime_data(tmp_path)
    backup = tmp_path / "backup.zip"
    create_runtime_backup(backup, data_dir=source, maintenance_window=True)
    target = tmp_path / "target"
    target.mkdir()
    (target / "old.txt").write_text("old-state", encoding="utf-8")
    original_replace = runtime_backup._replace_path
    failed = False

    def fail_install_once(source_path: Path, target_path: Path) -> None:
        nonlocal failed
        if source_path.name == "staging-data" and not failed:
            failed = True
            raise OSError("injected install failure")
        original_replace(source_path, target_path)

    monkeypatch.setattr(runtime_backup, "_replace_path", fail_install_once)

    with pytest.raises(OSError, match="injected install failure"):
        restore_runtime_backup(
            backup,
            data_dir=target,
            replace=True,
            maintenance_window=True,
        )
    assert (target / "old.txt").read_text(encoding="utf-8") == "old-state"
    assert not (target / "raw").exists()
    assert not list(tmp_path.glob(".runtime-backup-*"))


def test_restore_extraction_failure_never_mutates_target(tmp_path: Path, monkeypatch):
    source = _runtime_data(tmp_path)
    backup = tmp_path / "backup.zip"
    create_runtime_backup(backup, data_dir=source, maintenance_window=True)
    target = tmp_path / "target"
    target.mkdir()
    (target / "old.txt").write_text("old-state", encoding="utf-8")

    def fail_extract(*args, **kwargs):
        raise OSError("injected extraction failure")

    monkeypatch.setattr(runtime_backup, "_extract_backup", fail_extract)

    with pytest.raises(OSError, match="injected extraction failure"):
        restore_runtime_backup(
            backup,
            data_dir=target,
            replace=True,
            maintenance_window=True,
        )
    assert (target / "old.txt").read_text(encoding="utf-8") == "old-state"
    assert not list(tmp_path.glob(".runtime-backup-*"))


def test_restore_preserves_previous_data_if_automatic_rollback_also_fails(tmp_path: Path, monkeypatch):
    source = _runtime_data(tmp_path)
    backup = tmp_path / "backup.zip"
    create_runtime_backup(backup, data_dir=source, maintenance_window=True)
    target = tmp_path / "target"
    target.mkdir()
    (target / "old.txt").write_text("old-state", encoding="utf-8")
    original_replace = runtime_backup._replace_path

    def fail_install_and_rollback(source_path: Path, target_path: Path) -> None:
        if source_path.name in {"staging-data", "previous-data"}:
            raise OSError("injected replacement failure")
        original_replace(source_path, target_path)

    monkeypatch.setattr(runtime_backup, "_replace_path", fail_install_and_rollback)

    with pytest.raises(RuntimeBackupError, match="旧数据保留在"):
        restore_runtime_backup(
            backup,
            data_dir=target,
            replace=True,
            maintenance_window=True,
        )
    temporary_roots = list(tmp_path.glob(".runtime-backup-*"))
    assert len(temporary_roots) == 1
    assert (temporary_roots[0] / "previous-data" / "old.txt").read_text(encoding="utf-8") == "old-state"


def test_backup_cli_reports_machine_readable_success_and_failures(tmp_path: Path):
    source = _runtime_data(tmp_path)
    backup = tmp_path / "backup.zip"
    target = tmp_path / "target"

    missing_ack = _run_cli(
        "backup-create",
        "--data-dir",
        str(source),
        "--output",
        str(backup),
    )
    assert missing_ack.returncode == 1
    assert json.loads(missing_ack.stdout)["ok"] is False

    created = _run_cli(
        "backup-create",
        "--data-dir",
        str(source),
        "--output",
        str(backup),
        "--actor",
        "cli-operator",
        "--maintenance-window",
    )
    assert created.returncode == 0, created.stderr
    assert json.loads(created.stdout)["backup_id"].startswith("rb-")

    validated = _run_cli("backup-validate", "--backup", str(backup))
    assert validated.returncode == 0, validated.stderr
    assert json.loads(validated.stdout)["valid"] is True

    restored = _run_cli(
        "backup-restore",
        "--backup",
        str(backup),
        "--data-dir",
        str(target),
        "--maintenance-window",
    )
    assert restored.returncode == 0, restored.stderr
    assert json.loads(restored.stdout)["restart_required"] is True

    no_replace = _run_cli(
        "backup-restore",
        "--backup",
        str(backup),
        "--data-dir",
        str(target),
        "--maintenance-window",
    )
    assert no_replace.returncode == 1
    assert "--replace" in json.loads(no_replace.stdout)["error"]
