import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CategoriesPage from '../src/views/CategoriesPage.vue'

vi.mock('../src/api', () => ({
  API: { getPublicTaxonomy: vi.fn() },
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

import { API } from '../src/api'

const linkStub = { template: '<a><slot /></a>' }

describe('CategoriesPage', () => {
  beforeEach(() => {
    vi.mocked(API.getPublicTaxonomy).mockReset()
  })

  it('renders categories', async () => {
    vi.mocked(API.getPublicTaxonomy).mockResolvedValue({
      data: {
        data: {
          categories: [
            { id: 1, name: '前端', article_count: 3, description: 'frontend' },
            { id: 2, name: '后端', article_count: 5 },
          ],
        },
      },
    } as any)
    const wrapper = mount(CategoriesPage, {
      global: { stubs: { RouterLink: linkStub } },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('所有分类')
    expect(wrapper.text()).toContain('前端')
    expect(wrapper.text()).toContain('后端')
    expect(wrapper.text()).toContain('3')
  })

  it('renders without categories', async () => {
    vi.mocked(API.getPublicTaxonomy).mockResolvedValue({
      data: { data: { categories: [] } },
    } as any)
    const wrapper = mount(CategoriesPage, {
      global: { stubs: { RouterLink: linkStub } },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('所有分类')
    expect(wrapper.findAll('.modern-category-card').length).toBe(0)
  })

  it('handles API errors', async () => {
    vi.mocked(API.getPublicTaxonomy).mockRejectedValue(new Error('boom'))
    const wrapper = mount(CategoriesPage, {
      global: { stubs: { RouterLink: linkStub } },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('所有分类')
  })
})
