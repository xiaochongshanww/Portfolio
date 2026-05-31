import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Login from '../src/views/Login.vue'

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: mockPush }),
}))

const mockPost = vi.fn()
vi.mock('../src/apiClient', () => ({
  default: {
    post: (...args: any[]) => mockPost(...args),
  },
}))

describe('Login', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockPush.mockReset()
    mockPost.mockReset()
  })

  it('renders login form', async () => {
    const wrapper = mount(Login, {
      global: {
        plugins: [createPinia()],
        stubs: {
          'el-form': { template: '<div><slot /></div>' },
          'el-form-item': { template: '<div><slot /></div>' },
          'el-input': { template: '<input />' },
          'el-button': { template: '<button><slot /></button>' },
          'el-link': { template: '<a><slot /></a>' },
          'el-card': { template: '<div><slot /></div>' },
          'router-link': { template: '<a><slot /></a>' },
        },
      },
    })
    expect(wrapper.find('input').exists()).toBe(true)
  })

  it('handles login button text', () => {
    const wrapper = mount(Login, {
      global: {
        plugins: [createPinia()],
        stubs: {
          'el-form': { template: '<div><slot /></div>' },
          'el-form-item': { template: '<div><slot /></div>' },
          'el-input': { template: '<input />' },
          'el-button': { template: '<button><slot /></button>' },
          'el-link': { template: '<a><slot /></a>' },
          'el-card': { template: '<div><slot /></div>' },
          'router-link': { template: '<a><slot /></a>' },
        },
      },
    })
    expect(wrapper.text()).toContain('登录')
  })
})
