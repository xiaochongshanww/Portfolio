import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import Home from '../src/views/Home.vue'
import ArticleFeedRow from '../src/components/public/ArticleFeedRow.vue'

vi.mock('../src/api', () => ({
  API: {
    getPublicArticles: vi.fn(() =>
      Promise.resolve({ data: { data: { list: [], total: 0 } } }),
    ),
    getPublicTaxonomy: vi.fn(() =>
      Promise.resolve({ data: { data: { categories: [], tags: [] } } }),
    ),
  },
}))
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('../src/stores/user', () => ({
  useUserStore: () => ({ user: null, isAuthenticated: false, initAuth: vi.fn() }),
}))

import { API } from '../src/api'

function makeArticle(overrides = {}) {
  return {
    id: 1,
    slug: 'test-post',
    title: '测试文章',
    summary: '这是摘要',
    content_excerpt: '',
    published_at: '2026-08-20T10:00:00Z',
    created_at: '2026-08-20T10:00:00Z',
    category: 'AI',
    tags: ['RAG'],
    author: { nickname: '小重山', name: 'a@b.c' },
    views_count: 5,
    likes_count: 1,
    comments_count: 2,
    ...overrides,
  }
}

function mountHome() {
  return mount(Home, {
    global: {
      plugins: [createPinia()],
      stubs: {
        'el-skeleton': true,
        TechnicalVisual: true,
      },
    },
  })
}

describe('Home (公开站首页)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(API.getPublicArticles).mockResolvedValue({
      data: { data: { list: [], total: 0 } },
    })
    vi.mocked(API.getPublicTaxonomy).mockResolvedValue({
      data: { data: { categories: [], tags: [] } },
    })
  })

  it('shows empty state when no articles', async () => {
    const wrapper = mountHome()
    await flushPromises()
    expect(wrapper.text()).toContain('还没有发布文章')
    expect(vi.mocked(API.getPublicArticles)).toHaveBeenCalled()
  })

  it('renders featured card and feed rows without community metadata', async () => {
    const articles = [
      makeArticle({ id: 1, title: '最新一篇', slug: 'latest' }),
      makeArticle({ id: 2, title: '第二篇', slug: 'second', category: 'Git' }),
      makeArticle({ id: 3, title: '第三篇', slug: 'third', category: '其他' }),
    ]
    vi.mocked(API.getPublicArticles).mockResolvedValue({
      data: { data: { list: articles, total: 3 } },
    })
    const wrapper = mountHome()
    await flushPromises()

    // featured
    expect(wrapper.find('.latest-card').exists()).toBe(true)
    expect(wrapper.text()).toContain('最新一篇')
    // feed rows 跳过第一篇
    const rows = wrapper.findAll('.feed-row')
    expect(rows.length).toBe(2)

    // 红线断言:页面不出现作者邮箱/点赞/收藏/评论数/阅读量
    const text = wrapper.text()
    expect(text).not.toContain('a@b.c')
    expect(text).not.toContain('点赞')
    expect(text).not.toContain('收藏')
    expect(text).not.toContain('阅读量')

    // DOM 中不渲染计数节点(ArticleFeedRow 无对应 prop)
    const rowComp = wrapper.findAllComponents(ArticleFeedRow)[0]
    expect(rowComp.props('title')).toBe('第二篇')
  })

  it('shows error state with retry when API fails', async () => {
    vi.mocked(API.getPublicArticles).mockRejectedValue(new Error('network'))
    const wrapper = mountHome()
    await flushPromises()
    expect(wrapper.text()).toContain('内容加载失败')
    expect(wrapper.find('.retry-btn').exists()).toBe(true)
  })

  it('shows loading skeleton initially', () => {
    const wrapper = mountHome()
    expect(wrapper.find('.el-skeleton').exists() || wrapper.html().includes('skeleton')).toBe(true)
  })

  it('renders up to four topic cards from taxonomy', async () => {
    vi.mocked(API.getPublicArticles).mockResolvedValue({
      data: { data: { list: [makeArticle()], total: 1 } },
    })
    vi.mocked(API.getPublicTaxonomy).mockResolvedValue({
      data: {
        data: {
          categories: [
            { id: 1, slug: 'ai', name: 'AI 工程', description: 'RAG 与 Agent' },
            { id: 2, slug: 'py', name: 'Python', description: '' },
          ],
          tags: [],
        },
      },
    })
    const wrapper = mountHome()
    await flushPromises()
    const cards = wrapper.findAll('.topic-card')
    expect(cards.length).toBe(2)
    expect(cards[0].text()).toContain('AI 工程')
  })
})

describe('ArticleFeedRow', () => {
  it('formats CJK date and hides summary slot when absent', () => {
    const wrapper = mount(ArticleFeedRow, {
      props: {
        title: '标题',
        publishedAt: '2026-08-20T10:00:00Z',
        href: '/article/x',
      },
    })
    expect(wrapper.text()).toContain('8 月 20 日')
    expect(wrapper.find('.feed-title').text()).toBe('标题')
    expect(wrapper.attributes('href')).toBe('/article/x')
  })

  it('renders as div when no href', () => {
    const wrapper = mount(ArticleFeedRow, {
      props: { title: '标题', publishedAt: '2026-08-20T10:00:00Z' },
    })
    expect(wrapper.find('div.feed-row').exists()).toBe(true)
  })

  it('never renders view/like/comment counts (contract)', () => {
    const wrapper = mount(ArticleFeedRow, {
      props: { title: 't', summary: 's', publishedAt: '2026-01-01', href: '/x' },
    })
    const html = wrapper.html()
    for (const banned of ['views_count', 'likes_count', 'comments_count', '👁', '❤']) {
      expect(html).not.toContain(banned)
    }
  })
})
