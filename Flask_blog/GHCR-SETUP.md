# GitHub Container Registry 配置指南

## 1. 自动构建设置

GitHub Actions已配置，每次推送到`main`分支时自动构建镜像。

## 2. 镜像权限设置

首次推送后，需要设置镜像为公开访问：

1. 访问 https://github.com/xiaochongshanww/Portfolio/pkgs/container/flask-blog-backend
2. 点击右侧 "Package settings"  
3. 在 "Danger Zone" 中点击 "Change visibility"
4. 选择 "Public" 并确认
5. 对 flask-blog-frontend 重复相同步骤

## 3. 本地构建和推送

如需本地构建：

```bash
# 登录GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u xiaochongshanww --password-stdin

# 构建并推送  
./build-and-push.sh
```

## 4. 部署使用

```bash
# 快速部署（使用预构建镜像）
./quick-deploy.sh

# 查看可用镜像标签
docker search ghcr.io/xiaochongshanww/flask-blog-backend
```

## 5. 版本管理

- `latest`: 最新main分支构建
- `v1.0.0`: 语义化版本标签  
- `main`: 主分支最新提交
- `[commit-sha]`: 特定提交版本

## 故障排除

**拉取失败**：镜像可能未设置为公开，需要登录：
```bash
docker login ghcr.io
```

**推送失败**：检查GITHUB_TOKEN权限是否包含`packages:write`