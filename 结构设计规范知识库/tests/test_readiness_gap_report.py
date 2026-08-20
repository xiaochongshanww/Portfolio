import json
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.render_readiness_gap_report import (
    ReadinessGapReportError,
    load_gap_report_data,
    render_markdown,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _audit(*, ready: bool = False) -> dict:
    items = (
        []
        if ready
        else [
            {
                "check_id": "source_release",
                "name": "来源发布资格",
                "blocking": True,
                "status": "blocked",
                "detail": "来源证据未收口",
                "owner": "来源治理负责人",
                "actions": ["补齐凭证索引"],
                "verification": ["validate_source_register --require-release-eligible"],
            },
            {
                "check_id": "closed_trial",
                "name": "封闭试用证据",
                "blocking": True,
                "status": "not_provided",
                "detail": "没有完成记录",
                "owner": "试用负责人",
                "actions": ["执行受控试用"],
                "verification": ["validate_trial_record"],
            },
            {
                "check_id": "rerank_quality",
                "name": "精排质量证据",
                "blocking": False,
                "status": "pending",
                "detail": "真实对照未完成",
                "owner": "检索质量负责人",
                "actions": ["保持默认关闭"],
                "verification": ["run_rerank_quality_evidence"],
            },
        ]
    )
    return {
        "profile": "external",
        "ready": ready,
        "checked_at": "2026-08-20T00:00:00+00:00",
        "closure": {
            "ready": ready,
            "blocking_count": 0 if ready else 2,
            "warning_count": 0 if ready else 1,
            "items": items,
        },
    }


def test_gap_report_reduces_external_audit_to_actionable_view(tmp_path):
    path = tmp_path / "audit.json"
    path.write_text(json.dumps(_audit(), ensure_ascii=False), encoding="utf-8")

    data = load_gap_report_data(path)
    markdown = render_markdown(data)

    assert data["ready"] is False
    assert len(data["items"]) == 3
    assert "## 未收口项" in markdown
    assert "source_release" in markdown
    assert "保持默认关闭" in markdown
    assert "授权原件" in markdown
    assert "api_key" not in markdown


def test_gap_report_rejects_non_external_or_inconsistent_audit(tmp_path):
    path = tmp_path / "audit.json"
    payload = _audit(ready=True)
    payload["profile"] = "internal-research"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ReadinessGapReportError, match="profile=external"):
        load_gap_report_data(path)

    payload = _audit()
    payload["closure"]["ready"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ReadinessGapReportError, match="closure.ready"):
        load_gap_report_data(path)


def test_gap_report_cli_fails_closed_and_require_ready(tmp_path):
    audit = tmp_path / "audit.json"
    output = tmp_path / "gap.md"
    audit.write_text(json.dumps(_audit()), encoding="utf-8")

    rendered = subprocess.run(
        [
            sys.executable,
            "scripts/render_readiness_gap_report.py",
            "--audit-json",
            str(audit),
            "--output",
            str(output),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert rendered.returncode == 0, rendered.stderr
    assert output.is_file()

    gated_output = tmp_path / "gated.md"
    gated = subprocess.run(
        [
            sys.executable,
            "scripts/render_readiness_gap_report.py",
            "--audit-json",
            str(audit),
            "--output",
            str(gated_output),
            "--require-ready",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert gated.returncode == 1
    assert gated_output.is_file()

    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    bad_output = tmp_path / "bad.md"
    failed = subprocess.run(
        [
            sys.executable,
            "scripts/render_readiness_gap_report.py",
            "--audit-json",
            str(bad),
            "--output",
            str(bad_output),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert failed.returncode == 1
    assert not bad_output.exists()
