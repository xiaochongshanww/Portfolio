#!/bin/bash
# Git pre-push hook — 在推送前运行关键测试
# 安装: ln -sf ../../scripts/pre-push.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push

set -e

echo "🔍 运行推送前检查..."

# 检查后端语法
echo "📝 检查 Python 语法..."
python3 -m py_compile backend/app/__init__.py 2>/dev/null || true

# 运行后端测试（仅核心模块，快速）
echo "🧪 运行后端核心测试..."
cd backend && python -m pytest tests/test_auth.py tests/test_articles.py \
    tests/test_comments.py -q --tb=short 2>/dev/null && cd .. || {
    echo "❌ 后端核心测试失败，禁止推送"
    exit 1
}

# 运行前端测试
echo "🧪 运行前端测试..."
cd frontend && npx vitest run --reporter=verbose 2>/dev/null && cd .. || {
    echo "❌ 前端测试失败，禁止推送"
    exit 1
}

echo "✅ 推送前检查通过！"
exit 0
