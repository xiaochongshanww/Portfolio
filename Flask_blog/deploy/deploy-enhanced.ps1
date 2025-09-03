# Flask Blog 增强版一键部署脚本
# 支持多种部署模式和完整的验证流程

Param(
    [string]$ComposeFile = "docker-compose.prod.yml",
    [string]$Mode = "standard", # standard, performance, monitoring
    [switch]$Rebuild,
    [switch]$Pull,
    [switch]$SkipTests,
    [switch]$EnableSSL,
    [switch]$BackupFirst,
    [string]$BaseUrl = "http://localhost",
    [int]$Timeout = 60
)

# 颜色输出函数
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    
    switch ($Color) {
        "Red" { Write-Host $Message -ForegroundColor Red }
        "Green" { Write-Host $Message -ForegroundColor Green }
        "Yellow" { Write-Host $Message -ForegroundColor Yellow }
        "Blue" { Write-Host $Message -ForegroundColor Blue }
        "Cyan" { Write-Host $Message -ForegroundColor Cyan }
        default { Write-Host $Message }
    }
}

function Write-Step {
    param([string]$Message)
    Write-ColorOutput "🔄 $Message" "Cyan"
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "✅ $Message" "Green"
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "⚠️  $Message" "Yellow"
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "❌ $Message" "Red"
}

# 检查先决条件
function Test-Prerequisites {
    Write-Step "检查部署先决条件..."
    
    $missingTools = @()
    
    # 检查Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        $missingTools += "Docker"
    }
    
    # 检查Docker Compose
    if (-not (docker compose version 2>$null)) {
        $missingTools += "Docker Compose"
    }
    
    # 检查curl (用于测试)
    if (-not (Get-Command curl -ErrorAction SilentlyContinue)) {
        $missingTools += "curl"
    }
    
    if ($missingTools.Count -gt 0) {
        Write-Error "缺少必需工具: $($missingTools -join ', ')"
        Write-Host "请先安装这些工具再继续部署"
        exit 1
    }
    
    Write-Success "先决条件检查通过"
}

# 检查环境变量配置
function Test-EnvironmentConfig {
    Write-Step "检查环境配置..."
    
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Write-Warning "未找到 .env 文件，从示例文件创建..."
            Copy-Item ".env.example" ".env"
            Write-Warning "⚠️  请编辑 .env 文件，更新所有 'CHANGE-ME-*' 占位符"
            Write-Host "按任意键继续..." -ForegroundColor Yellow
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        } else {
            Write-Error "未找到 .env 或 .env.example 文件"
            exit 1
        }
    }
    
    # 检查敏感配置是否更新
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "CHANGE-ME-") {
        Write-Warning "⚠️  检测到未更新的配置占位符"
        Write-Host "建议更新以下配置项:" -ForegroundColor Yellow
        $envContent | Select-String "CHANGE-ME-" | ForEach-Object {
            Write-Host "  - $($_.Line)" -ForegroundColor Yellow
        }
        Write-Host "按任意键继续..." -ForegroundColor Yellow
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
    
    Write-Success "环境配置检查完成"
}

# 创建备份
function Invoke-PreDeploymentBackup {
    if (-not $BackupFirst) { return }
    
    Write-Step "创建部署前备份..."
    
    try {
        if (docker ps --format "table {{.Names}}" | Select-String "blog_backend") {
            Write-Host "执行数据库备份..." -ForegroundColor Blue
            docker compose -f $ComposeFile exec -T backend bash -c "cd /app && chmod +x scripts/backup.sh && ./scripts/backup.sh"
            Write-Success "备份完成"
        } else {
            Write-Warning "后端容器未运行，跳过备份"
        }
    } catch {
        Write-Warning "备份过程中出现错误: $($_.Exception.Message)"
        Write-Host "继续部署? (y/N): " -NoNewline -ForegroundColor Yellow
        $response = Read-Host
        if ($response -ne "y" -and $response -ne "Y") {
            exit 1
        }
    }
}

# 构建部署命令
function Get-DeployCommand {
    $composeFiles = @($ComposeFile)
    
    switch ($Mode.ToLower()) {
        "performance" {
            $composeFiles += "deploy/docker-compose.performance.yml"
            Write-Host "启用性能优化模式" -ForegroundColor Blue
        }
        "monitoring" {
            $composeFiles += "deploy/docker-compose.monitoring.yml"
            Write-Host "启用监控模式" -ForegroundColor Blue
        }
        "full" {
            $composeFiles += "deploy/docker-compose.performance.yml"
            $composeFiles += "deploy/docker-compose.monitoring.yml"
            Write-Host "启用完整模式 (性能优化 + 监控)" -ForegroundColor Blue
        }
    }
    
    $composeArgs = $composeFiles | ForEach-Object { "-f", $_ }
    return $composeArgs
}

# 执行部署
function Invoke-Deployment {
    Write-Step "开始部署流程..."
    
    $composeArgs = Get-DeployCommand
    
    # 拉取镜像
    if ($Pull) {
        Write-Host "拉取基础镜像..." -ForegroundColor Blue
        docker compose @composeArgs pull
    }
    
    # 构建参数
    $buildArgs = @("up", "-d")
    if ($Rebuild) {
        $buildArgs += "--build", "--force-recreate"
        Write-Host "强制重建镜像..." -ForegroundColor Blue
    } else {
        $buildArgs += "--build"
    }
    
    # 执行部署
    Write-Host "启动服务..." -ForegroundColor Blue
    docker compose @composeArgs @buildArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "部署失败"
        exit 1
    }
    
    Write-Success "服务启动完成"
}

# 等待服务就绪
function Wait-ForServices {
    Write-Step "等待服务就绪..."
    
    $maxRetries = $Timeout
    $retries = 0
    $services = @{
        "Backend" = "$BaseUrl/api/v1/health"
        "Frontend" = "$BaseUrl/"
    }
    
    foreach ($service in $services.GetEnumerator()) {
        $retries = 0
        Write-Host "等待 $($service.Key) 服务..." -ForegroundColor Blue
        
        do {
            try {
                $response = Invoke-WebRequest -Uri $service.Value -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
                if ($response.StatusCode -eq 200) {
                    Write-Success "$($service.Key) 服务已就绪"
                    break
                }
            } catch {
                # 忽略错误，继续重试
            }
            
            Start-Sleep -Seconds 2
            $retries++
            
            if ($retries % 10 -eq 0) {
                Write-Host "仍在等待 $($service.Key) 服务 ($retries/$maxRetries)..." -ForegroundColor Yellow
            }
            
        } while ($retries -lt $maxRetries)
        
        if ($retries -ge $maxRetries) {
            Write-Warning "$($service.Key) 服务未能及时就绪"
        }
    }
}

# 运行部署测试
function Invoke-DeploymentTests {
    if ($SkipTests) {
        Write-Warning "跳过部署测试"
        return
    }
    
    Write-Step "运行部署验证测试..."
    
    # 检查测试脚本是否存在
    if (-not (Test-Path "scripts/deploy-test.sh")) {
        Write-Warning "未找到测试脚本，跳过自动测试"
        return
    }
    
    try {
        # 在WSL或Git Bash中运行测试脚本
        $env:BASE_URL = $BaseUrl
        $env:TIMEOUT = $Timeout
        
        if (Get-Command wsl -ErrorAction SilentlyContinue) {
            Write-Host "使用WSL运行测试..." -ForegroundColor Blue
            wsl bash scripts/deploy-test.sh
        } elseif (Get-Command bash -ErrorAction SilentlyContinue) {
            Write-Host "使用Git Bash运行测试..." -ForegroundColor Blue
            bash scripts/deploy-test.sh
        } else {
            Write-Warning "无法运行bash测试脚本，进行基础HTTP测试..."
            Test-BasicEndpoints
        }
    } catch {
        Write-Warning "测试脚本执行出错: $($_.Exception.Message)"
        Test-BasicEndpoints
    }
}

# 基础端点测试
function Test-BasicEndpoints {
    Write-Host "执行基础端点测试..." -ForegroundColor Blue
    
    $endpoints = @{
        "首页" = "$BaseUrl/"
        "健康检查" = "$BaseUrl/api/v1/health"
        "OpenAPI文档" = "$BaseUrl/api/v1/openapi.json"
    }
    
    $passed = 0
    $total = $endpoints.Count
    
    foreach ($endpoint in $endpoints.GetEnumerator()) {
        try {
            $response = Invoke-WebRequest -Uri $endpoint.Value -UseBasicParsing -TimeoutSec 10
            if ($response.StatusCode -eq 200) {
                Write-Success "✓ $($endpoint.Key)"
                $passed++
            } else {
                Write-Warning "✗ $($endpoint.Key) - 状态码: $($response.StatusCode)"
            }
        } catch {
            Write-Warning "✗ $($endpoint.Key) - 错误: $($_.Exception.Message)"
        }
    }
    
    Write-Host "基础测试结果: $passed/$total 通过" -ForegroundColor Blue
}

# 显示部署信息
function Show-DeploymentSummary {
    Write-Step "部署总结"
    
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "🎉 Flask Blog 部署完成!" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "访问地址:" -ForegroundColor White
    Write-Host "  前端: $BaseUrl" -ForegroundColor Green
    Write-Host "  后端API: $BaseUrl/api/v1" -ForegroundColor Green
    Write-Host "  健康检查: $BaseUrl/api/v1/health" -ForegroundColor Green
    Write-Host "  API文档: $BaseUrl/api/v1/openapi.json" -ForegroundColor Green
    
    if ($Mode -eq "monitoring" -or $Mode -eq "full") {
        Write-Host "监控服务:" -ForegroundColor White
        Write-Host "  Grafana: http://localhost:3000 (admin/admin123)" -ForegroundColor Blue
        Write-Host "  Prometheus: http://localhost:9090" -ForegroundColor Blue
        Write-Host "  AlertManager: http://localhost:9093" -ForegroundColor Blue
    }
    
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "常用命令:" -ForegroundColor White
    Write-Host "  查看日志: docker compose -f $ComposeFile logs -f" -ForegroundColor Yellow
    Write-Host "  停止服务: docker compose -f $ComposeFile down" -ForegroundColor Yellow
    Write-Host "  重启后端: docker compose -f $ComposeFile restart backend" -ForegroundColor Yellow
    Write-Host "================================" -ForegroundColor Cyan
}

# 错误处理
function Handle-DeploymentError {
    param($ErrorMessage)
    
    Write-Error "部署失败: $ErrorMessage"
    Write-Host "故障排除建议:" -ForegroundColor Yellow
    Write-Host "1. 检查Docker服务是否运行" -ForegroundColor White
    Write-Host "2. 验证.env文件配置" -ForegroundColor White
    Write-Host "3. 查看容器日志: docker compose logs" -ForegroundColor White
    Write-Host "4. 检查端口占用: netstat -an | findstr :80" -ForegroundColor White
    
    exit 1
}

# 主执行流程
function Main {
    try {
        Write-ColorOutput "== Flask Blog 增强版一键部署 ==" "Cyan"
        Write-Host "部署模式: $Mode" -ForegroundColor Blue
        Write-Host "目标地址: $BaseUrl" -ForegroundColor Blue
        Write-Host ""
        
        # 1. 检查先决条件
        Test-Prerequisites
        
        # 2. 检查环境配置
        Test-EnvironmentConfig
        
        # 3. 预部署备份
        Invoke-PreDeploymentBackup
        
        # 4. 执行部署
        Invoke-Deployment
        
        # 5. 等待服务就绪
        Wait-ForServices
        
        # 6. 运行验证测试
        Invoke-DeploymentTests
        
        # 7. 显示部署总结
        Show-DeploymentSummary
        
    } catch {
        Handle-DeploymentError $_.Exception.Message
    }
}

# 显示帮助信息
if ($args -contains "-h" -or $args -contains "--help") {
    Write-Host @"
Flask Blog 增强版一键部署脚本

用法:
  .\deploy\deploy-enhanced.ps1 [选项]

选项:
  -Mode <模式>           部署模式: standard(默认), performance, monitoring, full
  -ComposeFile <文件>    Docker Compose文件 (默认: docker-compose.prod.yml)
  -Rebuild              强制重建镜像
  -Pull                 预拉取基础镜像
  -SkipTests            跳过部署验证测试
  -EnableSSL            启用SSL支持 (需要配置证书)
  -BackupFirst          部署前创建备份
  -BaseUrl <URL>        基础URL (默认: http://localhost)
  -Timeout <秒数>       服务启动超时时间 (默认: 60)

示例:
  .\deploy\deploy-enhanced.ps1                              # 标准部署
  .\deploy\deploy-enhanced.ps1 -Mode performance -Rebuild  # 性能优化模式重建
  .\deploy\deploy-enhanced.ps1 -Mode monitoring            # 启用监控
  .\deploy\deploy-enhanced.ps1 -Mode full -BackupFirst     # 完整模式，预先备份
"@
    exit 0
}

# 执行主函数
Main