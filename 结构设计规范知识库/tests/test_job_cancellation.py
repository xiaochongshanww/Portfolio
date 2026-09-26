from __future__ import annotations

import subprocess
from io import StringIO
from threading import Event, Lock, Thread
from types import SimpleNamespace

import pytest
from src.app.core.job_cancellation import (
    JobCancelled,
    bind_job_cancellation,
    job_cancellation_safe_section,
    reset_job_cancellation,
)
from src.pipeline.parsers import mineru


class BlockingOutput:
    def __init__(self, released: Event, started: Event) -> None:
        self.released = released
        self.started = started

    def __iter__(self):
        self.started.set()
        yield "MinerU is running"
        self.released.wait(5)


class FakeProcess:
    def __init__(self, stdout=None) -> None:
        self.pid = 1234
        self.stdout = stdout
        self.returncode = None
        self.killed = False
        self.waited = False

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.waited = True
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9
        if hasattr(self.stdout, "released"):
            self.stdout.released.set()


def test_cancelled_mineru_command_terminates_child_and_unblocks_output_reader(monkeypatch):
    cancellation = Event()
    process_created = Event()
    output_started = Event()
    released = Event()
    process = FakeProcess(BlockingOutput(released, output_started))

    def create_process(*_args, **_kwargs):
        process_created.set()
        return process

    monkeypatch.setattr(mineru.subprocess, "Popen", create_process)
    monkeypatch.setattr(mineru, "_terminate_mineru_process_tree", lambda child: child.kill())
    errors: list[BaseException] = []

    def run_command():
        token = bind_job_cancellation(cancellation, Lock())
        try:
            mineru._run_mineru_command(
                ["magic-pdf", "--parse"],
                progress_callback=lambda *_args: None,
                document="sample.pdf",
            )
        except BaseException as exc:
            errors.append(exc)
        finally:
            reset_job_cancellation(token)

    runner = Thread(target=run_command)
    runner.start()
    assert process_created.wait(1)
    assert output_started.wait(1)
    cancellation.set()
    runner.join(timeout=3)

    assert not runner.is_alive()
    assert process.killed is True
    assert isinstance(errors[0], JobCancelled)


def test_mineru_live_output_is_collected_and_reported(monkeypatch):
    process = FakeProcess(StringIO("page 1/2\npage 2/2\n"))
    progress: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(mineru.subprocess, "Popen", lambda *_args, **_kwargs: process)

    result = mineru._run_mineru_command(
        ["magic-pdf", "--parse"],
        progress_callback=lambda step, message, details: progress.append((step, message, details)),
        document="sample.pdf",
    )

    assert result.returncode == 0
    assert result.stdout == "page 1/2\npage 2/2"
    assert len(progress) == 2
    assert progress[-1][2]["parser_output"] == "page 2/2"


def test_windows_process_tree_termination_uses_taskkill_tree(monkeypatch):
    process = FakeProcess()
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(mineru, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(mineru.subprocess, "run", fake_run)

    mineru._terminate_mineru_process_tree(process)

    assert calls[0][0] == ["taskkill", "/PID", "1234", "/T", "/F"]
    assert calls[0][1]["timeout"] == 10
    assert process.killed is True
    assert process.waited is True


def test_activation_safe_section_aborts_if_cancellation_was_requested():
    cancellation = Event()
    cancellation.set()
    token = bind_job_cancellation(cancellation, Lock())
    try:
        with pytest.raises(JobCancelled):
            with job_cancellation_safe_section():
                pytest.fail("cancelled job must not enter activation commit")
    finally:
        reset_job_cancellation(token)
