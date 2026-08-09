from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from scripts import pull_compose_images as puller


def completed(returncode: int, *, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(
        ["docker", "compose", "pull"], returncode, stdout=stdout, stderr=stderr
    )


def test_build_pull_command_keeps_options_before_pull():
    command = puller.build_pull_command(
        ["open-webui", "metrics"],
        policy="always",
        compose_file=Path("compose.test.yml"),
        project_directory=Path("workspace"),
    )

    assert command == [
        "docker",
        "compose",
        "--project-directory",
        "workspace",
        "--file",
        "compose.test.yml",
        "pull",
        "--ignore-buildable",
        "--quiet",
        "--policy",
        "always",
        "open-webui",
        "metrics",
    ]


def test_pull_succeeds_without_sleep_on_first_attempt():
    calls: list[list[str]] = []
    run_options: list[dict] = []
    sleeps: list[float] = []
    messages: list[str] = []

    def run(command, **kwargs):
        calls.append(command)
        run_options.append(kwargs)
        return completed(0, stdout="image is up to date")

    result = puller.pull_compose_images(
        ["open-webui"], runner=run, sleeper=sleeps.append, output=messages.append
    )

    assert result == 0
    assert len(calls) == 1
    assert run_options[0]["timeout"] == puller.DEFAULT_ATTEMPT_TIMEOUT_SECONDS
    assert sleeps == []
    assert messages[-1].endswith("status=success services=open-webui")


def test_transient_failures_retry_with_capped_exponential_backoff():
    results = iter(
        [
            completed(1, stderr="TooManyRequests: retry-after: 1ms"),
            completed(1, stderr="TLS HANDSHAKE TIMEOUT"),
            completed(0),
        ]
    )
    sleeps: list[float] = []
    messages: list[str] = []

    result = puller.pull_compose_images(
        ["open-webui"],
        attempts=3,
        initial_delay=2,
        max_delay=3,
        runner=lambda *_args, **_kwargs: next(results),
        sleeper=sleeps.append,
        output=messages.append,
    )

    assert result == 0
    assert sleeps == [2, 3]
    assert any("classification=registry_rate_limit" in message for message in messages)
    assert any("classification=network_timeout" in message for message in messages)


def test_transient_failure_stops_at_attempt_limit():
    calls = 0
    sleeps: list[float] = []
    messages: list[str] = []

    def run(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return completed(23, stderr="503 Service Unavailable")

    result = puller.pull_compose_images(
        ["open-webui"],
        attempts=2,
        initial_delay=0.5,
        max_delay=1,
        runner=run,
        sleeper=sleeps.append,
        output=messages.append,
    )

    assert result == 23
    assert calls == 2
    assert sleeps == [0.5]
    assert messages[-1].endswith("classification=gateway_unavailable exit_code=23")


@pytest.mark.parametrize(
    ("diagnostic", "expected_category"),
    [
        ("Too Many Requests", "registry_rate_limit"),
        ("LOCAL ERROR: TLS: BAD RECORD MAC", "network_timeout"),
        ("connection reset by peer", "connection_interrupted"),
        ("temporary failure in name resolution", "temporary_dns"),
        ("504 Gateway Timeout", "gateway_unavailable"),
    ],
)
def test_transient_error_classification_is_case_insensitive(diagnostic, expected_category):
    assert puller.classify_transient_error(diagnostic) == expected_category


def test_permanent_or_unknown_failure_is_not_retried():
    calls = 0
    sleeps: list[float] = []

    def run(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return completed(18, stderr="manifest unknown: requested image not found")

    result = puller.pull_compose_images(
        ["missing-image"],
        runner=run,
        sleeper=sleeps.append,
        output=lambda _message: None,
    )

    assert result == 18
    assert calls == 1
    assert sleeps == []


def test_permanent_dns_name_failure_is_not_retried():
    calls = 0

    def run(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return completed(1, stderr="lookup invalid.registry.example: no such host")

    result = puller.pull_compose_images(
        ["open-webui"],
        runner=run,
        sleeper=lambda _delay: pytest.fail("permanent DNS failure must not be retried"),
        output=lambda _message: None,
    )

    assert result == 1
    assert calls == 1


def test_command_unavailable_returns_shell_compatible_code():
    messages: list[str] = []

    def unavailable(*_args, **_kwargs):
        raise FileNotFoundError("docker executable was not found")

    result = puller.pull_compose_images(["open-webui"], runner=unavailable, output=messages.append)

    assert result == 127
    assert "classification=command_unavailable" in messages[-1]


def test_attempt_timeout_retries_then_returns_timeout_code():
    calls = 0
    sleeps: list[float] = []
    messages: list[str] = []

    def timeout(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise subprocess.TimeoutExpired(["docker", "compose", "pull"], 3)

    result = puller.pull_compose_images(
        ["open-webui"],
        attempts=2,
        initial_delay=0.5,
        max_delay=1,
        attempt_timeout=3,
        runner=timeout,
        sleeper=sleeps.append,
        output=messages.append,
    )

    assert result == 124
    assert calls == 2
    assert sleeps == [0.5]
    assert "status=retry classification=attempt_timeout timeout_seconds=3" in messages[0]
    assert "status=failed classification=attempt_timeout timeout_seconds=3" in messages[-1]


@pytest.mark.parametrize(
    ("services", "attempts", "initial_delay", "max_delay", "attempt_timeout", "policy"),
    [
        ([], 1, 0, 0, 1, "missing"),
        (["--bad-option"], 1, 0, 0, 1, "missing"),
        (["valid"], 0, 0, 0, 1, "missing"),
        (["valid"], 1, -1, 0, 1, "missing"),
        (["valid"], 1, 2, 1, 1, "missing"),
        (["valid"], 1, 0, 0, 0, "missing"),
        (["valid"], 1, 0, 0, 1, "invalid"),
    ],
)
def test_invalid_options_fail_before_running_command(
    services, attempts, initial_delay, max_delay, attempt_timeout, policy
):
    with pytest.raises(ValueError):
        puller.pull_compose_images(
            services,
            attempts=attempts,
            initial_delay=initial_delay,
            max_delay=max_delay,
            attempt_timeout=attempt_timeout,
            policy=policy,
            runner=lambda *_args, **_kwargs: pytest.fail("runner must not be called"),
        )


def test_diagnostics_redact_assignments_and_url_credentials():
    messages: list[str] = []
    secret = "do-not-print-this"

    result = puller.pull_compose_images(
        ["open-webui"],
        runner=lambda *_args, **_kwargs: completed(
            1,
            stderr=(
                f"OPENWEBUI_API_KEY={secret} Authorization: Bearer {secret} "
                f"https://user:{secret}@registry.example.invalid manifest unknown"
            ),
        ),
        output=messages.append,
    )

    rendered = "\n".join(messages)
    assert result == 1
    assert secret not in rendered
    assert "OPENWEBUI_API_KEY=[REDACTED]" in rendered
    assert "Authorization: Bearer [REDACTED]" in rendered
    assert "https://[REDACTED]@registry.example.invalid" in rendered


def test_main_reports_cross_option_validation_error(capsys):
    result = puller.main(["--initial-delay", "4", "--max-delay", "2", "open-webui"])

    assert result == 2
    assert "maximum delay" in capsys.readouterr().err
