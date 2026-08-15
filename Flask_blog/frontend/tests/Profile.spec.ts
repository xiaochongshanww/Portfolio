import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import Profile from '../src/views/Profile.vue'

vi.mock('../src/api', () => ({
  API: { changePassword: vi.fn() },
}))
vi.mock('../stores/user', () => ({
  useUserStore: () => ({
    user: { nickname: 'me', email: 'me@x.com' },
    isAuthenticated: true,
    updateProfile: vi.fn(),
  }),
}))

beforeAll(() => {
  if (typeof (globalThis as any).ResizeObserver === 'undefined') {
    ;(globalThis as any).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
  }
})

function mountPage() {
  return mount(Profile, {
    global: {
      plugins: [createPinia()],
      stubs: {
        'el-button': { template: '<button><slot /></button>' },
        'el-card': { template: '<div class="card"><slot /></div>' },
        'el-form': { template: '<form><slot /></form>' },
        'el-form-item': { template: '<div><slot /></div>' },
        'el-input': { template: '<input class="pro-in" />' },
        'el-tabs': { template: '<div class="tabs"><slot /></div>' },
        'el-tab-pane': { template: '<div class="pane"><slot /></div>' },
        'el-upload': { template: '<div class="up" />' },
        'el-avatar': { template: '<div class="av" />' },
      },
    },
  })
}

describe('Profile', () => {
  it('renders the profile page', async () => {
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
