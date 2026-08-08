import json
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.api import health
from src.app.admin.jobs import JobManager
from src.app.admin.models import Job
from src.app.admin.storage import JobStore
from src.app.core.logging import ContextTextFormatter, JsonFormatter
from src.app.core.middleware import ServiceMiddleware
from src.app.core.request_context import (
    current_request_id,
    normalize_request_id,
    reset_request_id,
    set_request_id,
)


def test_json_log_contains_context_and_structured_fields():
    token = set_request_id("request-123")
    try:
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="request_completed",
            args=(),
            exc_info=None,
        )
        record.extra_data = {"status": 200, "duration_ms": 12}
        payload = json.loads(JsonFormatter().format(record))
    finally:
        reset_request_id(token)

    assert payload["event"] == "request_completed"
    assert payload["request_id"] == "request-123"
    assert payload["status"] == 200
    assert payload["duration_ms"] == 12
    assert payload["timestamp"].endswith("+00:00")


def test_json_log_is_portable_across_host_encodings():
    record = logging.LogRecord("test.logger", logging.INFO, __file__, 1, "任务完成", (), None)

    rendered = JsonFormatter().format(record)

    assert rendered.isascii()
    assert json.loads(rendered)["event"] == "任务完成"


def test_text_log_does_not_drop_structured_fields():
    record = logging.LogRecord("test.logger", logging.INFO, __file__, 1, "job_completed", (), None)
    record.extra_data = {"job_id": "job-1", "status": "succeeded"}

    rendered = ContextTextFormatter("%(levelname)s %(message)s").format(record)

    assert "job_completed" in rendered
    assert '"job_id": "job-1"' in rendered


def test_request_id_is_validated_and_context_can_be_reset():
    assert normalize_request_id("valid:request-1") == "valid:request-1"
    generated = normalize_request_id("bad request\nforged")
    assert len(generated) == 32

    token = set_request_id("temporary")
    assert current_request_id() == "temporary"
    reset_request_id(token)
    assert current_request_id() == ""


def test_middleware_returns_normalized_request_id_and_collects_response():
    app = FastAPI()
    app.add_middleware(ServiceMiddleware)

    @app.get("/probe")
    async def probe():
        return {"ok": True}

    response = TestClient(app).get("/probe", headers={"X-Request-ID": "bad request\nforged"})

    assert response.status_code == 200
    assert len(response.headers["X-Request-ID"]) == 32
    assert " " not in response.headers["X-Request-ID"]


def test_openapi_documents_unready_response_contract():
    contract_app = FastAPI()
    contract_app.include_router(health.router)
    schema = TestClient(contract_app).get("/openapi.json").json()
    responses = schema["paths"]["/ready"]["get"]["responses"]

    assert "200" in responses
    assert "503" in responses
    assert responses["503"]["content"]["application/json"]["schema"]


def test_job_logs_inherit_request_correlation(tmp_path: Path):
    store = JobStore(tmp_path)
    job = Job(type="audit", request_id="request-456")
    store.save(job)
    token = set_request_id(job.request_id)
    try:
        store.append_log(job.job_id, "info", "任务开始")
    finally:
        reset_request_id(token)

    assert store.logs(job.job_id)[0]["request_id"] == "request-456"


def test_job_manager_propagates_and_restores_request_context(tmp_path: Path):
    store = JobStore(tmp_path)
    manager = JobManager(store)
    observed_request_ids = []
    job = Job(type="audit", request_id="request-789")

    manager._run(job, lambda _job, _store: observed_request_ids.append(current_request_id()) or {"ok": True})

    assert observed_request_ids == ["request-789"]
    assert job.status == "succeeded"
    assert current_request_id() == ""
    assert {entry["request_id"] for entry in store.logs(job.job_id)} == {"request-789"}


def test_job_manager_restores_context_after_workflow_failure(tmp_path: Path):
    store = JobStore(tmp_path)
    manager = JobManager(store)
    job = Job(type="audit", request_id="request-failed")

    def fail(_job, _store):
        raise RuntimeError("workflow failed")

    manager._run(job, fail)

    assert job.status == "failed"
    assert job.error == "workflow failed"
    assert current_request_id() == ""
    assert store.logs(job.job_id)[-1]["request_id"] == "request-failed"
