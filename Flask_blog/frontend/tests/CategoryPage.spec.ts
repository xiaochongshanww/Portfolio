import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CategoryPage from '../src/views/CategoryPage.vue'

vi.mock('../src/api', () => ({
  API: {
    getPublicTaxonomy: vi.fn(),
    getPublicArticles: vi.fn(),
  },
}))
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '1' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

import { API } from '../src/api'

const linkStub = { template: '<a><slot /></a>' }

function mountPage() {
  return mount(CategoryPage, {
    global: {
      stubs: {
        'el-button': linkStub,
        'el-button-group': { template: '<span><slot /></span>' },
        'el-select': { template: '<select><slot /></select>' },
        'el-option': { template: '<option />' },
        'el-skeleton': { template: '<div class="skel" />' },
        'el-tag': { template: '<span class="tag"><slot /></span>' },
        'router-link': linkStub,
      },
    },
  })
}

describe('CategoryPage', () => {
  beforeEach(() => {
    vi.mocked(API.getPublicTaxonomy).mockReset()
    vi.mocked(API.getPublicArticles).mockReset()
  })

  it('loads category info and articles', async () => {
    vi.mocked(API.getPublicTaxonomy).mockResolvedValue({
      data: {
        data: {
          categories: [{ id: 1, name: '前端', description: 'frontend desc' }],
        },
      },
    } as any)
    vi.mocked(API.getPublicArticles).mockResolvedValue({
      data: {
        data: {
          list: [
            { id: 10, title: 'Category Article', slug: 'ca', published_at: '2026-01-01T00:00:00Z' },
          ],
        },
      },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getPublicArticles)).toHaveBeenCalledWith({
      category_id: '1',
    })
    expect(wrapper.text()).toContain('前端')
    expect(wrapper.text()).toContain('Category Article')
  })

  it('falls back to default category name when not found', async () => {
    vi.mocked(API.getPublicTaxonomy).mockResolvedValue({
      data: { data: { categories: [] } },
    } as any)
    vi.mocked(API.getPublicArticles).mockResolvedValue({
      data: { data: { list: [] } },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('分类 1')
  })
})
