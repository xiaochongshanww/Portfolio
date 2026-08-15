import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TagsPage from '../src/views/TagsPage.vue'

vi.mock('../src/api', () => ({
  API: { getPublicTaxonomy: vi.fn() },
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

import { API } from '../src/api'

describe('TagsPage', () => {
  beforeEach(() => {
    vi.mocked(API.getPublicTaxonomy).mockReset()
  })

  it('renders tags from taxonomy API', async () => {
    vi.mocked(API.getPublicTaxonomy).mockResolvedValue({
      data: {
        data: {
          tags: [
            { id: 1, name: 'vue', slug: 'vue', article_count: 3 },
            { id: 2, name: 'python', slug: 'python', article_count: 5 },
          ],
        },
      },
    } as any)
    const wrapper = mount(TagsPage, {
      global: { stubs: { 'el-icon': true } },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('vue')
    expect(wrapper.text()).toContain('python')
  })

  it('renders empty when no tags', async () => {
    vi.mocked(API.getPublicTaxonomy).mockResolvedValue({
      data: { data: { tags: [] } },
    } as any)
    const wrapper = mount(TagsPage, {
      global: { stubs: { 'el-icon': true } },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('标签')
  })
})
