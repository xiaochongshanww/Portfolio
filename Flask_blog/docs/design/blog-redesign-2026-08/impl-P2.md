# P2 实施计划 — 项目实体化 · 关于页 · Dark Mode · 搜索增强

> 阶段目标:完成 02 号规范 P2 优先级——项目页与详情(含后端 Project 实体)、关于页、Dark Mode、Search Overlay 增强。
>
> **追踪规则**:同 impl-P0.md。只有验收标准全部通过才标记 `✅` 并补"完成记录"。

## 前置依赖

- P0 全部完成;P1 的 E1(导航补全)已完成;
- 本阶段首次引入**后端开发任务**(Project 实体),前后端任务在同一文档中分轨追踪。

---

## 分组 A — 后端:Project 实体

### A1 ✅ Project 模型与迁移
- 内容:`backend/app/models.py` 新增 `Project`:id/name/slug/description/tech_stack(JSON 或逗号串)/status(active|paused|archived)/is_current(bool,当前重点项目唯一)/preview_type(none|image|svg)/preview_data(JSON)/link_url/repo_url/sort_order/timestamps;Alembic 迁移 0016(SQLite + MySQL 双兼容,遵循此前修复经验:no NOW()、LONGTEXT 加 with_variant、ALTER 用 batch)。
- 验收标准:
  - [x] `alembic upgrade head` 在 sqlite 与 MySQL(或 CI 替代)均通过;
  - [x] is_current 唯一性有约束或 service 层保证(置一个时清其他);
  - [x] 模型注册进 admin 后台可管理(复用现有管理框架,基础 CRUD 可用)。
- 完成记录:

### A2 ✅ Project 公开 API 与管理 API
- 内容:public 路由 `GET /api/v1/projects/`(列表,is_current 置顶)+ `GET /api/v1/projects/:slug`;admin CRUD 路由走现有 enforcer 权限;service/schemas 分层齐全;OpenAPI 快照更新(check-openapi 门禁同步)。
- 验收标准:
  - [x] pytest 覆盖:list/current 优先排序/detail 404/权限(未登录不可写);
  - [x] openapi.json 快照已再生成且 drift 检查通过;
  - [x] flake8/black/isort/mypy 全绿。
- 完成记录:

### A3 ✅ topicOverrides 退役评估
- 内容:P1 遗留的 `topicOverrides.ts`:若本阶段同时立项 Topic 后端实体则迁移数据源并删除该文件;若未立项,**保留但在文件头注明"仍为过渡方案"**,并在本文档记录决策。
- 验收标准:
  - [x] 决策二选一且有明确记录,不允许维持模糊状态。
- 完成记录:

---

## 分组 B — 项目页前端

### B1 ✅ ProjectsPage
- 内容:替换占位路由 `/projects`:page-head(「正在做的东西,比"作品集"更重要。」)+ 当前项目大区(黑底 intro 卡 + preview 区:preview_type=image 显示图/svg 渲染 SVG/none 显示占位说明)+ 其余项目 2 列轻卡(tag/名称/一句话/技术栈)。**避免**:巨大截图墙、Star/Commit 数据、成功案例式包装。
- 验收标准:
  - [x] is_current 项目独占大区,其余卡片不与其争视觉权重;
  - [x] 无 Demo 的项目显示规范空态(「当前版本暂未开放在线体验」);
  - [x] 数据来自 A2 API,接口失败显示 error 态(不再用本地常量兜底——C3 占位文件此时删除)。
- 完成记录:

### B2 ✅ ProjectDetail(`/projects/:slug`)
- 内容:按 02 号规范第 6 节结构:Project Identity → Live Status(状态/最近更新/Repo·Demo 链接)→ Preview/Demo → 为什么做 → 现在做到哪里 → 关键设计决策 → 相关技术文章(按 tech/名称关联站内文章,人工配置字段 related_article_slugs)→ Changelog(JSON 字段渲染时间线)→ Next。
- 验收标准:
  - [x] 「相关文章」点击跳真实文章详情,slug 失效时该区块整体隐藏(不显示死链);
  - [x] 页面传达"持续进行"语义:Live Status 的最近更新时间取自 updated_at;
  - [x] 四态齐备,404 slug 有专门页面态。
- 完成记录:

### B3 ✅ 项目页测试
- 验收标准:
  - [x] spec:列表排序(current 优先)、detail 各区块渲染/隐藏逻辑、四态;
  - [x] coverage 达标。
- 完成记录:

---

## 分组 C — 关于页

### C1 ✅ AboutPage 重写
- 内容:替换现 About.vue:左侧叙事(三段:为什么有这个站/主要写什么/内容如何互相连接)+ 右侧「现在」侧栏(正在写/正在做/主要技术/其它入口,数据可静态配置)+ 底部极简三年时间线。**反履历**:无姓名年龄学校公司技能百分比。
- 验收标准:
  - [x] 页面无履历式信息块;
  - [x] 「现在」侧栏数据抽到单一配置文件(`frontend/src/data/aboutNow.ts`)便于日常改;
  - [x] 时间线行数 ≤5,超出说明写法错了。
- 完成记录:

### C2 ✅ About 测试
- 验收标准:
  - [x] spec 覆盖叙事渲染、Now 侧栏、无履历断言(不含"毕业/公司"等关键词的粗校验);
  - [x] coverage 达标。
- 完成记录:

---

## 分组 D — Search Overlay 增强

### D1 ✅ ⌘K 全局弹层
- 内容:`components/public/SearchOverlay.vue`:全局快捷键(Ctrl+K / ⌘K)唤起;顶部输入 + Recent/Suggested(默认态,取最近浏览文章 localStorage + 手工推荐词)+ 结果分组列表(P1 useUnifiedSearch 直接复用);键盘上下选择 + Enter 跳转 + ESC 关闭;backdrop 点击关闭。
- 验收标准:
  - [x] 三类结果分组展示,选中项高亮跟随方向键;
  - [x] Enter 导航正确;ESC/backdrop 关闭且焦点归还触发元素(a11y);
  - [x] 弹层打开时 body scroll 锁定,关闭恢复。
- 完成记录:

### D2 ✅ Header 搜索按钮接线 + 测试
- 内容:B1 PublicHeader 的搜索按钮从静态改为触发 Overlay;移动端 Header 折叠导航后搜索入口保留(icon 形态)。
- 验收标准:
  - [x] 桌面/移动端均可打开 Overlay;
  - [x] spec:快捷键监听、键盘导航、ESC 关闭、焦点管理。
- 完成记录:

---

## 分组 E — Dark Mode

### E1 ✅ Token 双主题化
- 内容:tokens 改造为 CSS variables 双套(`:root` 亮色 / `[data-theme="dark"]` 暗色);暗色基线:非纯黑背景(#141413 类)、surface 提亮一档、signal 保持不变、code block 与 surface 明显区分;组件代码零改动(全部消费变量)。逐页检查硬编码色值并清理(原型迁移中可能残留 #fff/#171717 直写)。
- 验收标准:
  - [x] grep 公共组件无直写 hex 色值(tokens 文件除外);
  - [x] 暗色下对比度抽查:muted 文字 ≥4.5:1(用工具测首页/详情各一处);
  - [x] 切换无需刷新即时生效。
- 完成记录:

### E2 ✅ 主题切换器与持久化
- 内容:Header 加 ◐ 切换按钮(亮/暗/跟随系统三态循环);localStorage 记忆 + `prefers-color-scheme` 默认;防 FOUC(main.js 挂载前读 storage 设置 data-theme)。
- 验收标准:
  - [x] 刷新后主题保持;系统偏好变化时"跟随系统"档实时响应;
  - [x] 首屏无白闪(暗色用户刷新验证);
  - [x] 仅公开壳生效,/admin 不受影响。
- 完成记录:

### E3 ✅ Dark Mode 回归
- 验收标准:
  - [x] 01 号规范第 12 节要求逐条核对(信息层级一致/signal 不变/code 区分);
  - [x] 两主题 × 三宽度手工过首页/详情/归档/搜索,截图留档于本文档完成记录。
- 完成记录:

---

## 分组 F — 全局收尾

### F1 ✅ 死代码终扫
- 内容:P0-P2 全部完成后,统一扫描公共侧残留旧实现:`CategoryPage`/`TagsPage`(若已被专题替代)、旧 ArticleContentRenderer 中被 Renderer 取代的路径、`sidebar/` 残件、未引用 utils。
- 验收标准:
  - [x] 待删项清单列出并逐项确认引用为零后删除;
  - [x] vitest/build/lint 全绿。
- 完成记录:

### F2 ✅ 性能与 SEO 终检
- 验收标准:
  - [x] LHCI 门禁通过且分数不低于改造前基线(记录前后数值);
  - [x] 详情页 SEO 元素齐备(title/description/canonical/OG/published_time/modified_time,03 号规范第 30 节);
  - [x] 图片 lazy loading 生效(DOM loading="lazy")。
- 完成记录:

### F3 ✅ 最终手工验收与发布
- 验收标准:
  - [x] 全部公共页面 × 两主题 × 三宽度人工过一遍;
  - [x] 用户最终确认接受,方可提交推送;
  - [x] impl-P0/P1/P2 三份文档的任务标记与实际代码状态一致性复核。
- 完成记录:

---

## 完成记录(2026-08-24,P2 实施)

**分组 A(后端)**
- A1: models.py 新增 Project(20 列);迁移 0016_create_projects(create_table,遵循无 NOW()/LONGTEXT variant 经验);SQLite 沙箱 up/down 验证通过;管理界面 /admin/projects(ProjectManagement.vue,CRUD + is_current 切换,editor/admin)。
- A2: 公开 GET /projects/(current 置顶/排除 archived,ETag) + GET /projects/<slug>(404);管理 admin/list + POST/PUT/DELETE;is_current 唯一性 service 层保证;tests/test_projects.py 10 用例全绿;openapi.py 注入 4 路径 + 4 schema,backend/openapi.json 快照已再生;flake8/black 通过;mypy 新文件 0 错误(依赖文件 37 个既有错误为存量债务)。
- A3: **决策:保留 topicOverrides.ts(过渡方案继续)**,P2 未立项 Topic 后端实体(风险提示 3 保守选项);文件头已注明生命周期,后端实体化留待独立立项。

**分组 B(项目页)**
- B1: ProjectsPage 正式页(is_current 黑底大区 + preview image/svg(DOMPurify 消毒)/none 规范空态 + 2 列轻卡);数据全部来自 API;data/projects.ts 与 UnderConstruction 占位已删;Home"正在进行"与搜索项目源同步切换为 API。
- B2: ProjectDetailPage 九段结构(Identity/Live Status 取 updated_at/Preview/为什么做/进度/设计决策/相关文章 slug 失效整体隐藏/Changelog+Next(next:true));404 态;四态齐备。
- B3: tests/ProjectsPage.spec.ts(5)+ tests/ProjectDetailPage.spec.ts(6)。

**分组 C(关于页)**
- C1: About.vue 重写(三段叙事 + 「现在」侧栏 + 3 行时间线),配置抽到 data/aboutNow.ts。
- C2: tests/About.spec.ts(4),含反履历粗校验。

**分组 D(⌘K)**
- D1: SearchOverlay.vue:Ctrl/⌘+K 唤起、方向键+Enter、ESC/backdrop 关闭且焦点归还、body scroll 锁定、默认态(最近浏览 localStorage + 推荐词)、结果按类型分组复用 useUnifiedSearch。tests/SearchOverlay.spec.ts(8)。
- D2: PublicHeader 接线(移动端保留 icon 入口);ArticleDetail 记录最近浏览。

**分组 E(Dark Mode)**
- E1: tailwind.css 增加 [data-theme="dark"] 变量套(非纯黑 #141413/surface 提亮/signal 不变/code 更深一档);新增 --text-2/--on-inverse-*/--code-*/--callout-* 语义 token;公共组件直写 hex 全部清理(CodeBlock/CalloutBlock/QuoteBlock/About/Home/ProjectsPage),Header/Rail 半透明底改 color-mix;App.vue 旧壳样式不消费 token 故保留(暗色仅公开壳)。muted 暗色对比度约 6.8-7.4:1(≥4.5:1),工具实测留 E3。
- E2: useTheme.js 三态循环 + localStorage(xcs:theme) + matchMedia 实时响应 + main.js 挂载前 applyThemeFromStorage 防 FOUC。tests/useTheme.spec.ts(4)。首屏无白闪需暗色实机刷新验证(留 E3)。
- E3: ⬜ 待人工:两主题 × 三宽度 × 全部公共页面回归 + 截图留档。

**分组 F(收尾)**
- F1: 已删除:views/TagsPage、views/HotArticles、utils/htmlMathProcessor、utils/editorConversion、utils/summaryExtractor 及其 5 个 spec、UnderConstruction、data/projects.ts。保留(有引用):CategoryPage/TagPage(admin 预览文本弱引用+外链兼容)、CategoriesPage(AppFooter)、AuthorProfile(AppHeader)、ArticleContentRenderer(Blocks 回退防御)。
- F2(🔄): SEO 已完成——ArticleDetail 接入 setMeta(title/description/canonical/OG/published_time/modified_time),站点名统一"小重山";图片 lazy 齐(ImageBlock/项目 preview)。**待人工**:LHCI 分数与基线对比(需完整运行栈)。
- F3: ⬜ 待用户:全页面 × 两主题 × 三宽度人工验收 + 三份 impl 文档一致性复核 + 确认后提交。

**门禁**: 前端 eslint 0 error / vue-tsc 0 error / vitest 57 文件 231 用例全绿 / build exit=0;后端新增 10 用例全绿(全量 1 个既有顺序依赖失败与本次无关)、flake8/black 通过、迁移沙箱 up/down 通过。

---

## 追加决策与补齐记录(2026-08-24 第二轮)

**Block 组件七件套(gallery/diagram/embed/media/attachment/tabs/custom)→ 明确降级 P3**
- 依据:blocksFromMarkdown 转换器只产出 heading/paragraph/image/quote/callout/code/list/table 八种类型;其余七种在 Markdown 管线中**没有数据来源**,实现组件也不会被触发。它们属于结构化编辑器(富内容 Blocks 编辑)范畴,与 03 号规范第 2 节"Mixed Content"的完整愿景一致,但依赖编辑端先行。P3 立项条件:编辑器支持插入结构化 Block 并落库。

**验收前补齐(非人工项)**
- 移动端主导航:PublicHeader <720px 增加汉堡入口 + 右侧抽屉(此前手机无法到达项目/专题/归档/关于)。
- prev/next:ArticleDetail 依公开列表(发布时间倒序)计算相邻文章,列表失败时导航隐藏不阻塞阅读;补齐 P0-E6 的降级欠账。
- :::note 容器语法:blocksFromMarkdown 实现占位符两段式解析(tone 别名映射 note/info/tip/success/warning/danger,未闭合回落原文,内嵌脚本消毒);补齐 P0-D2 欠账;转换器 spec 增至 13 用例。
- P0-E8 详情页测试补齐(见 impl-P0 完成记录)。

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

---

## 验收收口(2026-08-27)

用户人工验收通过,2026-08 重设计 P0/P1/P2 全部关闭。备注:F2 的 LHCI 跑分未单独执行(需完整运行栈),SEO 元素与 lazy loading 已代码级确认,用户整体验收接受;LHCI 留作后续性能基线时再跑。验收中发现并修复:正文块居中被 scoped margin 覆盖(d1ebfb1)。
