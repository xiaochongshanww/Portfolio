import io
import json
import urllib.error
from pathlib import Path

import pytest

from scripts import verify_quality


def test_api_evaluation_surfaces_output_error(monkeypatch, tmp_path: Path):
    responses = iter(
        [
            {"job_id": "job-1"},
            {
                "status": "succeeded",
                "outputs": {"ok": False, "error": "检索服务未就绪", "failures": []},
            },
        ]
    )
    monkeypatch.setattr(verify_quality, "_api_json", lambda *args, **kwargs: next(responses))

    result = verify_quality._run_api_evaluation(
        "regular",
        "http://127.0.0.1:8017",
        "key",
    )

    assert result["ok"] is False
    assert result["error"] == "检索服务未就绪"


def test_api_evaluation_sends_builtin_id(monkeypatch):
    calls = []
    responses = iter(
        [
            {"job_id": "job-1"},
            {
                "status": "succeeded",
                "outputs": {
                    "ok": True,
                    "case_count": 100,
                    "failures": [],
                    "evaluation_set_id": "structured",
                },
            },
        ]
    )

    def fake_api_json(*args, **kwargs):
        calls.append((args, kwargs))
        return next(responses)

    monkeypatch.setattr(verify_quality, "_api_json", fake_api_json)

    result = verify_quality._run_api_evaluation(
        "structured",
        "http://127.0.0.1:8017",
        "key",
    )

    assert result["ok"] is True
    assert result["evaluation_set_id"] == "structured"
    assert calls[0][1]["payload"] == {"top_k": 5, "evaluation_set": "structured"}
    assert "file" not in calls[0][1]["payload"]


def test_answer_evaluation_uses_explicit_target(monkeypatch, tmp_path: Path):
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "api_base": kwargs["api_base"],
            "case_count": 24,
            "passed_count": 24,
            "failure_count": 0,
            "pass_rate": 1,
            "check_rates": {},
            "refusal_pass_rate": 1,
            "failures": [],
            "results": [],
        }

    monkeypatch.setattr(verify_quality, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(verify_quality, "run_answer_evaluation", fake_run)

    result = verify_quality._run_answer_evaluation_against_api(
        "http://127.0.0.1:8017",
        "runtime-key",
    )

    assert result["ok"] is True
    assert captured["api_base"] == "http://127.0.0.1:8017"
    assert captured["api_key"] == "runtime-key"
    report_path = tmp_path / "reports" / "evaluation_answer_latest.json"
    assert report_path.is_file()
    assert json.loads(report_path.read_text(encoding="utf-8"))["evaluation_set_id"] == "answer"


def test_verification_report_uses_known_error_instead_of_unknown():
    markdown = verify_quality._render_verification_markdown(
        {
            "passed": False,
            "generated_at": "now",
            "steps": [{"name": "评估", "ok": False, "error": "目标 API 未就绪"}],
        }
    )

    assert "目标 API 未就绪" in markdown
    assert "未知错误" not in markdown


def test_local_evaluation_explains_quality_failures(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(verify_quality, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(
        verify_quality,
        "run_evaluation",
        lambda path, top_k: {
            "ok": True,
            "case_count": 1,
            "failures": [{"id": "case-1"}],
        },
    )

    result = verify_quality._run_evaluation(
        tmp_path / "cases.jsonl",
        "local",
        "本地评估",
        "regular",
    )

    assert result["ok"] is False
    assert result["error"] == "检索评估完成但有 1 个失败用例"
    assert result["evaluation_set_id"] == "regular"


def test_credential_precedence_and_explicit_none(tmp_path: Path):
    command_file = tmp_path / "command.key"
    environment_file = tmp_path / "environment.key"
    legacy_file = tmp_path / "legacy.key"
    command_file.write_text("command-secret", encoding="utf-8")
    environment_file.write_text("environment-file-secret", encoding="utf-8")
    legacy_file.write_text("legacy-secret", encoding="utf-8")

    credential = verify_quality._resolve_api_credential(
        api_key_file=str(command_file),
        no_api_key=False,
        environ={
            "QUALITY_API_KEY": "environment-secret",
            "QUALITY_API_KEY_FILE": str(environment_file),
        },
        legacy_path=legacy_file,
    )
    assert credential.source == "environment"
    assert credential.key == "environment-secret"

    credential = verify_quality._resolve_api_credential(
        api_key_file=str(command_file),
        no_api_key=False,
        environ={"QUALITY_API_KEY_FILE": str(environment_file)},
        legacy_path=legacy_file,
    )
    assert credential.source == "command_file"
    assert credential.key == "command-secret"

    credential = verify_quality._resolve_api_credential(
        api_key_file=None,
        no_api_key=False,
        environ={"QUALITY_API_KEY_FILE": str(environment_file)},
        legacy_path=legacy_file,
    )
    assert credential.source == "environment_file"

    credential = verify_quality._resolve_api_credential(
        api_key_file=None,
        no_api_key=False,
        environ={},
        legacy_path=legacy_file,
    )
    assert credential.source == "legacy_file"

    credential = verify_quality._resolve_api_credential(
        api_key_file=str(command_file),
        no_api_key=True,
        environ={"QUALITY_API_KEY": "environment-secret"},
        legacy_path=legacy_file,
    )
    assert credential == verify_quality.ApiCredential(key="", source="explicit_none")


def test_credential_file_errors_and_repr_do_not_leak_secret(tmp_path: Path):
    missing = tmp_path / "missing.key"
    with pytest.raises(ValueError, match="不存在"):
        verify_quality._resolve_api_credential(
            api_key_file=str(missing),
            no_api_key=False,
            environ={},
            legacy_path=tmp_path / "legacy.key",
        )

    empty = tmp_path / "empty.key"
    empty.write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError, match="为空"):
        verify_quality._resolve_api_credential(
            api_key_file=str(empty),
            no_api_key=False,
            environ={},
            legacy_path=tmp_path / "legacy.key",
        )

    credential = verify_quality.ApiCredential(key="do-not-leak", source="test")
    assert "do-not-leak" not in repr(credential)


def test_access_probe_reports_auth_failure_without_secret(monkeypatch):
    body = io.BytesIO(json.dumps({"detail": "Unauthorized"}).encode("utf-8"))

    def reject(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:8017/admin/status",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=body,
        )

    monkeypatch.setattr(verify_quality, "_api_json", reject)
    credential = verify_quality.ApiCredential(key="secret-value", source="environment")

    result = verify_quality._probe_api_access("http://127.0.0.1:8017", credential)

    assert result["ok"] is False
    assert result["status_code"] == 401
    assert result["credential_source"] == "environment"
    assert result["credential_supplied"] is True
    assert "secret-value" not in json.dumps(result, ensure_ascii=False)
