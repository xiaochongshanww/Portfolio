import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent


def test_runtime_image_bundles_console_and_runtime_assets():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
    runtime_requirements = (PROJECT_ROOT / "requirements-runtime.txt").read_text(
        encoding="utf-8"
    )
    frontend_package = json.loads(
        (PROJECT_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    frontend_npmrc = (PROJECT_ROOT / "frontend" / ".npmrc").read_text(
        encoding="utf-8"
    )

    assert "FROM node:22-alpine AS frontend-builder" in dockerfile
    assert "RUN npm install --global npm@10.9.8" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "COPY --from=frontend-builder /app/frontend/dist frontend/dist/" in dockerfile
    assert "COPY data/evaluation/ data/evaluation/" in dockerfile
    assert "COPY data/metadata/ data/metadata/" in dockerfile
    assert "--require-hashes -r requirements-runtime.txt" in dockerfile
    assert "!data/evaluation/**" in dockerignore
    assert "!data/metadata/**" in dockerignore
    assert "pymupdf==" in runtime_requirements.casefold()
    assert frontend_package["packageManager"] == "npm@10.9.8"
    assert frontend_package["engines"] == {"node": "22.x", "npm": "10.9.8"}
    assert "engine-strict=true" in frontend_npmrc.splitlines()


def test_runtime_and_development_dependencies_are_locked():
    lock_entries = {}
    for filename in ("requirements-runtime.txt", "requirements-dev.txt"):
        lines = (PROJECT_ROOT / filename).read_text(encoding="utf-8").splitlines()
        requirements = [
            line.strip().removesuffix("\\").strip()
            for line in lines
            if line.strip()
            and not line[0].isspace()
            and not line.lstrip().startswith(("#", "-"))
        ]
        hashes = [line.strip() for line in lines if line.strip().startswith("--hash=sha256:")]
        assert requirements
        assert all("==" in requirement for requirement in requirements)
        assert hashes
        lock_entries[filename] = set(requirements)

    assert (PROJECT_ROOT / "requirements-runtime.in").is_file()
    assert (PROJECT_ROOT / "requirements-dev.in").is_file()
    assert lock_entries["requirements-runtime.txt"] <= lock_entries["requirements-dev.txt"]


def test_dependency_lock_toolchain_is_pinned_and_machine_readable():
    config = json.loads((PROJECT_ROOT / "dependency-lock.json").read_text(encoding="utf-8"))
    tools = (PROJECT_ROOT / "requirements-tools.txt").read_text(encoding="utf-8")

    assert config["schema_version"] == 1
    assert config["python_version"] == "3.11"
    assert config["generate_hashes"] is True
    assert tools.splitlines()[-1] == f"uv=={config['uv_version']}"
    assert {item["output"] for item in config["locks"]} == {
        "requirements-runtime.txt",
        "requirements-dev.txt",
    }


def test_compose_persists_runtime_data_and_uses_v1_backend():
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert compose.startswith("name: structural-spec-kb")
    assert "path: .env" in compose
    assert "required: false" in compose
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
    assert "os: [ubuntu-latest, windows-latest]" in workflow
    assert "python scripts/lock_dependencies.py --check" in workflow
    assert "--require-hashes -r requirements-dev.txt" in workflow
    assert "Package portability (${{ matrix.source }} -> ${{ matrix.target }})" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "actions/download-artifact@v4" in workflow
    assert "--require-cross-platform" in workflow
    assert "npm install --global npm@10.9.8" in workflow
    assert "npm test" in workflow
    assert "npm run typecheck" in workflow
    assert "npm run build" in workflow
    assert "docker build --tag structural-spec-kb:ci ." in workflow
    assert "/static/index.html" in workflow
    assert "/health" in workflow
