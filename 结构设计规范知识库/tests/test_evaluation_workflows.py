from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.app.admin.models import Job
from src.app.admin.storage import JobStore
from src.app.admin import workflows
from src.app.api.admin import AnswerEvaluateRequest


def test_answer_evaluation_request_rejects_client_supplied_target():
    with pytest.raises(ValidationError):
        AnswerEvaluateRequest(api_base="http://example.com")


def test_retrieval_evaluation_execution_failure_marks_workflow_failed(monkeypatch, tmp_path: Path):
    store = JobStore(tmp_path / "jobs")
    job = Job(type="evaluate", params={"file": str(tmp_path / "cases.jsonl")})
    monkeypatch.setattr(workflows, "AUDIT_DIR", tmp_path / "audit")
    monkeypatch.setattr(
        workflows,
        "run_evaluation",
        lambda path, top_k: {"ok": False, "error": "知识库检索服务未就绪"},
    )

    with pytest.raises(workflows.EvaluationExecutionFailed, match="检索服务未就绪"):
        workflows.evaluate_workflow(job, store)

    persisted = store.read(job.job_id)
    assert persisted["outputs"]["ok"] is False
    assert Path(persisted["outputs"]["report_path"]).is_file()
    assert "执行错误" in Path(persisted["outputs"]["markdown_report_path"]).read_text(encoding="utf-8")


def test_answer_evaluation_unready_target_fails_before_cases(monkeypatch, tmp_path: Path):
    store = JobStore(tmp_path / "jobs")
    job = Job(type="answer_evaluate", params={})
    monkeypatch.setattr(workflows, "AUDIT_DIR", tmp_path / "audit")
    monkeypatch.setattr(
        workflows,
        "settings",
        SimpleNamespace(answer_evaluation_api_base="http://127.0.0.1:8017", api_keys=["key"]),
    )
    monkeypatch.setattr(
        workflows,
        "probe_api_readiness",
        lambda api_base: {"ok": False, "error": "目标 API 未就绪：BM25_MISSING"},
    )
    monkeypatch.setattr(
        workflows,
        "run_answer_evaluation",
        lambda **kwargs: pytest.fail("未就绪时不应执行回答用例"),
    )

    with pytest.raises(workflows.EvaluationExecutionFailed, match="BM25_MISSING"):
        workflows.answer_evaluate_workflow(job, store)

    persisted = store.read(job.job_id)
    assert persisted["outputs"]["api_base"] == "http://127.0.0.1:8017"
    assert persisted["outputs"]["readiness"]["ok"] is False


def test_answer_quality_failure_is_completed_evaluation(monkeypatch, tmp_path: Path):
    store = JobStore(tmp_path / "jobs")
    job = Job(type="answer_evaluate", params={})
    monkeypatch.setattr(workflows, "AUDIT_DIR", tmp_path / "audit")
    monkeypatch.setattr(
        workflows,
        "settings",
        SimpleNamespace(answer_evaluation_api_base="http://127.0.0.1:8017", api_keys=["key"]),
    )
    monkeypatch.setattr(
        workflows,
        "probe_api_readiness",
        lambda api_base: {"ok": True, "api_base": api_base},
    )
    monkeypatch.setattr(
        workflows,
        "run_answer_evaluation",
        lambda **kwargs: {
            "ok": True,
            "api_base": kwargs["api_base"],
            "case_count": 2,
            "passed_count": 1,
            "failure_count": 1,
            "pass_rate": 0.5,
            "check_rates": {},
            "refusal_pass_rate": 1,
            "failures": [{"id": "quality", "query": "q", "failed_checks": ["facts_all"]}],
            "results": [],
        },
    )

    result = workflows.answer_evaluate_workflow(job, store)

    assert result["ok"] is True
    assert result["pass_rate"] == 0.5
    assert result["readiness"]["ok"] is True


def test_answer_request_failure_marks_workflow_failed(monkeypatch, tmp_path: Path):
    store = JobStore(tmp_path / "jobs")
    job = Job(type="answer_evaluate", params={})
    monkeypatch.setattr(workflows, "AUDIT_DIR", tmp_path / "audit")
    monkeypatch.setattr(
        workflows,
        "settings",
        SimpleNamespace(answer_evaluation_api_base="http://127.0.0.1:8017", api_keys=["key"]),
    )
    monkeypatch.setattr(
        workflows,
        "probe_api_readiness",
        lambda api_base: {"ok": True, "api_base": api_base},
    )
    monkeypatch.setattr(
        workflows,
        "run_answer_evaluation",
        lambda **kwargs: {
            "ok": False,
            "error": "回答级盲测有 1/2 个请求未完成",
            "api_base": kwargs["api_base"],
            "case_count": 2,
            "passed_count": 1,
            "failure_count": 1,
            "pass_rate": 0.5,
            "check_rates": {"request": 0.5},
            "refusal_pass_rate": 1,
            "failures": [
                {
                    "id": "request",
                    "query": "q",
                    "failed_checks": ["request"],
                    "error": "connection refused",
                }
            ],
            "results": [],
        },
    )

    with pytest.raises(workflows.EvaluationExecutionFailed, match="请求未完成"):
        workflows.answer_evaluate_workflow(job, store)

    persisted = store.read(job.job_id)
    assert persisted["outputs"]["ok"] is False
    assert Path(persisted["outputs"]["report_path"]).is_file()
