# 项目改造进度追踪

> 文档目的：记录两份改造计划（[refactoring-plan.md](./refactoring-plan.md) 五阶段、[refactoring-deep-plan.md](./refactoring-deep-plan.md) 大规模重构）的**执行进度、完成状态与剩余待办**，便于跨环境续接与审查。
> 创建日期：2026-08-14
> 对应计划：[refactoring-plan.md](./refactoring-plan.md)、[refactoring-deep-plan.md](./refactoring-deep-plan.md)

---

## 一、总览

| 维度 | 状态 |
|------|------|
| `refactoring-plan.md` 五阶段 | ✅ 全部完成 |
| `refactoring-deep-plan.md` 大规模重构 | ✅ 基本完成 |
| 后端测试 | ✅ 88/88 通过 |
| 前端测试 | ✅ 20/20 通过 |
| 前端 typecheck | ✅ 0 错误 |
| 前端 lint | ✅ 0 errors |
| 后端 lint（black/flake8/isort） | ✅ 通过 |
| 覆盖率门槛 | ✅ 后端 33%、前端 60%（实际 82.55%） |
| CI job | ✅ 9 个（lint×2 / test×2 / typecheck×2 / e2e / lhci） |
| 与远程同步 | ✅ 工作区干净，main 与 origin/main 一致 |

---

## 二、refactoring-plan.md 五阶段进度

### 阶段一：清理与收敛 — ✅ 完成

| 项 | 状态 | 说明 |
|----|------|------|
| 1.1 删除死代码 | ✅ | App-backup/main-debug/markdownProcessor.simple/debug*/test*/test.html/run_no_reload/run_smart_routing/create_external_db 等已删除 |
| 1.2 收敛多套实现 | ✅ | 编辑器 9→1（VditorEditor）；启动脚本 3→1（run.py）；Markdown 处理器收敛为 markdownProcessor.reliable.js |
| 1.3 清理 .gitignore | ⚠️ 部分 | .env.dev 已清理；**src/generated 与 openapi.json 保留跟踪**（codegen 依赖后端，移除会破坏 CI/构建，评估后放弃） |
| 1.4 删除未使用依赖 | ✅ | yapf/mysqlclient 移除；boto3/oss2/cos 注释清理 |

### 阶段二：工程基础设施 — ✅ 完成

| 项 | 状态 | 说明 |
|----|------|------|
| 2.1 lint/format 工具 | ✅ | requirements-dev.txt + pyproject.toml（black/flake8/isort）+ eslint/prettier 均已配置 |
| 2.2 CI 配置 | ✅ | 9 个 job，含 e2e（MySQL service + Playwright chromium） |
| 2.3 统一 API 调用层 | ✅ | 86 处 apiClient 直接调用 + 6 处原生 fetch 全部迁移到 `@/api` 统一入口；删除 media.js/backup.js wrapper |

### 阶段三：架构治理 — ✅ 完成

| 项 | 状态 | 说明 |
|----|------|------|
| 3.1 后端路由瘦身 | ✅ | 已拆出 service 层的模块：articles / comments / taxonomy / users / media / backup / auth |
| 3.2 前端路由与权限 | ✅ | 6 个路由启用 `props: true`；permission 指令已存在 |
| 3.3 前端状态管理 | ✅ | store 合并为 user.js（session.js 已删） |

### 阶段四：测试加固 — ✅ 完成

| 项 | 状态 | 说明 |
|----|------|------|
| 4.1 后端测试 | ✅ | 88 个测试；media/logs/security 已有覆盖；**新增 test_backup.py（9 个）** |
| 4.2 前端测试 | ✅ | 20 个测试；修复 vitest.setup.ts（node 26 + jsdom 26 localStorage 兼容） |
| 4.3 E2E | ✅ | 3 条 spec（core-flow / article-flow / search）；已接入 CI（e2e job） |

### 阶段五：配置与安全加固 — ✅ 完成

| 项 | 状态 | 说明 |
|----|------|------|
| 5.1 环境变量治理 | ✅ | .env.dev 清理；.env.example 为唯一模板 |
| 5.2 依赖锁定 | ✅ | 新增 backend/requirements-lock.txt（74 个生产包，dev 工具排除） |
| 5.3 Docker 治理 | ✅ | 新增根 .dockerignore；容器非 root；构建上下文精简 |

---

## 三、refactoring-deep-plan.md 进度

### 一、API 调用统一（原 H3）— ✅ 完成

| 步骤 | 状态 | 说明 |
|------|------|------|
| Step 1：补全 src/api/index.js 导出 | ✅ | 新增约 40 个 HandwrittenAPI 方法覆盖全部端点 |
| Step 2：替换 apiClient 直接调用 | ✅ | 86 处迁移（含各 view 局部 API 对象） |
| Step 3：替换直接 fetch 调用 | ✅ | 6 处迁移（VditorEditor/CategoryPage/TagPage/AuthorProfile） |
| Step 4：删除冗余 api 文件 | ✅ | media.js / backup.js 已删除 |

### 二、大文件拆分（原 H1）— ✅ 完成（拆分至可接受规模）

| 文件 | 原行数 | 现行数 | 提取的子组件 |
|------|--------|--------|-------------|
| NewArticle.vue | 3038 | 2800 | TagManager / SEOFields / SchedulePicker / CoverImageEditor |
| ArticleDetail.vue | 2203 | 1663 | ArticleSidebar / ArticleHeader / ArticleActions / ArticleInteractions |
| BackupManagement.vue | 2110 | 1898 | BackupDetailDialog / BackupRecordList / CreateBackupDialog |
| VditorEditor.vue | 1515 | 1270 | vditorToolbar.ts / vditorUploader.ts（前期已完成） |

### 三、页面组件 props 化（原 M2）— ✅ 完成

- 6 个路由启用 `props: true`：NewArticle(edit) / ArticleDetail / AuthorProfile / CategoryPage / TagPage
- 组件均支持 props + 路由参数双通道

---

## 四、执行过程中的额外修复

| 项 | 说明 |
|----|------|
| backup 模块 3 处真实 bug | `size_bytes`→`file_size`；`timezone(timedelta(days=N))` 非法；`get_config` 引用不存在的模型属性 |
| vitest 环境 | node 26 + jsdom 26 下 localStorage 缺失 → vitest.setup.ts 垫片，9 个失败测试归零 |
| errorCodes 生成 | 生成脚本补 JSDoc，避免重新生成时类型回归 |
| .gitignore 误忽略 | `.dockerignore` 曾被 .gitignore 忽略，已修复可跟踪 |

---

## 五、剩余待办（计划外 / 可选）

| 项 | 说明 | 优先级 |
|----|------|--------|
| 其余大文件拆分 | UserManagement(1961) / TagManagement(1860) / ArticleManagement(1596) / Home(1583) — 不在 deep-plan 清单内 | 低 |
| 后端 service 层未全覆盖 | security（模拟数据）/ logs（已有 logging_utils）/ search / settings（逻辑简单）无独立 service.py | 低 |
| E2E 稳定性验证 | e2e job 已配置，但需真实 MySQL 环境跑通验证（CI 运行时问题未实机验证） | 中 |
| 前端覆盖率门槛 | 实际 82.55% > 60% 门槛，可后续上调 | 低 |

---

## 六、相关 Git 记录

| 提交 | 内容 |
|------|------|
| `3f5c1e8` | 前端 typecheck 成为真实 CI 门禁（0 错误） |
| `72b1adf` | 统一 API 层 + 完成改造计划（86 处迁移、组件拆分、测试修复） |
| `8f61c21` | 深度拆分大文件（CoverImageEditor/ArticleHeader/ArticleActions 等 6 个新组件） |
| `d5c958f` | 完成剩余差距（fetch 统一、comments/taxonomy service、覆盖率门槛、backup bug 修复） |
| `2702169` | E2E CI、.dockerignore、依赖锁定、users service 层 |

---

## 七、跨环境续接指引

1. **确认代码最新**：`git pull origin main`（当前 HEAD = `2702169`）。
2. **后端测试**：`cd backend && python -m pytest tests/`（需 `.venv` 或系统 python 已装 requirements）。
3. **前端验证**：`cd frontend && npm ci && npm run typecheck && npm run test:cov && npm run build`。
4. **E2E**：需 `docker compose up -d` 启动完整后端 + 数据库后，`cd frontend && npx playwright test`。
5. **剩余待办**见第五节，按需推进。
