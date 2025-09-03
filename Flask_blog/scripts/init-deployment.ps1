# 一键部署初始化脚本 (Windows PowerShell版本)
# 用于确保外部元数据系统和备份系统正常工作

param(
    [switch]$SkipBuild,
    [switch]$Force
)

Write-Host "🚀 开始一键部署初始化..." -ForegroundColor Green

# 1. 检查必要的目录
Write-Host "📁 检查并创建必要目录..." -ForegroundColor Yellow
$directories = @(
    "backend\backups\physical",
    "backend\backups\snapshots", 
    "backend\metadata",
    "backend\uploads_store"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  ✓ 创建目录: $dir" -ForegroundColor Green
    } else {
        Write-Host "  ✓ 目录已存在: $dir" -ForegroundColor Green
    }
}

# 2. 检查Docker环境
Write-Host "🐳 检查Docker环境..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "  ✓ Docker已安装: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Docker未安装，请先安装Docker Desktop" -ForegroundColor Red
    exit 1
}

try {
    $composeVersion = docker-compose --version
    Write-Host "  ✓ Docker Compose已安装: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Docker Compose未安装" -ForegroundColor Red
    exit 1
}

# 3. 检查.env文件
if (!(Test-Path ".env")) {
    Write-Host "📝 创建.env文件..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "  ⚠️  请编辑.env文件，配置必要的环境变量" -ForegroundColor Yellow
}

# 4. 构建和启动服务
if (!$SkipBuild) {
    Write-Host "🏗️  构建Docker镜像..." -ForegroundColor Yellow
    docker-compose -f docker-compose.prod.yml build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ❌ Docker镜像构建失败" -ForegroundColor Red
        exit 1
    }
}

Write-Host "🚀 启动服务..." -ForegroundColor Yellow
docker-compose -f docker-compose.prod.yml up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ 服务启动失败" -ForegroundColor Red
    exit 1
}

# 5. 等待服务启动
Write-Host "⏳ 等待服务启动完成..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# 6. 检查服务状态
Write-Host "🔍 检查服务状态..." -ForegroundColor Yellow
docker-compose -f docker-compose.prod.yml ps

# 7. 验证外部元数据系统
Write-Host "✅ 验证外部元数据系统..." -ForegroundColor Yellow
$verificationScript = @"
from app import create_app
from app.backup.backup_records_external import get_external_metadata_manager
try:
    app = create_app()
    with app.app_context():
        manager = get_external_metadata_manager()
        stats = manager.get_statistics()
        print(f'外部元数据系统正常运行，当前有 {stats["total_backup_records"]} 条备份记录')
except Exception as e:
    print(f'外部元数据系统验证出错: {e}')
"@

try {
    $result = docker-compose -f docker-compose.prod.yml exec -T backend python -c $verificationScript
    Write-Host "  ✅ 外部元数据系统验证成功" -ForegroundColor Green
    Write-Host "  $result" -ForegroundColor Cyan
} catch {
    Write-Host "  ⚠️  外部元数据系统验证失败，但可能是首次运行正常现象" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 一键部署初始化完成！" -ForegroundColor Green
Write-Host ""
Write-Host "📋 接下来的步骤:" -ForegroundColor Cyan
Write-Host "1. 检查.env文件配置是否正确"
Write-Host "2. 访问 http://localhost 查看应用"
Write-Host "3. 登录后台管理系统测试备份功能"
Write-Host ""
Write-Host "🔧 常用命令:" -ForegroundColor Cyan
Write-Host "  查看日志: docker-compose -f docker-compose.prod.yml logs -f"
Write-Host "  停止服务: docker-compose -f docker-compose.prod.yml down"
Write-Host "  重启服务: docker-compose -f docker-compose.prod.yml restart"