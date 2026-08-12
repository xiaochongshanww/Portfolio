import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const probeModelProviders = vi.hoisted(() => vi.fn())

vi.mock('../admin-api', () => ({ probeModelProviders }))

import OverviewTab from './OverviewTab.vue'

function mountOverview() {
  return mount(OverviewTab, {
    props: {
      ready: {
        ready: true,
        status: 'ready',
        reasons: [],
        checks: {},
        built_at: '',
        checked_at: '2026-08-12T00:00:00+00:00',
        data_version_hash: '',
        version: '',
      },
      documents: {
        built: true,
        documents: [],
        document_count: 0,
        chunk_count: 0,
        image_count: 0,
        data_version_hash: '',
        built_at: '',
        parser_backend: '',
        missing_artifact_count: 0,
      },
      metrics: {},
      quality: {},
    },
  })
}

describe('provider capability diagnostics', () => {
  beforeEach(() => {
    probeModelProviders.mockReset()
  })

  it('does not spend provider calls until the operator clicks detect', async () => {
    probeModelProviders.mockResolvedValue({
      ok: true,
      checked_at: '2026-08-12T00:00:00+00:00',
      providers: [
        {
          provider: 'zhipuai',
          capability: 'embedding',
          model: 'embedding-3',
          ok: true,
          status: 'ok',
          latency_ms: 120,
          http_status: null,
        },
        {
          provider: 'mimo',
          capability: 'chat',
          model: 'mimo-v2-omni',
          ok: true,
          status: 'ok',
          latency_ms: 180,
          http_status: null,
        },
      ],
    })

    const wrapper = mountOverview()
    expect(probeModelProviders).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('尚未检测')

    await wrapper.setProps({ metrics: { requests_total: 1 } })
    expect(probeModelProviders).not.toHaveBeenCalled()

    await wrapper.get('[data-testid="provider-probe-button"]').trigger('click')
    await flushPromises()

    expect(probeModelProviders).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('智谱 Embedding')
    expect(wrapper.text()).toContain('MiMo 聊天')
    expect(wrapper.text()).toContain('120 ms')
    expect(wrapper.text().match(/可用/g)).toHaveLength(2)
  })

  it('renders stable provider failures and transport errors', async () => {
    probeModelProviders.mockResolvedValueOnce({
      ok: false,
      checked_at: '2026-08-12T00:00:00+00:00',
      providers: [
        {
          provider: 'zhipuai',
          capability: 'embedding',
          model: 'embedding-3',
          ok: false,
          status: 'auth_failed',
          latency_ms: 90,
          http_status: 401,
        },
        {
          provider: 'mimo',
          capability: 'chat',
          model: 'mimo-v2-omni',
          ok: false,
          status: 'rate_limited',
          latency_ms: 140,
          http_status: 429,
        },
      ],
    })

    const wrapper = mountOverview()
    await wrapper.get('[data-testid="provider-probe-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('鉴权失败')
    expect(wrapper.text()).toContain('HTTP 401')
    expect(wrapper.text()).toContain('已限流')
    expect(wrapper.text()).toContain('HTTP 429')

    probeModelProviders.mockRejectedValueOnce(new Error('供应商探测端点不可达'))
    await wrapper.get('[data-testid="provider-probe-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('供应商探测端点不可达')
    expect(wrapper.text()).not.toContain('智谱 Embedding')
  })

  it('suppresses duplicate clicks while a provider probe is running', async () => {
    let resolveProbe: (value: unknown) => void = () => undefined
    probeModelProviders.mockReturnValue(new Promise(resolve => {
      resolveProbe = resolve
    }))

    const wrapper = mountOverview()
    const button = wrapper.get('[data-testid="provider-probe-button"]')
    await button.trigger('click')
    await button.trigger('click')

    expect(probeModelProviders).toHaveBeenCalledTimes(1)
    expect(button.attributes('disabled')).toBeDefined()
    expect(button.text()).toBe('检测中')

    resolveProbe({ ok: true, checked_at: '', providers: [] })
    await flushPromises()

    expect(button.attributes('disabled')).toBeUndefined()
    expect(button.text()).toBe('检测')
  })
})
