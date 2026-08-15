import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ArticleReview from '../src/views/admin/ArticleReview.vue'

vi.mock('../src/api', () => ({
  API: {
    getArticles: vi.fn(),
    getAuditLogs: vi.fn(),
    getArticleVersions: vi.fn(),
    approveArticle: vi.fn(),
    rejectArticle: vi.fn(),
  },
}))
vi.mock('../stores/user', () => ({
  useUserStore: () => ({ user: { role: 'admin' }, isAuthenticated: true }),
}))

import { API } from '../src/api'

function mountPage() {
  return mount(ArticleReview, {
    global: {
      plugins: [createPinia()],
      stubs: {
        'el-alert': { template: '<div><slot /></div>' },
        'el-button': { template: '<button><slot /></button>' },
        'el-card': { template: '<div class="card"><slot /></div>' },
        'el-empty': { template: '<div class="empty" />' },
        'el-icon': true,
        'el-input': { template: '<input />' },
        'el-option': { template: '<option />' },
        'el-pagination': { template: '<div class="pager" />' },
        'el-select': { template: '<select><slot /></select>' },
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template:
            '<td><slot :row="{ id: 1, title: \'a\', status: \'pending\', author_id: 1 }" /></td>',
        },
        'el-tag': { template: '<span class="tag"><slot /></span>' },
      },
    },
  })
}

describe('ArticleReview', () => {
  beforeEach(() => {
    vi.mocked(API.getArticles).mockReset()
  })

  it('loads and renders articles for review', async () => {
    vi.mocked(API.getArticles).mockResolvedValue({
      data: { code: 0, data: { list: [], total: 0 } },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getArticles)).toHaveBeenCalled()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
