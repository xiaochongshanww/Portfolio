Param(
  [string]$ComposeFile = "docker-compose.prod.yml",
  [switch]$Rebuild,
  [switch]$Pull
)

Write-Host "== Flask Blog 一键部署 ==" -ForegroundColor Cyan
if ($Pull) { docker compose -f $ComposeFile pull }
if ($Rebuild) { docker compose -f $ComposeFile build --no-cache }

docker compose -f $ComposeFile up -d --build

Write-Host "等待后端健康检查..." -ForegroundColor Yellow
$tries=0
while ($tries -lt 30) {
  try {
    $resp = Invoke-WebRequest -Uri http://localhost/api/v1/health -UseBasicParsing -TimeoutSec 3
    if ($resp.StatusCode -eq 200) { Write-Host "后端已就绪" -ForegroundColor Green; break }
  } catch {}
  Start-Sleep -Seconds 2
  $tries++
}

if ($tries -ge 30) { Write-Warning "后端健康检查超时 (可手动查看日志: docker compose logs backend)" }

Write-Host "访问: http://localhost" -ForegroundColor Cyan
