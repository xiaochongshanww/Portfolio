import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import UserManagement from '../src/views/admin/UserManagement.vue'

vi.mock('../src/api', () => ({
  API: {
    getUsers: vi.fn(),
    deleteUser: vi.fn(),
    updateUser: vi.fn(),
    resetUserPassword: vi.fn(),
  },
}))
vi.mock('../stores/user', () => ({
  useUserStore: () => ({ user: { role: 'admin' }, isAuthenticated: true }),
}))

import { API } from '../src/api'

function mountPage() {
  return mount(UserManagement, {
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
            '<td><slot :row="{ id: 1, email: \'a@b.com\', role: \'author\', nickname: \'n\' }" /></td>',
        },
        'el-tag': { template: '<span class="tag"><slot /></span>' },
      },
    },
  })
}

describe('UserManagement', () => {
  beforeEach(() => {
    vi.mocked(API.getUsers).mockReset()
  })

  it('loads and renders users', async () => {
    vi.mocked(API.getUsers).mockResolvedValue({
      data: { code: 0, data: { list: [], total: 0 } },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getUsers)).toHaveBeenCalled()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
