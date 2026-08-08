export type JsonMap = Record<string, any>

const API_KEY_STORAGE = 'rag_api_key'
export const AUTH_REQUIRED_EVENT = 'rag-auth-required'

export function getApiKey() {
  return localStorage.getItem(API_KEY_STORAGE) || ''
}

export function setApiKey(value: string) {
  const normalized = value.trim()
  if (normalized) {
    localStorage.setItem(API_KEY_STORAGE, normalized)
  } else {
    localStorage.removeItem(API_KEY_STORAGE)
  }
}

function headers(extra: HeadersInit = {}, apiKey = getApiKey()) {
  const key = apiKey.trim()
  return {
    ...(key ? { Authorization: `Bearer ${key}` } : {}),
    ...extra,
  }
}

export class ApiError extends Error {
  public readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

async function throwApiError(response: Response): Promise<never> {
  let detail = ''
  try {
    const payload = await response.json()
    detail = String(payload?.detail || payload?.message || '')
  } catch {
    // The response may not contain JSON.
  }

  const message = detail || (response.status === 401
    ? 'API Key 缺失或无效，请重新验证。'
    : `${response.status} ${response.statusText}`)
  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent(AUTH_REQUIRED_EVENT, {
      detail: { status: response.status, message },
    }))
  }
  throw new ApiError(response.status, message)
}

export async function apiGet<T = any>(url: string): Promise<T> {
  const response = await fetch(url, { headers: headers() })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiGetWithApiKey<T = any>(url: string, apiKey: string): Promise<T> {
  const response = await fetch(url, { headers: headers({}, apiKey) })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiPost<T = any>(url: string, body?: JsonMap): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: headers(body ? { 'Content-Type': 'application/json' } : {}),
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiPatch<T = any>(url: string, body: JsonMap): Promise<T> {
  const response = await fetch(url, {
    method: 'PATCH',
    headers: headers({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiPut<T = any>(url: string, body: JsonMap): Promise<T> {
  const response = await fetch(url, {
    method: 'PUT',
    headers: headers({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiDelete<T = any>(url: string): Promise<T> {
  const response = await fetch(url, { method: 'DELETE', headers: headers() })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiBlobUrl(url: string): Promise<string> {
  const response = await fetch(url, { headers: headers() })
  if (!response.ok) await throwApiError(response)
  return URL.createObjectURL(await response.blob())
}
