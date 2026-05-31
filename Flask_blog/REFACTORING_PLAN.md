# 项目优化实施方案

基于当前代码库的工程审计结果，按优先级分阶段推进。每个阶段独立可交付，避免长周期分支带来的合并痛苦。

---

## 阶段一：清理与收敛（预计 1-2 天）

### 1.1 删除死代码

以下文件可确认删除（有替代方案且无引用）：

| 文件 | 理由 |
|------|------|
| `frontend/src/App-backup.vue` | 旧版 App 备份，`App.vue` 为当前使用 |
| `frontend/src/main-debug.js` | 调试入口，`main.js` 为当前使用 |
| `frontend/src/utils/markdownProcessor.simple.js` | 另有两套实现，且 `markdownProcessor.js` 为主入口 |
| `frontend/src/utils/markdownProcessor.reliable.js` | 同上 |
| `frontend/src/utils/debugKaTeX.js` | 调试文件 |
| `frontend/src/utils/testColorFix.js` | 测试文件 |
| `frontend/src/utils/testMarkdown.js` | 测试文件 |
| `frontend/test.html` | 独立测试页面 |
| `frontend/public/tinymce/` | 如使用 TinyMCE 组件则保留，否则可移除 |
| `backend/run_no_reload.py` | `run.py` 为主入口 |
| `backend/run_smart_routing.py` | `run.py` 为主入口 |
| `backend/create_external_db.py` | `create_new_external_db.py` 为新版 |
| `backend/recreate_external_db.py` | 同名逻辑包含在 `backup/` 模块中 |
| `backend/debug_*.py` | 所有 debug_ 前缀文件均为调试用途 |
| `cc_0904.txt` | 不明内容的文本文件 |
| `浏览器日志/` 目录 | 调试日志不应提交 |
| `csp-debug.html` | 调试页面 |

### 1.2 收敛多套实现

**编辑器组件（9 个 → 保留 1-2 个）：**
- 选择其中一种作为标准编辑器（建议 `BlockEditorV2.vue` 或 `TinyMCEEditor.vue`），其余标记删除
- 如果不同场景需要不同的编辑器（例如快速编辑 vs 富文本），最多保留两种
- 删除 `VditorEditor.vue`、`SimpleHTMLEditor.vue`、`PureTinyMCEEditor.vue`、`SimpleTinyMCE.vue`、`RichMarkdownEditor.vue`、`BlockEditor.vue`、`BlockEditorShiki.vue` 中未被选中的文件

**后端启动脚本（3 个 → 1 个）：**
- 统一使用 `run.py`，删除 `run_no_reload.py` 和 `run_smart_routing.py`
- 不同的启动模式通过环境变量或命令行参数控制：`python run.py --no-reload` 或 `FLASK_RELOAD=0 python run.py`

**Markdown 处理器（3 个 → 1 个）：**
- 保留 `markdownProcessor.js`，删除 `*.simple.js` 和 `*.reliable.js`
- 如确有不同处理需求，通过配置参数区分，而不是复制文件

### 1.3 清理 .gitignore

追加以下规则：

```gitignore
# 自动生成的代码（构建时生成，不应提交）
frontend/src/generated/

# 重复的 OpenAPI 定义
openapi.json
backend/openapi.json
frontend/openapi.json

# 根目录的 npm 文件（如果前端在 frontend/ 下管理）
package.json
package-lock.json

# 环境文件（已提交的 .env.dev 应删除后再忽略）
.env.dev
```

并执行 `git rm --cached` 删除已跟踪的产物文件：

```bash
git rm --cached .DS_Store
git rm --cached .env.dev
git rm --cached cc_0904.txt
git rm --cached -r 浏览器日志/
git rm --cached backend/openapi.json frontend/openapi.json openapi.json
```

### 1.4 删除未使用的依赖

**后端 `requirements.txt`：**
- `yapf==0.40.2` — 代码格式化工具，应移到 `requirements-dev.txt`
- `mysqlclient==2.2.4` — 与 `PyMySQL==1.1.1` 同为 MySQL 驱动，选一个即可
- 注释掉的 boto3/oss2/cos 依赖直接移除

**前端 `package.json`：**
- 查看 `import` 语句确认未被引用的包（如编辑器组件目前实际使用哪一套，未使用的编辑器库可移除）

---

## 阶段二：工程基础设施（预计 2-3 天）

### 2.1 引入代码规范工具

**后端：**
- 新增 `requirements-dev.txt`，加入：
  ```
  flake8==7.1.0
  black==24.4.2
  isort==5.13.2
  mypy==1.10.0
  pytest-cov==5.0.0
  ```
- 在项目根目录创建 `pyproject.toml`（或 `setup.cfg`）配置 flake8/black/isort：
  ```toml
  [tool.black]
  line-length = 88
  target-version = ["py311"]

  [tool.isort]
  profile = "black"
  line_length = 88
  ```
- 添加 `Makefile` 或脚本快捷方式：
  ```makefile
  lint: black --check . flake8 .
  format: black . isort .
  typecheck: mypy backend/
  ```

**前端：**
- 启用 eslint（`package.json` 中已有 `"lint": "eslint src --ext .js,.ts,.vue || true"` 但无配置文件）
- 创建 `eslint.config.js`：
  ```js
  import pluginVue from 'eslint-plugin-vue'
  import ts from '@typescript-eslint/eslint-plugin'

  export default [
    ...pluginVue.configs['flat/recommended'],
    { rules: { /* 团队共识规则 */ } }
  ]
  ```
- 添加 prettier 配置 `frontend/.prettierrc`：
  ```json
  {
    "semi": false,
    "singleQuote": true,
    "tabWidth": 2,
    "trailingComma": "all"
  }
  ```
- 在 `package.json` 的 scripts 中加入 `"format": "prettier --write src/"`

### 2.2 补充 CI 配置

创建 `.github/workflows/ci.yml`：

```yaml
name: CI

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install flake8 black isort
      - run: black --check backend/
      - run: flake8 backend/
      - run: isort --check-only backend/

  test-backend:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8
        env: { MYSQL_ROOT_PASSWORD: test, MYSQL_DATABASE: blog_test }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r backend/requirements.txt
      - run: pip install pytest pytest-cov
      - run: cd backend && pytest --cov=app

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd frontend && npm ci
      - run: cd frontend && npm run test
      - run: cd frontend && npm run lint

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd frontend && npm ci && npm run build
```

### 2.3 统一 API 调用层

当前三套 API 调用方式并存：
- `src/api/index.js` — 统一出口（推荐保留）
- `src/api/backup.js`、`src/api/media.js` — 独立模块
- `src/generated/services/` — 自动生成代码

**方案：**
1. 选择以 `src/generated/services/` 为唯一 API 层（自动生成，类型安全），或
2. 以 `src/api/` 为唯一层（手写，灵活）
3. 将 `src/generated/` 加入 `.gitignore`，CI 中执行 `npm run codegen`

推荐选方案 1，因为项目已投资 OpenAPI 代码生成，且 TypeScript 类型是自动生成的增值。

---

## 阶段三：架构治理（预计 2-3 天）

### 3.1 后端路由瘦身

当前 `articles/routes.py` 包含了大量业务逻辑（工作流判断、权限校验、SEO 字段处理）。

**重构模式：**
```
articles/
  routes.py      — 仅做 HTTP 编排（参数提取、路由装饰、响应返回）
  service.py     — 业务逻辑（工作流、权限校验、缓存策略）
  schemas.py     — 请求/响应 Pydantic 模型（如有）
```

示例拆分：

```python
# articles/routes.py
@articles_bp.route('/<id>/submit', methods=['POST'])
@jwt_required()
def submit_article(id):
    user_id = get_jwt_identity()
    article = ArticleService.submit_for_review(id, user_id)
    return jsonify(article_schema.dump(article))

# articles/service.py
class ArticleService:
    @staticmethod
    def submit_for_review(article_id, user_id):
        article = Article.query.get_or_404(article_id)
        if article.author_id != user_id:
            raise Forbidden("只有作者才能提交审核")
        if article.status != ArticleStatus.DRAFT:
            raise Conflict("仅草稿状态可提交审核")
        article.status = ArticleStatus.PENDING_REVIEW
        db.session.commit()
        cache.invalidate_article(article_id)
        return article
```

这个模式可以逐步推广 — 不要求一役全改，但**新功能必须按此模式**。

### 3.2 前端路由与权限指令

- `src/router.js` 中目前路由集中定义，建议按 feature 分组（public / auth / admin），支持懒加载（现在可能已实现，需确认）
- `src/directives/permission.ts` 权限指令已存在，检查是否在所有管理页面中一致应用

### 3.3 统一前端状态管理

- `src/stores/session.js` 和 `src/stores/user.js` 职责有重叠
- 建议合并为一个 `authStore`（认证状态 + 用户信息），分离出 `preferenceStore`（主题、设置等）

---

## 阶段四：测试加固（预计 2-3 天）

### 4.1 后端测试补充

当前已有 14 个测试文件，覆盖了访问控制、ETag、搜索等。需重点关注覆盖率盲区：

- **媒体管理**：`media/` 模块无测试
- **备份恢复**：`backup/` 模块测试仅 `test_backup_integration.py`，未覆盖增量和恢复边界条件
- **日志管理**：`logs/` 模块无测试
- **安全管理**：`security/` 模块无测试

在 `pyproject.toml` 中设置覆盖率门槛：

```toml
[tool.pytest.ini_options]
addopts = "--cov=app --cov-report=term-missing --cov-fail-under=60"
```

### 4.2 前端测试补充

当前仅 3 个测试文件（工具函数），需要补充：

- **组件测试**：核心组件如 `ArticleContentRenderer.vue`、`CommentsThread.vue`、`ImageUploader.vue`
- **页面测试**：`Login.vue`、`Home.vue` 等关键页面
- **集成测试**：API 客户端与 store 的交互

使用现有工具链（vitest + @vue/test-utils），补全流程：

```bash
cd frontend
npm run test:ui   # 交互式运行现有测试
# 补充测试后，将 coverage 加入 vitest.config.ts
```

### 4.3 E2E 测试

使用 Playwright 补充关键路径的 E2E 测试：

```
e2e/
  login.spec.ts         # 登录 → 跳转首页
  article-flow.spec.ts  # 创建文章 → 提交审核 → 审核通过 → 发布
  search.spec.ts        # 搜索 → 查看结果 → 进入详情
```

---

## 阶段五：配置与安全加固（预计 1-2 天）

### 5.1 环境变量治理

- 删除已提交的 `.env.dev`
- 创建 `.env.example` 作为唯一模板（已存在，确保是最新的）
- 在 `deploy.sh` 和部署文档中强调：`cp .env.example .env` 后**必须修改所有密钥**

### 5.2 依赖锁定

- 后端使用 `pip freeze > requirements-lock.txt` 生成锁定文件（可选，但推荐用于生产部署）
- 或者使用 `pip-tools`：
  ```bash
  pip install pip-tools
  pip-compile backend/requirements.in -o backend/requirements.txt
  ```

### 5.3 Dockerfile 精简

- 合并 `Dockerfile.backend` 和 `Dockerfile.backend.dev`，通过构建参数区分：
  ```dockerfile
  ARG ENV=production
  RUN if [ "$ENV" = "development" ]; then pip install -r requirements-dev.txt; fi
  ```
- 为所有 Dockerfile 添加 `.dockerignore`（确保不复制 `.env`、`node_modules`、`__pycache__`、`git` 目录等）

---

## 执行优先级速查表

```
优先级    阶段    操作                         预计工时
─────────────────────────────────────────────────────
P0        一      删除死代码 + 清理 .gitignore    0.5天
P0        一      收敛多套实现（编辑器等）         0.5天
P1        二      引入 lint/format 配置           0.5天
P1        二      配置 CI                         0.5天
P1        三      后端路由瘦身（articles 模块示范） 1天
P2        二      统一 API 调用层                  0.5天
P2        三      前端 store 合并                  0.5天
P2        四      补充测试覆盖率                   2天
P3        五      环境变量 + Docker 治理           1天
P3        四      E2E 测试接入                    1天
```

**总计：约 8 天**，可并行推进 P1/P2 的不同轨道。

---

## 落地原则

1. **不做大爆炸式重构** — 每次改动一个模块，提交一个 PR，测试通过再合入
2. **每阶段独立可交付** — P1 做完就提交合并，不等 P2
3. **不新增抽象** — 删代码而不是加封装层，缩减代码量优先于设计优雅
4. **删除是最高效的优化** — 不明用途的文件先删，没人报错就是正确的
