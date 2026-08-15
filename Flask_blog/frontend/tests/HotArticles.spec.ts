import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import HotArticles from '../src/views/HotArticles.vue'

vi.mock('../src/api', () => ({
  API: {
    getHotArticles: vi.fn(),
  },
}))

import { API } from '../src/api'

const routerLinkStub = { template: '<a><slot /></a>' }

const SAMPLE = {
  id: 1,
  title: 'Article A',
  slug: 'article-a',
  summary: 'summary text',
  views_count: 10,
  likes_count: 2,
  score: 5,
  author: { name: 'Bob' },
}

describe('HotArticles', () => {
  beforeEach(() => {
    vi.mocked(API.getHotArticles).mockReset()
  })

  it('renders fetched articles after loading', async () => {
    vi.mocked(API.getHotArticles).mockResolvedValue({
      data: { data: { list: [SAMPLE] } },
    } as any)
    const wrapper = mount(HotArticles, {
      global: { stubs: { RouterLink: routerLinkStub } },
    })
    expect(wrapper.text()).toContain('热门文章')
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getHotArticles)).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Article A')
    expect(wrapper.text()).toContain('summary text')
    expect(wrapper.text()).toContain('10 次阅读')
    expect(wrapper.text()).toContain('2 个赞')
    expect(wrapper.text()).toContain('Bob')
    expect(wrapper.text()).toContain('热度: 5')
  })

  it('renders empty list without crash', async () => {
    vi.mocked(API.getHotArticles).mockResolvedValue({
      data: { data: { list: [] } },
    } as any)
    const wrapper = mount(HotArticles, {
      global: { stubs: { RouterLink: routerLinkStub } },
    })
    await flushPromises()
    expect(wrapper.findAll('article').length).toBe(0)
  })

  it('handles API errors gracefully', async () => {
    vi.mocked(API.getHotArticles).mockRejectedValue(new Error('boom'))
    const wrapper = mount(HotArticles, {
      global: { stubs: { RouterLink: routerLinkStub } },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('热门文章')
    expect(wrapper.findAll('article').length).toBe(0)
  })

  it('falls back to anonymous author', async () => {
    vi.mocked(API.getHotArticles).mockResolvedValue({
      data: { data: { list: [{ ...SAMPLE, author: null }] } },
    } as any)
    const wrapper = mount(HotArticles, {
      global: { stubs: { RouterLink: routerLinkStub } },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('匿名作者')
  })
})
