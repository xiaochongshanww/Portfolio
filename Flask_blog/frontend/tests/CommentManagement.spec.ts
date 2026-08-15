import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CommentManagement from '../src/views/admin/CommentManagement.vue'

vi.mock('../src/api', () => ({
  API: {
    getAdminComments: vi.fn(),
    getCommentStats: vi.fn(),
    moderateComment: vi.fn(),
    moderateCommentBatch: vi.fn(),
  },
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
}))

import { API } from '../src/api'

function mountPage() {
  return mount(CommentManagement, {
    global: {
      stubs: {
        'el-alert': { template: '<div><slot /></div>' },
        'el-button': { template: '<button><slot /></button>' },
        'el-card': { template: '<div class="card"><slot /></div>' },
        'el-col': { template: '<div><slot /></div>' },
        'el-date-picker': { template: '<input />' },
        'el-dialog': { template: '<div class="dlg"><slot /></div>' },
        'el-empty': { template: '<div class="empty" />' },
        'el-form': { template: '<form><slot /></form>' },
        'el-form-item': { template: '<div><slot /></div>' },
        'el-icon': true,
        'el-input': { template: '<input />' },
        'el-option': { template: '<option />' },
        'el-pagination': { template: '<div class="pager" />' },
        'el-row': { template: '<div><slot /></div>' },
        'el-select': { template: '<select><slot /></select>' },
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template:
            '<td><slot :row="{ id: 1, content: \'comment\', status: \'pending\', article_id: 1 }" /></td>',
        },
        'el-tag': { template: '<span class="tag"><slot /></span>' },
      },
    },
  })
}

describe('CommentManagement', () => {
  beforeEach(() => {
    vi.mocked(API.getAdminComments).mockReset()
    vi.mocked(API.getCommentStats).mockReset()
  })

  it('loads and renders comments', async () => {
    vi.mocked(API.getAdminComments).mockResolvedValue({
      data: { code: 0, data: { list: [], total: 0 } },
    } as any)
    vi.mocked(API.getCommentStats).mockResolvedValue({
      data: { code: 0, data: {} },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getAdminComments)).toHaveBeenCalled()
  })

  it('renders when API errors', async () => {
    vi.mocked(API.getAdminComments).mockResolvedValue({
      data: { code: 500, message: 'boom' },
    } as any)
    vi.mocked(API.getCommentStats).mockResolvedValue({
      data: { code: 0, data: {} },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
