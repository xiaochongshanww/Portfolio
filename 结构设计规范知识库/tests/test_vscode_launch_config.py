import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_vite_debug_launch_tracks_the_server_process_and_uses_fixed_port():
    launch = json.loads((PROJECT_ROOT / ".vscode" / "launch.json").read_text(encoding="utf-8"))
    vite = next(item for item in launch["configurations"] if item["name"] == "前端：Vite")

    assert vite["type"] == "node"
    assert vite["request"] == "launch"
    assert vite["program"] == "${workspaceFolder}/frontend/node_modules/vite/bin/vite.js"
    assert vite["cwd"] == "${workspaceFolder}/frontend"
    assert vite["args"] == ["--host", "127.0.0.1", "--port", "5173", "--strictPort"]

    full_stack = next(item for item in launch["compounds"] if item["name"] == "全栈：API + 前端")
    assert full_stack["stopAll"] is True
    assert "前端：Vite" in full_stack["configurations"]
