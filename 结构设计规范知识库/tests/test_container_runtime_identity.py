from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent


def test_runtime_dependencies_do_not_depend_on_root_home() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "RUN python -m venv /opt/venv" in dockerfile
    assert "ENV PATH=/opt/venv/bin:$PATH" in dockerfile
    assert "COPY --from=python-builder /opt/venv /opt/venv" in dockerfile
    assert "/root/.local" not in dockerfile


def test_runtime_image_switches_to_dedicated_user_after_writable_paths_are_prepared() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    runtime = dockerfile.split(" AS runtime", maxsplit=1)[1]

    assert "ARG APP_UID=10001" in runtime
    assert "ARG APP_GID=10001" in runtime
    assert "case \"$APP_UID\" in ''|*[!0-9]*)" in runtime
    assert "case \"$APP_GID\" in ''|*[!0-9]*)" in runtime
    assert '[ "$APP_UID" -gt 0 ]' in runtime
    assert '[ "$APP_GID" -gt 0 ]' in runtime
    assert "useradd" in runtime
    assert "chown" in runtime
    assert "USER app:app" in runtime
    assert runtime.index("mkdir -p /app/db /app/logs /app/data") < runtime.index("USER app:app")
    assert runtime.rfind("COPY ") < runtime.index("USER app:app")


def test_compose_build_can_match_linux_host_identity() -> None:
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "APP_UID: ${APP_UID:-1000}" in compose
    assert "APP_GID: ${APP_GID:-1000}" in compose
    assert "APP_UID=1000" in env_example
    assert "APP_GID=1000" in env_example


def test_ci_verifies_effective_non_root_identity_and_write_access() -> None:
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "structural-spec-kb-ci.yml").read_text(
        encoding="utf-8"
    )

    assert "Verify non-root runtime identity and write access" in workflow
    assert "docker exec structural-spec-kb-ci id -u" in workflow
    assert "test -w /app/data" in workflow
    assert "touch /app/data/.ci-write-probe" in workflow
    assert "touch /app/data/.ci-compose-write-probe" in workflow
    assert '--build-arg APP_UID="$(id -u)"' in workflow
    assert '--build-arg APP_GID="$(id -g)"' in workflow
    assert "docker exec rag-api id -u" in workflow
