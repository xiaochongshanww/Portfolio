# 本地后端启动脚本
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
    Write-Host "[backend] foreground start (Ctrl+C to stop) - http://127.0.0.1:5050" -ForegroundColor Cyan
    python run.py
    exit $LASTEXITCODE
}

# Detach:cmd /c start 包一层,输出统一进日志文件(避免 Start-Process
# 双重定向在部分 PowerShell 版本下抛错),PID 记录供 stop-backend.ps1 清理
$cmd = "/c cd /d `"$here`" && python run.py > instance\backend.log 2>&1"
$proc = Start-Process -FilePath "cmd.exe" -ArgumentList $cmd -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 1
# 记录真正的 python 子进程(而非 cmd 壳)
$py = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.ParentProcessId -eq $proc.Id } | Select-Object -First 1
$realPid = if ($py) { $py.ProcessId } else { $proc.Id }
Set-Content -Path "$here\instance\backend.pid" -Value $realPid
Write-Host "[backend] detached, PID=$realPid (log: instance/backend.log; stop: .\stop-backend.ps1)" -ForegroundColor Green
