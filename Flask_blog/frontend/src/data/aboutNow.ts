/**
 * 关于页「现在」侧栏 + 叙事 + 时间线的单一配置源(impl-P2 C1)。
 * 日常更新只改这个文件,不动组件。
 */

export interface AboutNowItem {
  label: string
  text: string
}

export interface AboutTimelineRow {
  year: string
  title: string
  text: string
}

export const ABOUT_HEADLINE = '我更关心“把东西做出来”，然后把过程写清楚。'

/** 三段叙事:为什么有这个站 / 主要写什么 / 内容如何互相连接(反履历) */
export const ABOUT_NARRATIVE: string[] = [
  '这里是我的个人技术主页。主要记录 Python、AI、软件设计、产品实践，以及那些在真实项目里反复遇到、最终值得单独写下来的问题。',
  '文章不是为了追热点而发布，项目也不是为了凑作品集。更希望它们能互相连接：一个项目产生问题，一篇文章把问题说明白，新的理解再回到项目里。',
  '所以这里会同时存在长文、实验、项目记录、代码、图表和持续更新的专题。',
]

/** 「现在」侧栏 */
export const ABOUT_NOW: AboutNowItem[] = [
  { label: '正在写', text: 'RAG 系列与 AI 工程实践' },
  { label: '正在做', text: 'Structure Lab · 交互式结构稳定性实验' },
  { label: '主要技术', text: 'Python · Vue · Flask · LLM' },
  { label: '其它入口', text: 'GitHub · RSS · 邮件' },
]

/** 极简时间线:行数 ≤5(impl-P2 C1 验收),超出说明写法错了 */
export const ABOUT_TIMELINE: AboutTimelineRow[] = [
  {
    year: '2026',
    title: 'AI 工程、权限架构与产品实验',
    text: '大量时间放在真实系统设计、RAG、Agent、权限边界和前端产品体验上。',
  },
  {
    year: '2025',
    title: '工程化与自动化',
    text: '继续使用 Python 做测试、自动化和后端工具，也开始更系统地整理项目文档。',
  },
  {
    year: '更早',
    title: '从测试工程走向开发',
    text: '从 Selenium、pytest 等自动化实践逐渐扩展到完整应用开发。',
  },
]
