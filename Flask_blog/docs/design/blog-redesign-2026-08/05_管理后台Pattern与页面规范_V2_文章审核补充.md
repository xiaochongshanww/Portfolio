# 05_管理后台Pattern与页面规范_V2：文章审核补充

> 状态：Design Baseline Addendum  
> 关联原型：`article-review-queue-v1.html`、`article-review-detail-v1.html`

## 1. 后台内容 IA

```text
内容
├─ 文章
├─ 审核
└─ 评论
```

三者职责固定：

```text
文章管理
= 全生命周期内容管理

文章审核
= Pending Review 工作队列

评论管理
= 评论审核与讨论治理
```

文章管理里的“待审核”只是状态统计，不承担完整审核工作流。

## 2. Review Queue Pattern

标准结构：

```text
Page Header

Summary
├─ 待审核
└─ 今日已审核

Tabs
├─ 待审核
├─ 最近处理
└─ 我审核的

Toolbar
├─ Search
├─ Topic Filter
└─ Sort

Review Queue Table
```

审核页禁止使用旧式 Hero Card、渐变 Tab、彩色 KPI Card 和大型空状态插画。

## 3. 队列字段

推荐：

```text
文章
提交人
专题
提交时间
等待时长
操作
```

默认按提交时间升序，让最早进入队列的文章优先处理。

列表只提供：

```text
开始审核
```

不直接提供：

```text
通过
驳回
```

文章审核必须先阅读完整内容。

## 4. Review Detail Pattern

Desktop：

```text
Article Preview | Review Panel 360px
```

Tablet / Mobile：

```text
Article Preview
↓
Review Panel
```

Article Preview 应尽可能复用公开站 `ArticleRenderer`，避免维护两套正文渲染。

Review Panel 至少包含：

```text
状态
提交人
专题
标签
提交时间
最后更新时间
审核历史
```

主要动作：

```text
驳回
通过并发布
```

## 5. 驳回

点击“驳回”打开 Dialog：

```text
驳回文章

驳回原因 *
[ 内容需要补充 ▼ ]

审核意见
[ 请说明需要修改的内容…… ]

取消            确认驳回
```

审核意见原则上必填。

## 6. 通过

点击“通过并发布”需要明确结果：

```text
通过并发布「文章标题」？

文章将立即在公开站可访问。

取消        通过并发布
```

## 7. 状态流转

```text
Draft
  ↓ Submit
Pending Review
  ├─ Approve → Published
  └─ Reject  → Returned / Draft
```

中文至少区分：

```text
草稿
待审核
已发布
已退回
```

建议保留 `returned / rejected` 语义，不要驳回后无痕地直接回到草稿。

## 8. 审核历史

至少记录：

```text
submitted
approved
rejected
resubmitted
```

每条包括：

```text
Action
Actor
Time
Comment optional
```

历史不可覆盖。

## 9. 页面联动

```text
文章管理 → 待审核统计
        → Review Queue

Dashboard → 待审核文章
          → Review Queue
```

Dashboard 和文章管理只负责导航到审核工作流，不直接承担审核动作。

## 10. 并发与版本

审核必须基于明确版本。

如果审核期间文章发生更新：

```text
Review Version != Current Version
```

应阻止直接通过旧版本，并提示重新检查最新内容。

长期建议审核请求绑定：

```text
ArticleVersion / ReviewRequest
```

而不是只绑定可变化的 Article 主记录。

## 11. Vue 页面

```text
ArticleManagement.vue
ArticleReviewQueue.vue
ArticleReviewDetail.vue
```

组件建议：

```text
ReviewQueueTable.vue
ReviewHistory.vue
ReviewDecisionPanel.vue
RejectArticleDialog.vue
```

文章预览复用：

```text
ArticleRenderer.vue
```

## 12. 路由

```text
/admin/articles
/admin/reviews
/admin/reviews/:reviewId
```

## 13. 验收

- [ ] Sidebar 内容分组包含审核
- [ ] Queue 无 Hero Card
- [ ] Tabs 使用普通 Selected State
- [ ] 队列有提交时间和等待时长
- [ ] 列表不直接通过 / 驳回
- [ ] 必须进入完整预览才能审核
- [ ] 审核历史可见
- [ ] 驳回有原因 / 意见
- [ ] 通过明确意味着发布
- [ ] 审核基于明确版本
- [ ] Dashboard / 文章管理可跳转审核队列

## 14. 最终原则

文章审核不是“给文章状态加两个按钮”，而是完整工作流：

```text
Submit
→ Queue
→ Read
→ Decide
→ Record
```
