import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CategoryManagement from '../src/views/admin/CategoryManagement.vue'

vi.mock('../src/api', () => ({
  API: {
    getTaxonomyStats: vi.fn(),
    createCategory: vi.fn(),
    updateCategory: vi.fn(),
    deleteCategory: vi.fn(),
  },
}))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
}))

import { API } from '../src/api'

function mountPage() {
  return mount(CategoryManagement, {
    global: {
      stubs: {
        'el-button': { template: '<button><slot /></button>' },
        'el-dialog': { template: '<div class="dlg"><slot /></div>' },
        'el-empty': { template: '<div class="empty" />' },
        'el-form': { template: '<form><slot /></form>' },
        'el-form-item': { template: '<div><slot /></div>' },
        'el-icon': true,
        'el-input': { template: '<input />' },
        'el-option': { template: '<option />' },
        'el-select': { template: '<select><slot /></select>' },
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template:
            '<td><slot :row="{ id: 1, name: \'前端\', slug: \'frontend\', article_count: 0 }" /></td>',
        },
        'el-tag': { template: '<span class="tag"><slot /></span>' },
      },
    },
  })
}

describe('CategoryManagement', () => {
  beforeEach(() => {
    vi.mocked(API.getTaxonomyStats).mockReset()
  })

  it('loads and renders categories', async () => {
    vi.mocked(API.getTaxonomyStats).mockResolvedValue({
      data: {
        code: 0,
        data: {
          categories: [{ id: 1, name: '前端', slug: 'frontend' }],
          summary: { total: 1 },
        },
      },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getTaxonomyStats)).toHaveBeenCalled()
    expect(wrapper.find('.category-management').exists()).toBe(true)
  })

  it('handles API error response', async () => {
    vi.mocked(API.getTaxonomyStats).mockResolvedValue({
      data: { code: 500, message: 'boom' },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.category-management').exists()).toBe(true)
  })
})
