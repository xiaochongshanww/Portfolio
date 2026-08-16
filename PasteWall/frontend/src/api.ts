import type { Item, ItemsResponse } from './types'

export const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'] as const

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try {
      const data = await res.json()
      if (data && typeof data.error === 'string') message = data.error
    } catch {
      /* 非 JSON 响应,用默认消息 */
    }
    throw new ApiError(res.status, message)
  }
  return res.json() as Promise<T>
}

export function fetchItems(): Promise<ItemsResponse> {
  return request<ItemsResponse>('/api/items', { cache: 'no-store' })
}

export function postText(text: string): Promise<{ item: Item }> {
  return request('/api/items', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: 'text', text }),
  })
}

export function postImage(mimeType: string, dataBase64: string): Promise<{ item: Item }> {
  return request('/api/items', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: 'image', mimeType, dataBase64 }),
  })
}

export function deleteItem(id: string): Promise<{ ok: boolean }> {
  return request(`/api/items/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function imageUrl(file: string): string {
  return '/images/' + encodeURIComponent(file)
}
