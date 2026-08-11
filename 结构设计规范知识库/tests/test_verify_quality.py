import io
import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from scripts import verify_quality


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


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
                    "verification_run_id": "a" * 32,
                    "runtime_config_hash": "b" * 64,
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
        "a" * 32,
        "b" * 64,
    )

    assert result["ok"] is True
    assert result["evaluation_set_id"] == "structured"
    assert calls[0][1]["payload"] == {
        "top_k": 5,
        "evaluation_set": "structured",
        "verification_run_id": "a" * 32,
    }
    assert "file" not in calls[0][1]["payload"]


def test_api_evaluation_rejects_mismatched_evidence_context(monkeypatch):
    responses = iter(
        [
            {"job_id": "job-1"},
            {
                "status": "succeeded",
                "outputs": {
                    "ok": True,
                    "case_count": 100,
                    "failures": [],
                    "verification_run_id": "c" * 32,
                    "runtime_config_hash": "d" * 64,
                },
            },
        ]
    )
    monkeypatch.setattr(verify_quality, "_api_json", lambda *args, **kwargs: next(responses))

    result = verify_quality._run_api_evaluation(
        "regular",
        "http://127.0.0.1:8017",
        "key",
        "a" * 32,
        "b" * 64,
    )

    assert result["ok"] is False
    assert "证据上下文" in result["error"]


def test_failed_api_evaluation_is_preserved_in_current_run(monkeypatch, tmp_path: Path):
    responses = iter(
        [
            {"job_id": "job-1"},
            {
                "status": "failed",
                "error": "检索服务未就绪",
                "outputs": {
                    "ok": False,
                    "error": "检索服务未就绪",
                    "report_path": "remote/report.json",
                },
            },
        ]
    )
    monkeypatch.setattr(verify_quality, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(verify_quality, "_api_json", lambda *args, **kwargs: next(responses))

    result = verify_quality._run_api_evaluation(
        "regular",
        "http://127.0.0.1:8017",
        "key",
        "a" * 32,
        "b" * 64,
    )

    report_path = tmp_path / "reports" / "runs" / ("a" * 32) / "evaluation.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert result["ok"] is False
    assert report["verification_run_id"] == "a" * 32
    assert report["runtime_config_hash"] == "b" * 64
    assert report["error"] == "检索服务未就绪"
    assert "report_path" not in report
    assert not (tmp_path / "reports" / "evaluation_latest.json").exists()


def test_missing_evaluations_create_same_run_placeholders_without_reusing_latest(
    monkeypatch,
    tmp_path: Path,
):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "evaluation_latest.json").write_text(
        json.dumps({"ok": True, "verification_run_id": "c" * 32}),
        encoding="utf-8",
    )
    monkeypatch.setattr(verify_quality, "REPORTS_DIR", reports_dir)

    verify_quality._ensure_quality_run_reports(
        "a" * 32,
        "b" * 64,
        [
            {
                "name": "常规检索评估",
                "ok": False,
                "skipped": True,
                "error": "显式跳过",
            }
        ],
    )

    run_dir = reports_dir / "runs" / ("a" * 32)
    for name in ("evaluation.json", "evaluation_structured.json", "evaluation_answer.json"):
        report = json.loads((run_dir / name).read_text(encoding="utf-8"))
        assert report["verification_run_id"] == "a" * 32
        assert report["runtime_config_hash"] == "b" * 64
        assert report["execution_status"] == "skipped"
        assert report["ok"] is False
    legacy = json.loads((reports_dir / "evaluation_latest.json").read_text(encoding="utf-8"))
    assert legacy["verification_run_id"] == "c" * 32


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
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["evidence_context_schema"] == 1
    assert len(report["runtime_config_hash"]) == 64


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


def test_verification_report_renders_evidence_context():
    markdown = verify_quality._render_verification_markdown(
        {
            "passed": False,
            "generated_at": "now",
            "verification_run_id": "a" * 32,
            "runtime_config_hash": "b" * 64,
            "steps": [],
        }
    )

    assert "`" + "a" * 32 + "`" in markdown
    assert "`" + "b" * 64 + "`" in markdown


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


def test_api_preflight_combines_readiness_and_access_without_secret(monkeypatch):
    monkeypatch.setenv("QUALITY_API_KEY", "secret-value")
    monkeypatch.setattr(
        verify_quality,
        "probe_api_readiness",
        lambda api_base: {
            "ok": True,
            "api_base": api_base,
            "ready": True,
            "checks": {"collection_count": 1636},
        },
    )
    monkeypatch.setattr(
        verify_quality,
        "_probe_api_access",
        lambda api_base, credential: {
            "ok": True,
            "credential_source": credential.source,
            "credential_supplied": bool(credential.key),
        },
    )
    monkeypatch.setattr(
        verify_quality,
        "_probe_provider_capabilities",
        lambda api_base, credential: {
            "ok": True,
            "providers": [
                {"provider": "zhipuai", "capability": "embedding", "status": "ok"},
                {"provider": "mimo", "capability": "chat", "status": "ok"},
            ],
        },
    )

    result = verify_quality._run_api_preflight(
        "http://127.0.0.1:8017",
        api_key_file=None,
        no_api_key=False,
    )

    assert result["ok"] is True
    assert [step["name"] for step in result["steps"]] == [
        "API 凭据加载",
        "目标 API 就绪预检",
        "目标 API 鉴权预检",
        "模型供应商能力预检",
    ]
    assert "secret-value" not in json.dumps(result, ensure_ascii=False)


def test_api_preflight_fails_closed_when_readiness_fails(monkeypatch):
    monkeypatch.setattr(
        verify_quality,
        "probe_api_readiness",
        lambda api_base: {
            "ok": False,
            "api_base": api_base,
            "ready": False,
            "reasons": ["缺少 MIMO API Key"],
        },
    )
    monkeypatch.setattr(
        verify_quality,
        "_probe_api_access",
        lambda api_base, credential: {"ok": True},
    )

    result = verify_quality._run_api_preflight(
        "http://127.0.0.1:8017",
        api_key_file=None,
        no_api_key=True,
    )

    assert result["ok"] is False
    assert result["steps"][1]["reasons"] == ["缺少 MIMO API Key"]
    assert result["steps"][3]["skipped"] is True


def test_provider_capability_probe_keeps_only_non_secret_contract(monkeypatch):
    monkeypatch.setattr(
        verify_quality,
        "_api_json",
        lambda *args, **kwargs: {
            "ok": False,
            "checked_at": "2026-08-12T00:00:00Z",
            "providers": [
                {
                    "provider": "zhipuai",
                    "capability": "embedding",
                    "model": "embedding-2",
                    "ok": False,
                    "status": "auth_failed",
                    "latency_ms": 12,
                    "http_status": 401,
                    "upstream_body": "secret provider response",
                },
                {
                    "provider": "mimo",
                    "capability": "chat",
                    "model": "mimo-v2.5",
                    "ok": True,
                    "status": "ok",
                    "latency_ms": 20,
                    "http_status": None,
                    "output": "private generated output",
                },
            ],
        },
    )

    result = verify_quality._probe_provider_capabilities(
        "http://127.0.0.1:8017",
        verify_quality.ApiCredential(key="client-secret", source="test"),
    )

    assert result["ok"] is False
    assert "zhipuai/embedding=auth_failed" in result["error"]
    rendered = json.dumps(result, ensure_ascii=False)
    assert "client-secret" not in rendered
    assert "secret provider response" not in rendered
    assert "private generated output" not in rendered


def test_full_verification_does_not_call_evaluations_after_provider_probe_failure(
    monkeypatch, tmp_path: Path
):
    runtime_hash = "1" * 64
    run_id = "2" * 32
    monkeypatch.setattr(verify_quality, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(verify_quality, "new_verification_run_id", lambda: run_id)
    monkeypatch.setattr(
        verify_quality,
        "current_evidence_context",
        lambda: {
            "evidence_context_schema": 1,
            "runtime_config_hash": runtime_hash,
        },
    )
    monkeypatch.setattr(
        verify_quality,
        "_collect_api_preflight",
        lambda *args, **kwargs: (
            {
                "ok": False,
                "steps": [
                    {"name": "API 凭据加载", "ok": True},
                    {"name": "目标 API 就绪预检", "ok": True},
                    {
                        "name": "目标 API 鉴权预检",
                        "ok": True,
                        "runtime_config_hash": runtime_hash,
                    },
                    {
                        "name": "模型供应商能力预检",
                        "ok": False,
                        "providers": [
                            {
                                "provider": "mimo",
                                "capability": "chat",
                                "status": "auth_failed",
                            }
                        ],
                    },
                ],
            },
            verify_quality.ApiCredential(key="client-secret", source="test"),
        ),
    )
    monkeypatch.setattr(
        verify_quality,
        "_run_api_evaluation",
        lambda *args, **kwargs: pytest.fail("retrieval evaluation must not run"),
    )
    monkeypatch.setattr(
        verify_quality,
        "_run_answer_evaluation_against_api",
        lambda *args, **kwargs: pytest.fail("answer evaluation must not run"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "verify_quality.py",
            "--skip-tests",
            "--skip-frontend",
            "--api-base",
            "http://127.0.0.1:8017",
            "--no-api-key",
        ],
    )

    with pytest.raises(SystemExit, match="1"):
        verify_quality.main()

    report = json.loads(
        (tmp_path / "reports" / "runs" / run_id / "verification.json").read_text(encoding="utf-8")
    )
    evaluation_steps = {
        step["name"]: step
        for step in report["steps"]
        if step["name"] in {"常规检索评估", "结构化专项评估", "回答级盲测"}
    }
    assert set(evaluation_steps) == {"常规检索评估", "结构化专项评估", "回答级盲测"}
    assert all(step["skipped"] is True for step in evaluation_steps.values())
    assert all("供应商能力预检失败" in step["error"] for step in evaluation_steps.values())


def test_preflight_cli_is_ascii_safe_and_does_not_write_reports(tmp_path: Path):
    port = _free_loopback_port()
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "ascii"
    verification = verify_quality.REPORTS_DIR / verify_quality.VERIFICATION_JSON_NAME
    before = verification.read_bytes() if verification.is_file() else None

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_quality.py",
            "--preflight-only",
            "--api-base",
            f"http://127.0.0.1:{port}",
            "--no-api-key",
        ],
        cwd=Path.cwd(),
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["ok"] is False
    assert result["mode"] == "existing_api"
    after = verification.read_bytes() if verification.is_file() else None
    assert after == before


@pytest.mark.parametrize(
    ("api_base", "bind_host"),
    [
        ("http://127.0.0.1:8017", "127.0.0.1"),
        ("http://localhost:8017", "127.0.0.1"),
        ("http://[::1]:8017", "::1"),
    ],
)
def test_managed_api_target_accepts_explicit_loopback_http(api_base: str, bind_host: str):
    target = verify_quality._parse_managed_api_target(api_base)

    assert target.api_base == api_base
    assert target.bind_host == bind_host
    assert target.port == 8017


@pytest.mark.parametrize(
    "api_base",
    [
        "https://127.0.0.1:8017",
        "http://127.0.0.1",
        "http://127.0.0.1:8017/api",
        "http://127.0.0.1:8017?debug=1",
        "http://127.0.0.1:8017#fragment",
        "http://user:password@127.0.0.1:8017",
        "http://127.0.0.1:99999",
        "http://192.168.1.8:8017",
        "http://example.com:8017",
    ],
)
def test_managed_api_target_rejects_unsafe_or_ambiguous_targets(api_base: str):
    with pytest.raises(verify_quality.ManagedApiError):
        verify_quality._parse_managed_api_target(api_base)


def test_managed_api_refuses_occupied_port(tmp_path: Path):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = int(listener.getsockname()[1])
        manager = verify_quality.ManagedApiProcess(
            target=verify_quality._parse_managed_api_target(f"http://127.0.0.1:{port}"),
            log_path=tmp_path / "api.log",
        )

        with pytest.raises(verify_quality.ManagedApiError, match="端口已占用"):
            manager.start(timeout_seconds=1)

    assert manager.process is None
    assert not (tmp_path / "api.log").exists()


def test_managed_api_real_process_starts_and_stops(tmp_path: Path):
    module_path = tmp_path / "managed_fixture.py"
    module_path.write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "@app.get('/health')\n"
        "def health():\n"
        "    return {'status': 'ok'}\n",
        encoding="utf-8",
    )
    port = _free_loopback_port()
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(tmp_path), environment.get("PYTHONPATH", "")) if value
    )
    manager = verify_quality.ManagedApiProcess(
        target=verify_quality._parse_managed_api_target(f"http://127.0.0.1:{port}"),
        log_path=tmp_path / "api.log",
        app="managed_fixture:app",
        cwd=tmp_path,
        environ=environment,
    )

    started = manager.start(timeout_seconds=15)
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
        payload = json.loads(response.read().decode("utf-8"))
    stopped = manager.stop(timeout_seconds=10)

    assert started["api_base"] == f"http://127.0.0.1:{port}"
    assert payload == {"status": "ok"}
    assert stopped["ok"] is True
    assert manager.process is not None and manager.process.poll() is not None


def test_managed_api_failed_start_redacts_environment_secret(tmp_path: Path):
    module_path = tmp_path / "failed_fixture.py"
    module_path.write_text(
        "import os\nraise RuntimeError('credential=' + os.environ['ZHIPUAI_API_KEY'])\n",
        encoding="utf-8",
    )
    port = _free_loopback_port()
    environment = dict(os.environ)
    environment["ZHIPUAI_API_KEY"] = "secret-must-not-leak"
    environment["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(tmp_path), environment.get("PYTHONPATH", "")) if value
    )
    manager = verify_quality.ManagedApiProcess(
        target=verify_quality._parse_managed_api_target(f"http://127.0.0.1:{port}"),
        log_path=tmp_path / "failed.log",
        app="failed_fixture:app",
        cwd=tmp_path,
        environ=environment,
    )

    with pytest.raises(verify_quality.ManagedApiError) as error:
        manager.start(timeout_seconds=10)

    assert "<redacted>" in str(error.value)
    assert "secret-must-not-leak" not in str(error.value)
    assert manager.process is not None and manager.process.poll() is not None


def test_managed_child_args_only_removes_lifecycle_switch():
    arguments = [
        "--manage-api",
        "--api-base",
        "http://127.0.0.1:8017",
        "--api-key-file",
        "C:/secure/quality.key",
    ]

    assert verify_quality._managed_child_args(arguments) == arguments[1:]


def _write_fake_deferred_run(command: list[str], reports: Path) -> None:
    run_id = "a" * 32
    verification = {
        "generated_at": "fresh",
        "passed": True,
        "verification_run_id": run_id,
        "steps": [{"name": "质量门禁", "ok": True}],
    }
    for kind in ("regular", "structured", "answer", "gate", "verification"):
        payload = (
            verification if kind == "verification" else {"verification_run_id": run_id, "ok": True}
        )
        verify_quality.write_quality_report(
            reports,
            kind,
            payload,
            f"# {kind}\n",
            verification_run_id=run_id,
        )
    handoff = Path(command[command.index("--deferred-result-file") + 1])
    verify_quality.atomic_write_json(
        handoff,
        {
            "schema_version": 1,
            "verification_run_id": run_id,
            "verification_report": f"runs/{run_id}/verification.json",
        },
    )


def test_managed_verification_reports_startup_failure_without_stale_evidence(
    monkeypatch,
    tmp_path: Path,
):
    reports = tmp_path / "reports"
    reports.mkdir()
    stale_path = reports / verify_quality.VERIFICATION_JSON_NAME
    stale_path.write_text(
        json.dumps({"generated_at": "stale", "passed": True, "steps": []}),
        encoding="utf-8",
    )

    def fail_start(self, *, timeout_seconds):
        raise verify_quality.ManagedApiError("startup failed")

    def forbidden_child(*args, **kwargs):
        pytest.fail("启动失败后不应执行质量验证子进程")

    monkeypatch.setattr(verify_quality, "REPORTS_DIR", reports)
    monkeypatch.setattr(verify_quality.ManagedApiProcess, "start", fail_start)
    monkeypatch.setattr(verify_quality.subprocess, "run", forbidden_child)

    exit_code = verify_quality._run_managed_verification(
        "http://127.0.0.1:8017",
        ["--manage-api"],
        startup_timeout_seconds=1,
    )
    result = json.loads(stale_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert result["generated_at"] != "stale"
    assert result["passed"] is False
    assert result["steps"][0]["name"] == "托管 API 启动"
    assert result["steps"][0]["ok"] is False


def test_managed_verification_forwards_custom_base_and_owns_cleanup(
    monkeypatch,
    tmp_path: Path,
):
    reports = tmp_path / "reports"
    calls: dict[str, object] = {}

    class FakeManager:
        def __init__(self, *, target, log_path):
            self.target = target
            self.log_path = log_path

        def _child_environment(self):
            return dict(os.environ)

        def start(self, *, timeout_seconds):
            calls["start_timeout"] = timeout_seconds
            return {
                "api_base": self.target.api_base,
                "log_path": str(self.log_path),
            }

        def stop(self, *, timeout_seconds=10):
            calls["stopped"] = True
            return {"ok": True, "forced": False, "exit_code": 0}

    def fake_run(command, **kwargs):
        calls["command"] = command
        calls["environment"] = kwargs["env"]
        _write_fake_deferred_run(command, reports)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(verify_quality, "REPORTS_DIR", reports)
    monkeypatch.setattr(verify_quality, "ManagedApiProcess", FakeManager)
    monkeypatch.setattr(verify_quality.subprocess, "run", fake_run)

    exit_code = verify_quality._run_managed_verification(
        "http://127.0.0.1:8123",
        ["--manage-api", "--api-base", "http://127.0.0.1:8123", "--skip-tests"],
        startup_timeout_seconds=7,
    )
    result = json.loads(
        (reports / verify_quality.VERIFICATION_JSON_NAME).read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert calls["start_timeout"] == 7
    assert calls["stopped"] is True
    assert calls["environment"]["ANSWER_EVALUATION_API_BASE"] == "http://127.0.0.1:8123"
    assert "--manage-api" not in calls["command"]
    assert "--defer-quality-publish" in calls["command"]
    assert "http://127.0.0.1:8123" in calls["command"]
    assert result["passed"] is True
    assert result["steps"][0]["name"] == "托管 API 启动"
    assert result["steps"][-1]["name"] == "托管 API 回收"


def test_managed_cleanup_failure_is_published_as_failed_atomic_run(
    monkeypatch,
    tmp_path: Path,
):
    reports = tmp_path / "reports"

    class FakeManager:
        def __init__(self, *, target, log_path):
            self.target = target
            self.log_path = log_path

        def _child_environment(self):
            return dict(os.environ)

        def start(self, *, timeout_seconds):
            return {"api_base": self.target.api_base, "log_path": str(self.log_path)}

        def stop(self, *, timeout_seconds=10):
            return {"ok": False, "forced": False, "error": "cleanup failed"}

    def fake_run(command, **kwargs):
        _write_fake_deferred_run(command, reports)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(verify_quality, "REPORTS_DIR", reports)
    monkeypatch.setattr(verify_quality, "ManagedApiProcess", FakeManager)
    monkeypatch.setattr(verify_quality.subprocess, "run", fake_run)

    exit_code = verify_quality._run_managed_verification(
        "http://127.0.0.1:8123",
        ["--manage-api", "--api-base", "http://127.0.0.1:8123"],
        startup_timeout_seconds=7,
    )
    pointer = json.loads((reports / "quality_run_latest.json").read_text(encoding="utf-8"))
    verification = json.loads((reports / "verification_latest.json").read_text(encoding="utf-8"))

    assert exit_code == 1
    assert pointer["passed"] is False
    assert verification["passed"] is False
    assert verification["steps"][-1]["name"] == "托管 API 回收"
    assert verification["steps"][-1]["ok"] is False


def test_managed_verification_interrupts_with_cleanup_and_fresh_failure_report(
    monkeypatch,
    tmp_path: Path,
):
    reports = tmp_path / "reports"
    calls: dict[str, object] = {}

    class FakeManager:
        def __init__(self, *, target, log_path):
            self.target = target
            self.log_path = log_path

        def _child_environment(self):
            return dict(os.environ)

        def start(self, *, timeout_seconds):
            return {
                "api_base": self.target.api_base,
                "log_path": str(self.log_path),
            }

        def stop(self, *, timeout_seconds=10):
            calls["stopped"] = True
            return {"ok": True, "forced": False, "exit_code": 0}

    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(verify_quality, "REPORTS_DIR", reports)
    monkeypatch.setattr(verify_quality, "ManagedApiProcess", FakeManager)
    monkeypatch.setattr(verify_quality.subprocess, "run", interrupt)

    exit_code = verify_quality._run_managed_verification(
        "http://127.0.0.1:8123",
        ["--manage-api", "--api-base", "http://127.0.0.1:8123"],
        startup_timeout_seconds=7,
    )
    result = json.loads(
        (reports / verify_quality.VERIFICATION_JSON_NAME).read_text(encoding="utf-8")
    )

    assert exit_code == 130
    assert calls["stopped"] is True
    assert result["passed"] is False
    assert result["managed_api"]["interrupted"] is True
    assert result["steps"][-1]["name"] == "托管 API 回收"
    assert result["steps"][-1]["ok"] is True


def test_managed_preflight_owns_cleanup_without_overwriting_quality_report(
    monkeypatch,
    tmp_path: Path,
    capsys,
):
    reports = tmp_path / "reports"
    reports.mkdir()
    verification = reports / verify_quality.VERIFICATION_JSON_NAME
    verification.write_text("existing-report", encoding="utf-8")
    calls: dict[str, object] = {}

    class FakeManager:
        def __init__(self, *, target, log_path):
            self.target = target
            self.log_path = log_path

        def _child_environment(self):
            return dict(os.environ)

        def start(self, *, timeout_seconds):
            calls["start_timeout"] = timeout_seconds
            return {
                "api_base": self.target.api_base,
                "log_path": str(self.log_path),
            }

        def stop(self, *, timeout_seconds=10):
            calls["stopped"] = True
            return {"ok": True, "forced": False, "exit_code": 0}

    monkeypatch.setattr(verify_quality, "REPORTS_DIR", reports)
    monkeypatch.setattr(verify_quality, "ManagedApiProcess", FakeManager)
    monkeypatch.setattr(
        verify_quality,
        "_run_api_preflight",
        lambda *args, **kwargs: {
            "ok": True,
            "steps": [
                {"name": "目标 API 就绪预检", "ok": True},
                {"name": "目标 API 鉴权预检", "ok": True},
            ],
        },
    )

    exit_code = verify_quality._run_managed_preflight(
        "http://127.0.0.1:8123",
        api_key_file=None,
        no_api_key=True,
        startup_timeout_seconds=7,
    )
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert calls == {"start_timeout": 7, "stopped": True}
    assert result["ok"] is True
    assert result["writes_quality_reports"] is False
    assert verification.read_text(encoding="utf-8") == "existing-report"


def test_managed_preflight_startup_failure_does_not_create_quality_report(
    monkeypatch,
    tmp_path: Path,
    capsys,
):
    reports = tmp_path / "reports"

    def fail_start(self, *, timeout_seconds):
        raise verify_quality.ManagedApiError("startup failed")

    monkeypatch.setattr(verify_quality, "REPORTS_DIR", reports)
    monkeypatch.setattr(verify_quality.ManagedApiProcess, "start", fail_start)

    exit_code = verify_quality._run_managed_preflight(
        "http://127.0.0.1:8123",
        api_key_file=None,
        no_api_key=True,
        startup_timeout_seconds=1,
    )
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert result["ok"] is False
    assert not (reports / verify_quality.VERIFICATION_JSON_NAME).exists()


def test_managed_api_stop_forces_kill_after_timeout(tmp_path: Path):
    class StubbornProcess:
        returncode = None

        def __init__(self):
            self.terminated = False
            self.killed = False

        def poll(self):
            return None if not self.killed else -9

        def terminate(self):
            self.terminated = True

        def wait(self, timeout):
            if not self.killed:
                raise subprocess.TimeoutExpired("managed-api", timeout)
            self.returncode = -9
            return self.returncode

        def kill(self):
            self.killed = True

    manager = verify_quality.ManagedApiProcess(
        target=verify_quality._parse_managed_api_target("http://127.0.0.1:8017"),
        log_path=tmp_path / "api.log",
    )
    process = StubbornProcess()
    manager.process = process

    result = manager.stop(timeout_seconds=0.01)

    assert result["ok"] is True
    assert result["forced"] is True
    assert process.terminated is True
    assert process.killed is True
