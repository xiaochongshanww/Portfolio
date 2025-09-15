#!/bin/bash
# 验证GitHub Actions自动构建设置

echo "🔍 验证GitHub Actions自动构建配置"
echo "================================="

# 检查workflow文件
if [ -f ".github/workflows/build-and-push.yml" ]; then
    echo "✅ GitHub Actions workflow文件存在"
    echo "📍 位置: .github/workflows/build-and-push.yml"
else
    echo "❌ 缺少workflow文件"
    exit 1
fi

# 检查Docker文件
echo ""
echo "🐳 检查Docker构建文件..."
if [ -f "Dockerfile.backend" ] && [ -f "Dockerfile.frontend" ]; then
    echo "✅ Docker文件完整"
    echo "   - Dockerfile.backend ✓"
    echo "   - Dockerfile.frontend ✓"
else
    echo "❌ 缺少Docker构建文件"
fi

# 检查预构建配置
echo ""
echo "📦 检查预构建部署配置..."
if [ -f "docker-compose.prebuilt.yml" ]; then
    echo "✅ 预构建Docker Compose配置存在"
    # 检查镜像地址
    if grep -q "ghcr.io/xiaochongshanww" docker-compose.prebuilt.yml; then
        echo "✅ GHCR镜像地址配置正确"
    else
        echo "⚠️  镜像地址可能需要检查"
    fi
else
    echo "❌ 缺少预构建配置文件"
fi

echo ""
echo "🚀 下一步操作："
echo "1. 提交并推送代码:"
echo "   git add ."
echo "   git commit -m \"Setup GitHub Actions auto-build\""
echo "   git push origin main"
echo ""
echo "2. 等待3-5分钟后访问:"
echo "   https://github.com/xiaochongshanww/Portfolio/actions"
echo ""
echo "3. 首次构建成功后，设置镜像为公开访问:"
echo "   https://github.com/xiaochongshanww/Portfolio/packages"
echo ""
echo "4. 然后就可以快速部署了:"
echo "   ./quick-deploy.sh"