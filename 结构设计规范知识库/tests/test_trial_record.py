import json
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.create_trial_record import build_planned_record
from scripts.render_trial_record import render_markdown
from scripts.validate_trial_record import validate_trial_record


def _record(**overrides):
    record = {
        "schema_version": 1,
        "status": "completed",
        "trial_id": "TRIAL-001",
        "participant_id": "P-001",
        "started_at": "2026-08-20T09:00:00+08:00",
        "ended_at": "2026-08-20T10:00:00+08:00",
        "delivery": "受控宿主机",
        "environment_owner": "project-owner",
        "source_register_version": "source-register-2026-08-20",
        "data_cleanup_date": "2026-08-21",
        "preflight": {
            "participant_acknowledged": True,
            "source_scope_confirmed": True,
            "no_unrelated_data": True,
            "key_log_owner_defined": True,
            "disclaimer_shown": True,
        },
        "fixed_tasks": [
            {
                "task_id": f"T-00{index}",
                "question": f"规范定位任务 {index}",
                "found_basis": True,
                "references": [f"GB 50009-2012 条文/表号/页码 {index}"],
                "human_review_required": True,
                "defect_ids": [],
            }
            for index in range(1, 4)
        ],
        "defects": [],
        "conclusion": {
            "decision": "adjust",
            "evidence": ["固定任务记录", "参与者反馈"],
            "unresolved_risks": ["需要继续观察复杂表格"],
            "data_deleted": True,
            "next_owner": "project-owner",
            "next_date": "2026-08-27",
        },
    }
    record.update(overrides)
    return record


def _write_record(tmp_path: Path, record: dict) -> Path:
    path = tmp_path / "trial.json"
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return path


def test_completed_trial_record_is_valid(tmp_path):
    record = _record()
    result = validate_trial_record(_write_record(tmp_path, record))

    assert result["ok"] is True
    assert result["status"] == "completed"
    assert result["task_count"] == 3
    markdown = render_markdown(record, result)
    assert "## 固定任务" in markdown
    assert "TRIAL-001" in markdown
    assert "计划记录不构成真实试用完成证据" not in markdown


def test_running_trial_requires_all_preflight_checks(tmp_path):
    record = _record(status="running", ended_at=None, conclusion=None)
    record["preflight"]["disclaimer_shown"] = False

    result = validate_trial_record(_write_record(tmp_path, record))

    assert result["ok"] is False
    assert any("全部确认前置条件" in issue for issue in result["issues"])


def test_completed_trial_requires_basis_references_and_conclusion(tmp_path):
    record = _record()
    record["fixed_tasks"][0]["references"] = []
    record["conclusion"]["evidence"] = []

    result = validate_trial_record(_write_record(tmp_path, record))

    assert result["ok"] is False
    assert any("fixed_tasks[0].references不能为空" in issue for issue in result["issues"])
    assert any("conclusion.evidence不能为空" in issue for issue in result["issues"])


def test_trial_record_rejects_secret_fields(tmp_path):
    record = _record()
    record["api_key"] = "should-never-be-recorded"

    result = validate_trial_record(_write_record(tmp_path, record))

    assert result["ok"] is False
    assert any("禁止保存密钥" in issue for issue in result["issues"])


def test_planned_record_generator_creates_non_evidence_record(tmp_path):
    record = build_planned_record(
        trial_id="TRIAL-PLAN-001",
        participant_id="P-001",
        delivery="受控宿主机",
        environment_owner="project-owner",
        source_register_version="source-register-2026-08-20",
        tasks=["规范定位", "表格取值", "公式复核"],
    )
    path = _write_record(tmp_path, record)

    result = validate_trial_record(path)

    assert result["ok"] is True
    assert result["status"] == "planned"
    assert record["preflight"]["participant_acknowledged"] is False
    assert record["conclusion"] is None
    assert "计划记录不构成真实试用完成证据" in render_markdown(record, result)


def test_planned_record_generator_requires_three_tasks():
    with pytest.raises(ValueError, match="至少需要 3 个固定任务"):
        build_planned_record(
            trial_id="TRIAL-PLAN-001",
            participant_id="P-001",
            delivery="受控宿主机",
            environment_owner="project-owner",
            source_register_version="source-register-2026-08-20",
            tasks=["规范定位", "表格取值"],
        )


def test_planned_record_cli_creates_once_and_refuses_overwrite(tmp_path):
    output = tmp_path / "trial.json"
    command = [
        sys.executable,
        "scripts/create_trial_record.py",
        "--output",
        str(output),
        "--trial-id",
        "TRIAL-CLI-001",
        "--participant-id",
        "P-CLI-001",
        "--delivery",
        "受控宿主机",
        "--environment-owner",
        "project-owner",
        "--source-register-version",
        "source-register-2026-08-20",
        "--task",
        "规范定位",
        "--task",
        "表格取值",
        "--task",
        "公式复核",
    ]

    created = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert created.returncode == 0, created.stderr
    assert json.loads(created.stdout)["status"] == "planned"
    assert "source-register-2026-08-20" not in created.stdout
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "planned"

    markdown_output = tmp_path / "trial.md"
    rendered = subprocess.run(
        [
            sys.executable,
            "scripts/render_trial_record.py",
            "--record",
            str(output),
            "--output",
            str(markdown_output),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert rendered.returncode == 0, rendered.stderr
    assert "## 固定任务" in markdown_output.read_text(encoding="utf-8")

    repeated = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert repeated.returncode == 1
    assert "输出文件已存在" in repeated.stdout
