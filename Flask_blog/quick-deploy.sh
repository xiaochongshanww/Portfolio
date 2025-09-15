#!/bin/bash
# 真正的一键部署脚本 - 使用预构建镜像

set -e

echo "🚀 Flask Blog 快速部署 (预构建镜像版本)"
echo "========================================"

# 配置检查
COMPOSE_FILE="docker-compose.prebuilt.yml"
ENV_FILE=".env"

# 1. 环境检查
echo "🔍 检查部署环境..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 2. 环境配置检查
if [ ! -f "$ENV_FILE" ]; then
    echo "📝 创建环境配置文件..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️  请编辑 .env 文件，配置数据库密码等敏感信息"
        echo "❓ 是否现在就编辑? (y/N): "
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        fi
    else
        echo "❌ 未找到 .env.example 文件"
        exit 1
    fi
fi

# 3. 拉取最新镜像
echo "📦 拉取预构建镜像..."
if docker-compose -f $COMPOSE_FILE pull; then
    echo "✅ 镜像拉取成功"
else
    echo "⚠️  镜像拉取失败，可能需要配置GHCR访问权限"
    echo "💡 解决方案："  
    echo "   1. 确保镜像已设置为公开 (参考 GHCR-SETUP.md)"
    echo "   2. 或登录GitHub: docker login ghcr.io"
    echo "💡 是否继续使用本地构建? (y/N): "
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        COMPOSE_FILE="docker-compose.prod.yml"
        echo "🔄 切换到本地构建模式..."
    else
        exit 1
    fi
fi

# 4. 启动服务
echo "🚀 启动服务..."
docker-compose -f $COMPOSE_FILE up -d

# 5. 等待服务就绪
echo "⏳ 等待服务启动..."
sleep 30

# 6. 健康检查
echo "🏥 检查服务状态..."
if curl -f http://localhost/api/v1/health &> /dev/null; then
    echo "✅ 服务启动成功!"
    echo ""
    echo "🎉 部署完成!"
    echo "📱 访问地址: http://localhost"
    echo "🔧 管理命令:"
    echo "   查看日志: docker-compose -f $COMPOSE_FILE logs -f"
    echo "   停止服务: docker-compose -f $COMPOSE_FILE down"
    echo "   重启服务: docker-compose -f $COMPOSE_FILE restart"
else
    echo "⚠️  服务可能未完全启动，请检查日志:"
    echo "   docker-compose -f $COMPOSE_FILE logs"
fi

echo ""
echo "📊 当前服务状态:"
docker-compose -f $COMPOSE_FILE ps