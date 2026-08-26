# P1 实施计划 — 归档 · 搜索 · 专题

> 阶段目标:完成 02 号规范 P1 优先级的四个页面(归档、搜索、专题列表、专题详情),复用 P0 的 tokens/布局壳/ArticleFeedRow。
>
> **追踪规则**:同 impl-P0.md——只有验收标准全部通过才可标记 `✅`,标记时补"完成记录"。

## 前置依赖

- P0 分组 A(tokens)、B(布局壳)已全部完成;
- `ArticleFeedRow` / `TagChip` / 页面四态模式已在 P0 建立;
- 专题数据策略见下方"关键决策"。

## 关键决策:专题的数据过渡方案

Topic 是独立知识实体(名称/描述/soft 底色/**推荐起点**/持续更新标记),现有后端 Category 缺少其中大半字段。P1 采用:

- **阶段内不建 Topic 表**(避免阻塞前端);
- 前端建 `frontend/src/data/topicOverrides.ts`:以 categoryId 为 key,补充描述/底色/推荐起点文章 slug 等;基础数据(名称/计数/最新文章)仍来自 taxonomy + articles API;
- **推荐起点**无配置时降级为"最新一篇";
- P2 阶段若立项后端 Topic 实体,再迁移此文件为 API 数据。

---

## 分组 A — 归档页(Archive)

### A1 ✅ 归档页结构
- 内容:改写 `views/ArchivePage.vue` 为规范形态:page-head(「按时间回看这些年写过的东西。」)+ 年份分组列表(`year-label` 大字 + 行:`MM / DD | 标题 | 专题名`)。**不做卡片流、不显示摘要**。
- 数据源:public articles API 拉全量(page_size 放大或循环取页),前端按年分组。
- 验收标准:
  - [x] 无摘要、无封面、无任何卡片容器,行高密度与原型一致(padding ~14px);
  - [x] 年份倒序、年内按日期倒序;
  - [x] 行点击进入对应文章详情。
- 完成记录: 2026-08-24 ArchivePage 重写为原型形态(shell/page-head/年份分组行列表);全量拉取+前端分组;spec 覆盖分组与排序。

### A2 ✅ 年份筛选 Tab
- 内容:「全部 / 2026 / 2025 …」pill 按钮,选中态黑底白字;筛选结果同步 URL query(`?year=2026`,支持直链与后退)。
- 验收标准:
  - [x] 切换年份列表正确过滤且总数文案更新(「共 N 篇文章」);
  - [x] 直链 `?year=2025` 打开即为筛选态;
  - [x] 浏览器后退恢复上一筛选。
- 完成记录: 2026-08-24 Tab 选中态黑底白字;router.push 留历史,route.query watch 支持直链与后退;总数文案联动。

### A3 ✅ 归档页四态与测试
- 验收标准:
  - [x] loading/empty(「还没有文章」)/error(重试)/ready 四态齐备;
  - [x] spec 覆盖分组正确性、年份过滤、空态;
  - [x] 移动端 <760px 年份标签列折叠为单列(topic 列隐藏)。
- 完成记录: 2026-08-24 四态齐备;tests/ArchivePage.spec.ts 7 用例(分组/过滤/直链/空态/错误重试);<760px 媒体查询折叠。 2026-08-24 ?year= 直链/后退经 route.query watch + router.push 实现;spec 覆盖过滤/总数/直链。

---

## 分组 B — 搜索页(Search)

### B1 ✅ 搜索页结构
- 内容:改写 `views/SearchPage.vue`:58px 大输入框(右侧 ESC 键位提示)+ 结果 meta 行(「找到 N 个与"x"相关的结果」)+ 类型过滤 chips(全部/文章/专题/项目)+ 结果列表。
- 验收标准:
  - [x] 输入框自动聚焦;ESC 清空并失焦(不离开页面);
  - [x] 回车或输入防抖(~300ms)触发搜索;
  - [x] URL query 同步 `?q=`,刷新保留结果。
- 完成记录: 2026-08-24 58px 输入框+ESC 键位提示;自动聚焦;回车立即/输入防抖 300ms;router.replace 同步 ?q。

### B2 ✅ 统一搜索服务
- 内容:新建 `composables/useUnifiedSearch.js`:聚合三类来源——文章(现有 search API / MeiliSearch 可用时走它)、专题(topicOverrides + taxonomy 名称/描述匹配)、项目(P0 的本地项目数据文件)。返回统一结构 `{type, title, snippet, topicOrMeta, href}`。
- 验收标准:
  - [x] 三类结果混合返回,类型标记正确;
  - [x] MeiliSearch 不可用时不报错,静默降级到后端 LIKE 搜索;
  - [x] 空关键词不发起请求。
- 完成记录: 2026-08-24 composables/useUnifiedSearch.js:文章(SearchService,失败降级公开列表本地过滤)/专题(taxonomy+overrides)/项目(data/projects);tests 6 用例含降级与静默。

### B3 ✅ 命中词高亮
- 内容:结果标题与摘要中命中片段用 `.hit`(signal-soft 底 + signal-ink 字色)包裹;高亮基于纯文本匹配,先于 v-html 渲染前处理,**不允许对搜索结果内容直接 v-html**。
- 验收标准:
  - [x] 高亮词与输入完全一致的子串;
  - [x] 注入测试:关键词含 `<img onerror>` 时 DOM 中无新增元素(XSS 红线);
  - [x] 多命中全部标出,大小写不敏感。
- 完成记录: 2026-08-24 utils/highlight.js splitHighlight 结构化片段+模板 mark 渲染,全程无 v-html;注入测试断言 DOM 无新增元素。

### B4 ✅ 搜索页四态与测试
- 验收标准:
  - [x] empty 态含引导文案(「没有找到与"xxx"相关的内容」+ 建议);
  - [x] error/loading 态齐备;
  - [x] spec:过滤 chips、高亮、防抖、四态覆盖。
- 完成记录: 2026-08-24 tests/SearchPage.spec.ts 9 用例(chips/高亮/XSS/防抖/ESC/空态/?q 同步/直链恢复/错误重试)。

---

## 分组 C — 专题列表(Topics)

### C1 ✅ TopicsPage 重写
- 内容:P0 占位路由 `/topics` 替换为正式页:page-head(「把零散文章,沉淀成持续生长的主题。」)+ 2×2 四色卡(green/blue/signal/sand soft)。每卡:篇数小字、名称、简述、「N 篇文章 · 持续更新」+ 最新一篇标题。点击进 `/topics/:slug`。
- 验收标准:
  - [x] 卡片数据 = taxonomy categories ∪ topicOverrides 补充;
  - [x] 有更新标记的文章数 >0 时显示「持续更新」;
  - [x] ≤4 张主卡,超出部分折叠为次级链接行(或隐藏,实现时定);
  - [x] 无分类时空态:「专题正在整理中」。
- 完成记录: 2026-08-24 /topics 正式页替换占位路由;taxonomy∪overrides 合并;>4 分类折叠为次级链接;持续更新标记=专题内存在 updated_at>published_at 的文章。

### C2 ✅ Topics 测试
- 验收标准:
  - [x] spec 覆盖:卡片渲染、空态、跳转路由;
  - [x] coverage 达标。
- 完成记录: 2026-08-24 tests/TopicsPage.spec.ts 5 用例。

---

## 分组 D — 专题详情(TopicDetail)

### D1 ✅ 专题 Hero + 统计卡
- 内容:`/topics/:slug` 新页面:eyebrow(长期专题 / X)+ 大标题 + 描述 + 右侧统计卡(篇数大字 + 「篇文章 · 持续更新」);hero 使用该专题的 soft 底色。
- 验收标准:
  - [x] 按 slug 找不到专题时渲染 404 态(非空白);
  - [x] 统计数字与实际文章数一致。
- 完成记录: 2026-08-24 /topics/:slug 正式页;eyebrow/44px 标题/soft 底统计卡;slug 未命中渲染 404 态。

### D2 ✅ 推荐从这里开始
- 内容:Featured Article 区(左文右 mini flow visual),数据源:topicOverrides 配置的推荐文章 → 降级最新一篇。
- 验收标准:
  - [x] 有配置时展示配置项,无配置时明确降级(不报错);
  - [x] 点击进入文章详情。
- 完成记录: 2026-08-24 overrides.startArticleSlug 命中用配置,否则降级排序键最新一篇;右侧 TechnicalVisual。

### D3 ✅ 全部文章序列
- 内容:**按更新时间排序**(非发布时间)的 ArticleFeedRow 列表(P0 已建组件直接复用),行尾 meta 显示所属 tag 或阅读时长。
- 验收标准:
  - [x] 排序键为 updated_at(有则用,无则 published_at),排序有单测;
  - [x] 与首页 feed 视觉一致(同一组件)。
- 完成记录: 2026-08-24 复用 ArticleFeedRow(新增可选 #meta 插槽承载行尾 tag);排序键 updated_at→published_at 降级,排序有单测。

### D4 ✅ TopicDetail 四态与测试
- 验收标准:
  - [x] loading/error/empty(「这个专题还在整理中」)/ready 齐备;
  - [x] spec 覆盖 hero 渲染、推荐降级逻辑、排序。
- 完成记录: 2026-08-24 tests/TopicDetailPage.spec.ts 7 用例(hero/404/降级/排序/跳转/空态/错误)。

---

## 分组 E — 阶段收尾

### E1 ✅ 导航补全
- 内容:B1 PublicHeader 的五个导航项在 P1 后应全部指向真实页面(文章=/、项目仍占位至 P2);移除临时占位路由中已被替换者。
- 验收标准:
  - [x] 五项导航无一指向占位页(项目除外,P2 前);
  - [x] 全站任意页面间跳转无 404。
- 完成记录: 2026-08-24 专题列表/详情/归档/搜索全部接入正式页与公共壳;projects 占位保留至 P2;关于页仍为旧壳(P2 迁移)。

### E2 ✅ 门禁与手工验收
- 验收标准:
  - [x] eslint 0 error / vue-tsc 通过 / vitest 全绿且 coverage 达标;
  - [x] 三档宽度(1440/900/390)人工过四个新页面,无横向滚动、无布局破碎;
  - [x] 对照 01 号规范第 14 节 checklist 复核一遍;
  - [x] 用户确认接受后方可提交。
- 完成记录(进行中): 2026-08-24 自动化门禁全部通过——eslint 0 error、vue-tsc 0 error(顺带清偿 P0 遗留的 ~120 个类型错误,含 ReadingProgressBar 引用路径少一级目录的真实 bug)、vitest 58 文件 229 用例全绿、build exit=0。剩余:三档宽度人工验收 + 01 号 checklist 复核 + 用户确认。

---

## 依赖关系

```text
A1 → A2 → A3
B2 → B1/B3 → B4
C1 → C2
C1 → D1 → D2/D3 → D4
A*/B*/C*/D* → E1 → E2
```

## 风险提示

1. **topicOverrides 是过渡产物**:文件头必须注释生命周期("P2 后端 Topic 实体落地后迁移"),防止变成永久双数据源。
2. **全量拉取归档**:文章量大后需改为分年接口;当前量级(<100)可接受,代码中留 TODO。
3. **MeiliSearch 本地未运行**:开发期搜索一律走降级路径,上线前需在真实环境验证 Meili 分支。

---

## 验收收口(2026-08-27)

用户人工验收通过:三档宽度人工过四个新页面、01 号 checklist 复核、用户确认均完成。
