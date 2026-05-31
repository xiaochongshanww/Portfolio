# 系统架构

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端                                │
│          Browser (SPA) / API Client / Mobile                │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP / WSS
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Nginx (Gateway)                          │
│       静态资源 / API反向代理 / SSL终端 / 限流 / 安全头       │
└──────┬──────────────────────┬──────────────────┬────────────┘
       │                      │                  │
       ▼                      ▼                  ▼
┌──────────────┐    ┌──────────────────┐  ┌──────────────────┐
│   Frontend   │    │    Backend API   │  │    Public API    │
│  (Vue 3 SPA) │    │  Flask/Gunicorn  │  │  /public/v1/*    │
│              │    │                  │  │  (只读缓存)       │
└──────────────┘    └───────┬──────────┘  └──────────────────┘
                            │
              ┌─────────────┼──────────────────┐
              │             │                  │
              ▼             ▼                  ▼
        ┌──────────┐ ┌──────────┐ ┌──────────────────┐
        │  MySQL 8 │ │  Redis   │ │   MeiliSearch    │
        │ (主存储) │ │(缓存/队列)│ │   (全文搜索)      │
        └──────────┘ └──────────┘ └──────────────────┘
```

---

## 后端架构

### 模块划分 (Flask Blueprints)

| Blueprint | 前缀 | 职责 |
|-----------|------|------|
| `auth` | `/api/v1/auth` | 注册/登录/令牌刷新/密码变更 |
| `articles` | `/api/v1/articles` | 文章 CRUD、工作流、版本控制、公开接口 |
| `comments` | `/api/v1/comments` | 树状评论、审核、批量操作 |
| `search` | `/api/v1/search` | MeiliSearch 全文搜索（DB 回退） |
| `users` | `/api/v1/users` | 用户资料、角色管理、公开作者页 |
| `taxonomy` | `/api/v1/taxonomy` | 分类与标签 CRUD |
| `uploads` | `/api/v1/uploads` | 图片上传（多尺寸 + WebP） |
| `media` | `/api/v1/media` | 媒体库管理（文件夹/搜索/批量） |
| `metrics` | `/api/v1/metrics` | 站点统计、访客追踪 |
| `security` | `/api/v1/security` | 安全监控、威胁检测、IP封禁 |
| `settings` | `/api/v1/settings` | 系统设置（通用/内容/安全） |
| `logs` | `/api/v1/admin/logs` | 日志查询与分析 |
| `backup` | `/api/v1/backup` | 物理备份、增量备份、恢复管理 |
| `docs` | `/spec` | OpenAPI 动态文档 |

### 分层设计（以 articles 为例）

```
routes.py        → HTTP 编排 (参数提取 + 响应)
  │
  ▼
service.py       → 业务逻辑 (工作流/权限/缓存)
  │
  ▼
schemas.py       → Pydantic 请求/响应模型
  │
  ▼
models.py        → SQLAlchemy 数据模型
```

### 关键数据流

```
创建文章:
  POST /api/v1/articles/
  → @require_auth (JWT 鉴权)
  → ArticleCreateModel (Pydantic 校验)
  → ArticleService.create_article() (业务逻辑)
  → render_and_sanitize() (Markdown → HTML + Bleach 清洗)
  → db.session.commit() (持久化)
  → index_article() (MeiliSearch 索引)
  → invalidate_article_cache() (Redis 缓存失效)

阅读文章:
  GET /api/v1/articles/public/slug/<slug>
  → Redis 缓存查询 (cache_track_set / cache_track_get)
  → 权限检查 (published → 公开)
  → serialize_article() (批量序列化支持预查计数)
  → ETag 协商缓存
```

---

## 前端架构

### 目录结构

```
frontend/src/
├── views/           # 页面级组件 (~30)
│   ├── admin/       # 管理后台 (~15)
│   └── *.vue        # 公开页面
├── components/      # 可复用 UI 组件 (~30)
│   ├── layout/      # AppHeader / AppFooter
│   ├── sidebar/     # 侧边栏组件
│   └── media/       # 媒体库组件
├── stores/          # Pinia 状态管理
│   ├── user.js      # 认证/用户状态
├── api/             # API 客户端
│   ├── apiClient.js # Axios 实例
│   ├── index.js     # 统一出口 (API.*)
│   └── generatedClientAdapter.js  # 生成代码适配器
├── generated/       # openapi-typescript-codegen 输出
├── utils/           # 工具函数
├── directives/      # 自定义 Vue 指令
├── composables/     # 组合式函数
└── router.js        # 路由配置
```

### 状态管理

```
userStore (Pinia):
  state:    token, role, user, isAuthenticated
  getters:  hasRole(), isAdmin, isEditor, canAccessAdmin, etc.
  actions:  setAuth(), fetchUserInfo(), login(), logout(), initAuth()
```

---

## 部署架构

```
生产环境 (docker-compose.prod.yml):
  backend     → Gunicorn (4 workers × 4 threads)
  frontend    → Nginx 托管静态资源
  mysql       → MySQL 8 (持久卷 mysqldata)
  redis       → Redis 7 (缓存 + 限流 + Celery Broker)
  meili       → MeiliSearch (持久卷 meilidata)
  celery_worker → Celery Worker (异步任务)
  celery_beat   → Celery Beat (定时发布调度)

开发环境 (docker-compose.dev.yml):
  同上，额外启用:
  - 后端热重载 (watchfiles)
  - 前端 HMR (Vite Dev Server)
  - 远程调试 (debugpy 端口 5678)
```

---

## 安全架构

```
┌─────────────────────────────────────┐
│            Nginx 安全层              │
│  HTTPS / CSP / HSTS / X-Frame-Options│
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│          Flask 中间件层              │
│  CORS  / 安全响应头 / 限流           │
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│          JWT 认证层                  │
│  Access Token (30min) + Refresh     │
│  刷新令牌 → 旧令牌黑名单 (Redis)     │
│  改密码 → 全量 Refresh 吊销          │
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│         权限控制层                    │
│  @require_auth / @require_roles     │
│  @permission_required (ROLE_MATRIX) │
│  @workflow_transition (状态机守卫)    │
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│         内容安全层                    │
│  Bleach HTML 清洗 / CSP 限制         │
│  DOMPurify 前端二次过滤              │
└─────────────────────────────────────┘
```

---

## 测试策略

参见 [test-system-evaluation.md](./test-system-evaluation.md)

层级:
```
E2E (Playwright)        → 核心流程
集成测试 (pytest)       → API 端点 (SQLite + FakeRedis)
单元测试 (vitest)       → 前端组件 + Store
静态分析 (black/eslint) → 代码风格
```

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](../README.md) | 项目概览与快速开始 |
| [DEPLOYMENT.md](../DEPLOYMENT.md) | 生产部署指南 |
| [DEVELOPMENT.md](../DEVELOPMENT.md) | 开发环境设置 |
| [code-review-report.md](./code-review-report.md) | 代码审查结果 |
| [test-system-evaluation.md](./test-system-evaluation.md) | 测试体系评估 |
