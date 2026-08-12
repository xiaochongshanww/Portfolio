# GitHub Token 过期管理

## 过期提醒设置

### 方法1: GitHub通知
GitHub会在token过期前7天发送邮件提醒到您的GitHub邮箱。

### 方法2: 日历提醒  
创建token时记录过期日期，设置日历提醒提前1周。

### 方法3: 脚本检查
将以下命令添加到您的shell配置文件：

```bash
# 在 ~/.bashrc 或 ~/.zshrc 中添加
alias check-github-token='curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user || echo "⚠️ GitHub token可能已过期"'
```

## 最佳实践

### ✅ 推荐做法
1. **生产部署**: 100%使用GitHub Actions
2. **本地开发**: 使用GitHub CLI (`gh auth login`)
3. **Token过期时间**: 30-60天(如果必须使用)
4. **权限最小化**: 只授予必需的packages权限

### ❌ 避免做法
1. 不要设置永不过期的token
2. 不要在脚本中硬编码token
3. 不要将token提交到git仓库
4. 不要授予超出需要的权限

## 应急处理

如果在生产部署时发现token过期：

```bash
# 1. 快速回退到本地构建
./quick-deploy.sh
# (脚本会自动检测并提供本地构建选项)

# 2. 或使用GitHub CLI快速登录
gh auth login
gh auth token | docker login ghcr.io -u xiaochongshanww --password-stdin
./build-and-push.sh
```