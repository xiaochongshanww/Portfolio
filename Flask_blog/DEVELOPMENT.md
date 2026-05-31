# Flask Blog 开发环境指南

## 🚀 快速开始

### 1. 启动开发环境
```powershell
# 一键启动所有服务
./dev-start.ps1
```

### 2. 访问应用
- **前端**: http://localhost:3000
- **后端API**: http://localhost:8000  
- **API文档**: http://localhost:8000/api/v1/docs

### 3. 数据库连接
- **MySQL**: localhost:3306 (用户: blog, 密码: blog)
- **Redis**: localhost:6379
- **Meilisearch**: http://localhost:7700

## 🐛 VS Code调试

### 方法1: 完整栈调试
1. 启动开发环境: `./dev-start.ps1`
2. 在VS Code中按 `F5`
3. 选择 `🐳 Full Stack: Docker Development`
4. 在backend代码中设置断点
5. 访问 http://localhost:8000 触发断点

### 方法2: 仅后端调试
1. 启动基础服务: `./dev-debug.ps1 restart backend`  
2. 在VS Code中按 `F5`
3. 选择 `🐳 Backend: Docker Development`

### 调试特性
- ✅ **热重载**: 修改代码自动重启
- ✅ **断点调试**: 完整的Python调试支持
- ✅ **变量监视**: 实时查看变量值
- ✅ **调用栈**: 完整的调用链追踪

## 🛠️ 开发工具

### 日常使用脚本
```powershell
# 查看服务状态
./dev-debug.ps1 status

# 查看日志
./dev-debug.ps1 logs backend
./dev-debug.ps1 logs frontend

# 重启服务
./dev-debug.ps1 restart backend

# 进入容器
./dev-debug.ps1 shell backend

# 数据库操作
./dev-debug.ps1 db

# 停止环境
./dev-stop.ps1

# 完全清理
./dev-stop.ps1 -Clean
```

### VS Code任务
使用 `Ctrl+Shift+P` → `Tasks: Run Task`:
- `docker-dev-full` - 启动完整开发环境
- `docker-dev-backend` - 仅启动后端相关服务
- `docker-dev-stop` - 停止所有服务
- `docker-dev-logs` - 查看实时日志
- `docker-dev-rebuild` - 重新构建并启动

## 📁 项目结构

```
Flask_blog/
├── backend/                 # 后端源码 (映射到容器)
├── frontend/               # 前端源码 (映射到容器)
├── docker-compose.dev.yml  # 开发环境配置
├── .env.dev               # 开发环境变量
├── Dockerfile.backend    # 后端镜像 (BUILD_ENV=development)
├── Dockerfile.frontend   # 前端镜像 (target=dev)
├── docker-compose.yml    # 生产 Compose
├── Makefile              # 测试 / Lint 命令 (跨平台)
├── dev-*.ps1             # 开发工具脚本 (Windows)
├── deploy.sh             # 部署脚本 (Linux/macOS)
└── deploy.ps1            # 部署脚本 (Windows)
```

## 🔧 高级配置

### 环境变量
开发环境配置在 `.env.dev` 中：
- `FLASK_DEBUG=1` - 启用Flask调试模式
- `FLASK_DEBUG_MODE=remote` - 启用远程调试
- `SQLALCHEMY_ECHO=true` - 显示SQL日志

### 热重载配置
- **后端**: 源码映射 `./backend:/app/backend:cached`
- **前端**: 源码映射 `./frontend:/app:cached`
- **Vite HMR**: 端口24678用于热更新

### 数据持久化
开发环境数据存储：
- `mysqldata_dev` - MySQL数据
- `redisdata_dev` - Redis数据  
- `meilidata_dev` - Meilisearch数据
- `uploads` - 文件上传
- `backend_venv` - Python环境缓存
- `frontend_node_modules` - Node.js模块缓存

## 🐳 Docker vs 本地开发对比

| 特性 | 本地开发 | Docker开发 |
|------|----------|------------|
| 环境一致性 | ❌ | ✅ |
| 依赖管理 | 复杂 | 简单 |
| 服务启动 | 分别启动 | 一键启动 |
| 调试支持 | 原生 | 远程调试 |
| 热重载 | ✅ | ✅ |
| 资源隔离 | ❌ | ✅ |

## 🚨 故障排除

### 常见问题

**1. 容器启动失败**
```powershell
# 查看详细日志
./dev-debug.ps1 logs

# 重新构建
./dev-debug.ps1 build
```

**2. 调试连接失败**  
```powershell
# 检查端口5678是否被占用
netstat -an | findstr :5678

# 重启后端服务
./dev-debug.ps1 restart backend
```

**3. 热重载不工作**
```powershell
# 检查卷映射
docker-compose -f docker-compose.dev.yml config

# 重新挂载卷
./dev-debug.ps1 build backend
```

**4. 数据库连接错误**
```powershell
# 检查数据库状态
./dev-debug.ps1 status

# 执行数据库迁移
./dev-debug.ps1 db
```

### 性能优化

**Windows Docker性能调整:**
- 启用 WSL2 后端
- 分配足够内存 (4GB+)
- 使用 `cached` 卷挂载选项

**开发体验优化:**
- 使用 `watchfiles` 替代默认文件监视
- 分离node_modules挂载避免跨平台问题
- Python环境缓存提升重启速度

## 📋 开发检查清单

**每日开发流程:**
- [ ] 运行 `./dev-start.ps1` 启动环境
- [ ] 检查 `./dev-debug.ps1 status` 服务状态
- [ ] 在VS Code中启用调试模式
- [ ] 开发完成后运行测试
- [ ] 提交前运行 `./dev-stop.ps1` 清理

**代码提交前:**
- [ ] 确保所有服务正常运行
- [ ] 运行单元测试和集成测试
- [ ] 检查代码格式和linting
- [ ] 验证前后端API对接正常

现在您拥有了完整的Docker化开发环境，既保持了生产环境一致性，又提供了优秀的开发体验！