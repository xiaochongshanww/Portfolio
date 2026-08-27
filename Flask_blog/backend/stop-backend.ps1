# 本地后端停止脚本:按 start-backend.ps1 记录的 PID 精确清理;
# 无 pid 文件时按命令行匹配 run.py 并连子进程(reloader)一起杀。
$ErrorActionPreference = "SilentlyContinue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $here "instance\backend.pid"

$killed = 0

if (Test-Path $pidFile) {
    $target = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($target) {
        taskkill /F /PID $target /T | Out-Null
        Write-Host "[backend] stopped PID $target (tree)" -ForegroundColor Green
        $killed++
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# 兜底:清掉所有 run.py 残留(含 reloader 子进程)
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'run\.py' } |
    ForEach-Object {
        taskkill /F /PID $_.ProcessId /T | Out-Null
        Write-Host "[backend] killed leftover $($_.ProcessId)" -ForegroundColor Yellow
        $killed++
    }

if ($killed -eq 0) { Write-Host "[backend] nothing to stop" }
exit 0
