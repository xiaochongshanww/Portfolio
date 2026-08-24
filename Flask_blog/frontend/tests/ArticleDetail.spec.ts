import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ArticleDetail from '../src/views/ArticleDetail.vue'

vi.mock('../src/api', () => ({
  API: {
    getArticleBySlug: vi.fn(),
    getArticle: vi.fn(),
    getPublicArticles: vi.fn(),
    likeArticle: vi.fn(),
    bookmarkArticle: vi.fn(),
    getArticleVersions: vi.fn(),
    createArticleVersion: vi.fn(),
    rollbackVersion: vi.fn(),
    diffVersions: vi.fn(),
    submitArticle: vi.fn(),
    approveArticle: vi.fn(),
    rejectArticle: vi.fn(),
    scheduleArticle: vi.fn(),
    unscheduleArticle: vi.fn(),
    unpublishArticle: vi.fn(),
  },
}))
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { slug: 'test-article' } }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))
vi.mock('../stores/user', () => ({
  useUserStore: () => ({
    user: null,
    isAuthenticated: false,
    initAuth: vi.fn(),
  }),
}))
vi.mock('lowlight', () => ({
  common: {},
  createLowlight: () => ({ highlight: () => ({}) }),
}))
// E8:jsdom 中跳过 shiki 异步高亮,直接返回纯文本 pre
vi.mock('../src/utils/blockHighlighter', () => ({
  highlightCode: async (code: string) =>
    `<pre class="shiki-plain"><code>${String(code ?? '')}</code></pre>`,
}))
vi.mock('highlight.js', () => ({
  default: { highlightAuto: () => ({ value: '' }) },
}))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()) },
}))

import { API } from '../src/api'

beforeAll(() => {
  if (typeof (globalThis as any).ResizeObserver === 'undefined') {
    ;(globalThis as any).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
  }
})

const ARTICLE = {
  id: 1,
  title: 'Test Article',
  slug: 'test-article',
  status: 'published',
  content_html: '<p>hello</p>',
  content_md: '# hello',
  summary: 'sum',
  author_id: 1,
  views_count: 5,
  likes_count: 2,
  bookmarks_count: 1,
  published_at: '2026-01-01T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
  tags: [{ id: 1, name: 'vue' }],
  author: { id: 1, nickname: 'Bob' },
}

function mountPage() {
  return mount(ArticleDetail, {
    global: {
      plugins: [createPinia()],
      stubs: {
        CommentsThread: { template: '<div class="c-stub" />' },
        CoverImage: { template: '<div class="cov-stub" />' },
        ArticleContentRenderer: { template: '<div class="render-stub" />' },
        ArticleActions: { template: '<div class="act-stub" />' },
        ArticleInteractions: { template: '<div class="int-stub" />' },
        ReadingRail: { template: '<div class="rail-stub" />' },
        'el-button': { template: '<button><slot /></button>' },
        'el-empty': { template: '<div class="empty" />' },
        'el-icon': true,
        'el-skeleton': { template: '<div class="skel" />' },
        'el-tag': { template: '<span class="tag"><slot /></span>' },
      },
    },
  })
}

describe('ArticleDetail', () => {
  beforeEach(() => {
    vi.mocked(API.getArticleBySlug).mockReset()
    vi.mocked(API.getPublicArticles).mockReset()
    vi.mocked(API.getPublicArticles).mockResolvedValue({
      data: { data: { list: [] } },
    } as any)
    document.head.innerHTML = ''
  })

  it('loads and renders a published article via blocks pipeline', async () => {
    vi.mocked(API.getArticleBySlug).mockResolvedValue({
      data: { data: ARTICLE },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getArticleBySlug)).toHaveBeenCalledWith('test-article')
    // 新排版:文章身份区标题渲染
    expect(wrapper.find('.article-title').text()).toBe('Test Article')
    // Blocks 管线生效(content_md='# hello' → heading block),不再走旧渲染器
    expect(wrapper.find('.article-renderer').exists()).toBe(true)
    expect(wrapper.find('h1.heading-block, h2.heading-block, h3.heading-block').exists()).toBe(true)
    // 结尾维护区(E6)
    expect(wrapper.find('.maintenance').exists()).toBe(true)
    // 阅读工具挂载
    expect(wrapper.find('.rail-stub').exists()).toBe(true)
  })

  it('E8 兼容性:存量 Markdown 全类型无损渲染(含 :::note callout)', async () => {
    const legacyMd = [
      '# 深入理解 RAG',
      '',
      '普通段落,含**加粗**与`行内代码`。',
      '',
      ':::note 设计原则',
      '所有 Block 共享同一条内容轴。',
      ':::',
      '',
      '## 基础富文本',
      '',
      '- 列表项一',
      '- 列表项二',
      '',
      '> 引用第一行',
      '> — 页面备注',
      '',
      '```python:demo.py',
      'print("hello")',
      '```',
      '',
      '| 列 A | 列 B |',
      '| --- | --- |',
      '| 1 | 2 |',
    ].join('\n')
    vi.mocked(API.getArticleBySlug).mockResolvedValue({
      data: { data: { ...ARTICLE, content_md: legacyMd } },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()

    const text = wrapper.find('.reading-canvas').text()
    for (const expected of ['深入理解 RAG', '加粗', '行内代码', '设计原则', '列表项一', '引用第一行', '页面备注', 'hello', '列 A']) {
      expect(text).toContain(expected)
    }
    // callout 走 CalloutBlock(tone-note),不是普通段落
    expect(wrapper.find('.callout-block').exists()).toBe(true)
    // 代码块头部栏显示文件名
    expect(wrapper.find('.code-block').exists()).toBe(true)
    // 表格渲染
    expect(wrapper.find('.table-block, table').exists()).toBe(true)
  })

  it('E8 SEO:加载后注入 og/article 时间与 canonical', async () => {
    vi.mocked(API.getArticleBySlug).mockResolvedValue({
      data: { data: ARTICLE },
    } as any)
    mountPage()
    await flushPromises()
    await Promise.resolve()
    expect(document.head.querySelector('meta[property="og:title"]')?.getAttribute('content')).toBe('Test Article')
    expect(document.head.querySelector('meta[property="article:published_time"]')?.getAttribute('content')).toBe('2026-01-01T00:00:00Z')
    expect(document.head.querySelector('meta[property="article:modified_time"]')).toBeTruthy()
    expect(document.head.querySelector('link[rel="canonical"]')).toBeTruthy()
  })

  it('E6 补充:相邻文章 prev/next 导航(当前篇在列表中间)', async () => {
    vi.mocked(API.getArticleBySlug).mockResolvedValue({
      data: { data: ARTICLE },
    } as any)
    vi.mocked(API.getPublicArticles).mockResolvedValue({
      data: {
        data: {
          list: [
            { slug: 'newer-post', title: '更新的一篇' },
            { slug: 'test-article', title: 'Test Article' },
            { slug: 'older-post', title: '更早的一篇' },
          ],
        },
      },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    const nav = wrapper.find('.article-nav')
    expect(nav.exists()).toBe(true)
    expect(nav.text()).toContain('更新的一篇')
    expect(nav.text()).toContain('更早的一篇')
    expect(nav.find('a').attributes('href')).toBe('/article/newer-post')
  })

  it('E6 补充:列表拉取失败时导航隐藏,不影响正文', async () => {
    vi.mocked(API.getArticleBySlug).mockResolvedValue({
      data: { data: ARTICLE },
    } as any)
    vi.mocked(API.getPublicArticles).mockRejectedValue(new Error('list down'))
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.article-nav').exists()).toBe(false)
    expect(wrapper.find('.maintenance').exists()).toBe(true)
  })

  it('handles article not found without crashing', async () => {
    vi.mocked(API.getArticleBySlug).mockRejectedValue(new Error('not found'))
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getArticleBySlug)).toHaveBeenCalled()
  })
})
