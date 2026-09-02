import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import SystemPerformance from '../src/views/admin/SystemPerformance.vue'

vi.mock('../src/api', () => ({
  API: {
    getSystemHealth: vi.fn(),
    getPublicArticles: vi.fn(),
    getMediaList: vi.fn(),
  },
}))

import { API } from '../src/api'

function mountPage() {
  return mount(SystemPerformance, {
    global: {
      stubs: {
        RouterLink: { template: '<a><slot /></a>' },
      },
    },
  })
}

const HEALTH = {
  data: {
    code: 0,
    data: {
      cpu: 24,
      memory: 48,
      disk: 39,
      cpu_count: 8,
      cpu_count_physical: 4,
      cpu_freq: 3600,
      memory_total_gb: 64,
      disk_total_gb: 1402,
      process_count: 492,
      uptime_hours: 30,
      networkIn: 50000,
      networkOut: 5855,
    },
  },
}

describe('SystemPerformance(V2 系统页面)', () => {
  beforeEach(() => {
    vi.mocked(API.getSystemHealth).mockReset()
    vi.mocked(API.getSystemHealth).mockResolvedValue(HEALTH)
  })

  it('renders summary strip and overview from system health', async () => {
    const wrapper = mountPage()
    await flushPromises()
    // Summary:真实使用率
    expect(wrapper.text()).toContain('24%')
    expect(wrapper.text()).toContain('48%')
    expect(wrapper.text()).toContain('39%')
    // 系统概览:真实规格字段(不与 Summary 重复)
    expect(wrapper.text()).toContain('进程数')
    expect(wrapper.text()).toContain('492')
    expect(wrapper.text()).toContain('64 GB')
    // 服务状态:探测项渲染
    expect(wrapper.text()).toContain('Web API')
    expect(wrapper.text()).toContain('数据库')
  })

  it('renders uptime in days when over 24h', async () => {
    const wrapper = mountPage()
    await flushPromises()
    // uptime_hours=30 → 1 天
    expect(wrapper.text()).toContain('1 天')
  })

  it('renders when health API fails without crashing', async () => {
    vi.mocked(API.getSystemHealth).mockRejectedValue(new Error('boom'))
    vi.mocked(API.getPublicArticles).mockRejectedValue(new Error('db down'))
    vi.mocked(API.getMediaList).mockRejectedValue(new Error('media down'))
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.find('.performance-page').exists()).toBe(true)
    // 探测失败 → 服务状态如实显示异常,不虚构
    const serviceRows = wrapper.findAll('.kv-row').filter((r) => r.text().includes('Web API'))
    expect(serviceRows.length).toBeGreaterThan(0)
    expect(wrapper.text()).toContain('0%')
  })
})
