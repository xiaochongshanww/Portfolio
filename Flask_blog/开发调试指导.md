# Flask Blog 开发调试指导

## 🎯 概述

本项目提供了完全容器化的开发环境，实现了开发环境与生产环境的完全一致性，同时保持了优秀的开发体验。

## 🚀 快速开始

### 第一次使用

1. **启动开发环境**
   ```powershell
   ./dev-start.ps1
   ```

2. **等待服务启动**（约30秒）
   - 脚本会自动检查服务健康状态
   - 显示绿色✅表示服务就绪

3. **开始调试**
   - 在VS Code中按 `F5`
   - 选择 `🐳 Full Stack: Docker Development`
   - 在backend代码中设置断点
   - 访问 http://localhost:3000 开始开发！

### 访问地址

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/api/v1/docs
- **MySQL**: localhost:3308 (用户: blog, 密码: blog)
- **Redis**: localhost:6380
- **Meilisearch**: http://localhost:7701

> 💡 注意：开发环境使用了不同的端口以避免与现有服务冲突

## 🐛 调试模式

### VS Code调试配置

项目已配置3种调试模式：

1. **🐳 Full Stack: Docker Development**
   - 启动完整的Docker开发环境
   - 前后端+数据库全部容器化运行
   - 支持Python断点调试

2. **🐳 Backend: Docker Development**  
   - 仅启动后端相关服务
   - 适用于专注后端开发

3. **传统模式**（保留原有配置）
   - 本地运行前后端
   - Docker仅运行数据库服务

### 调试特性

- ✅ **热重载**: 修改代码自动重启服务
- ✅ **断点调试**: 完整的Python调试支持  
- ✅ **变量监视**: 实时查看变量值
- ✅ **调用栈**: 完整的调用链追踪
- ✅ **前端HMR**: Vite热更新支持

## 🛠️ 开发工具

### 核心脚本

```powershell
# 启动开发环境
./dev-start.ps1

# 调试工具
./dev-debug.ps1 status          # 查看服务状态
./dev-debug.ps1 logs backend    # 查看后端日志
./dev-debug.ps1 logs frontend   # 查看前端日志
./dev-debug.ps1 restart backend # 重启后端服务
./dev-debug.ps1 shell backend   # 进入后端容器
./dev-debug.ps1 db              # 数据库操作工具

# 停止环境
./dev-stop.ps1                  # 停止所有服务
./dev-stop.ps1 -Clean           # 完全清理环境
```

### VS Code任务

使用 `Ctrl+Shift+P` → `Tasks: Run Task`：

- `docker-dev-full` - 启动完整开发环境
- `docker-dev-backend` - 仅启动后端相关服务
- `docker-dev-stop` - 停止所有服务
- `docker-dev-logs` - 查看实时日志
- `docker-dev-rebuild` - 重新构建并启动

## 📋 日常开发流程

### 标准工作流程

1. **开始开发**
   ```powershell
   ./dev-start.ps1
   ```

2. **VS Code调试**
   - 按 `F5` 启动调试
   - 选择Docker调试模式
   - 在代码中设置断点

3. **开发过程**
   - 修改代码自动热重载
   - 使用断点调试问题
   - 查看服务日志排查错误

4. **结束开发**
   ```powershell
   ./dev-stop.ps1
   ```

### 调试技巧

**后端调试：**
```powershell
# 查看后端实时日志
./dev-debug.ps1 logs backend

# 进入后端容器执行命令
./dev-debug.ps1 shell backend
# 容器内执行：
flask db upgrade  # 数据库迁移
python -m pytest  # 运行测试
```

**前端调试：**
```powershell
# 查看前端构建日志
./dev-debug.ps1 logs frontend

# 重启前端服务
./dev-debug.ps1 restart frontend
```

**数据库调试：**
```powershell
# 数据库操作菜单
./dev-debug.ps1 db

# 选项包括：
# 1. 连接MySQL命令行
# 2. 执行数据库迁移  
# 3. 重置数据库
```

## 🔧 高级配置

### 环境变量

开发环境配置文件：`.env.dev`
```env
# 开发模式配置
FLASK_ENV=development
FLASK_DEBUG=1
SQLALCHEMY_ECHO=true  # 显示SQL日志

# 调试模式
FLASK_DEBUG_MODE=remote  # 启用远程调试
```

### 性能优化

**Docker配置优化：**
- 使用WSL2后端（Windows）
- 分配足够内存（4GB+）
- 启用BuildKit加速构建

**卷映射优化：**
- 源码使用`cached`模式映射
- Node modules独立卷避免跨平台问题
- Python环境缓存提升重启速度

### 自定义配置

**修改端口映射：**
编辑 `docker-compose.dev.yml` 中的ports配置

**添加新服务：**
在 `docker-compose.dev.yml` 中添加服务定义

**调整资源限制：**
在服务配置中添加 `deploy.resources` 限制

## 🚨 故障排除

### 常见问题

**1. 容器启动失败**
```powershell
# 查看启动日志
./dev-debug.ps1 logs

# 重新构建镜像
./dev-debug.ps1 build

# 检查Docker状态
docker ps -a
```

**2. 调试连接失败**
```powershell  
# 检查调试端口
netstat -an | findstr :5678

# 确认后端容器运行
./dev-debug.ps1 status

# 重启后端服务
./dev-debug.ps1 restart backend
```

**3. 热重载不工作**
```powershell
# 验证卷映射
docker-compose -f docker-compose.dev.yml config

# 重建容器
./dev-debug.ps1 build backend
```

**4. 前端访问失败**
```powershell
# 检查前端服务状态  
./dev-debug.ps1 logs frontend

# 确认端口未被占用
netstat -an | findstr :3000
```

**5. 数据库连接错误**
```powershell
# 检查数据库健康状态
./dev-debug.ps1 status

# 执行数据库迁移
./dev-debug.ps1 db
```

### 完全重置环境

```powershell
# 停止并清理所有资源
./dev-stop.ps1 -Clean

# 重新构建并启动
./dev-start.ps1
```

## 📊 Docker vs 本地开发对比

| 特性 | 本地开发 | Docker开发 | 推荐 |
|------|----------|------------|------|
| **环境一致性** | ❌ 依赖本地环境 | ✅ 完全一致 | Docker |
| **依赖管理** | 复杂，易冲突 | 隔离，简单 | Docker |
| **服务启动** | 需分别启动 | 一键启动 | Docker |
| **调试支持** | 原生体验 | 远程调试 | 各有优势 |
| **热重载** | ✅ 原生支持 | ✅ 配置支持 | 相同 |
| **资源隔离** | ❌ 共享系统 | ✅ 完全隔离 | Docker |
| **团队协作** | 环境配置复杂 | 零配置启动 | Docker |

## 🎯 开发最佳实践

### 代码提交前检查

- [ ] 确保所有服务正常运行
- [ ] 运行单元测试和集成测试
- [ ] 检查代码格式和linting
- [ ] 验证前后端API对接正常
- [ ] 确认热重载功能正常

### 性能监控

```powershell
# 查看容器资源使用
docker stats

# 查看服务健康状态
./dev-debug.ps1 status

# 监控服务日志
./dev-debug.ps1 logs
```

### 团队协作

**新成员入门：**
1. Clone项目代码
2. 运行 `./dev-start.ps1`
3. 等待环境启动完成
4. 开始开发！

**环境同步：**
- 所有依赖在容器中，版本完全一致
- 数据库结构通过迁移文件同步
- 配置通过环境文件管理

## 🌟 总结

通过这套Docker化开发环境，您将获得：

- ✨ **零配置启动**：新成员一键启动完整开发环境
- ✨ **环境一致性**：开发环境与生产环境完全相同
- ✨ **专业调试**：完整的断点调试和热重载支持
- ✨ **工具化管理**：脚本化的服务管理和故障排除
- ✨ **团队协作**：统一的开发标准和工具链

现在您可以享受真正专业的全栈开发体验了！🚀