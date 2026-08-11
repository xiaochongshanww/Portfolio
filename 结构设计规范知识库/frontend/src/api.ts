import { client } from './generated/api/client.gen'

export type JsonMap = Record<string, unknown>

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

export function authorizationHeaders(apiKey = getApiKey(), extra: HeadersInit = {}) {
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

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function apiErrorDetail(payload: unknown): string {
  if (typeof payload === 'string') return payload
  if (!payload || typeof payload !== 'object') return ''
  const record = payload as Record<string, unknown>
  return String(record.detail || record.message || '')
}

function createApiError(status: number, statusText: string, payload: unknown): ApiError {
  const detail = apiErrorDetail(payload)
  const message = detail || (status === 401
    ? 'API Key 缺失或无效，请重新验证。'
    : `${status} ${statusText}`.trim())
  if (status === 401) {
    window.dispatchEvent(new CustomEvent(AUTH_REQUIRED_EVENT, {
      detail: { status, message },
    }))
  }
  return new ApiError(status, message)
}

async function throwApiError(response: Response): Promise<never> {
  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    // The response may not contain JSON.
  }
  throw createApiError(response.status, response.statusText, payload)
}

client.setConfig({ baseUrl: window.location.origin })

client.interceptors.request.use((request) => {
  const key = getApiKey().trim()
  if (key && !request.headers.has('Authorization')) {
    request.headers.set('Authorization', `Bearer ${key}`)
  }
  return request
})

client.interceptors.error.use((error, response) => {
  if (!response) return error
  return createApiError(response.status, response.statusText, error)
})

export async function apiGet<T = unknown>(url: string): Promise<T> {
  const response = await fetch(url, { headers: authorizationHeaders() })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiGetWithApiKey<T = unknown>(url: string, apiKey: string): Promise<T> {
  const response = await fetch(url, { headers: authorizationHeaders(apiKey) })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiPost<T = unknown>(url: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: authorizationHeaders(getApiKey(), body ? { 'Content-Type': 'application/json' } : {}),
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiPatch<T = unknown>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: 'PATCH',
    headers: authorizationHeaders(getApiKey(), { 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiPut<T = unknown>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: 'PUT',
    headers: authorizationHeaders(getApiKey(), { 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiDelete<T = unknown>(url: string): Promise<T> {
  const response = await fetch(url, { method: 'DELETE', headers: authorizationHeaders() })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiBlobUrl(url: string): Promise<string> {
  const response = await fetch(url, { headers: authorizationHeaders() })
  if (!response.ok) await throwApiError(response)
  return URL.createObjectURL(await response.blob())
}
