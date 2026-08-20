import json
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.render_source_register_report import render_markdown as render_source_register_markdown
from scripts.validate_source_register import SourceRegisterError, validate_source_register

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_current_source_register_is_structurally_valid_but_not_release_eligible():
    result = validate_source_register()

    assert result["ok"] is True
    assert result["source_count"] == 6
    assert result["production_source_count"] == 5
    assert result["test_only_sources"] == ["test_image.pdf"]
    assert result["runtime_test_only_sources"] == []
    assert result["release_eligible"] is False
    assert any("权利等级为 B" in item for item in result["release_blockers"])
    assert any("原始扫描件仍位于仓库跟踪路径" in item for item in result["release_blockers"])
    assert not any(
        "test_only 来源仍位于活动运行 manifest" in item for item in result["release_blockers"]
    )
    register = json.loads(
        (PROJECT_ROOT / "docs" / "governance" / "来源登记台账.json").read_text(encoding="utf-8")
    )
    markdown = render_source_register_markdown(result, register["documents"])
    assert "## 逐来源补证" in markdown
    assert "取得日期或凭证索引缺失" in markdown
    assert "授权原件" in markdown


def test_current_source_register_is_eligible_for_internal_research():
    result = validate_source_register()

    assert result["internal_research_eligible"] is True
    assert result["internal_research_blockers"] == []


def test_source_register_blocks_forbidden_rights_in_internal_research(tmp_path):
    register_path = tmp_path / "来源登记台账.json"
    register = json.loads(
        (PROJECT_ROOT / "docs" / "governance" / "来源登记台账.json").read_text(encoding="utf-8")
    )
    register["documents"][0]["rights"]["status"] = "C"
    register_path.write_text(json.dumps(register, ensure_ascii=False), encoding="utf-8")

    result = validate_source_register(register_path)

    assert result["internal_research_eligible"] is False
    assert any("权利等级为 C" in item for item in result["internal_research_blockers"])


def test_source_register_rejects_hash_drift(tmp_path):
    register_path = tmp_path / "来源登记台账.json"
    register = json.loads(
        (PROJECT_ROOT / "docs" / "governance" / "来源登记台账.json").read_text(encoding="utf-8")
    )
    register["documents"][0]["original_sha256"] = "0" * 64
    register_path.write_text(json.dumps(register, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(SourceRegisterError, match="SHA-256 不匹配"):
        validate_source_register(register_path)


def test_source_register_can_be_used_as_a_release_gate():
    result = validate_source_register()

    assert result["release_blockers"]
    assert result["release_eligible"] is False


def test_source_register_release_gate_cli_fails_closed(tmp_path):
    completed = subprocess.run(
        [sys.executable, "scripts/validate_source_register.py", "--require-release-eligible"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "source_release_not_eligible" in completed.stdout
    assert "ZHIPUAI_API_KEY" not in completed.stdout

    report = tmp_path / "source-register.md"
    rendered = subprocess.run(
        [
            sys.executable,
            "scripts/render_source_register_report.py",
            "--output",
            str(report),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert rendered.returncode == 0, rendered.stderr
    assert "对外发布资格" in report.read_text(encoding="utf-8")


def test_source_register_rejects_scope_mismatch(tmp_path):
    register_path = tmp_path / "来源登记台账.json"
    register = json.loads(
        (PROJECT_ROOT / "docs" / "governance" / "来源登记台账.json").read_text(encoding="utf-8")
    )
    register["documents"][-1]["release_scope"] = "production"
    register_path.write_text(json.dumps(register, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(SourceRegisterError, match="不能声明为 production 来源"):
        validate_source_register(register_path)


def test_source_register_structure_check_allows_missing_active_pointer(tmp_path):
    result = validate_source_register(active_db_path=tmp_path / "missing-active-db.json")

    assert result["ok"] is True
    assert result["release_eligible"] is False
    assert any("活动数据库指针不存在" in item for item in result["release_blockers"])
