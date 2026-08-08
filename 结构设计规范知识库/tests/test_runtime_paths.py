import json
import os
import subprocess
import sys
from pathlib import Path

from src.pipeline.paths import PROJECT_ROOT, configured_project_path


def test_configured_project_path_resolves_default_relative_and_absolute(monkeypatch, tmp_path):
    monkeypatch.delenv("TEST_RUNTIME_PATH", raising=False)
    assert configured_project_path("TEST_RUNTIME_PATH", "data") == (PROJECT_ROOT / "data").resolve()

    monkeypatch.setenv("TEST_RUNTIME_PATH", "runtime-data")
    assert configured_project_path("TEST_RUNTIME_PATH", "ignored") == (PROJECT_ROOT / "runtime-data").resolve()

    absolute = tmp_path / "absolute-data"
    monkeypatch.setenv("TEST_RUNTIME_PATH", str(absolute))
    assert configured_project_path("TEST_RUNTIME_PATH", "ignored") == absolute.resolve()


def test_pipeline_path_constants_follow_data_dir_at_process_start(tmp_path):
    data_dir = tmp_path / "isolated-data"
    env = os.environ.copy()
    env["DATA_DIR"] = str(data_dir)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; "
                "from src.pipeline import paths; "
                "print(json.dumps({"
                "'data': str(paths.DATA_DIR), "
                "'active': str(paths.ACTIVE_DB_PATH), "
                "'jobs': str(paths.DATA_DIR / 'jobs'), "
                "'images': str(paths.IMAGES_DIR)"
                "}))"
            ),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "data": str(data_dir.resolve()),
        "active": str((data_dir / "active_db.json").resolve()),
        "jobs": str((data_dir / "jobs").resolve()),
        "images": str((data_dir / "images").resolve()),
    }


def test_pipeline_cli_initializes_with_configured_data_dir(tmp_path):
    env = os.environ.copy()
    env["DATA_DIR"] = str(tmp_path / "cli-data")
    result = subprocess.run(
        [sys.executable, "-m", "src.pipeline", "package-import", "--help"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--data-dir DATA_DIR" in result.stdout
