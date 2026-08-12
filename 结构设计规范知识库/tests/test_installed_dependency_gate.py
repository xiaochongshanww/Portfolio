from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
INSTALL_DEV = (
    "python -m pip install --disable-pip-version-check --require-hashes -r requirements-dev.txt"
)
INSTALL_RUNTIME = (
    "python -m pip install --disable-pip-version-check --require-hashes -r requirements-runtime.txt"
)
PIP_CHECK = "python -m pip check"


def _workflow_job(workflow: str, job: str, next_job: str) -> str:
    return workflow.split(f"  {job}:", 1)[1].split(f"  {next_job}:", 1)[0]


def _assert_install_check_work_order(block: str, install: str, work: str) -> None:
    assert block.count(PIP_CHECK) == 1
    assert block.index(install) < block.index(PIP_CHECK) < block.index(work)


def test_ci_checks_installed_development_and_runtime_dependency_graphs():
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "structural-spec-kb-ci.yml").read_text(
        encoding="utf-8"
    )

    backend = _workflow_job(workflow, "backend", "frontend")
    producer = _workflow_job(workflow, "package-producer", "package-portability")
    portability = _workflow_job(workflow, "package-portability", "container")

    _assert_install_check_work_order(backend, INSTALL_DEV, "python -m ruff check")
    _assert_install_check_work_order(
        producer, INSTALL_RUNTIME, "python -m scripts.create_portability_package"
    )
    _assert_install_check_work_order(
        portability, INSTALL_RUNTIME, "python -m src.pipeline package-probe"
    )


def test_runtime_image_checks_builder_graph_before_copying_and_removing_pip():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    install = (
        "RUN python -m pip install --no-cache-dir --require-hashes -r requirements-runtime.txt"
    )
    check = "RUN python -m pip check"
    venv_cleanup = "RUN python -m pip uninstall --yes wheel setuptools pip"
    copy = "COPY --from=python-builder /opt/venv /opt/venv"
    runtime_cleanup = "RUN python -m pip uninstall --yes jaraco.context wheel setuptools pip"

    assert dockerfile.count(check) == 1
    assert (
        dockerfile.index(install)
        < dockerfile.index(check)
        < dockerfile.index(venv_cleanup)
        < dockerfile.index(copy)
    )
    assert dockerfile.index(runtime_cleanup) < dockerfile.index(copy)
