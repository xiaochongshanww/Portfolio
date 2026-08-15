import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import RestoreManagement from '../src/views/admin/RestoreManagement.vue'

vi.mock('../src/api', () => ({
  API: {
    getRestoreRecords: vi.fn(),
    getRestoreProgress: vi.fn(),
    cancelRestore: vi.fn(),
    cleanupStuckRestores: vi.fn(),
  },
}))
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
}))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
}))

import { API } from '../src/api'

function mountPage() {
  return mount(RestoreManagement, {
    global: {
      stubs: {
        'el-button': { template: '<button><slot /></button>' },
        'el-card': { template: '<div class="card"><slot /></div>' },
        'el-empty': { template: '<div class="empty" />' },
        'el-icon': true,
        'el-pagination': { template: '<div class="pager" />' },
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template:
            '<td><slot :row="{ id: 1, restore_id: \'r1\', status: \'completed\' }" /></td>',
        },
        'el-tag': { template: '<span class="tag"><slot /></span>' },
      },
    },
  })
}

describe('RestoreManagement', () => {
  beforeEach(() => {
    vi.mocked(API.getRestoreRecords).mockReset()
  })

  it('loads and renders restore records', async () => {
    vi.mocked(API.getRestoreRecords).mockResolvedValue({
      data: { code: 0, data: { items: [], total: 0 } },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getRestoreRecords)).toHaveBeenCalled()
  })

  it('renders when restore API errors', async () => {
    vi.mocked(API.getRestoreRecords).mockResolvedValue({
      data: { code: 500, message: 'boom' },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
