import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent


def test_runtime_image_bundles_console_and_runtime_assets():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
    runtime_requirements = (PROJECT_ROOT / "requirements-runtime.txt").read_text(encoding="utf-8")
    frontend_package = json.loads(
        (PROJECT_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    frontend_npmrc = (PROJECT_ROOT / "frontend" / ".npmrc").read_text(encoding="utf-8")

    assert "FROM node:22-alpine@sha256:" in dockerfile
    assert "RUN npm install --global npm@10.9.8" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "COPY --from=frontend-builder /app/frontend/dist frontend/dist/" in dockerfile
    assert "COPY data/evaluation/ data/evaluation/" in dockerfile
    assert "COPY data/metadata/ data/metadata/" in dockerfile
    assert "--require-hashes -r requirements-runtime.txt" in dockerfile
    assert "pip uninstall --yes jaraco.context wheel setuptools pip" in dockerfile
    assert "!data/evaluation/**" in dockerignore
    assert "!data/metadata/**" in dockerignore
    assert "pymupdf==" in runtime_requirements.casefold()
    assert "zai-sdk==0.2.3" in runtime_requirements.casefold()
    assert "zhipuai==" not in runtime_requirements.casefold()
    assert "pyjwt==2.13.0" in runtime_requirements.casefold()
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
            if line.strip() and not line[0].isspace() and not line.lstrip().startswith(("#", "-"))
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
    assert tools.isascii(), "requirements-tools.txt must be readable by legacy Windows pip"
    assert tools.splitlines()[-1] == f"uv=={config['uv_version']}"
    assert {item["output"] for item in config["locks"]} == {
        "requirements-runtime.txt",
        "requirements-dev.txt",
        "requirements-parser.txt",
    }


def test_pdf_parser_dependencies_are_separate_and_locked():
    parser_input = (PROJECT_ROOT / "requirements-parser.in").read_text(encoding="utf-8")
    parser_lock = (PROJECT_ROOT / "requirements-parser.txt").read_text(encoding="utf-8")

    assert "-r requirements-runtime.in" in parser_input
    assert "magic-pdf[full]==1.3.12" in parser_input
    assert "magic-pdf==1.3.12" in parser_lock
    assert "pymupdf==1.28.2" not in parser_lock.casefold()
    assert not (PROJECT_ROOT / "requirements.txt").exists()


def test_compose_persists_runtime_data_and_uses_v1_backend():
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert compose.startswith("name: structural-spec-kb")
    assert "path: .env" in compose
    assert "required: false" in compose
    assert "./data:/app/data" in compose
    assert "DATA_DIR=/app/data" in compose
    assert "open-webui-data:/app/backend/data" in compose
    assert compose.count("image: structural-spec-kb:${STRUCTURAL_SPEC_KB_IMAGE_TAG:-local}") == 2
    assert compose.count("context: .") == 1
    assert "APP_UID: ${APP_UID:-1000}" in compose
    assert "APP_GID: ${APP_GID:-1000}" in compose
    assert "openwebui-preflight:" in compose
    assert 'command: ["python", "-m", "src.app.core.openwebui_probe"]' in compose
    assert "OPENAI_API_BASE_URLS: http://api:8000/v1" in compose
    assert "MIMO_MODEL: ${MIMO_MODEL:-mimo-v2.5}" in compose
    assert "OPENAI_API_KEYS: ${OPENWEBUI_API_KEY:-not-needed}" in compose
    assert 'ENABLE_PERSISTENT_CONFIG: "false"' in compose
    assert 'ENABLE_OLLAMA_API: "false"' in compose
    assert "condition: service_healthy" in compose
    assert "condition: service_completed_successfully" in compose


def test_repository_ci_covers_backend_frontend_and_container():
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "structural-spec-kb-ci.yml").read_text(
        encoding="utf-8"
    )

    assert "python -m pytest -q" in workflow
    assert "os: [ubuntu-latest, windows-latest]" in workflow
    assert "python scripts/lock_dependencies.py --check" in workflow
    assert "--require-hashes -r requirements-dev.txt" in workflow
    assert "Package portability (${{ matrix.source }} -> ${{ matrix.target }})" in workflow
    assert "actions/upload-artifact@" in workflow
    assert "actions/download-artifact@" in workflow
    assert "python scripts/validate_ci_actions.py" in workflow
    assert "python scripts/validate_container_images.py" in workflow
    assert "python scripts/validate_container_security.py" in workflow
    assert "python scripts/validate_docker_context.py" in workflow
    assert "--require-cross-platform" in workflow
    assert "python -m scripts.verify_runtime_package_cold_start" in workflow
    assert "python -m scripts.verify_runtime_package_recovery" in workflow
    assert "npm install --global npm@10.9.8" in workflow
    assert "python scripts/export_openapi.py" in workflow
    assert "npm run api:check" in workflow
    assert "npm test" in workflow
    assert "npm run typecheck" in workflow
    assert "npm run build" in workflow
    assert "--tag structural-spec-kb:ci" in workflow
    assert '--build-arg APP_UID="$(id -u)"' in workflow
    assert '--build-arg APP_GID="$(id -g)"' in workflow
    assert "OpenWebUI authenticated integration" in workflow
    assert "--tag structural-spec-kb:ci-openwebui" in workflow
    assert "python scripts/pull_compose_images.py" in workflow
    assert "--attempt-timeout 600" in workflow
    assert "--policy always" in workflow
    assert "docker compose up --no-build --pull never --detach open-webui" in workflow
    assert workflow.index("python scripts/pull_compose_images.py") < workflow.index(
        "docker compose up --no-build --pull never --detach open-webui"
    )
    assert "http://127.0.0.1:3000/api/v1/auths/signin" in workflow
    assert "Authorization: Bearer $OPENWEBUI_TOKEN" in workflow
    assert "http://127.0.0.1:3000/api/models" in workflow
    assert "ci-openwebui-connection-key" in workflow
    assert "/static/index.html" in workflow
    assert "/health" in workflow
    assert "aquasecurity/setup-trivy@3fb12ec12f41e471780db15c232d5dd185dcb514" in workflow
    assert "version: v0.73.0" in workflow
    assert "--format spdx-json" in workflow
    assert "container-vulnerabilities.json" in workflow
    assert "--severity HIGH,CRITICAL" in workflow
    assert "--ignorefile .trivyignore.yaml" in workflow
    assert "--exit-code 1" in workflow


def test_frontend_api_contract_generation_is_pinned_and_cross_platform():
    package = json.loads((PROJECT_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    checker = (PROJECT_ROOT / "frontend" / "scripts" / "check-api-contract.mjs").read_text(
        encoding="utf-8"
    )

    assert package["devDependencies"]["@hey-api/openapi-ts"] == "0.97.3"
    assert package["scripts"]["api:generate"] == "openapi-ts"
    assert package["scripts"]["api:check"] == "node scripts/check-api-contract.mjs"
    assert "process.execPath" in checker
    assert "@hey-api/openapi-ts/bin/run.js" in checker
    assert "['diff', '--exit-code', '--', ...contractPaths]" in checker
    assert "['ls-files', '--others', '--exclude-standard', '--', ...contractPaths]" in checker


def test_external_container_images_are_immutable_and_maintained():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dependabot = (REPOSITORY_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    drift_workflow = (
        REPOSITORY_ROOT / ".github" / "workflows" / "container-image-drift.yml"
    ).read_text(encoding="utf-8")

    assert dockerfile.startswith("# syntax=docker/dockerfile:1@sha256:")
    assert dockerfile.count("@sha256:") == 4
    assert dockerfile.count("FROM python:3.11-slim@sha256:") == 2
    assert "ghcr.io/open-webui/open-webui:v0.9.5@sha256:" in compose
    assert (PROJECT_ROOT / "scripts" / "validate_container_images.py").is_file()
    assert 'package-ecosystem: "docker"' in dependabot
    assert 'package-ecosystem: "docker-compose"' in dependabot
    assert 'directory: "/结构设计规范知识库"' in dependabot
    assert "schedule:" in drift_workflow
    assert "workflow_dispatch:" in drift_workflow
    assert "python scripts/validate_container_images.py --check-remote" in drift_workflow
    assert "python scripts/validate_container_security.py --check-remote" in drift_workflow
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in drift_workflow
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97" in drift_workflow


def test_container_security_policy_is_machine_readable():
    lock = json.loads(
        (PROJECT_ROOT / "security" / "container-security-lock.json").read_text(encoding="utf-8")
    )
    exceptions = json.loads((PROJECT_ROOT / ".trivyignore.yaml").read_text(encoding="utf-8"))

    assert lock["scanner"]["version"] == "v0.73.0"
    assert len(lock["scanner"]["linux_amd64_archive_sha256"]) == 64
    assert lock["policy"]["severities"] == ["HIGH", "CRITICAL"]
    assert lock["policy"]["ignore_unfixed"] is True
    assert exceptions == {"vulnerabilities": []}


def test_runtime_backup_cli_is_part_of_delivery_contract():
    pipeline_cli = (PROJECT_ROOT / "src" / "pipeline" / "__main__.py").read_text(encoding="utf-8")
    backup_module = PROJECT_ROOT / "src" / "pipeline" / "runtime_backup.py"

    assert backup_module.is_file()
    assert "create_runtime_backup" in pipeline_cli
    assert "validate_runtime_backup" in pipeline_cli
    assert "restore_runtime_backup" in pipeline_cli
    assert '"backup-create"' in pipeline_cli
    assert '"backup-validate"' in pipeline_cli
    assert '"backup-restore"' in pipeline_cli
