import { describe, it, expect, vi, beforeAll } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AdminLayout from '../src/views/admin/AdminLayout.vue'
import { useUserStore } from '../src/stores/user'

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
  RouterLink: { template: '<a><slot /></a>' },
  RouterView: { template: '<div class="router-view" />' },
}))

beforeAll(() => {
  if (typeof window.matchMedia === 'undefined') {
    window.matchMedia = ((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })) as unknown as typeof window.matchMedia
  }
})

const stubs = {
  'el-icon': true,
  RouterLink: { template: '<a><slot /></a>' },
  'el-dropdown': {
    template: '<div class="dd"><slot /><slot name="dropdown" /></div>',
  },
  'el-dropdown-menu': { template: '<div class="ddm"><slot /></div>' },
  'el-dropdown-item': { template: '<div class="ddi"><slot /></div>' },
}

/** 通过真实 pinia store 注入用户(shell 按 user.role 决定可见菜单) */
function mountShell(userInfo: { role: string; email: string }) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useUserStore()
  store.user = userInfo as never
  return mount(AdminLayout, {
    global: {
      plugins: [pinia],
      stubs,
    },
  })
}

describe('AdminLayout(2026 Shell)', () => {
  it('renders shell with new IA sidebar groups and topbar', async () => {
    const wrapper = mountShell({ role: 'admin', email: 'manual@verify.com' })
    await flushPromises()
    // 五分组 IA(04 §5.3)
    const labels = wrapper.findAll('.nav-label').map((n) => n.text())
    expect(labels).toEqual(['工作台', '内容', '组织', '资源', '系统'])
    // 品牌 + 底部账号(04 §5.2/§5.4)
    expect(wrapper.find('.brand-name').text()).toBe('小重山 CMS')
    expect(wrapper.find('.account-name').text()).toBe('manual@verify.com')
    expect(wrapper.find('.account-role').text()).toBe('管理员')
    // Topbar 面包屑与返回网站(04 §6)
    expect(wrapper.find('.breadcrumb').exists()).toBe(true)
    expect(wrapper.find('.top-btn').text()).toContain('返回网站')
    // 旧壳视觉不得回潮(04 §3)
    const html = wrapper.html()
    expect(html).not.toMatch(/linear-gradient/)
    expect(html).not.toMatch(/glow/i)
  })

  it('admin sees user management; author does not', async () => {
    const admin = mountShell({ role: 'admin', email: 'manual@verify.com' })
    await flushPromises()
    const adminItems = admin.findAll('.nav-item').map((n) => n.text())
    expect(adminItems.some((t) => t.includes('用户'))).toBe(true)
    expect(adminItems.some((t) => t.includes('文章'))).toBe(true)

    const author = mountShell({ role: 'author', email: 'a@b.c' })
    await flushPromises()
    const authorItems = author.findAll('.nav-item').map((n) => n.text())
    expect(authorItems.some((t) => t.includes('文章'))).toBe(true)
    expect(authorItems.some((t) => t.includes('用户'))).toBe(false)
    expect(authorItems.some((t) => t.includes('评论'))).toBe(false)
  })
})
