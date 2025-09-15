# 开发环境调试助手脚本
param(
    [string]$Action = "status",
    [string]$Service = "all"
)

function Show-Help {
    Write-Host "🛠️  Flask Blog 开发环境调试工具" -ForegroundColor Green
    Write-Host ""
    Write-Host "用法: ./dev-debug.ps1 [动作] [服务]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "动作 (Action):" -ForegroundColor Yellow
    Write-Host "  status   - 查看服务状态 (默认)" -ForegroundColor White
    Write-Host "  logs     - 查看服务日志" -ForegroundColor White
    Write-Host "  restart  - 重启服务" -ForegroundColor White
    Write-Host "  shell    - 进入服务容器" -ForegroundColor White
    Write-Host "  build    - 重新构建服务" -ForegroundColor White
    Write-Host "  db       - 数据库操作" -ForegroundColor White
    Write-Host ""
    Write-Host "服务 (Service):" -ForegroundColor Yellow
    Write-Host "  all       - 所有服务 (默认)" -ForegroundColor White
    Write-Host "  backend   - 后端服务" -ForegroundColor White  
    Write-Host "  frontend  - 前端服务" -ForegroundColor White
    Write-Host "  db        - MySQL数据库" -ForegroundColor White
    Write-Host "  redis     - Redis缓存" -ForegroundColor White
    Write-Host "  meili     - Meilisearch搜索" -ForegroundColor White
    Write-Host ""
    Write-Host "示例:" -ForegroundColor Cyan
    Write-Host "  ./dev-debug.ps1 logs backend     # 查看后端日志" -ForegroundColor White
    Write-Host "  ./dev-debug.ps1 restart frontend # 重启前端服务" -ForegroundColor White
    Write-Host "  ./dev-debug.ps1 shell backend    # 进入后端容器" -ForegroundColor White
}

$ComposeFile = "docker-compose.dev.yml"

switch ($Action.ToLower()) {
    "help" { Show-Help; exit 0 }
    "h" { Show-Help; exit 0 }
    "--help" { Show-Help; exit 0 }
    
    "status" {
        Write-Host "📊 开发环境服务状态" -ForegroundColor Green
        docker-compose -f $ComposeFile ps
        
        Write-Host "`n🌐 服务健康检查:" -ForegroundColor Cyan
        $services = @(
            @{Name="后端API"; URL="http://localhost:8000/api/v1/health"},
            @{Name="前端应用"; URL="http://localhost:3000"},
            @{Name="Meilisearch"; URL="http://localhost:7700/health"}
        )
        
        foreach ($service in $services) {
            try {
                $response = Invoke-WebRequest -Uri $service.URL -UseBasicParsing -TimeoutSec 3
                Write-Host "  ✅ $($service.Name): 正常运行" -ForegroundColor Green
            } catch {
                Write-Host "  ❌ $($service.Name): 无法访问" -ForegroundColor Red
            }
        }
    }
    
    "logs" {
        Write-Host "📋 查看服务日志: $Service" -ForegroundColor Green
        if ($Service -eq "all") {
            docker-compose -f $ComposeFile logs -f
        } else {
            docker-compose -f $ComposeFile logs -f $Service
        }
    }
    
    "restart" {
        Write-Host "🔄 重启服务: $Service" -ForegroundColor Green
        if ($Service -eq "all") {
            docker-compose -f $ComposeFile restart
        } else {
            docker-compose -f $ComposeFile restart $Service
        }
        Write-Host "✅ 服务重启完成" -ForegroundColor Green
    }
    
    "shell" {
        if ($Service -eq "all") {
            Write-Host "❌ 请指定具体服务名称" -ForegroundColor Red
            exit 1
        }
        Write-Host "🐚 进入 $Service 容器..." -ForegroundColor Green
        docker-compose -f $ComposeFile exec $Service /bin/bash
    }
    
    "build" {
        Write-Host "🏗️  重新构建服务: $Service" -ForegroundColor Green
        if ($Service -eq "all") {
            docker-compose -f $ComposeFile up -d --build
        } else {
            docker-compose -f $ComposeFile up -d --build $Service
        }
        Write-Host "✅ 构建完成" -ForegroundColor Green
    }
    
    "db" {
        Write-Host "🗃️  数据库工具" -ForegroundColor Green
        Write-Host "1. 连接MySQL" -ForegroundColor Yellow
        Write-Host "2. 执行数据库迁移" -ForegroundColor Yellow
        Write-Host "3. 重置数据库" -ForegroundColor Yellow
        $choice = Read-Host "请选择 (1-3)"
        
        switch ($choice) {
            "1" {
                docker-compose -f $ComposeFile exec db mysql -u blog -p blog
            }
            "2" {
                docker-compose -f $ComposeFile exec backend flask db upgrade
            }
            "3" {
                $confirm = Read-Host "⚠️  确定要重置数据库吗? 这将删除所有数据! (y/N)"
                if ($confirm -eq "y" -or $confirm -eq "Y") {
                    docker-compose -f $ComposeFile exec backend flask db downgrade
                    docker-compose -f $ComposeFile exec backend flask db upgrade
                    Write-Host "✅ 数据库已重置" -ForegroundColor Green
                }
            }
        }
    }
    
    default {
        Write-Host "❌ 未知动作: $Action" -ForegroundColor Red
        Show-Help
        exit 1
    }
}