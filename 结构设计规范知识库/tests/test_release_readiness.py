import json
import subprocess
import sys
from pathlib import Path

import scripts.audit_release_readiness as readiness
from scripts.create_release_evidence_manifest import build_manifest


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def _write_context(tmp_path: Path, *, completed: bool = False) -> tuple[Path, Path, Path]:
    report = _write_json(
        tmp_path / "verification.json",
        {"passed": True, "data_version_hash": "current-version"},
    )
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
                f"| D-001 | 授权 | {'已确定' if completed else '网络搜集扫描 PDF 仅限内部研究和封闭验证，发布资格关闭'} | default | trigger |",
                f"| D-002 | 交付 | {'已确定' if completed else '保留宿主机运行和知识包 CLI，不承诺安装器、桌面版或公共 Web 服务'} | default | trigger |",
            ]
        ),
        encoding="utf-8",
    )
    return snapshot, roadmap, decisions


def _write_rerank_evidence(tmp_path: Path) -> tuple[Path, Path]:
    comparison = _write_json(
        tmp_path / "rerank-comparison.json",
        {
            "ok": True,
            "comparison_complete": True,
            "case_count": 100,
            "fallback_case_count": 0,
            "provider": "zhipu",
            "data_version_hash": "current-version",
        },
    )
    answer = _write_json(
        tmp_path / "rerank-answer.json",
        {
            "ok": True,
            "rerank_enabled": True,
            "case_count": 24,
            "pass_rate": 1.0,
            "data_version_hash": "current-version",
        },
    )
    return comparison, answer


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
    source = next(item for item in result["checks"] if item["id"] == "source_release")
    assert source["items"] == ["rights"]
    assert source["remediation"]["owner"] == "来源治理负责人"
    assert (
        "validate_source_register.py --require-release-eligible"
        in source["remediation"]["verification"][0]
    )
    assert any("来源资格" in item for item in result["blockers"])
    assert len(result["warnings"]) == 1
    assert result["closure"]["blocking_check_ids"] == [
        "source_release",
        "closed_trial",
        "delivery_decision",
    ]
    assert result["closure"]["warning_check_ids"] == ["rerank_quality"]
    trial_closure = next(
        item for item in result["closure"]["items"] if item["check_id"] == "closed_trial"
    )
    assert trial_closure["owner"] == "试用负责人"
    assert trial_closure["verification"]


def test_internal_research_profile_is_ready_without_external_release_evidence(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(readiness, "PROJECT_ROOT", tmp_path)
    snapshot, roadmap, decisions = _write_context(tmp_path)
    monkeypatch.setattr(
        readiness,
        "validate_source_register",
        lambda: {
            "release_eligible": False,
            "release_blockers": ["rights"],
            "internal_research_eligible": True,
            "internal_research_blockers": [],
        },
    )
    monkeypatch.setattr(readiness, "validate_runtime_manifest", lambda: {"ok": True})

    result = readiness.audit_release_readiness(
        profile="internal-research",
        snapshot_path=snapshot,
        roadmap_path=roadmap,
        decisions_path=decisions,
    )

    assert result["ready"] is True
    assert result["external_release_ready"] is False
    assert result["blockers"] == []
    source = next(item for item in result["checks"] if item["id"] == "source_internal_research")
    assert source["ok"] is True
    trial = next(item for item in result["checks"] if item["id"] == "closed_trial")
    assert trial["status"] == "not_required"
    assert trial["blocking"] is False
    delivery = next(item for item in result["checks"] if item["id"] == "delivery_decision")
    assert delivery["status"] == "internal_only"
    assert delivery["blocking"] is False

    decisions.write_text(
        decisions.read_text(encoding="utf-8")
        .replace("内部研究", "外部公开")
        .replace("宿主机运行和知识包 CLI，不承诺安装器、桌面版或公共 Web 服务", "公共 Web 服务"),
        encoding="utf-8",
    )
    unsafe_result = readiness.audit_release_readiness(
        profile="internal-research",
        snapshot_path=snapshot,
        roadmap_path=roadmap,
        decisions_path=decisions,
    )
    assert unsafe_result["ready"] is False
    unsafe_delivery = next(
        item for item in unsafe_result["checks"] if item["id"] == "delivery_decision"
    )
    assert unsafe_delivery["status"] == "blocked"
    assert unsafe_delivery["blocking"] is True
    assert any(item.startswith("D-001") for item in unsafe_delivery["items"])


def test_evidence_manifest_is_optional_but_blocking_when_supplied(tmp_path, monkeypatch):
    monkeypatch.setattr(readiness, "PROJECT_ROOT", tmp_path)
    snapshot, roadmap, decisions = _write_context(tmp_path)
    manifest_path = tmp_path / "release-evidence.json"
    manifest_path.write_text(json.dumps(build_manifest()), encoding="utf-8")
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
        evidence_manifest=manifest_path,
    )

    evidence = next(item for item in result["checks"] if item["id"] == "release_evidence_manifest")
    assert evidence["ok"] is False
    assert evidence["blocking"] is True
    assert evidence["status"] == "incomplete"
    assert evidence["remediation"]["owner"] == "发布证据负责人"
    assert "release_evidence_manifest" in result["closure"]["blocking_check_ids"]


def test_readiness_can_pass_with_completed_external_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(readiness, "PROJECT_ROOT", tmp_path)
    snapshot, roadmap, decisions = _write_context(tmp_path, completed=True)
    rerank_comparison, rerank_answer = _write_rerank_evidence(tmp_path)
    trial = _write_json(
        tmp_path / "trial.json",
        {"status": "completed", "conclusion": {"decision": "continue"}},
    )
    monkeypatch.setattr(
        readiness,
        "validate_source_register",
        lambda: {"release_eligible": True, "release_blockers": []},
    )
    monkeypatch.setattr(
        readiness,
        "validate_runtime_manifest",
        lambda: {"ok": True, "data_version_hash": "current-version"},
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
        rerank_comparison_report=rerank_comparison,
        rerank_answer_report=rerank_answer,
    )

    assert result["ready"] is True
    assert result["blockers"] == []
    assert result["warnings"] == []


def test_completed_rerank_status_without_evidence_is_not_verified(tmp_path, monkeypatch):
    monkeypatch.setattr(readiness, "PROJECT_ROOT", tmp_path)
    snapshot, roadmap, decisions = _write_context(tmp_path, completed=True)
    monkeypatch.setattr(
        readiness,
        "validate_source_register",
        lambda: {"release_eligible": True, "release_blockers": []},
    )
    monkeypatch.setattr(
        readiness,
        "validate_runtime_manifest",
        lambda: {"ok": True, "data_version_hash": "current-version"},
    )
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
    assert rerank["status"] == "invalid"
    assert "精排对照报告不存在" in rerank["detail"]


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


def test_quality_evidence_rejects_report_bound_to_old_runtime_version(tmp_path, monkeypatch):
    monkeypatch.setattr(readiness, "PROJECT_ROOT", tmp_path)
    snapshot, roadmap, decisions = _write_context(tmp_path, completed=True)
    report_path = tmp_path / "verification.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["data_version_hash"] = "old-version"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    snapshot_payload = json.loads(snapshot.read_text(encoding="utf-8"))
    snapshot_payload["reports"]["verification"]["sha256"] = (
        __import__("hashlib").sha256(report_path.read_bytes()).hexdigest()
    )
    snapshot.write_text(json.dumps(snapshot_payload), encoding="utf-8")

    monkeypatch.setattr(
        readiness,
        "validate_source_register",
        lambda: {"release_eligible": True, "release_blockers": []},
    )
    monkeypatch.setattr(
        readiness,
        "validate_runtime_manifest",
        lambda: {"ok": True, "data_version_hash": "current-version"},
    )
    monkeypatch.setattr(
        readiness,
        "validate_trial_record",
        lambda _path: {"ok": True, "status": "completed"},
    )
    trial = _write_json(
        tmp_path / "trial.json",
        {"status": "completed", "conclusion": {"decision": "continue"}},
    )

    result = readiness.audit_release_readiness(
        snapshot_path=snapshot,
        roadmap_path=roadmap,
        decisions_path=decisions,
        trial_record=trial,
    )

    quality = next(item for item in result["checks"] if item["id"] == "quality_evidence")
    assert quality["ok"] is False
    assert quality["status"] == "invalid"
    assert "当前运行版本=current-version" in quality["detail"]
    assert result["ready"] is False


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


def test_render_markdown_includes_source_blocker_details():
    markdown = readiness.render_markdown(
        {
            "profile": "external",
            "ready": False,
            "checked_at": "now",
            "checks": [
                {
                    "id": "source_release",
                    "name": "来源发布资格",
                    "ok": False,
                    "blocking": True,
                    "status": "blocked",
                    "detail": "2 项来源资格阻断",
                    "items": ["规范 A: 权利等级为 B", "规范 A: 凭证索引缺失"],
                }
            ],
            "blockers": ["2 项来源资格阻断"],
            "warnings": [],
        }
    )

    assert "## 来源资格明细" in markdown
    assert "规范 A: 权利等级为 B" in markdown
    assert "规范 A: 凭证索引缺失" in markdown


def test_render_markdown_includes_closure_matrix():
    markdown = readiness.render_markdown(
        {
            "profile": "external",
            "ready": False,
            "checked_at": "now",
            "checks": [],
            "closure": {
                "items": [
                    {
                        "check_id": "closed_trial",
                        "name": "封闭试用证据",
                        "status": "not_provided",
                        "blocking": True,
                        "owner": "试用负责人",
                        "verification": ["validate_trial_record.py"],
                    }
                ]
            },
            "blockers": ["未提供已完成的试用记录"],
            "warnings": [],
        }
    )

    assert "## 收口矩阵" in markdown
    assert "试用负责人" in markdown
    assert "validate_trial_record.py" in markdown


def test_render_markdown_includes_remediation_actions():
    markdown = readiness.render_markdown(
        {
            "profile": "external",
            "ready": False,
            "checked_at": "now",
            "checks": [
                {
                    "id": "closed_trial",
                    "name": "封闭试用证据",
                    "ok": False,
                    "blocking": True,
                    "status": "not_provided",
                    "detail": "未提供已完成的试用记录",
                    "remediation": {
                        "owner": "试用负责人",
                        "actions": ["按方案执行受控真实试用"],
                        "verification": ["validate_trial_record.py"],
                    },
                }
            ],
            "blockers": ["未提供已完成的试用记录"],
            "warnings": [],
        }
    )

    assert "## 整改行动" in markdown
    assert "责任角色：试用负责人" in markdown
    assert "按方案执行受控真实试用" in markdown
    assert "validate_trial_record.py" in markdown
