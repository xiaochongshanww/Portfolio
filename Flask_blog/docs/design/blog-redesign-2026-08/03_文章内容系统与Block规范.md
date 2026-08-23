# 03_文章内容系统与Block规范

> 本文定义文章详情页的核心架构。  
> 关键结论：Article Detail 不是 Markdown Viewer，而是一个 Mixed Content Renderer。

---

## 1. 核心模型

文章详情页由两部分组成：

```text
Article Canvas
+
Page-level Reading Tools
```

其中：

```text
Article Canvas
负责内容

Reading Tools
负责导航和阅读辅助
```

两者不得产生布局依赖。

---

## 2. Markdown 的定位

Markdown 继续是最常用内容输入格式之一，但不能成为渲染模型本身。

错误模型：

```text
Article
→ Markdown String
→ v-html
```

推荐模型：

```text
Content Source
├─ Markdown
├─ Rich Text
├─ Structured Data
└─ Interactive Content
        ↓
Normalized Blocks
        ↓
Article Renderer
```

---

## 3. Block Model

建议定义：

```text
ArticleBlock
├─ paragraph
├─ heading
├─ list
├─ quote
├─ callout
├─ code
├─ image
├─ gallery
├─ table
├─ diagram
├─ embed
├─ media
├─ attachment
├─ tabs
└─ custom
```

基础 TS 模型可以设计成：

```ts
interface BaseBlock {
  id: string
  type: string
  width?: BlockWidth
}

type BlockWidth =
  | 'text'
  | 'code'
  | 'wide'
  | 'xwide'
```

---

## 4. Block Width System

统一宽度：

```text
text     760px
code     820px
wide     960px
xwide   1040px
```

推荐映射：

| Block | Width |
|---|---|
| paragraph | text |
| heading | text |
| list | text |
| quote | text |
| callout | text |
| code | code |
| attachment | text |
| media | text / wide |
| table | wide |
| image | wide |
| diagram | wide |
| gallery | xwide |
| interactive embed | xwide |
| custom | explicit |

最重要规则：

> 所有 Block 共享同一条页面中心轴。

宽内容必须：

```text
从中心向左右展开
```

不能：

```text
把正文整体向左推
```

---

## 5. Article Identity

文章顶部：

```text
Topic / Category

Title

Deck / Summary

Published At
Read Time
Last Updated

Tags
```

推荐宽度：

```text
760px
```

文章标题与正文共享同一中心轴。

不要：

- 标题 900px；
- 正文 760px；
- 再让目录占右栏。

否则页面从一开始就失去视觉轴线。

---

## 6. Lead Visual

文章可选开场视觉：

```text
Lead Visual
```

适合：

- 架构图；
- 关键流程；
- 产品截图；
- 技术关系图。

推荐：

```text
960px
```

Lead Visual 不是必须。

没有合适内容时可以不展示。

---

## 7. Paragraph / Heading

正文：

```text
17px
line-height: 1.85–1.95
max-width: 760px
```

H2：

```text
28–30px
margin-top: 48–52px
```

H3：

```text
20–22px
margin-top: 32–36px
```

避免：

- 标题层级过多；
- H4/H5 靠字号压得很小；
- 正文行宽超过 800px。

---

## 8. Callout

用途：

- 注意；
- 设计原则；
- 风险；
- 结论；
- 提示。

示例数据：

```ts
interface CalloutBlock {
  type: 'callout'
  tone: 'info' | 'warning' | 'success' | 'note'
  title?: string
  content: RichContent
}
```

Callout 不应出现过多颜色。

Signal Soft 可以作为默认强调色。

---

## 9. Quote

Quote 用于：

- 引用；
- 核心判断；
- 原则性总结。

视觉：

```text
左侧 3px Signal Line
无大面积背景
```

不要做巨大引号图标。

---

## 10. Code Block

Code Block 需要独立组件。

支持：

```text
language
filename
copy
horizontal scroll
highlight lines
diff
line number (optional)
```

推荐模型：

```ts
interface CodeBlock {
  type: 'code'
  language: string
  filename?: string
  code: string
  highlightLines?: number[]
  showLineNumbers?: boolean
}
```

默认宽度：

```text
820px
```

---

## 11. Image

模型：

```ts
interface ImageBlock {
  type: 'image'
  src: string
  alt: string
  caption?: string
  width?: 'text' | 'wide' | 'xwide'
  zoomable?: boolean
}
```

规则：

- 架构图默认 wide；
- 普通截图可 wide；
- 简单小图可以 text；
- Caption 回到 text width。

---

## 12. Gallery

模型：

```ts
interface GalleryBlock {
  type: 'gallery'
  items: ImageBlock[]
  layout?: 'grid' | 'compare' | 'carousel'
}
```

桌面：

```text
2–3 columns
```

移动：

```text
single column / carousel
```

默认：

```text
xwide
```

---

## 13. Table

必须使用真实 Table 语义，不使用截图。

支持：

- 横向滚动；
- Header；
- alignment；
- caption；
- 可选 sortable。

默认：

```text
wide
```

移动端不能强行缩小字体来塞进屏幕。

---

## 14. Diagram

Diagram 来源可以是：

```text
Mermaid
SVG
Structured JSON
Custom Component
```

模型示例：

```ts
interface DiagramBlock {
  type: 'diagram'
  format: 'mermaid' | 'svg' | 'custom'
  source: string
  caption?: string
}
```

默认：

```text
wide
```

---

## 15. Interactive Embed

这是本内容系统与普通 Markdown Blog 最大的区别之一。

适合：

- Structure Lab；
- Playground；
- 参数调节；
- 可视化 Demo；
- 小型 App。

模型：

```ts
interface EmbedBlock {
  type: 'embed'
  title: string
  component?: string
  src?: string
  openInNewWindow?: boolean
}
```

默认：

```text
xwide
```

要求：

- 有明确边框；
- 有局部 Header；
- 可打开新窗口；
- 页面加载失败时有 fallback。

---

## 16. Media

支持：

```text
video
audio
external
```

模型：

```ts
interface MediaBlock {
  type: 'media'
  mediaType: 'video' | 'audio' | 'external'
  title: string
  src: string
  poster?: string
  duration?: number
  caption?: string
}
```

不要直接裸露 iframe。

统一由 MediaBlock 包装。

---

## 17. Attachment

支持：

```text
PDF
Notebook
ZIP
Dataset
Source Code
Config
```

模型：

```ts
interface AttachmentBlock {
  type: 'attachment'
  name: string
  fileType: string
  size?: number
  url: string
  updatedAt?: string
}
```

展示：

```text
File Icon
Name
Size
Updated At
Download
```

---

## 18. Tabs

适合：

```text
Python
curl
JSON
```

或：

```text
Vue
React
Plain JS
```

模型：

```ts
interface TabsBlock {
  type: 'tabs'
  tabs: Array<{
    label: string
    content: ArticleBlock[]
  }>
}
```

Tabs 内部仍然可以复用 Block Renderer。

---

## 19. Reading Rail

Reading Rail 是页面级组件。

不是：

```text
Article Grid Column
```

而是：

```text
Fixed / Floating Reading Tool
```

Desktop：

```text
Viewport Right
└─ Reading Rail
```

职责：

- TOC；
- 当前章节；
- 阅读进度；
- 复制链接；
- 返回顶部。

关键约束：

> Reading Rail 是否存在，不得改变 Article Canvas 的任何 x 坐标。

---

## 20. Reading Rail 响应式

推荐：

```text
≥ 1280px
→ Floating Reading Rail

Tablet
→ Floating TOC Button

Mobile
→ TOC Button + Drawer / Bottom Sheet
```

不允许：

```text
Tablet 时把正文压窄来保留目录。
```

---

## 21. TOC 生成规则

TOC 默认由：

```text
H2
H3 optional
```

生成。

通常只展示 H2。

文章过长时：

```text
H2
└─ 当前 H2 下 H3
```

可以动态展开。

每个 heading 必须具有稳定 id。

---

## 22. 阅读进度

页面顶部：

```text
2px Progress Bar
```

Reading Rail：

```text
42%
```

移动目录入口：

```text
目录 42%
```

三处可以共享同一 progress state。

---

## 23. Article Closing

文章结尾不是正文突然结束。

推荐：

```text
Maintenance Info

Last Updated

Tags

Previous / Next
```

如果文章持续维护：

```text
这篇文章仍在持续维护
```

这比传统“相关文章 6 张卡片”更符合当前设计。

---

## 24. 数据结构建议

推荐：

```ts
interface Article {
  id: string
  slug: string
  title: string
  deck?: string

  topic?: TopicRef
  tags: TagRef[]

  publishedAt: string
  updatedAt?: string
  readingMinutes?: number

  lead?: ArticleBlock

  blocks: ArticleBlock[]

  maintenance?: {
    enabled: boolean
    message?: string
  }

  prev?: ArticleRef
  next?: ArticleRef
}
```

---

## 25. Markdown 转 Block

第一阶段不要求重写现有文章存储。

可以：

```text
Markdown
↓
Markdown Parser
↓
AST
↓
Article Blocks
↓
Renderer
```

例如：

```text
paragraph → ParagraphBlock
heading   → HeadingBlock
code      → CodeBlock
table     → TableBlock
image     → ImageBlock
```

特殊内容通过扩展语法或独立结构保存。

---

## 26. 向后兼容策略

已有 Markdown 文章必须继续正常渲染。

建议：

```text
Legacy Markdown
→ Normalized Blocks
```

不要：

```text
Legacy Markdown Renderer

和

New Block Renderer

长期维护两套完全独立视觉。
```

最终都进入统一 Renderer。

---

## 27. Renderer 组件建议

Vue：

```text
ArticleRenderer.vue
│
├─ ParagraphBlock.vue
├─ HeadingBlock.vue
├─ ListBlock.vue
├─ QuoteBlock.vue
├─ CalloutBlock.vue
├─ CodeBlock.vue
├─ ImageBlock.vue
├─ GalleryBlock.vue
├─ TableBlock.vue
├─ DiagramBlock.vue
├─ EmbedBlock.vue
├─ MediaBlock.vue
├─ AttachmentBlock.vue
└─ TabsBlock.vue
```

入口：

```vue
<component
  :is="blockComponentMap[block.type]"
  :block="block"
/>
```

Block Width 不应由每个组件随意写 CSS。

推荐统一：

```ts
block.width
```

映射到：

```text
content-width-text
content-width-code
content-width-wide
content-width-xwide
```

---

## 28. 安全

如果继续支持 Markdown HTML：

- 禁止直接信任用户输入 HTML；
- sanitize；
- iframe 必须白名单；
- external embed 限制来源；
- attachment 校验 MIME；
- SVG 需要安全处理。

---

## 29. 性能

文章可能包含大量媒体。

要求：

- Image lazy loading；
- 图片 responsive srcset；
- Video 不自动 preload 全量；
- Interactive Embed 懒加载；
- Mermaid / Diagram 按需加载；
- Code highlight 避免阻塞首屏；
- Lead Visual 优先于正文下方媒体。

---

## 30. SEO

文章详情必须提供：

```text
title
description
canonical
Open Graph
Article structured data
published_time
modified_time
```

技术图片应该有合理 alt。

---

## 31. Article Renderer 验收清单

### 布局

- [ ] Title 与正文共享中心轴
- [ ] Paragraph 最大宽度约 760px
- [ ] Code 约 820px
- [ ] Wide Block 约 960px
- [ ] X-Wide Block 约 1040px
- [ ] 所有 Block 对称展开
- [ ] Reading Rail 不推动正文
- [ ] Reading Rail 消失时正文位置完全不变

### 内容

- [ ] Markdown 正常渲染
- [ ] Code 可复制
- [ ] Image 有 Caption / Alt
- [ ] Gallery 响应式
- [ ] Table 横向滚动
- [ ] Diagram 可渲染
- [ ] Embed 有失败 fallback
- [ ] Media 有统一包装
- [ ] Attachment 可下载
- [ ] Tabs 可键盘操作

### 阅读工具

- [ ] TOC 自动生成
- [ ] 当前章节高亮
- [ ] 阅读进度准确
- [ ] 复制链接可用
- [ ] 回到顶部可用
- [ ] Tablet / Mobile 切换为 Drawer
- [ ] ESC 可关闭 Drawer

### 兼容

- [ ] 旧 Markdown 无需修改即可渲染
- [ ] 新 Block 与旧内容视觉一致
- [ ] 不存在两套文章视觉体系

---

## 32. 最终原则

文章系统最终应做到：

> 内容格式可以不断增加，但文章页面的阅读秩序不能因为内容类型增加而失控。

因此未来新增任何 Block，都必须先回答：

1. 它属于哪个宽度级别？
2. 它是否共享中心轴？
3. 移动端如何退化？
4. 是否需要独立 loading / error？
5. 是否应该进入 TOC？
6. 是否会破坏连续阅读节奏？

如果这些问题没有明确答案，不应直接加入 Article Renderer。
