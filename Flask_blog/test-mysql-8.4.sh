#!/bin/bash
# MySQL 8.4 配置验证脚本

echo "🔍 测试MySQL 8.4配置..."

# 1. 启动服务
echo "1. 启动Docker Compose服务..."
docker-compose -f docker-compose.prod.yml up -d db

# 2. 等待MySQL启动
echo "2. 等待MySQL 8.4启动完成..."
timeout=120
counter=0

while [ $counter -lt $timeout ]; do
    if docker-compose -f docker-compose.prod.yml exec -T db mysqladmin ping -h 127.0.0.1 --silent; then
        echo "✅ MySQL 8.4启动成功！"
        break
    fi
    
    echo "⏳ 等待MySQL启动... ($counter/$timeout 秒)"
    sleep 2
    counter=$((counter + 2))
done

if [ $counter -ge $timeout ]; then
    echo "❌ MySQL启动超时，检查日志:"
    docker-compose -f docker-compose.prod.yml logs db
    exit 1
fi

# 3. 验证数据库功能
echo "3. 验证数据库基本功能..."

# 检查字符集
echo "📝 检查字符集配置..."
charset_result=$(docker-compose -f docker-compose.prod.yml exec -T db mysql -u root -proot -e "SHOW VARIABLES LIKE 'character_set_server';" 2>/dev/null | grep utf8mb4)
if [[ $charset_result == *"utf8mb4"* ]]; then
    echo "✅ 字符集配置正确: utf8mb4"
else
    echo "⚠️  字符集配置可能有问题"
fi

# 检查认证插件
echo "🔐 检查认证插件..."
auth_result=$(docker-compose -f docker-compose.prod.yml exec -T db mysql -u root -proot -e "SELECT plugin FROM mysql.user WHERE user='blog';" 2>/dev/null)
echo "认证插件状态: $auth_result"

# 4. 测试连接
echo "4. 测试应用数据库连接..."
if docker-compose -f docker-compose.prod.yml exec -T db mysql -u blog -pblog -e "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ 应用用户连接成功"
else
    echo "❌ 应用用户连接失败"
fi

# 5. 显示版本信息
echo "5. MySQL版本信息:"
docker-compose -f docker-compose.prod.yml exec -T db mysql -u root -proot -e "SELECT VERSION();" 2>/dev/null

echo "🎉 MySQL 8.4配置验证完成！"