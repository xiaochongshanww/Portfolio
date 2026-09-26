from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_local_service_stop_script_is_confirmation_gated_and_project_scoped():
    script = (PROJECT_ROOT / "scripts" / "stop_local_services.ps1").read_text(encoding="utf-8")

    assert 'SupportsShouldProcess = $true, ConfirmImpact = "High"' in script
    assert '@{\n    8000 = "api"\n    5173 = "vite"\n    5174 = "vite"\n    5175 = "vite"' in script
    assert "OrdinalIgnoreCase" in script
    assert ".venv\\Scripts\\python.exe" in script
    assert "frontend\\node_modules\\vite\\bin\\vite.js" in script
    assert '"node.exe"' in script
    assert "$normalizedCommandLine -match $viteArgumentPattern" in script
    assert "Get-CimInstance Win32_Process" in script
    assert '"orphan process, no listener"' in script
    assert '$PSCmdlet.ShouldProcess($target, "Stop the process tree")' in script
    assert "/PID $processId /T /F" in script
    assert "cannot be verified as this project's service; skipped" in script


def test_local_service_stop_script_does_not_kill_unconfigured_ports():
    script = (PROJECT_ROOT / "scripts" / "stop_local_services.ps1").read_text(encoding="utf-8")

    assert "if (-not $configuredPorts.ContainsKey($port))" in script
    assert "Port $port is not a configured project service port; skipped." in script
    assert "No matching project service processes found on the selected ports." in script
