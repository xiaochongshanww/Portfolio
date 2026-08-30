# 05_管理后台Pattern与页面规范

> 本文定义小重山 CMS 后台可复用的页面 Pattern。  
> 目的：防止后续每增加一个管理页面，就重新设计一遍布局和交互。

---

# 1. Pattern 总览

后台页面主要由以下 Pattern 组成：

```text
Admin Shell

Page Header

Summary Strip

Toolbar

Data Table

Card / Section

Detail Drawer

Form

Dialog

Dropdown Menu

Batch Action

Empty / Loading / Error

Pagination
```

新页面原则上必须组合这些 Pattern，而不是自行创建新的布局体系。

---

# 2. List Management Pattern

最常用 Pattern。

适合：

- 文章；
- 评论；
- 专题；
- 标签；
- 项目；
- 用户；
- 日志。

标准结构：

```text
Page Header
  Title
  Description
  Primary Action

Summary Strip      optional

Toolbar
  Search
  Filters
  Secondary Action
  Result Count

Data Table

Table Footer
  Selection State
  Pagination
```

---

# 3. Page Header Pattern

结构：

```text
Title                         Primary Action
Description
```

例如：

```text
文章管理                      + 新建文章
管理、发布和维护站点文章内容。
```

约束：

- 一个页面最多一个 Primary Action；
- Secondary Action 放 Toolbar 或 Topbar；
- Title 不加 Icon；
- Header 不放入 Card。

---

# 4. Summary Strip Pattern

适用：

当数字能帮助用户做判断。

例如文章：

```text
全部文章
已发布
草稿
待审核
```

评论：

```text
待审核
今日评论
已通过
已拒绝
```

不适用：

- 日志列表；
- 简单配置页；
- 数据没有决策价值的列表。

结构：

```text
Summary Container
├─ Item
├─ Item
├─ Item
└─ Item
```

默认最多 4 个。

如果超过 4 个，优先重新判断哪些指标真正必要。

---

# 5. Toolbar Pattern

结构：

```text
Left
├─ Search
├─ Primary Filters
└─ More Filters

Right
├─ Result Count
├─ Refresh
└─ Secondary Action
```

推荐顺序：

```text
Search
→ 高频筛选
→ 低频筛选
→ 批量 / 工具动作
```

不要：

- Refresh 放到 Page Header；
- Search 单独一行、筛选又单独一张 Card；
- 每个 Filter 都使用不同控件高度。

---

# 6. Search Pattern

List 搜索默认：

```text
width: 280–360px
height: 34px
```

Placeholder 应说明搜索范围：

```text
搜索文章标题或摘要
搜索用户或邮箱
搜索操作、用户或资源
```

不要只写：

```text
搜索...
```

---

# 7. Filter Pattern

高频 Filter 直接展示。

例如文章：

```text
状态
专题
```

低频：

```text
作者
日期
标签
```

进入：

```text
更多筛选
```

避免工具栏同时出现 6–8 个 Select。

---

# 8. Data Table Pattern

## 8.1 Table 列设计

原则：

每列必须回答一个业务问题。

文章：

```text
文章
状态
专题
浏览
发布时间
最近更新
操作
```

评论：

```text
评论
状态
用户
文章
时间
操作
```

标签：

```text
标签
Slug
使用量
最近使用
操作
```

---

## 8.2 Table 第一列

第一业务列通常承担最主要识别信息。

例如：

```text
Title
Summary
Tag
```

或：

```text
Username
Email
```

不要把业务实体的重要信息拆到 3–4 列造成扫描困难。

---

# 9. Row Action Pattern

标准：

```text
[编辑] [···]
```

如果实体本身主要是查看：

```text
[查看] [···]
```

Menu 内：

```text
Secondary Action
Secondary Action
State Action
────────────
Danger Action
```

Danger Action 始终放最后。

---

# 10. Batch Action Pattern

只有真的存在批量业务价值时启用。

例如评论：

```text
选中 N 条

批量通过
批量拒绝
```

文章可支持：

```text
批量发布
批量移动专题
批量删除
```

但 V1 不必为了完整而全部实现。

批量模式原则：

```text
Selection
→ Action Bar
→ Confirm when dangerous
→ Partial failure feedback
```

---

# 11. Status Pattern

统一四类：

```text
success
warning
neutral
danger
```

例：

```text
已发布      success
待审核      warning
草稿        neutral
失败        danger
```

视觉：

```text
Dot + Text
```

如果 Status 本身还可操作，不要把状态直接做成 Dropdown。

应：

```text
状态展示
+
··· 中状态操作
```

---

# 12. Topic / Tag Pattern

Topic 与 Tag 不同。

## Topic

代表内容组织结构。

可以显示：

```text
AI 工程
```

使用轻量 Badge。

## Tag

用于文章局部标识。

可以多个：

```text
RAG
Python
Embedding
```

Tag 不应承担 Status 语义。

---

# 13. Dashboard Pattern

仪表盘不是“大屏”。

标准结构：

```text
Page Header

Metric Row

Main Grid
├─ 最近更新
├─ 待处理
├─ 内容概览
└─ 快速操作
```

仪表盘优先回答：

```text
现在有什么需要处理？
最近发生了什么？
```

不是：

```text
能放多少图表？
```

---

# 14. Dashboard Metric

允许 4 个左右：

```text
文章
评论
专题
项目
```

或：

```text
待审核
草稿
本月发布
浏览
```

不要四色 KPI。

---

# 15. Comments Pattern

评论属于审核工作流。

结构：

```text
Summary
→ 待审核 / 今日 / 已通过 / 已拒绝

Toolbar
→ Status
→ Article
→ Search

Table
→ Comment
→ Status
→ User
→ Article
→ Time
→ Actions
```

待审核行：

```text
通过
拒绝
```

已经审核：

```text
撤销
查看文章
```

低频动作可以进入 Menu。

---

# 16. Topics Pattern

专题属于内容治理。

字段：

```text
专题名称
说明
文章数
状态
最近更新
操作
```

推荐状态：

```text
持续更新
常规
隐藏
```

专题不是标签。

专题可以有：

- 描述；
- 封面 / Technical Visual；
- 推荐入口文章；
- 排序。

---

# 17. Tags Pattern

标签页应该比专题页更高密度。

字段：

```text
标签
Slug
使用量
最近使用
操作
```

推荐支持：

```text
搜索
按使用量排序
清理未使用
```

不需要复杂 KPI Hero。

---

# 18. Projects Pattern

项目是公开站新的一级内容类型。

管理字段：

```text
项目名称
状态
技术栈
相关文章
最近更新
操作
```

状态可以：

```text
开发中
已公开
维护中
已归档
草稿
```

项目 Detail/Edit 应支持：

```text
名称
Slug
Summary
Status
Tech Stack
Demo URL
Repo URL
Cover / Preview
Related Articles
Changelog
```

---

# 19. Media Library Pattern

媒体与普通 Data Table 不完全相同。

推荐：

```text
Toolbar
Search
Type Filter
Sort

Grid / Table Toggle optional
```

默认更适合 Grid：

```text
Thumbnail
Filename
Type
Size
Uploaded At
Usage Count
```

大量文件时可提供 Table View。

---

# 20. User Management Pattern

字段：

```text
用户
角色
状态
最后登录
创建时间
操作
```

用户详情适合 Drawer：

```text
Profile
Role
Sessions
Recent Activity
Security
```

---

# 21. Security Center Pattern

安全中心不是普通 Table。

适合：

```text
Status Cards / Sections
```

例如：

```text
安全状态
登录安全
会话
安全策略
最近安全事件
```

安全状态必须能快速判断：

```text
正常
需要处理
```

---

# 22. Audit Log Pattern

日志页使用高密度 Table。

字段：

```text
时间
用户
操作
资源
结果
IP
```

支持：

```text
搜索
操作类型
用户
时间范围
结果
导出
```

日志默认不需要 Summary Strip。

---

# 23. Settings Pattern

设置页使用：

```text
Stacked Setting Sections
```

例如：

```text
站点信息

内容设置

安全设置

系统
```

每个 Section：

```text
Card
├─ Header
└─ Key / Value Rows
```

不要把 Settings 做成 Data Table。

---

# 24. Form Pattern

新增 / 编辑文章、专题、项目时：

```text
Page Header

Main Form
Sidebar optional
```

文章编辑推荐：

```text
Main
├─ Title
├─ Deck
├─ Content Editor
└─ Article Blocks

Side
├─ Status
├─ Topic
├─ Tags
├─ Publish Time
├─ Slug
└─ SEO
```

如果屏幕窄：

```text
Side
→ collapsible sections
```

---

# 25. Form Save Pattern

长表单推荐：

```text
Save Draft
Preview
Publish
```

不要同时放：

```text
保存
保存并返回
保存并继续
预览
发布
发布并返回
```

过多操作。

明确主路径。

---

# 26. Dialog Pattern

适合：

```text
删除确认
状态变更
创建简单标签
批量操作确认
```

宽度建议：

```text
420–560px
```

Dialog 内容超过一个完整业务流程时，应改 Drawer 或 Page。

---

# 27. Drawer Pattern

适合：

```text
评论详情
用户详情
日志详情
媒体详情
快速编辑 Metadata
```

推荐宽度：

```text
480–640px
```

Drawer 不应承载文章编辑器。

---

# 28. Dropdown Menu Pattern

所有 `···` 菜单统一：

```text
width ≈ 160–200px
```

层级：

```text
Normal Actions

State Actions

Separator

Danger Actions
```

不在 Menu 内塞复杂 Form。

---

# 29. Empty Pattern

格式：

```text
Empty Title

Description

Optional Action
```

例如：

```text
暂无待审核评论

新的待审核评论会出现在这里。
```

如果用户可以立即解决空状态，可以增加：

```text
+ 新建专题
```

---

# 30. Loading Pattern

## Table

Skeleton rows。

## Dashboard

单个 Card 独立 Skeleton。

## Form

初始加载前禁用提交。

不推荐全屏遮罩。

---

# 31. Error Pattern

按错误层级：

```text
Field Error
Component Error
Page Error
Global Error
```

不要所有异常都 Toast。

例如筛选请求失败：

```text
列表加载失败
[重新加载]
```

比右上角 Toast 更可靠。

---

# 32. Toast Pattern

Toast 只用于短暂结果：

```text
保存成功
复制成功
上传完成
```

错误如果需要用户处理，不能只依赖 Toast。

---

# 33. Confirmation Pattern

危险操作必须明确对象。

不要：

```text
确定删除吗？
```

推荐：

```text
删除文章「深入理解 RAG：从检索到生成」？

删除后文章将不再出现在公开站。
```

按钮：

```text
取消
删除文章
```

---

# 34. Permissions Pattern

如果后续支持多角色：

UI 只负责：

```text
隐藏无权限动作
禁用需要上下文解释的动作
```

后端仍必须强制鉴权。

权限错误：

```text
你没有权限执行此操作。
```

不要：

```text
操作失败。
```

---

# 35. Table Column Priority

响应式时列隐藏顺序应预先定义。

例如文章：

```text
必须保留
Article
Status
Action

优先保留
Topic
Updated At

可隐藏
Views
Published At
```

不要由 CSS 随机压缩。

---

# 36. Bulk Selection

选中以后 Toolbar 可以进入：

```text
已选择 12 项

批量操作...
取消选择
```

切换分页或修改筛选条件时：

V1 推荐清空选择。

避免隐式跨页选择。

---

# 37. Sorting

只有有实际意义的字段支持排序。

例如：

```text
Updated At
Published At
Usage Count
Created At
```

不要所有 Header 都放排序箭头。

---

# 38. Result Count

Toolbar 或 Table Footer 展示：

```text
47 条结果
```

与 Pagination 总数保持一致。

---

# 39. Refresh

有后台实时变化价值时显示：

```text
刷新
```

不需要所有页面都机械加入 Refresh。

例如：

文章 / 评论
→ 可以有

设置
→ 不需要

---

# 40. 页面 Pattern 映射

| 页面 | Pattern |
|---|---|
| 仪表盘 | Dashboard |
| 文章 | List Management |
| 评论 | Review List + Batch |
| 专题 | Governance List |
| 标签 | Dense List |
| 项目 | Governance List |
| 媒体 | Media Grid |
| 用户 | List + Detail Drawer |
| 安全 | Status / Settings |
| 日志 | Audit Table |
| 设置 | Settings Sections |

---

# 41. Vue 组件建议

```text
AdminLayout.vue

AdminSidebar.vue
AdminTopbar.vue
AdminPageHeader.vue

AdminSummaryStrip.vue
AdminToolbar.vue
AdminSearchInput.vue
AdminFilterSelect.vue

AdminTable.vue
AdminTableFooter.vue
AdminPagination.vue

AdminStatus.vue
AdminTag.vue

AdminActionMenu.vue
AdminConfirmDialog.vue
AdminDrawer.vue

AdminEmptyState.vue
AdminErrorState.vue
AdminSkeleton.vue
```

注意：

> 不要把所有业务表格强行变成一个超级通用组件。

`AdminTable` 只统一基础视觉与基础能力。

具体列定义留给页面。

---

# 42. Element Plus 使用原则

后台可以继续使用 Element Plus。

推荐使用：

```text
ElTable
ElInput
ElSelect
ElButton
ElDropdown
ElDialog
ElDrawer
ElPagination
ElForm
```

但需要统一覆盖 Design Tokens。

不能：

```text
一个页面是 Element Plus 默认风格
另一个页面是 Tailwind 手写风格
```

原则：

```text
Element Plus
= Behavior + Accessibility + Base Component

Admin Design Tokens
= Final Visual
```

---

# 43. Tailwind 使用原则

Tailwind 负责：

- Layout；
- Spacing；
- Responsive；
- 非 Element Plus 结构组件。

Element Plus 负责：

- Form；
- Table；
- Select；
- Dialog；
- Drawer；
- Dropdown。

避免同一类组件两套实现。

---

# 44. 页面开发验收模板

每开发一个后台页面，Review：

```text
Page:
Route:

[ ] 是否使用 AdminLayout
[ ] 是否使用统一 Page Header
[ ] Primary Action 是否只有一个
[ ] 是否符合对应 Pattern
[ ] Search Placeholder 是否明确
[ ] 高频 Filter 是否直接展示
[ ] Table 列是否全部有业务价值
[ ] Status 是否使用统一语义
[ ] Row Action 是否使用统一模式
[ ] Danger Action 是否二次确认
[ ] Pagination 是否统一
[ ] Empty / Loading / Error 是否覆盖
[ ] Tablet / Mobile 是否可用
[ ] 是否出现旧版渐变 / Glow / Hero Card
```

---

# 45. 最终原则

后台 Pattern 的价值不在于：

> 所有页面长得一样。

而在于：

> 相同问题使用相同解决方案。

因此：

```text
同一种列表
→ 同一种 Toolbar

同一种状态
→ 同一种 Status

同一种危险操作
→ 同一种 Confirm

同一种详情
→ 同一种 Drawer
```

页面差异应该来自业务内容，而不是来自随意变化的 UI 结构。
