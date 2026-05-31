import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '../src/stores/user'

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('../src/apiClient', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}))

describe('userStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockGet.mockReset()
    mockPost.mockReset()
    // 清理 localStorage 副作用
    localStorage.clear()
  })

  it('starts unauthenticated', () => {
    const store = useUserStore()
    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
    expect(store.token).toBe('')
    expect(store.role).toBe('')
  })

  it('setAuth updates token and role', () => {
    const store = useUserStore()
    store.setAuth('test-token', 'author')
    expect(store.token).toBe('test-token')
    expect(store.role).toBe('author')
    expect(store.isAuthenticated).toBe(true)
    expect(localStorage.getItem('access_token')).toBe('test-token')
    expect(localStorage.getItem('role')).toBe('author')
  })

  it('fetchUserInfo populates user on success', async () => {
    const store = useUserStore()
    store.setAuth('t', 'author')
    mockGet.mockResolvedValueOnce({ data: { data: { id: 1, role: 'admin' } } })

    const result = await store.fetchUserInfo()
    expect(result).toEqual({ id: 1, role: 'admin' })
    expect(store.user).toEqual({ id: 1, role: 'admin' })
    expect(store.isAuthenticated).toBe(true)
    // role should sync from server response
    expect(store.role).toBe('admin')
  })

  it('fetchUserInfo clears state on 401', async () => {
    const store = useUserStore()
    store.setAuth('t', 'author')
    mockGet.mockRejectedValueOnce({ response: { status: 401 } })

    await store.fetchUserInfo()
    expect(store.token).toBe('')
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('logout clears all state', async () => {
    const store = useUserStore()
    store.setAuth('t', 'author')
    store.user = { id: 1, role: 'author' } as any
    store.isAuthenticated = true
    mockPost.mockResolvedValueOnce({ ok: true })

    await store.logout()
    expect(store.token).toBe('')
    expect(store.role).toBe('')
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('hasRole getter works correctly', () => {
    const store = useUserStore()
    store.user = { id: 1, role: 'admin' } as any
    store.isAuthenticated = true

    expect(store.hasRole('admin')).toBe(true)
    expect(store.hasRole(['admin', 'editor'])).toBe(true)
    expect(store.hasRole('author')).toBe(false)
    expect(store.hasRole(['editor', 'author'])).toBe(false)
  })

  it('role-specific getters', () => {
    const store = useUserStore()
    store.user = { id: 1, role: 'admin' } as any

    expect(store.isAdmin).toBe(true)
    expect(store.isEditor).toBe(false)
    expect(store.isAuthor).toBe(false)
    expect(store.canAccessAdmin).toBe(true)
    expect(store.canManageUsers).toBe(true)
    expect(store.canModerateContent).toBe(true)
  })
})
