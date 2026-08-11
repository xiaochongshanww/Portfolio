import type {
  AdminBlobPath,
  AdminDeletePath,
  AdminDeleteResponse,
  AdminGetPath,
  AdminGetResponse,
  AdminPatchBody,
  AdminPatchPath,
  AdminPatchResponse,
  AdminPostBody,
  AdminPostPath,
  AdminPostResponse,
  AdminPutBody,
  AdminPutPath,
  AdminPutResponse,
} from './contracts'

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

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
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

export async function apiGet<T = unknown>(url: string): Promise<T> {
  const response = await fetch(url, { headers: headers() })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiGetWithApiKey<T = unknown>(url: string, apiKey: string): Promise<T> {
  const response = await fetch(url, { headers: headers({}, apiKey) })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiPost<T = unknown>(url: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: headers(body ? { 'Content-Type': 'application/json' } : {}),
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiPatch<T = unknown>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: 'PATCH',
    headers: headers({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiPut<T = unknown>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: 'PUT',
    headers: headers({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiDelete<T = unknown>(url: string): Promise<T> {
  const response = await fetch(url, { method: 'DELETE', headers: headers() })
  if (!response.ok) await throwApiError(response)
  return response.json()
}

export async function apiBlobUrl(url: string): Promise<string> {
  const response = await fetch(url, { headers: headers() })
  if (!response.ok) await throwApiError(response)
  return URL.createObjectURL(await response.blob())
}

export function adminGet<P extends AdminGetPath>(url: P): Promise<AdminGetResponse<P>> {
  return apiGet<AdminGetResponse<P>>(url)
}

export function adminGetWithApiKey<P extends AdminGetPath>(
  url: P,
  apiKey: string,
): Promise<AdminGetResponse<P>> {
  return apiGetWithApiKey<AdminGetResponse<P>>(url, apiKey)
}

export function adminPost<P extends AdminPostPath>(
  url: P,
  ...args: AdminPostBody<P> extends undefined
    ? [body?: undefined]
    : [body: AdminPostBody<P>]
): Promise<AdminPostResponse<P>> {
  return apiPost<AdminPostResponse<P>>(url, args[0])
}

export function adminPatch<P extends AdminPatchPath>(
  url: P,
  body: AdminPatchBody,
): Promise<AdminPatchResponse<P>> {
  return apiPatch<AdminPatchResponse<P>>(url, body)
}

export function adminPut<P extends AdminPutPath>(
  url: P,
  body: AdminPutBody<P>,
): Promise<AdminPutResponse<P>> {
  return apiPut<AdminPutResponse<P>>(url, body)
}

export function adminDelete<P extends AdminDeletePath>(
  url: P,
): Promise<AdminDeleteResponse> {
  return apiDelete<AdminDeleteResponse>(url)
}

export function adminBlobUrl(url: AdminBlobPath): Promise<string> {
  return apiBlobUrl(url)
}
