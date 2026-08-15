import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import LogManagement from '../src/views/admin/LogManagement.vue'

vi.mock('../src/api', () => ({
  API: {
    queryLogs: vi.fn(),
    getLogStats: vi.fn(),
    getLogSources: vi.fn(),
    getLogUsers: vi.fn(),
    cleanupLogs: vi.fn(),
    exportLogs: vi.fn(),
  },
}))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
}))

import { API } from '../src/api'

const panelStub = { template: '<div><slot /></div>' }
const inputStub = { template: '<input />' }

function mountPage() {
  return mount(LogManagement, {
    global: {
      stubs: {
        'el-alert': panelStub,
        'el-button': { template: '<button><slot /></button>' },
        'el-card': { template: '<div class="card"><slot name="header" /><slot /></div>' },
        'el-col': panelStub,
        'el-date-picker': inputStub,
        'el-descriptions': { template: '<dl><slot /></dl>' },
        'el-descriptions-item': { template: '<dd><slot /></dd>' },
        'el-dialog': { template: '<div class="dlg"><slot /></div>' },
        'el-form': { template: '<form><slot /></form>' },
        'el-form-item': { template: '<div><slot /></div>' },
        'el-icon': true,
        'el-input': inputStub,
        'el-input-number': inputStub,
        'el-option': { template: '<option />' },
        'el-pagination': { template: '<div class="pager" />' },
        'el-radio': { template: '<span><slot /></span>' },
        'el-radio-group': { template: '<div><slot /></div>' },
        'el-row': panelStub,
        'el-select': { template: '<select><slot /></select>' },
        'el-switch': { template: '<input type="checkbox" />' },
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template:
            '<td><slot :row="{ id: 1, message: \'log\', level: \'INFO\', source: \'app\', timestamp: \'2026-01-01\' }" /></td>',
        },
        'el-tag': { template: '<span class="tag"><slot /></span>' },
        'el-tooltip': { template: '<span><slot /></span>' },
      },
    },
  })
}

describe('LogManagement', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'test-token')
    vi.mocked(API.queryLogs).mockReset()
    vi.mocked(API.getLogStats).mockReset()
    vi.mocked(API.getLogSources).mockReset()
  })

  it('loads and renders the log management page', async () => {
    vi.mocked(API.queryLogs).mockResolvedValue({
      data: { code: 0, data: { logs: [], total: 0 } },
    } as any)
    vi.mocked(API.getLogStats).mockResolvedValue({
      data: { code: 0, data: { total: 0, today: 0 } },
    } as any)
    vi.mocked(API.getLogSources).mockResolvedValue({
      data: { code: 0, data: ['app'] },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.queryLogs)).toHaveBeenCalled()
    expect(wrapper.find('.log-management').exists()).toBe(true)
  })

  it('renders even when logs API returns error', async () => {
    vi.mocked(API.queryLogs).mockResolvedValue({
      data: { code: 500, message: 'boom' },
    } as any)
    vi.mocked(API.getLogStats).mockResolvedValue({
      data: { code: 0, data: {} },
    } as any)
    vi.mocked(API.getLogSources).mockResolvedValue({
      data: { code: 0, data: [] },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.log-management').exists()).toBe(true)
  })
})
