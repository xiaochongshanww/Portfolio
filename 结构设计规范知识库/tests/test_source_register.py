import json
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.validate_source_register import SourceRegisterError, validate_source_register

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_current_source_register_is_structurally_valid_but_not_release_eligible():
    result = validate_source_register()

    assert result["ok"] is True
    assert result["source_count"] == 6
    assert result["release_eligible"] is False
    assert any("权利等级为 B" in item for item in result["release_blockers"])
    assert any("原始扫描件仍位于仓库跟踪路径" in item for item in result["release_blockers"])


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


def test_source_register_release_gate_cli_fails_closed():
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
