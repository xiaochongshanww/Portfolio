#!/bin/bash
# 一键部署初始化脚本
# 用于确保外部元数据系统和备份系统正常工作

set -e

echo "🚀 开始一键部署初始化..."

# 1. 检查必要的目录
echo "📁 检查并创建必要目录..."
mkdir -p backend/backups/physical
mkdir -p backend/backups/snapshots
mkdir -p backend/metadata
mkdir -p backend/uploads_store

# 2. 设置正确的权限
echo "🔒 设置目录权限..."
chmod 755 backend/backups
chmod 755 backend/metadata
chmod 755 backend/uploads_store

# 3. 检查Docker环境
echo "🐳 检查Docker环境..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 4. 检查.env文件
if [ ! -f ".env" ]; then
    echo "📝 创建.env文件..."
    cp .env.example .env
    echo "⚠️  请编辑.env文件，配置必要的环境变量"
fi

# 5. 构建和启动服务
echo "🏗️  构建Docker镜像..."
docker-compose -f docker-compose.prod.yml build

echo "🚀 启动服务..."
docker-compose -f docker-compose.prod.yml up -d

# 6. 等待服务启动
echo "⏳ 等待服务启动完成..."
sleep 30

# 7. 检查服务状态
echo "🔍 检查服务状态..."
docker-compose -f docker-compose.prod.yml ps

# 8. 验证外部元数据系统
echo "✅ 验证外部元数据系统..."
if docker-compose -f docker-compose.prod.yml exec -T backend python -c "
from app import create_app
from app.backup.backup_records_external import get_external_metadata_manager
app = create_app()
with app.app_context():
    manager = get_external_metadata_manager()
    stats = manager.get_statistics()
    print(f'外部元数据系统正常运行，当前有 {stats[\"total_backup_records\"]} 条备份记录')
"; then
    echo "✅ 外部元数据系统验证成功"
else
    echo "⚠️  外部元数据系统验证失败，但可能是首次运行正常现象"
fi

echo "🎉 一键部署初始化完成！"
echo ""
echo "📋 接下来的步骤:"
echo "1. 检查.env文件配置是否正确"
echo "2. 访问 http://localhost 查看应用"
echo "3. 登录后台管理系统测试备份功能"
echo ""
echo "🔧 常用命令:"
echo "  查看日志: docker-compose -f docker-compose.prod.yml logs -f"
echo "  停止服务: docker-compose -f docker-compose.prod.yml down"
echo "  重启服务: docker-compose -f docker-compose.prod.yml restart"