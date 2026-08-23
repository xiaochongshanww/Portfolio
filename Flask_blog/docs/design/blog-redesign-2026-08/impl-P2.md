# P2 实施计划 — 项目实体化 · 关于页 · Dark Mode · 搜索增强

> 阶段目标:完成 02 号规范 P2 优先级——项目页与详情(含后端 Project 实体)、关于页、Dark Mode、Search Overlay 增强。
>
> **追踪规则**:同 impl-P0.md。只有验收标准全部通过才标记 `✅` 并补"完成记录"。

## 前置依赖

- P0 全部完成;P1 的 E1(导航补全)已完成;
- 本阶段首次引入**后端开发任务**(Project 实体),前后端任务在同一文档中分轨追踪。

---

## 分组 A — 后端:Project 实体

### A1 ⬜ Project 模型与迁移
- 内容:`backend/app/models.py` 新增 `Project`:id/name/slug/description/tech_stack(JSON 或逗号串)/status(active|paused|archived)/is_current(bool,当前重点项目唯一)/preview_type(none|image|svg)/preview_data(JSON)/link_url/repo_url/sort_order/timestamps;Alembic 迁移 0016(SQLite + MySQL 双兼容,遵循此前修复经验:no NOW()、LONGTEXT 加 with_variant、ALTER 用 batch)。
- 验收标准:
  - [ ] `alembic upgrade head` 在 sqlite 与 MySQL(或 CI 替代)均通过;
  - [ ] is_current 唯一性有约束或 service 层保证(置一个时清其他);
  - [ ] 模型注册进 admin 后台可管理(复用现有管理框架,基础 CRUD 可用)。
- 完成记录:

### A2 ⬜ Project 公开 API 与管理 API
- 内容:public 路由 `GET /api/v1/projects/`(列表,is_current 置顶)+ `GET /api/v1/projects/:slug`;admin CRUD 路由走现有 enforcer 权限;service/schemas 分层齐全;OpenAPI 快照更新(check-openapi 门禁同步)。
- 验收标准:
  - [ ] pytest 覆盖:list/current 优先排序/detail 404/权限(未登录不可写);
  - [ ] openapi.json 快照已再生成且 drift 检查通过;
  - [ ] flake8/black/isort/mypy 全绿。
- 完成记录:

### A3 ⬜ topicOverrides 退役评估
- 内容:P1 遗留的 `topicOverrides.ts`:若本阶段同时立项 Topic 后端实体则迁移数据源并删除该文件;若未立项,**保留但在文件头注明"仍为过渡方案"**,并在本文档记录决策。
- 验收标准:
  - [ ] 决策二选一且有明确记录,不允许维持模糊状态。
- 完成记录:

---

## 分组 B — 项目页前端

### B1 ⬜ ProjectsPage
- 内容:替换占位路由 `/projects`:page-head(「正在做的东西,比"作品集"更重要。」)+ 当前项目大区(黑底 intro 卡 + preview 区:preview_type=image 显示图/svg 渲染 SVG/none 显示占位说明)+ 其余项目 2 列轻卡(tag/名称/一句话/技术栈)。**避免**:巨大截图墙、Star/Commit 数据、成功案例式包装。
- 验收标准:
  - [ ] is_current 项目独占大区,其余卡片不与其争视觉权重;
  - [ ] 无 Demo 的项目显示规范空态(「当前版本暂未开放在线体验」);
  - [ ] 数据来自 A2 API,接口失败显示 error 态(不再用本地常量兜底——C3 占位文件此时删除)。
- 完成记录:

### B2 ⬜ ProjectDetail(`/projects/:slug`)
- 内容:按 02 号规范第 6 节结构:Project Identity → Live Status(状态/最近更新/Repo·Demo 链接)→ Preview/Demo → 为什么做 → 现在做到哪里 → 关键设计决策 → 相关技术文章(按 tech/名称关联站内文章,人工配置字段 related_article_slugs)→ Changelog(JSON 字段渲染时间线)→ Next。
- 验收标准:
  - [ ] 「相关文章」点击跳真实文章详情,slug 失效时该区块整体隐藏(不显示死链);
  - [ ] 页面传达"持续进行"语义:Live Status 的最近更新时间取自 updated_at;
  - [ ] 四态齐备,404 slug 有专门页面态。
- 完成记录:

### B3 ⬜ 项目页测试
- 验收标准:
  - [ ] spec:列表排序(current 优先)、detail 各区块渲染/隐藏逻辑、四态;
  - [ ] coverage 达标。
- 完成记录:

---

## 分组 C — 关于页

### C1 ⬜ AboutPage 重写
- 内容:替换现 About.vue:左侧叙事(三段:为什么有这个站/主要写什么/内容如何互相连接)+ 右侧「现在」侧栏(正在写/正在做/主要技术/其它入口,数据可静态配置)+ 底部极简三年时间线。**反履历**:无姓名年龄学校公司技能百分比。
- 验收标准:
  - [ ] 页面无履历式信息块;
  - [ ] 「现在」侧栏数据抽到单一配置文件(`frontend/src/data/aboutNow.ts`)便于日常改;
  - [ ] 时间线行数 ≤5,超出说明写法错了。
- 完成记录:

### C2 ⬜ About 测试
- 验收标准:
  - [ ] spec 覆盖叙事渲染、Now 侧栏、无履历断言(不含"毕业/公司"等关键词的粗校验);
  - [ ] coverage 达标。
- 完成记录:

---

## 分组 D — Search Overlay 增强

### D1 ⬜ ⌘K 全局弹层
- 内容:`components/public/SearchOverlay.vue`:全局快捷键(Ctrl+K / ⌘K)唤起;顶部输入 + Recent/Suggested(默认态,取最近浏览文章 localStorage + 手工推荐词)+ 结果分组列表(P1 useUnifiedSearch 直接复用);键盘上下选择 + Enter 跳转 + ESC 关闭;backdrop 点击关闭。
- 验收标准:
  - [ ] 三类结果分组展示,选中项高亮跟随方向键;
  - [ ] Enter 导航正确;ESC/backdrop 关闭且焦点归还触发元素(a11y);
  - [ ] 弹层打开时 body scroll 锁定,关闭恢复。
- 完成记录:

### D2 ⬜ Header 搜索按钮接线 + 测试
- 内容:B1 PublicHeader 的搜索按钮从静态改为触发 Overlay;移动端 Header 折叠导航后搜索入口保留(icon 形态)。
- 验收标准:
  - [ ] 桌面/移动端均可打开 Overlay;
  - [ ] spec:快捷键监听、键盘导航、ESC 关闭、焦点管理。
- 完成记录:

---

## 分组 E — Dark Mode

### E1 ⬜ Token 双主题化
- 内容:tokens 改造为 CSS variables 双套(`:root` 亮色 / `[data-theme="dark"]` 暗色);暗色基线:非纯黑背景(#141413 类)、surface 提亮一档、signal 保持不变、code block 与 surface 明显区分;组件代码零改动(全部消费变量)。逐页检查硬编码色值并清理(原型迁移中可能残留 #fff/#171717 直写)。
- 验收标准:
  - [ ] grep 公共组件无直写 hex 色值(tokens 文件除外);
  - [ ] 暗色下对比度抽查:muted 文字 ≥4.5:1(用工具测首页/详情各一处);
  - [ ] 切换无需刷新即时生效。
- 完成记录:

### E2 ⬜ 主题切换器与持久化
- 内容:Header 加 ◐ 切换按钮(亮/暗/跟随系统三态循环);localStorage 记忆 + `prefers-color-scheme` 默认;防 FOUC(main.js 挂载前读 storage 设置 data-theme)。
- 验收标准:
  - [ ] 刷新后主题保持;系统偏好变化时"跟随系统"档实时响应;
  - [ ] 首屏无白闪(暗色用户刷新验证);
  - [ ] 仅公开壳生效,/admin 不受影响。
- 完成记录:

### E3 ⬜ Dark Mode 回归
- 验收标准:
  - [ ] 01 号规范第 12 节要求逐条核对(信息层级一致/signal 不变/code 区分);
  - [ ] 两主题 × 三宽度手工过首页/详情/归档/搜索,截图留档于本文档完成记录。
- 完成记录:

---

## 分组 F — 全局收尾

### F1 ⬜ 死代码终扫
- 内容:P0-P2 全部完成后,统一扫描公共侧残留旧实现:`CategoryPage`/`TagsPage`(若已被专题替代)、旧 ArticleContentRenderer 中被 Renderer 取代的路径、`sidebar/` 残件、未引用 utils。
- 验收标准:
  - [ ] 待删项清单列出并逐项确认引用为零后删除;
  - [ ] vitest/build/lint 全绿。
- 完成记录:

### F2 ⬜ 性能与 SEO 终检
- 验收标准:
  - [ ] LHCI 门禁通过且分数不低于改造前基线(记录前后数值);
  - [ ] 详情页 SEO 元素齐备(title/description/canonical/OG/published_time/modified_time,03 号规范第 30 节);
  - [ ] 图片 lazy loading 生效(DOM loading="lazy")。
- 完成记录:

### F3 ⬜ 最终手工验收与发布
- 验收标准:
  - [ ] 全部公共页面 × 两主题 × 三宽度人工过一遍;
  - [ ] 用户最终确认接受,方可提交推送;
  - [ ] impl-P0/P1/P2 三份文档的任务标记与实际代码状态一致性复核。
- 完成记录:

---

## 依赖关系

```text
A1 → A2 → B1/B2/B3 ─┐
A3(独立决策)────────┤
P1 完成 ──→ C1/C2 ──┼──→ F1 → F2 → F3
P1 B2 ──→ D1/D2 ────┤
B* 完成 ──→ E1/E2/E3 ┘
```

## 风险提示

1. **后端首秀**:A 组是本项目首个新实体迁移,务必沿用 SQLite 兼容三条经验(NOW()/LONGTEXT variant/batch alter),迁移前备份 dev.db。
2. **Dark Mode 是全局横切面**:E1 必须在其他所有页面定稿后再做,否则每加一页都要回归双主题;若中途需要,只允许新增页面直接写变量、禁止提前全面改造。
3. **A3 的取舍**:Topic 后端实体工作量不小,若 P2 排期紧张,明确选择"保留 overrides"比半途迁移更安全。
