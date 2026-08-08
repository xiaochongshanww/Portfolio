from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent


def test_runtime_image_bundles_console_and_runtime_assets():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
    runtime_requirements = (PROJECT_ROOT / "requirements-runtime.txt").read_text(
        encoding="utf-8"
    )

    assert "FROM node:22-alpine AS frontend-builder" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "COPY --from=frontend-builder /app/frontend/dist frontend/dist/" in dockerfile
    assert "COPY data/evaluation/ data/evaluation/" in dockerfile
    assert "COPY data/metadata/ data/metadata/" in dockerfile
    assert "!data/evaluation/**" in dockerignore
    assert "!data/metadata/**" in dockerignore
    assert "pymupdf==" in runtime_requirements.casefold()


def test_runtime_and_development_dependencies_are_locked():
    for filename in ("requirements-runtime.txt", "requirements-dev.txt"):
        lines = (PROJECT_ROOT / filename).read_text(encoding="utf-8").splitlines()
        requirements = [
            line.strip()
            for line in lines
            if line.strip() and not line.lstrip().startswith(("#", "-"))
        ]
        assert requirements
        assert all("==" in requirement for requirement in requirements)

    assert (PROJECT_ROOT / "requirements-runtime.in").is_file()
    assert (PROJECT_ROOT / "requirements-dev.in").is_file()


def test_compose_persists_runtime_data_and_uses_v1_backend():
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert compose.startswith("name: structural-spec-kb")
    assert "./data:/app/data" in compose
    assert "open-webui-data:/app/backend/data" in compose
    assert "OPENAI_API_BASE_URL=http://api:8000/v1" in compose
    assert "OPENAI_API_KEY=${OPENWEBUI_API_KEY:-not-needed}" in compose
    assert "condition: service_healthy" in compose


def test_repository_ci_covers_backend_frontend_and_container():
    workflow = (
        REPOSITORY_ROOT / ".github" / "workflows" / "structural-spec-kb-ci.yml"
    ).read_text(encoding="utf-8")

    assert "python -m pytest -q" in workflow
    assert "npm run build" in workflow
    assert "docker build --tag structural-spec-kb:ci ." in workflow
    assert "/static/index.html" in workflow
    assert "/health" in workflow
