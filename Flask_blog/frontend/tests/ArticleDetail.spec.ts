import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ArticleDetail from '../src/views/ArticleDetail.vue'

vi.mock('../src/api', () => ({
  API: {
    getArticleBySlug: vi.fn(),
    getArticle: vi.fn(),
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

  it('handles article not found without crashing', async () => {
    vi.mocked(API.getArticleBySlug).mockRejectedValue(new Error('not found'))
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getArticleBySlug)).toHaveBeenCalled()
  })
})
