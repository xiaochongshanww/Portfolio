import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import SystemPerformance from '../src/views/admin/SystemPerformance.vue'

vi.mock('../src/api', () => ({
  API: { getSystemHealth: vi.fn() },
}))

import { API } from '../src/api'

const panelStub = { template: '<div><slot /></div>' }

function mountPage() {
  return mount(SystemPerformance, {
    global: {
      stubs: {
        'el-button': { template: '<button><slot /></button>' },
        'el-button-group': { template: '<span><slot /></span>' },
        'el-card': { template: '<div class="card"><slot name="header" /><slot /></div>' },
        'el-col': panelStub,
        'el-empty': { template: '<div class="empty" />' },
        'el-icon': true,
        'el-row': panelStub,
        'el-switch': { template: '<input type="checkbox" />' },
        'v-chart': { template: '<div class="chart" />' },
      },
    },
  })
}

describe('SystemPerformance', () => {
  beforeEach(() => {
    vi.mocked(API.getSystemHealth).mockReset()
  })

  it('loads and renders system health', async () => {
    vi.mocked(API.getSystemHealth).mockResolvedValue({
      data: {
        code: 0,
        data: { cpu: 0.1, memory: 0.5, disk: 0.2 },
      },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getSystemHealth)).toHaveBeenCalled()
    expect(wrapper.find('.system-performance').exists()).toBe(true)
  })

  it('renders when health API fails', async () => {
    vi.mocked(API.getSystemHealth).mockRejectedValue(new Error('boom'))
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.system-performance').exists()).toBe(true)
  })
})
