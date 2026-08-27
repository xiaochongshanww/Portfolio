# 本地后端启动脚本:前台运行(推荐)
# 用法: .\start-backend.ps1           前台启动(Ctrl+C 即完整退出)
#       .\start-backend.ps1 -Detach  后台启动,PID 写入 instance/backend.pid
#       .\stop-backend.ps1           配对停止
param(
    [switch]$Detach
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

$env:DATABASE_URL = $env:DATABASE_URL ?? "sqlite:///$here/instance/dev.db"

if (-not $Detach) {
    Write-Host "[backend] foreground start (Ctrl+C to stop) - http://127.0.0.1:5000" -ForegroundColor Cyan
    python run.py
    exit $LASTEXITCODE
}

# Detach:记录 PID,供 stop-backend.ps1 精确清理
$proc = Start-Process -FilePath "python" -ArgumentList "run.py" `
    -WorkingDirectory $here -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput "$here\instance\backend.log" `
    -RedirectStandardError "$here\instance\backend.err.log"
Set-Content -Path "$here\instance\backend.pid" -Value $proc.Id
Write-Host "[backend] detached, PID=$($proc.Id) (log: instance/backend.log; stop: .\stop-backend.ps1)" -ForegroundColor Green
