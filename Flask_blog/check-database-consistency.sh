#!/bin/bash
# 数据库一致性检查脚本

echo "🔍 数据库结构一致性检查"
echo "=============================="

# 检查是否在Docker环境中
if docker-compose -f docker-compose.prod.yml ps db | grep -q "Up"; then
    echo "✅ 检测到Docker环境，使用容器内MySQL"
    DB_COMMAND="docker-compose -f docker-compose.prod.yml exec -T db mysql -u blog -pblog blog"
else
    echo "⚠️  未检测到Docker环境，请确保MySQL可访问"
    exit 1
fi

echo ""
echo "📊 检查 articles 表结构..."

# 检查 views_count 列是否存在
VIEWS_COUNT_EXISTS=$($DB_COMMAND -e "DESCRIBE articles;" 2>/dev/null | grep -c "views_count" || echo "0")

if [ "$VIEWS_COUNT_EXISTS" -gt 0 ]; then
    echo "✅ views_count 列存在"
    
    # 显示列详细信息
    echo "📋 views_count 列信息:"
    $DB_COMMAND -e "DESCRIBE articles;" 2>/dev/null | grep "views_count" | while read line; do
        echo "   $line"
    done
else
    echo "❌ views_count 列不存在"
    echo ""
    echo "🔧 修复建议:"
    echo "1. 运行数据库修复脚本: python fix-database-schema.py"
    echo "2. 或手动执行: ALTER TABLE articles ADD COLUMN views_count INT NOT NULL DEFAULT 0;"
fi

echo ""
echo "📊 检查相关索引..."

# 检查索引
INDEXES=$($DB_COMMAND -e "SHOW INDEX FROM articles WHERE Key_name LIKE '%views_count%';" 2>/dev/null | wc -l)
if [ "$INDEXES" -gt 1 ]; then  # 第一行是标题
    echo "✅ views_count 索引存在"
else
    echo "❌ views_count 索引不存在"
    echo "🔧 修复建议: CREATE INDEX ix_articles_views_count ON articles (views_count);"
fi

echo ""
echo "📊 检查性能优化索引..."

# 检查关键性能索引
PERFORMANCE_INDEXES=(
    "ix_articles_status_published_at"
    "ix_articles_author_published_at"
    "ix_articles_category_published_at"
)

for index in "${PERFORMANCE_INDEXES[@]}"; do
    EXISTS=$($DB_COMMAND -e "SHOW INDEX FROM articles WHERE Key_name='$index';" 2>/dev/null | wc -l)
    if [ "$EXISTS" -gt 1 ]; then
        echo "✅ $index 存在"
    else
        echo "❌ $index 不存在"
    fi
done

echo ""
echo "📊 数据库迁移历史..."
MIGRATION_COUNT=$($DB_COMMAND -e "SELECT COUNT(*) FROM alembic_version;" 2>/dev/null | tail -n 1)
CURRENT_VERSION=$($DB_COMMAND -e "SELECT version_num FROM alembic_version;" 2>/dev/null | tail -n 1)

echo "迁移记录数: $MIGRATION_COUNT"
echo "当前版本: $CURRENT_VERSION"

# 预期的最新版本（根据文件名判断）
LATEST_EXPECTED="0013_nullable_backup_id"
if [ "$CURRENT_VERSION" = "$LATEST_EXPECTED" ]; then
    echo "✅ 迁移版本正确"
else
    echo "⚠️  迁移版本可能不是最新: 期望 $LATEST_EXPECTED, 实际 $CURRENT_VERSION"
fi

echo ""
echo "📈 数据统计..."
ARTICLE_COUNT=$($DB_COMMAND -e "SELECT COUNT(*) FROM articles;" 2>/dev/null | tail -n 1)
echo "文章总数: $ARTICLE_COUNT"

if [ "$VIEWS_COUNT_EXISTS" -gt 0 ]; then
    ARTICLES_WITH_VIEWS=$($DB_COMMAND -e "SELECT COUNT(*) FROM articles WHERE views_count > 0;" 2>/dev/null | tail -n 1)
    echo "有浏览量的文章: $ARTICLES_WITH_VIEWS"
fi

echo ""
echo "=============================="
echo "🎯 检查完成"

if [ "$VIEWS_COUNT_EXISTS" -eq 0 ]; then
    echo ""
    echo "🚨 发现问题: views_count 列缺失"
    echo "💡 解决方案:"
    echo "   1. 运行修复脚本: python fix-database-schema.py"
    echo "   2. 重新运行迁移: flask db upgrade"
    echo "   3. 检查迁移日志确认无静默失败"
else
    echo "✅ 数据库结构看起来正常"
fi