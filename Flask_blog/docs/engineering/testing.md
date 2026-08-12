# 测试体系评估报告

> 评估范围：后端 pytest + 前端 vitest + CI 集成
> 评估标准：Google 测试金字塔（单元 → 集成 → E2E）+ 行业惯例

---

## 一、现状概览

### 1.1 测试数量

| 层级 | 文件数 | 用例数 | 测试框架 |
|------|--------|--------|----------|
| 后端单元/集成 | 14 | 31 | pytest + SQLite + FakeRedis |
| 前端单元 | 4 | 13 | vitest + jsdom |
| E2E | 0 | 0 | — |
| **合计** | **18** | **44** | |

### 1.2 后端测试覆盖模块

```
articles:     ✅ 访问控制(8) + ETag(2) + CRUD(1) + 审核(1) + 删除搜索(1) = 13
auth:         ✅ 登录/注册(1) + 刷新/登出(2) + 改密码(1) = 4
comments:     ✅ 评论创建(1) = 1
search:       ✅ 多标签搜索(4) = 4
likes/bmks:   ✅ 点赞收藏(1) = 1
versions:     ✅ 版本搜索评论权限(3) = 3
etag/score:   ✅ ETag + 热度(5) = 5
───────────────
已覆盖: 7/14 模块      未覆盖: backup, media, logs, security, settings, taxonomy, uploads
```

### 1.3 前端测试覆盖

```
userStore:        ✅ 7用例 (setAuth, fetchUserInfo, logout, 角色getter)
permission:       ✅ 2用例 (指令权限检查)
usePagedQuery:    ✅ 1用例 (分页请求)
editorRoundTrip:  ✅ 3用例 (编辑器往返)
───────────────
已覆盖: 4/40+ 文件   未覆盖: 全部 views + 组件
```

---

## 二、与完整测试体系的差距

### 2.1 测试金字塔对照

```
           ┌──────────┐
           │   E2E    │  ← 缺失 ❌ (0 测试)
          ┌┴──────────┴┐
          │  集成测试   │  ← 薄弱 ⚠️ (只有 API 级，无跨服务集成)
         ┌┴───────────┴┐
         │  单元测试    │  ← 不足 ⚠️ (31 + 13 = 44 个用例)
        ┌┴────────────┴┐
        │   静态分析    │  ← 部分 ✅ (black/flake8/eslint 配置了但 CI 中非阻塞)
```

### 2.2 后端缺口矩阵

| 模块 | 测试文件 | 用例数 | 状态 |
|------|----------|--------|------|
| articles | 8 文件 | 13 | ✅ 核心路径覆盖 |
| auth | 3 文件 | 4 | ✅ 基本覆盖 |
| comments | 1 文件 | 1 | ⚠️ 仅创建，缺审核/删除 |
| search | 1 文件 | 4 | ⚠️ 仅多标签，缺单标签/分页 |
| **backup** | **0** | **0** | **❌ 完全缺失** |
| **media** | **0** | **0** | **❌ 完全缺失** |
| **logs** | **0** | **0** | **❌ 完全缺失** |
| **security** | **0** | **0** | **❌ 完全缺失** |
| **settings** | **0** | **0** | **❌ 完全缺失** |
| **taxonomy** | **0** | **0** | **❌ 完全缺失** |
| **uploads** | **0** | **0** | **❌ 完全缺失** |
| **metrics** | **0** | **0** | **❌ 完全缺失** |

### 2.3 测试质量评估

#### 好的方面 ✅
- 使用 SQLite 内存数据库，测试隔离性好（每个测试前 `db.drop_all(); db.create_all()`）
- FakeRedis 模拟 Redis，不依赖外部服务
- DummyIdx 模拟 MeiliSearch，搜索测试可独立运行
- conftest.py 中禁用了 flask-limiter，避免限流干扰测试

#### 欠缺的方面 ❌
- **无覆盖率门禁**：`--cov-fail-under=0` 意味着 coverage 不会导致 CI 失败
- **无异常路径测试**：多数测试只测"快乐路径"，401/403/404/409 等很少覆盖
- **无 mock 审计**：未验证 `audit_log` 是否被正确调用
- **无并发测试**：slug 唯一性竞态等场景未覆盖
- **fixture 有残留风险**：`_clean_db` 使用 `autouse=True`，但未验证 fixture 本身的隔离性

### 2.4 前端缺口

| 类别 | 文件数 | 已测试 | 覆盖率 |
|------|--------|--------|--------|
| Views（页面） | ~30 | 0 | 0% |
| Components（组件） | ~30 | 0 | 0% |
| Stores（状态） | 2 | 1 | 50% |
| Utils（工具） | ~10 | 1 | 10% |
| API 层 | 5 | 0 | 0% |

### 2.5 E2E 缺口

**完全缺失**。至少需要覆盖以下核心路径：

```
1. 用户注册 → 登录 → 首页显示已登录
2. 创建文章 → 提交审核 → 审核通过 → 前台可见
3. 创建文章 → 提交审核 → 审核驳回 → 作者修改后重新提交
4. 搜索关键词 → 查看结果 → 进入详情页
5. 发表评论 → 审核通过 → 前台可见
6. 管理员修改用户角色 → 权限即时生效
```

---

## 三、风险量化

| 风险 | 等级 | 原因 |
|------|------|------|
| 重构无安全网 | **P1** | backup/media/logs/security/settings/taxonomy/uploads 七个模块无测试，修改这些模块的函数全靠人工验证 |
| 前端回归 | **P1** | 全部 30 个页面组件无测试，UI 调整可能无感知地破坏功能 |
| 部署验证缺失 | **P2** | 无 E2E 测试，部署后需要手动验证核心流程 |
| 安全漏洞遗漏 | **P2** | 无安全专项测试（注入/越权/XSS），依赖人工代码审查 |
| 性能退化 | **P3** | 无性能基线测试，N+1 查询等问题可能反复出现 |

---

## 四、建议改进路径

### Phase A：补齐后端缺失模块（3 天）

```
优先级: taxonomy > uploads > settings > media > security > logs > backup

每个模块至少覆盖：
- 成功路径（create/read/update/delete）
- 权限校验（未登录/角色不足返回 401/403）
- 参数校验（无效输入返回 400）
```

**示例 - taxonomy 测试骨架：**
```python
class TestCategoryAPI:
    def test_create_category(self, client, auth_headers):
        resp = client.post('/api/v1/taxonomy/categories/', json={
            'name': 'Tech', 'slug': 'tech'
        }, headers=auth_headers(role='admin'))
        assert resp.status_code == 201
        assert resp.json['data']['name'] == 'Tech'

    def test_create_category_unauthorized(self, client):
        resp = client.post('/api/v1/taxonomy/categories/', json={'name': 'Tech'})
        assert resp.status_code == 401

    def test_create_category_duplicate_slug(self, client, auth_headers):
        client.post('/api/v1/taxonomy/categories/', json={
            'name': 'Tech', 'slug': 'tech'
        }, headers=auth_headers(role='admin'))
        resp = client.post('/api/v1/taxonomy/categories/', json={
            'name': 'Tech Again', 'slug': 'tech'
        }, headers=auth_headers(role='admin'))
        assert resp.status_code == 409
```

### Phase B：补充前端组件测试（3 天）

``` 
优先级: ArticleContentRenderer > CommentsThread > ImageUploader > Login > NewArticle

每个组件覆盖：
- 正常渲染（给定 props 验证输出）
- loading/empty/error 三种状态
- 用户交互（点击、输入等）
```

### Phase C：接入 E2E 测试（2 天）

```
工具: Playwright
环境: docker compose up 启动完整栈

核心场景：
1. 注册 → 登录 → 创建文章 → 提交审核
2. 管理员登录 → 审核文章 → 前台验证可见
3. 搜索 → 浏览 → 评论
```

### Phase D：工程化加固（1 天）

```
- pytest --cov-fail-under=30  设置最低覆盖率门禁
- CI 中 frontend test job 失败应该阻塞合并
- 添加 API 契约测试 (schemathesis / openapi-core)
- 添加 git pre-push hook 自动运行测试
```

---

## 五、结论

**当前状态：不完整。** 测试体系处于"基础防线就位但远未完善"的阶段。

| 维度 | 评分 | 说明 |
|------|------|------|
| 后端核心模块 | 6/10 | articles/auth 有覆盖，但缺失 7/14 模块 |
| 后端基础设施 | 7/10 | conftest 隔离性好，FakeRedis/DummyIdx 设计合理 |
| 前端测试 | 2/10 | 仅 4 个测试文件，页面/组件覆盖率 0% |
| E2E 测试 | 0/10 | 完全缺失 |
| CI 集成 | 5/10 | 有 test job 但无覆盖率门禁 |
| 整体成熟度 | **4/10** | 有基本骨架但不足以支撑安全重构 |
