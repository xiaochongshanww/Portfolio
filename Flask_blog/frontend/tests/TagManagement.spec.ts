import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TagManagement from '../src/views/admin/TagManagement.vue'

vi.mock('../src/api', () => ({
  API: {
    getTaxonomyStats: vi.fn(),
    createTag: vi.fn(),
    updateTag: vi.fn(),
    deleteTag: vi.fn(),
  },
}))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
}))

import { API } from '../src/api'

function mountPage() {
  return mount(TagManagement, {
    global: {
      stubs: {
        'el-icon': true,
        'el-input': { template: '<input />' },
        'el-option': { template: '<option />' },
        'el-radio-button': { template: '<span class="rb"><slot /></span>' },
        'el-radio-group': { template: '<div class="rg"><slot /></div>' },
        'el-select': { template: '<select><slot /></select>' },
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template:
            '<td><slot :row="{ id: 1, name: \'vue\', slug: \'vue\', article_count: 0 }" /></td>',
        },
      },
    },
  })
}

describe('TagManagement', () => {
  beforeEach(() => {
    vi.mocked(API.getTaxonomyStats).mockReset()
  })

  it('loads and renders tags', async () => {
    vi.mocked(API.getTaxonomyStats).mockResolvedValue({
      data: {
        code: 0,
        data: {
          tags: [{ id: 1, name: 'vue', slug: 'vue' }],
          summary: { total: 1 },
        },
      },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getTaxonomyStats)).toHaveBeenCalled()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })

  it('handles API error response', async () => {
    vi.mocked(API.getTaxonomyStats).mockResolvedValue({
      data: { code: 500, message: 'boom' },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
