# 代码审查方案

基于行业最佳实践（Google CR Standards、ThoughtWorks Tech Radar、OWASP Top 10），从 7 个维度对项目进行系统性审查。

---

## 一、审查范围与轮次

### 1.1 范围矩阵

| 模块 | 后端 | 前端 | 基础设施 |
|------|------|------|----------|
| Blueprint/模块 | articles, auth, comments, search, backup, security, media, taxonomy, uploads, settings, logs, metrics | views, components, stores, api, utils, router | Docker, CI, config |
| 规模 | ~50 个 Python 文件 | ~70 个 Vue/JS/TS 文件 | ~20 个配置文件 |

### 1.2 审查轮次

```
Round 1: 架构 & 设计           (2 人·日)
Round 2: 安全 & 数据流          (1 人·日)
Round 3: 性能 & 可观测性        (1 人·日)
Round 4: 测试 & CI/CD           (1 人·日)
Round 5: 代码质量 & 一致性      (1 人·日)
```

每轮产出：问题清单（P0/P1/P2）+ 修复建议 + 预计工时。

---

## 二、审查维度与 Checklist

### 2.1 架构与设计（Round 1）

#### 2.1.1 模块职责与边界

```
[ ] Blueprint 之间是否有循环依赖？
    检查点: 查看 backend/app/__init__.py 中 register_blueprints 顺序
            grep -rn "from \.\.\." backend/app/*/routes.py | grep -v __init__
    风险: articles 模块 import 了大量跨模块类型 (Tag, Category, AuditLog 等)

[ ] Service 层是否与 Route 层充分分离？
    标准: Route 只做 HTTP 编排 (参数提取 + 响应序列化)，业务逻辑在 Service
    当前: articles 已拆分，但 auth/comments/search 等模块的 routes.py 中可能仍有混合

[ ] 前端组件层级是否合理？
    标准: views/ → 页面级 (路由)；components/ → 可复用 UI 原子
    检查: src/components 下是否存在只被单一 view 引用的 "假通用组件"？
```

#### 2.1.2 数据模型

```
[ ] SQLAlchemy 模型与迁移是否对齐？
    检查点: backend/app/models.py 字段定义 vs migrations/versions/ 中的变更
    命令:   flask db check （验证 model 与 migration 头一致）

[ ] 软删除机制是否一致？
     标准: 所有模型统一使用 deleted_at 或 deleted 布尔字段
     当前: Article 有 deleted 字段，但其他关联表(User/Comment/Tag/Category)呢？

[ ] 索引覆盖是否合理？
     检查点: 对 WHERE / JOIN / ORDER BY 中出现的字段，检查是否有对应索引
     命令:   SHOW INDEX FROM articles; SHOW INDEX FROM article_versions;
```

#### 2.1.3 API 设计

```
[ ] RESTful 命名是否一致？
     标准: 资源用复数名词，路径用小写 kebab-case
     例子: /articles/public/ vs /public/articles/ — 检查是否存在不一致

[ ] 响应格式是否统一？
     标准: { code, message, data } 三字段
     检查点: grep -rn "jsonify" backend/app/ — 查看是否有非标准格式

[ ] 分页参数是否统一？
     标准: page + page_size → 响应: { total, page, page_size, has_next, list }
     检查点: 所有列表接口是否都遵循同一模式？
```

### 2.2 安全审查（Round 2）

#### 2.2.1 OWASP Top 10 对照

```
[ ] A01: 权限控制失效 (Broken Access Control)
     检查点:
     - 每个需要鉴权的接口是否都有 @require_auth / @permission_required？
     - grep -rn "def .*_bp\.route" 得到的路由列表，逐条确认鉴权覆盖
     - 是否有公开接口意外暴露了内部数据？（如 GET /articles/ 默认返回 all status）

[ ] A02: 加密失败 (Cryptographic Failures)
     检查点:
     - JWT 密钥是否为生产环境唯一值？(grep JWT_SECRET)
     - 密码存储是否使用 bcrypt？(grep password 检查 models.py)

[ ] A03: 注入 (Injection)
     检查点:
     - SQLAlchemy ORM 是否有 raw SQL？(grep "text(\|execute(")
     - Markdown 渲染后的 HTML 是否经过 Bleach 清洗？(grep bleach / render_and_sanitize)
     - 前端是否使用 DOMPurify？(grep dompurify / DOMPurify)

[ ] A05: 安全配置 (Security Misconfiguration)
     检查点:
     - DEBUG 模式是否在生产环境禁用？
     - CORS 配置是否过松？(grep CORS_ORIGINS)
     - CSP 头是否配置？(grep Content-Security-Policy)
```

#### 2.2.2 认证与授权

```
[ ] JWT 双 Token 机制是否完整？
     - Access Token 有效期是否合理？(默认 15-30 min)
     - Refresh Token 是否支持吊销？(黑名单 Redis)
     - Token 刷新时旧 Token 是否立即失效？

[ ] 角色权限矩阵是否包含所有接口？
     检查点: ROLE_MATRIX (security/enforcer.py) 是否覆盖了所有 api 端点？
     方法:   提取所有 route 定义的权限装饰器 vs ROLE_MATRIX 键集合做差集

[ ] 细粒度资源权限是否完善？
     标准: 作者只能编辑自己的文章，编辑/管理员可以编辑全部
     检查点: 每个 "by id" 接口是否校验了资源所有权？
```

#### 2.2.3 敏感信息

```
[ ] 凭据是否硬编码？
     命令: grep -rn "password\|secret\|key\|token" backend/ --include="*.py" | grep -v "\.env\|JWT_SECRET\|import\|test"

[ ] 日志是否可能泄露 PII？
     检查点: 是否有日志记录了 request.data / request.json 未脱敏？
```

### 2.3 性能审查（Round 3）

#### 2.3.1 查询效率

```
[ ] N+1 查询检测
     检查点: serialize_article 中是否有循环内查询？
     -> 在序列化时执行了 ArticleLike.query.filter_by(article_id=a.id).count()
     -> 如果用 ORM 的 selectinload / joinedload 预加载可优化

[ ] 列表接口是否有全表扫描风险？
     检查点: list_articles / public_list_articles 的 WHERE 条件是否都有索引

[ ] 大字段是否被不必要地加载？
     检查点: 列表接口是否 SELECT 了 content_md/content_html 大字段？
     命令:   查看 Article 模型的 __tablename__ 和列表查询的 .options()
```

#### 2.3.2 缓存策略

```
[ ] 缓存穿透 / 击穿 / 雪崩防护
     检查点: 
     - 空结果是否缓存？（防穿透）
     - 热点 key 是否有过期时间分散？（防雪崩）
     - 重建缓存是否有互斥锁？（防击穿）

[ ] 缓存失效是否完整？
     检查点: 文章更新/删除/状态变更时，是否清除了所有相关缓存 key？
     -> invalidate_article_cache 中的 scan_iter 模式可能漏掉新的 key 模式

[ ] ETag 缓存是否有效？
     检查点: compute_etag 的计算成本是否值得？对大响应体计算 MD5 本身也有开销
```

#### 2.3.3 前端性能

```
[ ] 代码分割 (Code Splitting) 是否充分？
     检查点: router.js 中哪些页面使用了动态 import() vs 静态 import
     -> Home, Login, NewArticle 是静态导入，打包在一个初始 chunk 中

[ ] 图片优化是否到位？
     检查点: 多尺寸生成 (lg/md/sm/thumb) + WebP + lazy loading
     -> 检查前端组件是否插入了 <picture> + srcset

[ ] 包体积是否可控？
     命令:   cd frontend && npx vite-bundle-analyzer
     关注:  element-plus + echarts + vditor 等重型依赖是否按需加载？
```

### 2.4 可观测性（Round 3）

```
[ ] 结构化日志是否到位？
     标准: JSON 格式日志，包含 request_id, user_id, action, duration_ms
     检查点: backend/app/utils/logging_utils.py 的实现

[ ] Prometheus 指标是否覆盖关键路径？
     检查点: /metrics 端点暴露的指标
     - 请求总数 / 延迟分布 / 错误率
     - 缓存命中率
     - 文章发布计数、搜索查询计数

[ ] 健康检查是否足够？
     检查点: /api/v1/health 是否检查了 DB / Redis / MeiliSearch 连接？

[ ] 审计日志覆盖范围？
     检查点: log_action 被调用的位置列表
     -> 确认是否所有 "写操作" (create/update/delete/approve/reject/submit) 都记录了审计
```

### 2.5 测试审查（Round 4）

#### 2.5.1 测试覆盖

```
[ ] 后端测试覆盖盲区
     命令:   cd backend && pytest --cov=app --cov-report=term-missing
     目标:   核心业务模块 > 80%，整体 > 60%
     当前已覆盖: articles, auth — 需确认 coverage 报告

[ ] 前端测试覆盖盲区
     命令:   cd frontend && npx vitest run --coverage
     当前:   仅 3 个 spec 文件 (editorRoundTrip, permission, usePagedQuery)
     盲区: stores, views, api 层完全未覆盖

[ ] E2E 测试
     当前: 无
     核心路径: 注册 → 登录 → 创建文章 → 提交审核 → 审核通过 → 发布 → 前台可见
```

#### 2.5.2 测试质量

```
[ ] 测试独立性
     检查点: tests/ 中是否有测试依赖顺序（如 test_01、test_02 命名）？
     -> 每个测试应独立创建自己的数据

[ ] Mock 边界
     标准: 外部服务 (Redis/MeiliSearch) 应 mock；数据库推荐真实 SQLite 内存
     当前: tests/conftest.py 是否使用 FakeRedis？

[ ] 异常路径覆盖
     检查点: 是否测试了 401/403/404/409 等错误响应？
```

### 2.6 CI/CD 审查（Round 4）

```
[ ] CI Pipeline 完整性
     检查点: .github/workflows/ci.yml
     - 每次 push 是否都触发？
     - lint / test / build 是否并行执行？
     - 测试失败是否阻塞合并？

[ ] 构建缓存
     - Python pip 是否使用缓存？(actions/cache)
     - Node modules 是否缓存？
     - Docker 构建层是否缓存？

[ ] 部署 Pipeline (build-and-push.yml)
     检查点:
     - 镜像标签策略是否合理？(git-sha + semver + latest)
     - 是否做了安全扫描？(trivy / snyk)
     - 回滚策略是什么？
```

### 2.7 代码质量（Round 5）

#### 2.7.1 风格与一致性

```
[ ] Python 代码风格
     命令:   black --check backend/ && flake8 backend/
     检查:   pyproject.toml 配置是否正确生效

[ ] 前端代码风格
     命令:   eslint src && prettier --check src/
     检查:   是否有大量 no-console 警告？（生产环境不应有 console.log）

[ ] 命名一致性
     检查点:
     - 后端: 函数名是否 snake_case? 类名是否 PascalCase?
     - 前端: 组件文件 PascalCase? 工具函数 camelCase?
```

#### 2.7.2 错误处理

```
[ ] 全局异常处理是否到位？
     检查点: BusinessError handler 是否覆盖了所有蓝图？
     -> 未 catch 的异常是否会返回 500 和堆栈信息？（生产环境不应暴露）

[ ] 外部调用容错
     检查点:
     - Redis 不可用时是否正常降级？
     - MeiliSearch 不可用时文章创建/更新是否不受影响？
     - 图片处理失败是否不阻塞文章保存？
```

#### 2.7.3 配置管理

```
[ ] 环境变量治理
     检查点:
     - .env.example 是否与 .env.dev 同步？
     - 是否有未文档化的环境变量？
     - 是否有硬编码的 "magic number"?

[ ] Flask Config 管理
     检查点: app/__init__.py 中的 create_app 配置
     - 不同环境 (dev/test/prod) 是否有独立配置类？
     - 秘密是否只在运行时注入，而非代码中？
```

---

## 三、工具链

### 3.1 自动化工具体系

```
┌─────────────────────────────────────────────────┐
│                  PR 触发                          │
├─────────────────────────────────────────────────┤
│   lint-python   │   lint-frontend   │   build    │
│   (black/       │   (eslint/        │   (npm     │
│    flake8)      │    prettier)      │    build)  │
├──────────────────┴──────────────────┴───────────┤
│   test-backend             test-frontend         │
│   (pytest --cov)           (vitest)              │
├─────────────────────────────────────────────────┤
│   Bandit (Python SAST)   │   SonarQube (可选)    │
├─────────────────────────────────────────────────┤
│   Docker build + Trivy scan (安全漏洞扫描)       │
└─────────────────────────────────────────────────┘
```

### 3.2 建议引入的审查工具

| 工具 | 用途 | 引入方式 |
|------|------|----------|
| `bandit` | Python 安全静态扫描 | `pip install bandit` → `bandit -r backend/` |
| `safety` | Python 依赖漏洞检查 | `pip install safety` → `safety check -r requirements.txt` |
| `npm audit` | 前端依赖漏洞检查 | `cd frontend && npm audit` |
| `mypy` | Python 类型检查 | `pip install mypy` → `mypy backend/` |
| `vue-tsc` | Vue/TS 类型检查 | `cd frontend && npx vue-tsc --noEmit` |

### 3.3 手动审查辅助脚本

审查启动时应执行的基线命令：

```bash
# === 路由清单 ===
grep -rn "@.*_bp\.route" backend/app/ | sed 's/.*@//' | sort

# === 鉴权覆盖 ===
grep -rn "def " backend/app/*/routes.py | grep "route" | wc -l
grep -rn "@require_auth\|@require_roles\|@permission_required" backend/app/*/routes.py | wc -l
# 两者对比可发现未鉴权接口

# === 未捕获异常风险 ===
grep -rn "raise BusinessError" backend/app/ --include="*.py" | wc -l
grep -rn "except BusinessError" backend/app/ --include="*.py" | wc -l
# 差即代表依赖全局 error handler 兜底

# === 硬编码检查 ===
grep -rn "'http://\|'https://\|'localhost\|:5000\|:5173\|:8000" backend/app/ --include="*.py" | grep -v test | grep -v "#"

# === 前端未使用组件 ===
cd frontend && for f in src/components/*.vue; do
  name=$(basename $f .vue)
  count=$(grep -rn "$name" src/ --include="*.vue" --include="*.js" --include="*.ts" | grep -v "$f" | wc -l)
  if [ $count -eq 0 ]; then echo "UNUSED: $f"; fi
done
```

---

## 四、缺陷分级标准

| 级别 | 定义 | 响应时间 | 示例 |
|------|------|----------|------|
| **P0** | 生产崩溃/数据丢失/安全漏洞 | 立即修复 | SQL 注入、越权访问未发布文章、无权限用户可删除文章 |
| **P1** | 核心功能受限/严重性能问题 | 24h 内 | 文章发布后不可见、N+1 导致列表页 >5s、缓存污染导致数据错乱 |
| **P2** | 非核心功能异常/轻微性能 | 72h 内 | 收藏列表分页异常、搜索高亮缺失、错误信息不友好 |
| **P3** | 代码异味/风格问题/文档缺失 | 纳入迭代 | 命名不一致、缺少注释、未使用的变量 |

---

## 五、审查输出模板

每轮审查结束后生成如下报告：

```markdown
## Round N: [审查维度]

### P0 问题
- **[标题]** 路径:行号 — 简述。建议修复方案。

### P1 问题  
- **[标题]** 路径:行号 — 简述。建议修复方案。

### P2/P3 问题
- ...

### 亮点
- 值得推广的做法: ...
```

---

## 六、建议执行顺序

```
Week 1: 安全审查 (Round 2) → 最高优先级，上线前必须完成
Week 1: 架构审查 (Round 1) → 确定后续重构方向
Week 2: 测试审查 (Round 4) → 补充关键路径测试，为重构建立安全网
Week 2: 性能审查 (Round 3) → 识别性能瓶颈
Week 3: CI/CD 审查 (Round 4) → 加固交付管道
Week 3: 代码质量 (Round 5) → 一致性清理，打磨
```

安全先行：P0 级别的安全问题必须在进入下一轮审查前修复。
