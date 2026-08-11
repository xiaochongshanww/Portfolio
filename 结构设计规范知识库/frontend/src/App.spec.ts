import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App.vue'

const API_KEY_STORAGE = 'rag_api_key'

function jsonResponse(payload: unknown, status = 200): Response {
  const statusText = status === 401
    ? 'Unauthorized'
    : status >= 500
      ? 'Service Unavailable'
      : 'OK'
  return new Response(JSON.stringify(payload), {
    headers: { 'Content-Type': 'application/json' },
    status,
    statusText,
  })
}

function requestPath(input: RequestInfo | URL) {
  const url = input instanceof Request ? input.url : String(input)
  const parsed = new URL(url, window.location.origin)
  return `${parsed.pathname}${parsed.search}`
}

function successfulPayload(input: RequestInfo | URL) {
  const path = requestPath(input)
  if (path === '/ready') return { ready: true }
  if (path === '/knowledge/documents') return { built: true, chunk_count: 12, documents: [] }
  if (path === '/admin/corrections/candidates') return { documents: [] }
  if (path === '/admin/manual-structuring') return { documents: [] }
  if (path === '/admin/jobs') return { jobs: [] }
  return {}
}

function authorizationHeader(input: RequestInfo | URL, init?: RequestInit) {
  if (input instanceof Request) return input.headers.get('authorization')
  return new Headers(init?.headers).get('authorization')
}

function mountConsole() {
  return mount(App, {
    global: {
      stubs: {
        OverviewTab: { template: '<div data-testid="overview">overview</div>' },
        JobsTab: true,
        VersionsTab: true,
        ReviewTab: true,
        ManualStructuringTab: true,
        EvaluationTab: true,
        ChatTab: true,
      },
    },
  })
}

async function settleConsole() {
  await flushPromises()
  await flushPromises()
}

describe('console authentication bootstrap', () => {
  let wrapper: VueWrapper | null = null

  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    vi.unstubAllGlobals()
  })

  it('enters directly when the backend accepts an unauthenticated probe', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (requestPath(input) === '/admin/status') return jsonResponse({ built: true })
      return jsonResponse(successfulPayload(input))
    })
    vi.stubGlobal('fetch', fetchMock)

    wrapper = mountConsole()
    await settleConsole()

    expect(wrapper.find('[data-testid="overview"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('需要 API Key')
    expect(requestPath(fetchMock.mock.calls[0][0])).toBe('/admin/status')
    expect(authorizationHeader(fetchMock.mock.calls[0][0])).toBeNull()
    expect(fetchMock.mock.calls.some(([input]) => requestPath(input) === '/admin/jobs')).toBe(true)
  })

  it('asks for a key only after a 401 and does not fan out protected requests', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (requestPath(input) === '/admin/status') {
        if (authorizationHeader(input, init) === 'Bearer valid-key') return jsonResponse({ built: true })
        return jsonResponse({ detail: '需要有效凭据。' }, 401)
      }
      return jsonResponse(successfulPayload(input))
    })
    vi.stubGlobal('fetch', fetchMock)

    wrapper = mountConsole()
    await settleConsole()

    expect(wrapper.text()).toContain('需要 API Key')
    expect(wrapper.text()).toContain('需要有效凭据。')
    expect(fetchMock).toHaveBeenCalledTimes(1)

    await wrapper.get('#auth-api-key').setValue('valid-key')
    await wrapper.get('[data-testid="auth-form"]').trigger('submit')
    await settleConsole()

    expect(localStorage.getItem(API_KEY_STORAGE)).toBe('valid-key')
    expect(wrapper.text()).not.toContain('需要 API Key')
    expect(wrapper.find('[data-testid="overview"]').exists()).toBe(true)
    const authenticatedProbe = fetchMock.mock.calls.find(([input, init]) => (
      requestPath(input) === '/admin/status'
      && authorizationHeader(input, init) === 'Bearer valid-key'
    ))
    expect(authenticatedProbe).toBeDefined()
  })

  it('does not replace the stored key when a candidate is rejected', async () => {
    localStorage.setItem(API_KEY_STORAGE, 'previous-key')
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (requestPath(input) === '/admin/status') return jsonResponse({ detail: '候选 Key 无效。' }, 401)
      return jsonResponse({})
    })
    vi.stubGlobal('fetch', fetchMock)

    wrapper = mountConsole()
    await settleConsole()
    await wrapper.get('#auth-api-key').setValue('rejected-key')
    await wrapper.get('[data-testid="auth-form"]').trigger('submit')
    await settleConsole()

    expect(localStorage.getItem(API_KEY_STORAGE)).toBe('previous-key')
    expect(wrapper.get<HTMLInputElement>('#auth-api-key').element.value).toBe('rejected-key')
    expect(wrapper.text()).toContain('候选 Key 无效。')
  })

  it('stops a manual refresh after the access probe starts returning 401', async () => {
    let authorized = true
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (requestPath(input) === '/admin/status') {
        return authorized
          ? jsonResponse({ built: true })
          : jsonResponse({ detail: '访问凭据已失效。' }, 401)
      }
      return jsonResponse(successfulPayload(input))
    })
    vi.stubGlobal('fetch', fetchMock)

    wrapper = mountConsole()
    await settleConsole()
    const callsBeforeRefresh = fetchMock.mock.calls.length
    authorized = false

    const refreshButton = wrapper.findAll('button').find(button => button.text() === '刷新')
    expect(refreshButton).toBeDefined()
    await refreshButton!.trigger('click')
    await settleConsole()

    expect(fetchMock.mock.calls.length).toBe(callsBeforeRefresh + 1)
    expect(wrapper.text()).toContain('需要 API Key')
    expect(wrapper.text()).toContain('访问凭据已失效。')
  })

  it('shows a retryable connection state instead of an authentication prompt', async () => {
    let online = false
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (!online) throw new TypeError('Failed to fetch')
      if (requestPath(input) === '/admin/status') return jsonResponse({ built: true })
      return jsonResponse(successfulPayload(input))
    })
    vi.stubGlobal('fetch', fetchMock)

    wrapper = mountConsole()
    await settleConsole()

    expect(wrapper.text()).toContain('后端暂时不可用')
    expect(wrapper.text()).toContain('无法连接后端，请确认 API 服务正在运行。')
    expect(wrapper.text()).not.toContain('需要 API Key')

    online = true
    await wrapper.get('button.btn-primary').trigger('click')
    await settleConsole()

    expect(wrapper.find('[data-testid="overview"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('后端暂时不可用')
  })

  it('presents a non-401 backend failure as an unavailable service', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ detail: '服务正在启动。' }, 503)))

    wrapper = mountConsole()
    await settleConsole()

    expect(wrapper.text()).toContain('后端暂时不可用')
    expect(wrapper.text()).toContain('后端请求失败（HTTP 503）：服务正在启动。')
    expect(wrapper.text()).not.toContain('需要 API Key')
  })
})
