from pathlib import Path

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
        tmp_path / "cases.jsonl",
        "http://127.0.0.1:8017",
        "key",
    )

    assert result["ok"] is False
    assert result["error"] == "检索服务未就绪"


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
    assert (tmp_path / "reports" / "evaluation_answer_latest.json").is_file()


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

    result = verify_quality._run_evaluation(tmp_path / "cases.jsonl", "local", "本地评估")

    assert result["ok"] is False
    assert result["error"] == "检索评估完成但有 1 个失败用例"
