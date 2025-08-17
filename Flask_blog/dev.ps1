<#
  Dev launcher (diagnostic version)
  - Adds step logging with timestamps
  - Validates required tools (docker/python/npm)
  - Captures and reports first failure location
  - Keeps Chinese original messages but also short English keywords for clarity
  如果仍然退出 code=1, 请复制整段 [FAIL] / [TRACE] 输出反馈。
#>
param(
  [switch]$SkipFrontend,
  [switch]$SkipBackend,
  [int]$MySQLWaitSeconds = 60,
  [int]$MySQLPort = 3307
)
$ErrorActionPreference='Stop'
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

function Info($m){ Write-Host ("[INFO]  {0:HH:mm:ss}  {1}" -f (Get-Date), $m) -ForegroundColor Cyan }
function Warn($m){ Write-Host ("[WARN]  {0:HH:mm:ss}  {1}" -f (Get-Date), $m) -ForegroundColor Yellow }
function Fail($m){ Write-Host ("[FAIL]  {0:HH:mm:ss}  {1}" -f (Get-Date), $m) -ForegroundColor Red }
function Step($m){ Write-Host ("[STEP]  {0:HH:mm:ss}  {1}" -f (Get-Date), $m) -ForegroundColor Magenta }
function Check-Cmd($name){ if(-not (Get-Command $name -ErrorAction SilentlyContinue)){ Fail "缺少命令 / missing command: $name"; throw "Missing '$name'" } }

try {
  if(-not $MySQLPort -or $MySQLPort -le 0){ $MySQLPort = 3307 }
  Info "Debug MySQLPort value: $MySQLPort (type=$($MySQLPort.GetType().Name))"
  Step '初始化 / init'
  if(-not $SkipBackend){
    Step '后端依赖检查 / backend tool check'
    Check-Cmd docker
    Check-Cmd python
    Check-Cmd pip
    # npm 只在前端需要，这里可选
    if(-not $SkipFrontend){ Check-Cmd npm }

    Step 'Ensure containers'
    # MySQL
    $mysqlStatus = docker ps -a --format '{{.Names}}|{{.Status}}' | Where-Object { $_ -like 'blog-mysql|*' }
    if(-not $mysqlStatus){
      Info 'Starting MySQL (may pull image)'
      # Clean any lingering name
      if(docker ps -a --format '{{.Names}}' | Select-String -SimpleMatch 'blog-mysql'){
        Warn 'Removing stale blog-mysql container before start'
        docker rm -f blog-mysql | Out-Null
      }
  # Build port mapping directly with MySQLPort (avoid separate var issues)
  if(-not $MySQLPort -or $MySQLPort -le 0){ $MySQLPort = 3307 }
  $portMapString = ('{0}:3306' -f $MySQLPort)
  Info "MySQL port map: $portMapString"
  $dockerCmd = "docker run -d --name blog-mysql -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=blog -e MYSQL_USER=blog -e MYSQL_PASSWORD=blog -p $portMapString mysql:8.0"
  Info "Docker run about to execute (length=$($dockerCmd.Length))"
  Info "Docker cmd: $dockerCmd"
  iex $dockerCmd
  $exit=$LASTEXITCODE
  if($exit -ne 0){ throw "docker run mysql failed (exit=$exit)" }
    } else {
      if($mysqlStatus -notmatch 'Up '){
        Info 'MySQL container exists but not running -> docker start blog-mysql'
        docker start blog-mysql | Out-Null
      } else { Info 'Reusing running MySQL container' }
    }
    # Redis
    if(-not (docker ps --format '{{.Names}}' | Select-String -SimpleMatch 'blog-redis')){
      Info 'Starting Redis'
      if(docker ps -a --format '{{.Names}}' | Select-String -SimpleMatch 'blog-redis'){
        docker start blog-redis | Out-Null
      } else {
        docker run -d --name blog-redis -p 6379:6379 redis:7-alpine | Out-Null
      }
    } else { Info 'Reusing running Redis' }
    # MeiliSearch
    if(-not (docker ps --format '{{.Names}}' | Select-String -SimpleMatch 'blog-meili')){
      Info 'Starting MeiliSearch'
      if(docker ps -a --format '{{.Names}}' | Select-String -SimpleMatch 'blog-meili'){
        docker start blog-meili | Out-Null
      } else {
        docker run -d --name blog-meili -p 7700:7700 -e MEILI_NO_ANALYTICS=true getmeili/meilisearch:v1.7 | Out-Null
      }
    } else { Info 'Reusing running MeiliSearch' }

  Step 'Wait MySQL'
    $deadline = (Get-Date).AddSeconds($MySQLWaitSeconds)
    $ready=$false
    while((Get-Date) -lt $deadline){
      docker exec blog-mysql mysqladmin ping -uroot -proot --silent 2>$null
      if($LASTEXITCODE -eq 0){ $ready=$true; break }
      Start-Sleep 2
    }
    if(-not $ready){
      Warn 'MySQL not ready, tail last 80 log lines:'
      docker logs --tail 80 blog-mysql 2>$null | %{ Write-Host "[MYSQL] $_" }
      throw 'MySQL wait timeout'
    }
    Info 'MySQL ready, ensuring blog database & user'
    docker exec blog-mysql mysql -uroot -proot -e "CREATE DATABASE IF NOT EXISTS blog CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS 'blog'@'%' IDENTIFIED BY 'blog'; GRANT ALL PRIVILEGES ON blog.* TO 'blog'@'%'; FLUSH PRIVILEGES;" 2>$null
    # Verify blog user
    docker exec blog-mysql mysql -ublog -pblog -e "SELECT 1" 2>$null
    if($LASTEXITCODE -ne 0){ throw 'Blog user connection failed after setup' }

  Step 'Python venv'
    Set-Location "$ROOT/backend"
    if(-not (Test-Path .venv)){ Info '创建 venv'; python -m venv .venv }
    .\.venv\Scripts\Activate.ps1
    $pyVersion = (python -c "import sys;print(sys.version)")
    Info "Python: $pyVersion"

  Step 'Pip install backend deps'
    pip install -q -r requirements.txt

  Step 'Set env vars'
    $env:DATABASE_URL="mysql+pymysql://blog:blog@127.0.0.1:$MySQLPort/blog?charset=utf8mb4"
    $env:REDIS_URL='redis://127.0.0.1:6379/0'
    $env:MEILISEARCH_URL='http://127.0.0.1:7700'
    $env:JWT_SECRET_KEY='dev-secret'
    $env:UPLOAD_DIR=(Resolve-Path ..\uploads)
    $env:ALLOWED_IMAGE_TYPES='image/jpeg,image/png,image/webp'
    $env:MAX_IMAGE_SIZE='5242880'

  Step 'Run migrations'
    flask db upgrade

  Step 'Spawn backend'
    Start-Process powershell "-NoExit -Command Set-Location '$ROOT/backend'; .\.venv\Scripts\Activate.ps1; python run.py"
  }

  if(-not $SkipFrontend){
  Step 'Frontend deps'
    Set-Location "$ROOT/frontend"
    if(-not (Test-Path node_modules)){ Info '安装前端依赖 installing npm deps'; npm install }
    else { Info '复用已安装 node_modules' }

  Step 'Spawn frontend'
    Start-Process powershell "-NoExit -Command Set-Location '$ROOT/frontend'; npm run dev"
  }

  Step 'Done'
  Info "Backend http://localhost:5000  Frontend http://localhost:5173  Meili http://localhost:7700"
}
catch {
  Fail "脚本失败 / script failed: $($_.Exception.Message)"
  Write-Host '--- TRACE (stack) ---' -ForegroundColor DarkYellow
  Write-Host ($_.ScriptStackTrace)
  Write-Host '--- 结束 ---' -ForegroundColor DarkYellow
  exit 1
}
