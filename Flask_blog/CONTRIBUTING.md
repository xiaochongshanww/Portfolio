# 贡献指南

## 分支策略

```
main          — 生产就绪，仅接受 PR 合并
feature/*     — 新功能开发
fix/*         — 缺陷修复
refactor/*    — 代码重构
```

## 开发流程

```
1. 从 main 创建功能分支: git checkout -b feature/my-feature
2. 在本地开发调试
3. 运行测试确保不破坏现有功能
4. 提交 PR 到 main
```

## 代码规范

### 后端 (Python)

```bash
# 格式化
make format

# Lint 检查
make lint

# 类型检查
mypy backend/app/
```

- 遵循 PEP 8，使用 Black 格式化（行宽 88）
- import 分组：标准库 → 第三方 → 本地（isort 自动管理）
- 所有路由函数保持简洁，业务逻辑委托到 `service.py`

### 前端 (Vue / TypeScript)

```bash
# Lint
cd frontend && npm run lint

# 格式化
cd frontend && npm run format
```

- Vue 组件使用 `<script setup>` 语法
- TS 优先于 JS（新文件必须使用 TypeScript）
- 组件名使用 PascalCase，文件名与之对应

## 测试要求

### 后端

```bash
# 运行全部测试
make test-backend

# 带覆盖率
make test-backend-cov

# 新增代码必须包含测试
```

- 每个 API 端点至少覆盖：成功路径 + 鉴权校验 + 参数校验
- 使用 `helpers.py` 中的工厂函数创建测试数据
- 测试使用 SQLite 内存数据库，不依赖外部服务

### 前端

```bash
# 运行全部测试
make test-frontend

# 带覆盖率
make test-frontend-cov
```

- 核心组件（ArticleContentRenderer、CommentsThread 等）必须包含渲染测试
- Store 必须包含状态变更测试
- 测试需要覆盖 loading、empty、error 三种状态

### E2E

```bash
# 首次运行前安装浏览器
cd frontend && npx playwright install chromium

# 运行 E2E 测试
make test-e2e
```

- E2E 测试覆盖用户核心路径（注册 → 登录 → 创建 → 发布）
- E2E 测试不要求全部通过即可合入，但不能有阻塞性失败

## 提交规范

提交信息格式（遵循 Conventional Commits）：

```
<类型>: <简短描述>

<详细说明（可选）>
```

类型：

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 缺陷修复 |
| `refactor` | 代码重构 |
| `test` | 测试相关 |
| `docs` | 文档变更 |
| `chore` | 工具/配置变更 |
| `perf` | 性能优化 |
| `security` | 安全修复 |

示例：

```
feat: 添加文章定时发布功能

- 新增 schedule_article API
- scheduler 定时任务每分钟检查到期文章
- 前端文章编辑页添加定时发布选择器
```

## PR 模板

```markdown
## 变更内容

<!-- 简要描述 -->

## 测试验证

- [ ] 后端测试通过
- [ ] 前端测试通过
- [ ] 手动验证核心流程

## 注意事项

<!-- 部署注意事项、迁移脚本等 -->
```

## 部署检查清单

代码合并到 main 前：

- [ ] `make test-all` 通过
- [ ] lint 无新增警告
- [ ] 无硬编码密钥或凭证
- [ ] 新环境变量已添加到 `.env.example`
- [ ] 新 API 端点已添加鉴权和权限检查
