## Flask Blog 平台

本项目是一个具备版本控制、工作流审批、评论审核、搜索、点赞收藏、定时发布与动态 SEO 的内容平台示例。

## 🚀 快速部署

**一键部署指南**: [DEPLOYMENT.md](./DEPLOYMENT.md) - 完整的Docker一键部署解决方案，包含外部元数据系统和备份恢复功能。

```bash
# Linux/macOS
./deploy.sh

# Windows PowerShell  
.\deploy.ps1
```

### 核心特性
- 角色 / 权限：author / editor / admin 工作流 (draft -> pending_review -> published -> archived/rejected)。
- 文章：Markdown + 安全渲染 (Bleach) + 版本快照 & 回滚 + 定时发布 + SEO 字段 + 特色图。
- 搜索：MeiliSearch（失效回退 DB fuzzy）。
- 互动：点赞、收藏、树状评论（审核流）。
- 性能：Redis 缓存已发布文章 + ETag + 路由按需分包 + 图片懒加载 + 多尺寸/WEBP 生成。
- 安全：JWT Access/Refresh + 刷新吊销、CSP、安全头、HTML 清洗、速率限制(全局 + 细化)。
- 指标：Prometheus 指标、sitemap.xml / robots.txt。

### 技术栈
- 后端：Flask, SQLAlchemy, Alembic(Flask-Migrate), Redis, Flask-Limiter, MeiliSearch, APScheduler。
- 前端：Vue3 + Vite + Pinia + vue-router (动态 import) + EasyMDE + highlight.js。

### 环境变量 (节选)
| 变量 | 说明 | 默认 |
| ---- | ---- | ---- |
| DATABASE_URL | 数据库连接 (MySQL 推荐) | sqlite:///dev.db |
| REDIS_URL | Redis 地址 | redis://127.0.0.1:6379/0 |
| MEILISEARCH_URL | 搜索服务 | http://localhost:7700 |
| JWT_SECRET_KEY | JWT 密钥 | dev-secret |
| RATE_LIMIT_DEFAULT_MINUTE | 默认分钟限速 | 200 |
| ALLOWED_IMAGE_TYPES | 上传允许 MIME | image/jpeg,image/png,image/webp |
| MAX_IMAGE_SIZE | 图片最大字节 | 2097152 |

### 数据库迁移 (MySQL)
1. 设置 `DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname`。
2. 初始化（首次）:
   flask db init
3. 生成迁移:
   flask db migrate -m "message"
4. 应用迁移:
   flask db upgrade
 5. 校验 schema & 服务端字符集:
   python backend/scripts/mysql_check.py  (需设置 DATABASE_URL 环境变量)

### 上传错误码
| Code | 含义 |
| ---- | ---- |
| 4401 | 缺少文件或文件名为空 |
| 4402 | 类型不允许 (返回 allowed 列表) |
| 4403 | 文件过大 (返回 max) |

### 速率限制 (示例)
- 全局默认：配置中 RATE_LIMIT_DEFAULT_*
- /api/v1/articles/<id>/like : 30/min
- /api/v1/articles/<id>/bookmark : 30/min
- /api/v1/comments/ : 20/min
- /api/v1/comments/moderate/<id> : 60/min
- /api/v1/uploads/image : 20/min

### 本地开发
后端：
  export FLASK_APP=app:create_app
  flask run

前端：
  cd frontend && npm install && npm run dev

### 部署建议
- 使用 gunicorn/uwsgi + 反向代理 (Nginx) 处理静态与缓存头。
- 启用 Redis 分布式限流。
- 配置持久化存储目录 UPLOAD_DIR。
- 提供健康检查 /api/v1/health 与 /metrics。

### 待补充
- 完整 OpenAPI 片段示例
- CI/CD pipeline 示例 (构建 + 迁移 + 健康探针)
## Flask Blog / Content Platform

（Phase 1 交付基础版）

### 已实现 (Phase 1 范围)
- 角色 / 权限矩阵（Author / Editor / Admin 基础动作）
- 文章工作流：draft -> pending_review -> published / rejected；发布后支持 unpublish（归档）、定时发布 schedule/unschedule
- 文章创建 / 更新（Markdown 清洗 + slug 去重生成 + 标签去重/复用）
- Slug & ID 双路径访问，严格的草稿访问控制（仅作者本人 / 拥有审核或发布权限角色）
- 工作流状态守卫（后端 decorator + 测试）
- 图片上传接口（单图）+ 前端组件 + 编辑页粘贴/拖拽自动上传
- 点赞 / 收藏（后端接口 + 乐观防抖留待后续）
- 搜索基础（占位/可接入 MeiliSearch）
- ETag 缓存适配（前端拦截器支持 304）
- OpenAPI 文档生成（frontend/src/generated, backend/openapi.json）
- 后端测试：访问控制 / slug / ETag 等 8+ 用例稳定通过

### 待实现 / 下一阶段建议
- 富文本 WYSIWYG（当前为简易 Markdown 文本域 + 图片插入）
- 文章版本快照回滚 UI（后端接口已雏形）
- SEO 字段（meta title/description）、featured image、外部媒体嵌入
- 分类 / 标签管理前端界面
- 评论 threaded UI 与审核面板
- 作者主页 / 统计面板
- 更完整的权限矩阵（细粒度 action 映射）
- 性能优化（懒加载图片组件化、骨架屏、SSR/预渲染可选）

### 技术栈
Backend: Flask + SQLAlchemy + JWT + Redis(可选缓存) + Bleach(内容清洗) + (可选 MeiliSearch)
Frontend: Vue 3 + Vite + TypeScript + Pinia + 代码生成 API 客户端 (openapi-typescript-codegen)
Testing: pytest, vitest (预留), FakeRedis / test doubles

### 目录结构（简要）
backend/      后端应用（Blueprints, models, routes, services, docs）
frontend/     前端工程（src/views, components, generated API, stores）

### 快速开始
1. 安装依赖
   - 后端: 进入 backend 目录：`pip install -r requirements.txt`
   - 前端: 进入 frontend 目录：`npm install`
2. 启动服务
   - 后端开发: `flask run` (确保已设置 FLASK_APP=app:create_app )
   - 前端开发: `npm run dev` (默认代理到后端 API, 或配置 VITE_PROXY)
3. 访问前端： http://localhost:5173 （按 Vite 输出端口）

### 环境变量（示例）
| 变量 | 说明 | 示例 |
| ---- | ---- | ---- |
| FLASK_ENV | 环境 | development |
| DATABASE_URL | MySQL 连接 | mysql+pymysql://user:pass@localhost/blog |
| REDIS_URL | Redis 可选 | redis://localhost:6379/0 |
| JWT_SECRET | JWT 密钥 | (自定义) |
| SEARCH_ENDPOINT | MeiliSearch/ES 可选 | http://localhost:7700 |
| RATE_LIMIT_ENABLED | 可选限流 | true |

### 工作流与权限矩阵（节选）
状态流转：
draft -> pending_review -> (published | rejected)
published -> archived(=unpublish)
rejected -> draft (作者继续改) / pending_review (再次提交)

核心动作权限：
- workflow:submit (Author 拥有) -> draft -> pending_review
- workflow:approve / workflow:reject / workflow:publish (Editor / Admin)
- workflow:unpublish (Editor / Admin)

### API 文档
后端启动后可访问 /api/v1/openapi.json （或项目中 backend/openapi.json）。前端使用脚本生成：
`npm run gen:api` （示例脚本，若已配置）

### 测试
后端：在 backend 目录执行 `pytest -q`
（推荐使用虚拟环境，并确保测试使用 FakeRedis / 内存 DB）

### 前端开发注意
- 使用 src/api/index.js 统一出口；自动刷新 Token + ETag 缓存
- 访问文章详情优先内部 slug 接口（可带权限显示草稿），失败降级 public 接口
- 修改数据后可调用清理缓存 window.__API_CACHE__.clear()

### 部署建议（简要）
- 后端：uWSGI/Gunicorn + Nginx；开启 gzip；配置 Redis 用于缓存浏览/热门统计
- 数据库：MySQL 8（UTF8MB4），定期备份 + 慢查询日志
- 前端：Vite 构建后静态资源托管（Nginx / CDN）
- 日志：结构化 JSON（Gunicorn access + 应用 error）
- 监控：接入 Prometheus Exporter / Sentry（后续）

### 安全
- 输入清洗（Bleach）
- JWT 短期访问 + 刷新（拦截器自动刷新）
- 仅发布文章进入公共缓存层；草稿不缓存 slug
- TODO: CSRF / Content Security Policy / 附件大小限制 / 上传类型白名单强化

### Roadmap (下一步)
- 完整富文本块编辑器（支持拖拽排序 / 多媒体嵌入）
- 评论与通知系统
- 统计分析仪表盘（浏览热度、转化）
- 更细的审核日志与行为审计
- 多租户 / 国际化 UI

---
如需更详细的实现说明或下一阶段规划，可在 issue / 需求文档中继续补充。
# Flask Blog 平台 (Phase 1)

> 当前仓库处于 Phase 1 交付：聚焦文章基础 CRUD、工作流(草稿 → 待审核 → 已发布 / 退回 / 归档 / 定时)、角色/权限、访问控制、基础搜索与上传，并提供最小可运行的前后端与测试。本文档为总体 README（backend 目录下 README 仍保留更细节后端说明）。

## 1. 功能概览 (Phase 1 完成范围)

- 角色与权限：Admin / Editor / Author / Public；基于权限矩阵 (ROLE_MATRIX) 控制创建、审核、发布、拒绝、归档等操作。
- 文章工作流：draft → pending_review → (published | rejected | archived)；支持 rejected 回到 draft 再次提交；支持 scheduled 定时发布；published 之后可 archived / unpublish 回退。
- 访问控制：未登录/普通访客仅可见已发布 (published)；作者可见自己的非删除文章；编辑/管理员可见所有；草稿/待审核对无权用户返回 404 避免暴露。
- 内容安全：Markdown 渲染 + bleach 清洗；仅允许安全标签与属性 (后端 `content_sanitizer`).
- 搜索：接入 MeiliSearch (仅索引已发布)；重建脚本支持。
- 上传：支持图片上传与多尺寸生成 (lg/md/sm/thumb) + WebP；接口 `POST /api/v1/uploads/image`，返回各尺寸 URL。
- 缓存：Redis ETag 风格缓存 (详情 / 列表 / 搜索)；仅已发布文章按 slug 缓存；草稿访问不写缓存避免越权泄露。
- 限流：全局与关键接口的频率限制；缺 Redis 时自动回退内存限流。
- 监控：Prometheus 指标 `/metrics` (可选，依赖安装)；采集请求计数、时延、搜索、发布统计等。
- OpenAPI：运行时动态生成并注入扩展 (角色矩阵、工作流)；前端脚本同步生成代码与治理数据。
- 测试：Pytest 针对文章访问控制（ID / slug）与工作流关键路径的最小集；FakeRedis 清理确保不串数据。

## 2. 快速开始

### 2.1 依赖
- Python 3.11+
- Node.js 18+
- MySQL 8 / Redis 7 / MeiliSearch 1.7

### 2.2 本地运行 (后端)
```
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
flask db upgrade
python run.py  # 默认监听 5000 或 Gunicorn 8000 (见 run.py)
```
可复制根目录 `.env.example` 为 `.env` 覆盖默认配置。

### 2.3 本地运行 (前端)
```
cd frontend
npm install
npm run codegen   # 下载 OpenAPI -> 生成客户端 -> 错误码/治理数据
npm run dev       # http://localhost:5173
```
确保前端请求代理到后端 `/api/v1/*`（开发环境同域或通过 Vite 代理配置）。

### 2.4 Docker Compose (一键)
```
docker compose up -d --build
# 访问后端: http://localhost:8000/api/v1/health
# MeiliSearch 面板 (若开启): http://localhost:7700
```
初次启动后执行数据库迁移：容器内已在 worker 里保证 `flask db upgrade`；如需手动：
```
docker compose exec backend flask db upgrade
```

## 3. 环境变量 (摘选)
详见 `.env.example`。
- DATABASE_URL / REDIS_URL / MEILISEARCH_URL
- JWT_SECRET_KEY / JWT_ACCESS_MINUTES / JWT_REFRESH_DAYS
- UPLOAD_DIR / MAX_IMAGE_SIZE / ALLOWED_IMAGE_TYPES
- ENABLE_SCHEDULER / SCHEDULE_CHECK_INTERVAL
- CORS_ORIGINS

## 4. 权限与工作流

### 4.1 权限矩阵 (片段)
```
workflow:submit   -> author, editor, admin
workflow:approve  -> editor, admin
workflow:reject   -> editor, admin
workflow:publish  -> editor, admin
articles:create   -> author, editor, admin
articles:delete   -> editor, admin
```
前端经 `scripts/sync-governance.mjs` 生成 `frontend/src/governance/*`。

### 4.2 状态与流转
```
draft -> pending_review -> (published | rejected | archived)
rejected -> draft / pending_review
scheduled -> published / archived
published -> archived (或通过 unpublish 回到 draft)
```
路由示例：
- 提交审核: POST /api/v1/articles/{id}/submit
- 审核通过: POST /api/v1/articles/{id}/approve
- 驳回: POST /api/v1/articles/{id}/reject
- 定时: POST /api/v1/articles/{id}/schedule { scheduled_at }
- 取消定时: POST /api/v1/articles/{id}/unschedule
- 下线: POST /api/v1/articles/{id}/unpublish

## 5. 上传接口
`POST /api/v1/uploads/image` 表单字段 `file`；返回 JSON:
```
{
  code:0,
  data:{
    url: "/uploads/2024/08/uuid.jpg",
    width, height, size,
    webp: "/uploads/.../uuid.webp",
    variants:[ { label:"md", url:"...", width, height }, ... ]
  }
}
```
前端可选择最接近容器宽度的 `variants`；编辑器插入时可使用 `<picture>`。

## 6. 前端要点 (Phase 1)
- 代码生成：`npm run codegen` (含错误码 + 工作流 + 权限矩阵)。
- API 客户端：Axios + 单飞刷新 + 简易 ETag 缓存 (60s)。
- 权限指令 (预留) 与 `ROLE_MATRIX` 检查按钮显示。
- 文章详情页：展示可用下一状态按钮；图片上传与富文本编辑将在 Phase 2 增强。

## 7. 测试
后端：
```
cd backend
pytest -q
```
（当前重点：访问控制 / 工作流核心路径）。

## 8. 搜索 & 索引
- 已发布文章创建/更新时写入索引；非发布或下线/删除时移除。
- 重建：`python -m scripts.reindex_search`。

## 9. 安全实践
- JWT + 失效检查；限流；Markdown 清洗 (bleach)；安全响应头；以 404 隐藏无权限资源；上传类型与大小校验。

## 10. 部署建议 (简述)
- 生产：Gunicorn + (Nginx 反向代理 / 静态与上传)；开启 HTTPS；配置日志采集 (JSON)；Prometheus 抓取 /metrics。
- 设置备份策略 (MySQL binlog + 定期快照)；Redis 持久化 (AOF/RDB)；MeiliSearch 数据卷快照。
- 环境变量注入（Secrets 管理）；滚动升级时提前导出新 OpenAPI 供前端同步。

## 10.1 部署与性能优化 (当前阶段进展)
本阶段聚焦“部署 + 性能”初步落地，核心成果与下一步计划如下：

### 已完成
- Docker 化：新增 backend / frontend 多阶段 Dockerfile，`docker compose` 一键拉起 (MySQL / Redis / MeiliSearch / backend(Gunicorn) / frontend(Nginx))。
- Gunicorn 生产启动参数：多 worker + 线程（适度）以兼顾 I/O / 计算；可后续改为 `--worker-class gevent` 视需求。
- 静态与上传分离：`uploads` 目录以卷形式挂载，便于持久化 / 备份；删除（软删除）文章时自动移除搜索索引。
- 图片管线：上传即生成多尺寸 (lg/md/sm/thumb) + WebP；新增 LQIP (极小 Base64 占位) + 自动生成 `srcset`，前端编辑器插入 `<picture>` + `loading="lazy"`，提升 LCP。
- 富媒体短代码：支持 `:::video` (YouTube/BiliBili) 与 `:::gist`，后端短代码预处理 + 安全 iframe 白名单；前端懒加载 gist 内容。
- 内容安全：Bleach 允许的标签/属性扩展，iframe host 白名单过滤；仍默认拒绝未知外链脚本。
- 缓存策略：Redis 缓存已发布文章 + ETag 协商缓存；仅已发布写缓存，避免草稿泄露；删除与工作流状态切换时失效清理。
- 性能基线文档：新增 `PERFORMANCE.md` 描述目标指标、监控与优化方向（可继续补充 Lighthouse 分析结果）。

### 待办 / 计划
- Nginx 优化：静态资源与图片添加 `Cache-Control` 分层策略 + Brotli/Gzip；安全头 (CSP/Strict-Transport-Security/Referrer-Policy)。
- Lighthouse CI：集成 `lhci` (collect + assert) 进入管线，记录性能历史；首屏/LCP/CLS/SI 指标阈值配置。
- 进一步图片优化：按需生成 AVIF；老文章内容回填 `<picture>`（迁移脚本扫描 img 标签自动补写）。
- 后端指标：新增请求直方图 (latency buckets)、缓存命中率、图片处理耗时指标；接入告警规则（p95/p99）。
- 登录安全：单独登录限流、密码策略校验、可选 2FA；CSRF 策略说明（JWT 放 Cookie 场景需 SameSite/CSRF Token）。
- 构建与发布：CI/CD (测试 -> 构建镜像 -> 迁移 -> 健康检查 -> 灰度)；版本号与 git sha 注入 `/api/v1/health`。
- SEO & 可见性：sitemap.xml 增量生成 / JSON-LD / OpenGraph `og:image` 自动选最大合适变体。
- 断点预取：视网络状况预取下一篇推荐文章 (service worker 或 `<link rel=prefetch>`)。

### 本地快速验证 (PowerShell)
```
docker compose up -d --build
docker compose exec backend flask db upgrade
curl http://localhost:8000/api/v1/health
```
（若 Windows 无 curl，可使用 `Invoke-WebRequest`。）

### 性能追踪
参考 `PERFORMANCE.md`：包含基线采集、指标目标、建议的 Lighthouse 与 Prometheus 监控切入点。提交优化前后请更新该文档的对比表。后续计划在 CI 中自动产出 `lhci` 报告并存档。

> 如需新增性能实验（e.g. SSR、Edge 缓存、Service Worker 预缓存），建议先在 `PERFORMANCE.md` 记录假设与验证指标，再实施变更，保持可回溯性。

## 11. Phase 2 展望 (未完成项)
- 富文本 Markdown WYSIWYG（Milkdown / TipTap）+ 实时预览 + 历史版本/差异。
- 图片拖拽上传、内联选择与自动 `<picture>` 响应式。
- SEO 元字段 (meta title/description/slug 自定义) & Featured Image。
- 评论线程化 / 点赞 / 收藏 / 作者主页 / 统计面板。
- 更完整的工作流边界测试 (非法状态、权限拒绝) 与调度测试。
- 全文搜索高亮、分页策略优化、前端缓存层更细粒度失效。
- 国际化 (i18n) 完善与 UI 设计/性能优化 (懒加载 / Code Splitting / 图片占位符)。

## 12. 目录结构 (摘录)
```
backend/app
  articles/ ... 文章路由与工作流
  uploads/ ... 图片上传
  search/ ... 索引与查询
frontend/src
  governance/ ... 角色 & 工作流 & 错误码生成文件
  views/ArticleDetail.vue
  views/NewArticle.vue
```

## 13. 贡献 & 脚本
- OpenAPI 导出：`python -m scripts.export_openapi`
- 前端治理同步：`npm run governance:sync` (包含 drift 检测 `governance:check`)

---
如需进一步问题排查，可查看后端 JSON 日志 (含 request_id) 与 Prometheus 指标。

## 一键生产部署 (Docker)

提供精简生产编排 `docker-compose.prod.yml`，包含：
backend (Gunicorn)、celery_worker、celery_beat、frontend (Nginx 静态)、gateway (总 Nginx 反向代理)、MySQL、Redis、MeiliSearch。

### 快速开始
1. 复制环境变量文件
  cp .env.example .env  (Windows PowerShell: Copy-Item .env.example .env)
  修改 `.env` 中 JWT_SECRET_KEY、数据库账号等敏感项。
2. 启动
  docker compose -f docker-compose.prod.yml up -d --build
3. 访问
  前端: http://localhost
  API:   http://localhost/api/v1/health
4. 查看日志
  docker compose -f docker-compose.prod.yml logs -f backend

首次启动包含自动迁移 (entrypoint 执行 `flask db upgrade`)；可通过环境变量 AUTO_MIGRATE=0 关闭。

### 部署脚本 (Windows)
执行: `pwsh deploy/deploy.ps1` （可加 `-Rebuild` 强制重建、`-Pull` 预拉镜像）。

### 可调参数 (环境变量)
| 变量 | 说明 | 默认 |
| ---- | ---- | ---- |
| AUTO_MIGRATE | 启动时自动 `flask db upgrade` | 1 |
| REINDEX_ON_START | 启动后重建搜索索引 | false |
| FLASK_CONFIG | Flask 配置模式 | production |

### 数据持久化卷
| 卷 | 作用 |
| ---- | ---- |
| mysqldata | MySQL 数据库文件 |
| meilidata | MeiliSearch 数据 |
| uploads | 上传媒体文件 |

### 典型运维命令
| 目的 | 命令 |
| ---- | ---- |
| 进入后端容器 | docker compose -f docker-compose.prod.yml exec backend bash |
| 手动迁移 | docker compose -f docker-compose.prod.yml exec backend flask db upgrade |
| 重建索引 | docker compose -f docker-compose.prod.yml exec backend python -m scripts.reindex_search |
| 查看 celery 日志 | docker compose -f docker-compose.prod.yml logs -f celery_worker |

### 下一步可选增强
- 将 gateway Nginx 改为自定义镜像（加入安全头 / Brotli）。
- 在 CI 中构建并推送镜像（`flask-blog-backend:git-sha`）。
- 使用 `.env.prod` 区分生产变量并在 pipeline 注入 Secrets。
- 引入 Traefik / Caddy 自动 HTTPS。

