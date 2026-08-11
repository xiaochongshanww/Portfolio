import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getAdminPageImageObjectUrl, getAdminStatus } from './admin-api'
import {
  ApiError,
  AUTH_REQUIRED_EVENT,
  authorizationHeaders,
  setApiKey,
} from './api'

function jsonResponse(payload: unknown, status = 200, statusText = '') {
  return new Response(JSON.stringify(payload), {
    headers: { 'Content-Type': 'application/json' },
    status,
    statusText,
  })
}

describe('generated admin API adapter', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('injects the stored API key into generated requests', async () => {
    setApiKey('stored-key')
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ status: 'ready' }))
    vi.stubGlobal('fetch', fetchMock)

    await getAdminStatus()

    const request = fetchMock.mock.calls[0][0] as Request
    expect(request.url).toBe(`${window.location.origin}/admin/status`)
    expect(request.headers.get('Authorization')).toBe('Bearer stored-key')
  })

  it('preserves an explicit candidate key during first-load authentication', async () => {
    setApiKey('stale-key')
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ status: 'ready' }))
    vi.stubGlobal('fetch', fetchMock)

    await getAdminStatus({ headers: authorizationHeaders('candidate-key') })

    const request = fetchMock.mock.calls[0][0] as Request
    expect(request.headers.get('Authorization')).toBe('Bearer candidate-key')
  })

  it('converts JSON failures to ApiError and dispatches the 401 event', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: '凭据无效' }, 401, 'Unauthorized'))
    const listener = vi.fn()
    window.addEventListener(AUTH_REQUIRED_EVENT, listener)
    vi.stubGlobal('fetch', fetchMock)

    await expect(getAdminStatus()).rejects.toEqual(expect.objectContaining<ApiError>({
      message: '凭据无效',
      name: 'ApiError',
      status: 401,
    }))
    expect(listener).toHaveBeenCalledOnce()
    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({
      message: '凭据无效',
      status: 401,
    })
    window.removeEventListener(AUTH_REQUIRED_EVENT, listener)
  })

  it('keeps text error payloads readable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('upstream unavailable', {
      status: 503,
      statusText: 'Service Unavailable',
    })))

    await expect(getAdminStatus()).rejects.toEqual(expect.objectContaining<ApiError>({
      message: 'upstream unavailable',
      name: 'ApiError',
      status: 503,
    }))
  })

  it('turns the generated page-image Blob response into an object URL', async () => {
    const createObjectURL = vi.fn().mockReturnValue('blob:page-42')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(new Uint8Array([137, 80, 78, 71]), {
      headers: { 'Content-Type': 'image/png' },
    })))
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL })

    await expect(getAdminPageImageObjectUrl({
      path: { doc: 'GB 50009-2012', page: 42 },
    })).resolves.toBe('blob:page-42')
    const blob = createObjectURL.mock.calls[0][0] as Blob
    expect(blob.type).toBe('image/png')
    expect(typeof blob.arrayBuffer).toBe('function')
  })
})
