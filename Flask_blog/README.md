# Flask Blog 平台

一个具备**版本控制、工作流审批、评论审核、搜索、点赞收藏、定时发布与动态 SEO** 的内容平台示例，前后端分离、Docker 一键部署。

> 📚 完整文档中心见 [docs/README.md](./docs/README.md)（架构、设计、产品、运维、工程规范分目录）。

## 核心特性

- **角色 / 权限**：author / editor / admin 工作流（draft → pending_review → published → archived/rejected），统一 `security/enforcer.py` 强制层。
- **文章**：Markdown + 安全渲染（Bleach）+ 版本快照 & 回滚 + 定时发布 + SEO 字段 + 特色图（多尺寸/焦点裁剪）。
- **搜索**：MeiliSearch 索引已发布文章（失效回退 DB fuzzy）。
- **互动**：点赞、收藏、树状评论（审核流）。
- **媒体库**：图片多尺寸/WEBP/LQIP 生成、文件夹管理、焦点裁剪。
- **性能**：Redis 缓存 + ETag 协商缓存 + 前端路由按需分包 + 图片懒加载。
- **安全**：JWT Access/Refresh + 刷新吊销、CSP/安全头、HTML 清洗、全局+细化限流、安全监控面板。
- **备份恢复**：物理备份引擎、增量备份、外部元数据系统、恢复管理器。
- **可观测**：Prometheus 指标、sitemap.xml / robots.txt、审计日志、日志管理。

## 技术栈

- **后端**：Flask（应用工厂）、SQLAlchemy、Flask-Migrate（Alembic）、Flask-Bcrypt、Flask-Limiter、Redis、Celery、APScheduler、MeiliSearch、Prometheus client、Bleach、Flask-Babel。
- **前端**：Vue 3、Vite、Pinia、vue-router（动态 import）、Vditor、highlight.js / Shiki / KaTeX、Element Plus、Tailwind。
- **质量**：pytest（后端 300+）、Vitest（前端）、Playwright E2E、vue-tsc、eslint、black/flake8/isort、mypy、GitHub Actions（lint×2 / test×2 / typecheck×2 / openapi-drift / e2e / lhci）。

## 快速开始

### 一键 Docker 部署

```bash
./deploy.sh                 # 标准生产部署（bash 唯一入口）
./deploy.sh --rebuild       # 无缓存重建
./deploy.sh --skip-build    # 跳过构建
COMPOSE_FILE=docker-compose.monitoring.yml ./deploy.sh   # 监控编排
```

或直接 `docker compose up -d --build`（dev）/ `docker compose -f docker-compose.prod.yml up -d --build`（生产）。
生产编排含 backend(Gunicorn)、celery_worker、celery_beat、frontend(Nginx)、gateway(Nginx 反代)、MySQL、Redis、MeiliSearch；容器以非 root 运行，启动自动 `flask db upgrade`（可用 `AUTO_MIGRATE=0` 关闭）。

### 本地开发

后端：
```bash
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
flask db upgrade
python run.py        # 或 FLASK_APP=app:create_app flask run
```

前端：
```bash
cd frontend
npm install
npm run codegen      # 下载 OpenAPI -> 生成客户端 + 治理数据（后端未启动时回退 backend/openapi.json）
npm run dev          # http://localhost:5173（代理 /api/v1 到后端）
```

## 环境变量（节选）

| 变量 | 说明 | 默认 |
| ---- | ---- | ---- |
| DATABASE_URL | 数据库连接（MySQL 推荐） | sqlite:///dev.db |
| REDIS_URL | Redis 地址 | redis://127.0.0.1:6379/0 |
| MEILISEARCH_URL | 搜索服务 | http://localhost:7700 |
| JWT_SECRET_KEY | JWT 密钥 | dev-secret |
| APP_VERSION | 应用版本（覆盖 config.py 默认） | 1.0.0 |
| RATE_LIMIT_DEFAULT_MINUTE | 默认分钟限速 | 200 |
| UPLOAD_DIR / MAX_IMAGE_SIZE / ALLOWED_IMAGE_TYPES | 上传配置 | uploads / 2MB / jpeg,png,webp |

完整模板见 `.env.example`。

## 工作流与权限

```
draft -> pending_review -> (published | rejected | archived)
rejected -> draft / pending_review
scheduled -> published / archived
published -> archived (或通过 unpublish 回到 draft)
```

核心动作权限：

| 权限 | 角色 |
| ---- | ---- |
| workflow:submit | author, editor, admin |
| workflow:approve / reject / publish | editor, admin |
| articles:create / update | author, editor, admin |
| articles:delete | editor, admin |
| users:change_role | admin |

前端治理数据（roleMatrix / workflowTransitions / errorCodes）由后端 OpenAPI 的扩展字段生成，`npm run governance:check` 校验漂移。

## API 与 OpenAPI

- 运行时动态生成 OpenAPI：`GET /spec`（前端代码生成/下载默认端点）。
- 规范快照：`backend/openapi.json`（单一来源；`python -m scripts.export_openapi` 重新生成，CI 校验无漂移）。
- 前端代码生成：`npm run codegen`（openapi-typescript-codegen 生成 `src/generated`）。

### 上传错误码

| Code | 含义 |
| ---- | ---- |
| 4401 | 缺少文件或文件名为空 |
| 4402 | 类型不允许（返回 allowed 列表） |
| 4403 | 文件过大（返回 max） |

### 速率限制（示例）

- 全局默认：`RATE_LIMIT_DEFAULT_*`（200/min, 2000/day）
- `/api/v1/articles/<id>/like`、`/bookmark`：30/min；`/api/v1/comments/`：20/min；`/api/v1/uploads/image`：20/min

## 测试

```bash
# 后端（含覆盖率门槛 50%）
cd backend && python -m pytest tests/

# 前端
cd frontend && npm run typecheck && npm run test:cov && npm run build

# E2E（需 docker compose up -d 启动完整后端 + 数据库）
cd frontend && npx playwright test

# lint / 类型
cd backend && flake8 app/ tests/ && black --check app/ tests/ && mypy app
```

## 目录结构（摘录）

```
backend/app
  articles/ auth/ comments/ taxonomy/ users/ media/ backup/
  logs/ settings/ search/ security/ uploads/ metrics/
  services/         # content_sanitizer / image_variants / visitor_tracker
  security/enforcer # 统一权限 + 工作流状态机
  docs/openapi.py   # 动态 OpenAPI 组装 + 快照写入
frontend/src
  views/            # 前台 + admin 后台
  components/       # 拆分后的子组件（editor/cover/media/sidebar/backup/admin/home/layout）
  api/              # 统一 API 层（token 刷新 + ETag 缓存）
  governance/       # 角色 / 工作流 / 错误码生成文件
```

## 部署建议

- 生产：Gunicorn + Nginx 反代（静态与上传分离），HTTPS，JSON 日志，Prometheus 抓取 `/metrics`。
- 数据：MySQL 8（UTF8MB4）定期备份 + 慢查询；Redis 持久化；MeiliSearch 数据卷快照。
- 数据库迁移：`flask db migrate -m "message"` → `flask db upgrade`，可 `python backend/scripts/mysql_check.py` 校验 schema。
- 一键生产部署详见 [docs/operations/deployment.md](./docs/operations/deployment.md)；性能基线见 [docs/operations/performance.md](./docs/operations/performance.md)。

## 贡献

- OpenAPI 导出：`python -m scripts.export_openapi`
- 前端治理同步：`npm run governance:sync`（含 drift 检测 `governance:check`）
- 工程规范与重构进度见 [docs/engineering/standards.md](./docs/engineering/standards.md) 与 [docs/engineering/refactoring-progress.md](./docs/engineering/refactoring-progress.md)。
