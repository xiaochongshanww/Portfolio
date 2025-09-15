#!/bin/bash
# GitHub Token 更新助手脚本

echo "🔑 GitHub Token 更新助手"
echo "========================="

echo "📋 当前Token状态检查..."

# 检查当前token是否有效
if [ -n "$GITHUB_TOKEN" ]; then
    echo "✅ 环境变量 GITHUB_TOKEN 已设置"
    
    # 测试token有效性
    if curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user > /dev/null; then
        echo "✅ Token有效，可以访问GitHub API"
        
        # 获取token信息
        TOKEN_INFO=$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user)
        USERNAME=$(echo $TOKEN_INFO | grep -o '"login":"[^"]*' | cut -d'"' -f4)
        echo "👤 当前用户: $USERNAME"
    else
        echo "❌ Token已过期或无效"
        echo "🔗 请访问: https://github.com/settings/tokens"
        echo "📝 创建新token时确保包含以下权限:"
        echo "   - write:packages (推送镜像)"
        echo "   - read:packages (拉取镜像)"
        exit 1
    fi
else
    echo "❌ 未找到 GITHUB_TOKEN 环境变量"
    echo "💡 设置方法:"
    echo "   export GITHUB_TOKEN=your_token_here"
    echo "   或添加到 ~/.bashrc 或 ~/.zshrc"
fi

echo ""
echo "🚀 如果token有效，可以运行:"
echo "   ./build-and-push.sh"
echo ""
echo "⚡ 推荐使用 GitHub Actions 自动构建 (无需token管理):"
echo "   git push origin main  # 自动触发构建"