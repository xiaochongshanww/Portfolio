import json
import subprocess
import sys
from pathlib import Path

import scripts.audit_release_readiness as readiness


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def _write_context(tmp_path: Path, *, completed: bool = False) -> tuple[Path, Path, Path]:
    report = _write_json(tmp_path / "verification.json", {"passed": True})
    snapshot = _write_json(
        tmp_path / "snapshot.json",
        {
            "release_quality_status": "passed",
            "reports": {
                "verification": {
                    "path": str(report.relative_to(readiness.PROJECT_ROOT)),
                    "sha256": __import__("hashlib").sha256(report.read_bytes()).hexdigest(),
                }
            },
        },
    )
    status = "已完成" if completed else "工程完成，真实试用待执行"
    roadmap = tmp_path / "roadmap.md"
    roadmap.write_text(
        "\n".join(
            [
                f"| I-010 | P2 | 交付 | {status} | evidence |",
                f"| I-034 | P1 | 精排 | {'已完成' if completed else '工程完成，质量启用待证'} | evidence |",
            ]
        ),
        encoding="utf-8",
    )
    decisions = tmp_path / "decisions.md"
    decisions.write_text(
        "\n".join(
            [
                f"| D-001 | 授权 | {'已确定' if completed else '当前默认'} | default | trigger |",
                f"| D-002 | 交付 | {'已确定' if completed else '当前默认'} | default | trigger |",
            ]
        ),
        encoding="utf-8",
    )
    return snapshot, roadmap, decisions


def test_current_readiness_reports_external_blockers(tmp_path, monkeypatch):
    monkeypatch.setattr(readiness, "PROJECT_ROOT", tmp_path)
    snapshot, roadmap, decisions = _write_context(tmp_path)
    monkeypatch.setattr(
        readiness,
        "validate_source_register",
        lambda: {"release_eligible": False, "release_blockers": ["rights"]},
    )
    monkeypatch.setattr(readiness, "validate_runtime_manifest", lambda: {"ok": True})

    result = readiness.audit_release_readiness(
        snapshot_path=snapshot,
        roadmap_path=roadmap,
        decisions_path=decisions,
    )

    assert result["ok"] is True
    assert result["ready"] is False
    assert {item["id"] for item in result["checks"] if not item["ok"]} == {
        "source_release",
        "closed_trial",
        "delivery_decision",
        "rerank_quality",
    }
    assert any("来源资格" in item for item in result["blockers"])
    assert len(result["warnings"]) == 1


def test_readiness_can_pass_with_completed_external_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(readiness, "PROJECT_ROOT", tmp_path)
    snapshot, roadmap, decisions = _write_context(tmp_path, completed=True)
    trial = _write_json(
        tmp_path / "trial.json",
        {"status": "completed", "conclusion": {"decision": "continue"}},
    )
    monkeypatch.setattr(
        readiness,
        "validate_source_register",
        lambda: {"release_eligible": True, "release_blockers": []},
    )
    monkeypatch.setattr(readiness, "validate_runtime_manifest", lambda: {"ok": True})
    monkeypatch.setattr(
        readiness,
        "validate_trial_record",
        lambda _path: {"ok": True, "status": "completed"},
    )

    result = readiness.audit_release_readiness(
        snapshot_path=snapshot,
        roadmap_path=roadmap,
        decisions_path=decisions,
        trial_record=trial,
    )

    assert result["ready"] is True
    assert result["blockers"] == []
    assert result["warnings"] == []


def test_rerank_quality_is_non_blocking_when_feature_is_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(readiness, "PROJECT_ROOT", tmp_path)
    snapshot, roadmap, decisions = _write_context(tmp_path, completed=True)
    roadmap.write_text(
        roadmap.read_text(encoding="utf-8").replace(
            "| I-034 | P1 | 精排 | 已完成 | evidence |",
            "| I-034 | P1 | 精排 | 工程完成，质量启用待证 | evidence |",
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        readiness,
        "validate_source_register",
        lambda: {"release_eligible": True, "release_blockers": []},
    )
    monkeypatch.setattr(readiness, "validate_runtime_manifest", lambda: {"ok": True})
    trial = _write_json(
        tmp_path / "trial.json",
        {"status": "completed", "conclusion": {"decision": "continue"}},
    )
    monkeypatch.setattr(
        readiness,
        "validate_trial_record",
        lambda _path: {"ok": True, "status": "completed"},
    )

    result = readiness.audit_release_readiness(
        snapshot_path=snapshot,
        roadmap_path=roadmap,
        decisions_path=decisions,
        trial_record=trial,
    )

    rerank = next(item for item in result["checks"] if item["id"] == "rerank_quality")
    assert rerank["ok"] is False
    assert rerank["blocking"] is False
    assert result["ready"] is True


def test_readiness_cli_direct_entry_is_ascii_safe_and_fails_closed():
    completed = subprocess.run(
        [sys.executable, "scripts/audit_release_readiness.py"],
        cwd=readiness.PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert '"ready": false' in completed.stdout
    assert "ModuleNotFoundError" not in completed.stderr


def test_readiness_cli_help_is_utf8_safe():
    completed = subprocess.run(
        [sys.executable, "scripts/audit_release_readiness.py", "--help"],
        cwd=readiness.PROJECT_ROOT,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    stdout = completed.stdout.decode("utf-8")
    assert "审计当前项目是否具备对外发布条件" in stdout
    assert "����" not in stdout
