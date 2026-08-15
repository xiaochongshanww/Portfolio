import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TagPage from '../src/views/TagPage.vue'

vi.mock('../src/api', () => ({
  API: { getPublicArticles: vi.fn() },
}))
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { slug: 'vue' } }),
}))

import { API } from '../src/api'

const linkStub = { template: '<a><slot /></a>' }

describe('TagPage', () => {
  beforeEach(() => {
    vi.mocked(API.getPublicArticles).mockReset()
  })

  it('renders articles for the tag from route param', async () => {
    vi.mocked(API.getPublicArticles).mockResolvedValue({
      data: {
        data: {
          list: [
            { id: 1, title: 'Tag Article', slug: 'ta', published_at: '2026-01-01T00:00:00Z' },
          ],
        },
      },
    } as any)
    const wrapper = mount(TagPage, {
      global: { stubs: { 'router-link': linkStub } },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getPublicArticles)).toHaveBeenCalledWith({
      tag: 'vue',
    })
    expect(wrapper.text()).toContain('#vue')
    expect(wrapper.text()).toContain('Tag Article')
  })

  it('shows empty state when no articles', async () => {
    vi.mocked(API.getPublicArticles).mockResolvedValue({
      data: { data: { list: [] } },
    } as any)
    const wrapper = mount(TagPage, {
      global: { stubs: { 'router-link': linkStub } },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('暂无文章')
  })

  it('handles API errors by showing empty state', async () => {
    vi.mocked(API.getPublicArticles).mockRejectedValue(new Error('boom'))
    const wrapper = mount(TagPage, {
      global: { stubs: { 'router-link': linkStub } },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('暂无文章')
  })
})
