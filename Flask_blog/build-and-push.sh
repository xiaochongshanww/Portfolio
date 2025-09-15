#!/bin/bash
# 构建并推送镜像到registry的脚本
# 用于CI/CD或开发机器上预构建

set -e

# 配置
REGISTRY=${REGISTRY:-"ghcr.io/xiaochongshanww"}
VERSION=${VERSION:-"latest"}
BUILD_ARGS=""

echo "🏗️  开始构建Flask Blog镜像..."

# 获取Git提交信息作为版本标签
if git rev-parse --git-dir > /dev/null 2>&1; then
    GIT_COMMIT=$(git rev-parse --short HEAD)
    GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    BUILD_ARGS="--build-arg GIT_COMMIT=$GIT_COMMIT --build-arg GIT_BRANCH=$GIT_BRANCH"
    echo "📋 Git信息: $GIT_BRANCH@$GIT_COMMIT"
fi

# 构建后端镜像
echo "🔧 构建后端镜像..."
docker build $BUILD_ARGS \
    -f Dockerfile.backend \
    -t $REGISTRY/flask-blog-backend:$VERSION \
    -t $REGISTRY/flask-blog-backend:$GIT_COMMIT \
    .

# 构建前端镜像  
echo "🎨 构建前端镜像..."
docker build $BUILD_ARGS \
    -f Dockerfile.frontend \
    -t $REGISTRY/flask-blog-frontend:$VERSION \
    -t $REGISTRY/flask-blog-frontend:$GIT_COMMIT \
    .

# 推送镜像到registry
if [ "${PUSH_IMAGES:-true}" = "true" ]; then
    echo "📤 推送镜像到registry..."
    docker push $REGISTRY/flask-blog-backend:$VERSION
    docker push $REGISTRY/flask-blog-backend:$GIT_COMMIT
    docker push $REGISTRY/flask-blog-frontend:$VERSION  
    docker push $REGISTRY/flask-blog-frontend:$GIT_COMMIT
    
    echo "✅ 镜像推送完成!"
    echo "🚀 现在可以在目标服务器上运行:"
    echo "   docker-compose -f docker-compose.prebuilt.yml pull"
    echo "   docker-compose -f docker-compose.prebuilt.yml up -d"
else
    echo "⚠️  跳过推送 (设置 PUSH_IMAGES=true 来推送)"
fi

# 显示镜像大小
echo ""
echo "📊 构建的镜像信息:"
docker images | grep flask-blog | head -4

echo "🎉 构建完成!"