import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import AdminLayout from '../src/views/admin/AdminLayout.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/admin' }),
  useRouter: () => ({ push: vi.fn() }),
  createRouter: () => ({
    beforeEach: vi.fn(),
    afterEach: vi.fn(),
    push: vi.fn(),
    replace: vi.fn(),
  }),
  createWebHistory: vi.fn(),
  RouterView: { template: '<div class="router-view" />' },
}))
vi.mock('../stores/user', () => ({
  useUserStore: () => ({
    user: { role: 'admin' },
    isAuthenticated: true,
    logout: vi.fn(),
  }),
}))

describe('AdminLayout', () => {
  it('renders the admin layout shell', async () => {
    const wrapper = mount(AdminLayout, {
      global: {
        plugins: [createPinia()],
        stubs: {
          'el-icon': true,
          'router-link': { template: '<a><slot /></a>' },
          'el-dropdown': { template: '<div class="dd"><slot /></div>' },
          'el-dropdown-menu': { template: '<div class="ddm"><slot /></div>' },
          'el-dropdown-item': { template: '<div class="ddi"><slot /></div>' },
        },
      },
    })
    await flushPromises()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
