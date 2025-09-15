# Flask Blog 开发环境一键启动脚本
Write-Host "🚀 启动Flask Blog开发环境..." -ForegroundColor Green

# 检查Docker是否运行
try {
    docker ps > $null
    Write-Host "✅ Docker正在运行" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker未运行，请先启动Docker Desktop" -ForegroundColor Red
    exit 1
}

# 检查环境文件
if (!(Test-Path ".env.dev")) {
    Write-Host "📝 创建开发环境配置文件..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env.dev" -Force
    Write-Host "⚠️  请检查 .env.dev 文件中的配置" -ForegroundColor Yellow
}

# 启动所有服务
Write-Host "🔄 启动开发环境容器..." -ForegroundColor Blue
docker-compose -f docker-compose.dev.yml up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 开发环境启动成功!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 服务访问地址:" -ForegroundColor Cyan
    Write-Host "   前端: http://localhost:3000" -ForegroundColor White
    Write-Host "   后端: http://localhost:8000" -ForegroundColor White
    Write-Host "   API文档: http://localhost:8000/api/v1/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "🔍 数据库连接:" -ForegroundColor Cyan
    Write-Host "   MySQL: localhost:3306" -ForegroundColor White
    Write-Host "   Redis: localhost:6379" -ForegroundColor White
    Write-Host "   Meilisearch: http://localhost:7700" -ForegroundColor White
    Write-Host ""
    Write-Host "🛠️  开发工具:" -ForegroundColor Cyan
    Write-Host "   查看日志: docker-compose -f docker-compose.dev.yml logs -f" -ForegroundColor White
    Write-Host "   重启服务: docker-compose -f docker-compose.dev.yml restart" -ForegroundColor White
    Write-Host "   停止服务: docker-compose -f docker-compose.dev.yml down" -ForegroundColor White
    Write-Host ""
    Write-Host "🐛 VS Code调试:" -ForegroundColor Cyan
    Write-Host "   1. 按F5或Ctrl+Shift+P" -ForegroundColor White
    Write-Host "   2. 选择 '🐳 Full Stack: Docker Development'" -ForegroundColor White
    Write-Host "   3. 在backend代码中设置断点即可调试" -ForegroundColor White
    
    # 等待服务就绪
    Write-Host ""
    Write-Host "⏳ 等待服务启动完成..." -ForegroundColor Yellow
    Start-Sleep 10
    
    # 健康检查
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ 后端服务就绪!" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️  后端服务可能还在启动中，请稍后再试" -ForegroundColor Yellow
    }
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ 前端服务就绪!" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️  前端服务可能还在启动中，请稍后再试" -ForegroundColor Yellow
    }
    
} else {
    Write-Host "❌ 开发环境启动失败" -ForegroundColor Red
    Write-Host "💡 请检查Docker日志: docker-compose -f docker-compose.dev.yml logs" -ForegroundColor Yellow
}