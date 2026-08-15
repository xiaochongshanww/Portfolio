import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import SecurityMonitoring from '../src/views/admin/SecurityMonitoring.vue'

vi.mock('../src/api', () => ({
  API: {
    getSecurityStats: vi.fn(),
    getSecurityEvents: vi.fn(),
    getAccessStatsToday: vi.fn(),
    getSystemHealth: vi.fn(),
    handleSecurityEvent: vi.fn(),
  },
}))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
}))

import { API } from '../src/api'

function mountPage() {
  return mount(SecurityMonitoring, {
    global: {
      stubs: {
        'el-alert': { template: '<div><slot /></div>' },
        'el-button': { template: '<button><slot /></button>' },
        'el-card': { template: '<div class="card"><slot /></div>' },
        'el-col': { template: '<div><slot /></div>' },
        'el-empty': { template: '<div class="empty" />' },
        'el-icon': true,
        'el-row': { template: '<div><slot /></div>' },
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template:
            '<td><slot :row="{ id: 1, event_type: \'login\', severity: \'high\', ip: \'1.2.3.4\' }" /></td>',
        },
        'el-tag': { template: '<span class="tag"><slot /></span>' },
        'v-chart': { template: '<div class="chart" />' },
      },
    },
  })
}

describe('SecurityMonitoring', () => {
  beforeEach(() => {
    vi.mocked(API.getSecurityStats).mockReset()
    vi.mocked(API.getSecurityEvents).mockReset()
  })

  it('loads and renders security data', async () => {
    vi.mocked(API.getSecurityStats).mockResolvedValue({
      data: { code: 0, data: {} },
    } as any)
    vi.mocked(API.getSecurityEvents).mockResolvedValue({
      data: { code: 0, data: { events: [], total: 0 } },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getSecurityStats)).toHaveBeenCalled()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })

  it('renders when security API errors', async () => {
    vi.mocked(API.getSecurityStats).mockRejectedValue(new Error('boom'))
    vi.mocked(API.getSecurityEvents).mockRejectedValue(new Error('boom'))
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
