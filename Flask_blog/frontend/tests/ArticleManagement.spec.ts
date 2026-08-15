import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ArticleManagement from '../src/views/admin/ArticleManagement.vue'

vi.mock('../src/api', () => ({
  API: {
    getArticles: vi.fn(),
    getCategories: vi.fn(),
    getUsers: vi.fn(),
    getCurrentUser: vi.fn(),
    approveArticle: vi.fn(),
    rejectArticle: vi.fn(),
    deleteArticle: vi.fn(),
    submitArticle: vi.fn(),
    unpublishArticle: vi.fn(),
  },
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('../stores/user', () => ({
  useUserStore: () => ({ user: { role: 'admin' }, isAuthenticated: true }),
}))

import { API } from '../src/api'

function mountPage() {
  return mount(ArticleManagement, {
    global: {
      plugins: [createPinia()],
      stubs: {
        'el-button': { template: '<button><slot /></button>' },
        'el-card': { template: '<div class="card"><slot /></div>' },
        'el-dialog': { template: '<div class="dlg"><slot /></div>' },
        'el-empty': { template: '<div class="empty" />' },
        'el-form': { template: '<form><slot /></form>' },
        'el-form-item': { template: '<div><slot /></div>' },
        'el-icon': true,
        'el-input': { template: '<input />' },
        'el-option': { template: '<option />' },
        'el-pagination': { template: '<div class="pager" />' },
        'el-select': { template: '<select><slot /></select>' },
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template:
            '<td><slot :row="{ id: 1, title: \'a\', status: \'draft\', author_id: 1 }" /></td>',
        },
        'el-tag': { template: '<span class="tag"><slot /></span>' },
      },
    },
  })
}

describe('ArticleManagement', () => {
  beforeEach(() => {
    vi.mocked(API.getArticles).mockReset()
    vi.mocked(API.getCategories).mockReset()
  })

  it('loads and renders articles', async () => {
    vi.mocked(API.getArticles).mockResolvedValue({
      data: { code: 0, data: { list: [], total: 0 } },
    } as any)
    vi.mocked(API.getCategories).mockResolvedValue({
      data: { code: 0, data: { categories: [] } },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getArticles)).toHaveBeenCalled()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
