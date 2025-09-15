# Flask Blog 开发环境停止脚本
param(
    [switch]$Clean = $false
)

Write-Host "🛑 停止Flask Blog开发环境..." -ForegroundColor Yellow

if ($Clean) {
    Write-Host "🧹 清理模式：将删除所有容器、网络和匿名卷" -ForegroundColor Red
    $confirm = Read-Host "确定要继续吗? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "❌ 操作已取消" -ForegroundColor Green
        exit 0
    }
}

# 停止服务
docker-compose -f docker-compose.dev.yml down

if ($Clean) {
    Write-Host "🧹 清理开发环境资源..." -ForegroundColor Yellow
    
    # 移除开发环境相关的镜像
    $images = docker images --filter "reference=flask-blog-*dev*" -q
    if ($images) {
        docker rmi $images
        Write-Host "✅ 已清理开发环境镜像" -ForegroundColor Green
    }
    
    # 清理未使用的卷
    docker volume prune -f
    Write-Host "✅ 已清理未使用的数据卷" -ForegroundColor Green
    
    # 清理未使用的网络
    docker network prune -f  
    Write-Host "✅ 已清理未使用的网络" -ForegroundColor Green
    
    Write-Host "🎉 开发环境已完全清理" -ForegroundColor Green
} else {
    Write-Host "✅ 开发环境已停止" -ForegroundColor Green
    Write-Host "💡 使用 ./dev-start.ps1 重新启动" -ForegroundColor Cyan
    Write-Host "💡 使用 ./dev-stop.ps1 -Clean 完全清理环境" -ForegroundColor Cyan
}