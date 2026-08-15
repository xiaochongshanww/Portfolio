import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import BackupManagement from '../src/views/admin/BackupManagement.vue'

vi.mock('../src/api', () => ({
  API: {
    getBackupRecords: vi.fn(),
    getBackupStatistics: vi.fn(),
    getRestoreProgress: vi.fn(),
    createBackup: vi.fn(),
    deleteBackup: vi.fn(),
    downloadBackup: vi.fn(),
    cancelBackup: vi.fn(),
    restoreBackup: vi.fn(),
    cancelRestore: vi.fn(),
  },
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('../stores/user', () => ({
  useUserStore: () => ({ user: { role: 'admin' }, isAuthenticated: true, initAuth: vi.fn() }),
}))
vi.mock('@/stores/user.js', () => ({
  useUserStore: () => ({ user: { role: 'admin' }, isAuthenticated: true, initAuth: vi.fn() }),
}))

import { API } from '../src/api'

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
  return mount(BackupManagement, {
    global: {
      plugins: [createPinia()],
      stubs: {
        'el-button': { template: '<button><slot /></button>' },
        'el-card': { template: '<div class="card"><slot name="header" /><slot /></div>' },
        'el-col': { template: '<div><slot /></div>' },
        'el-dialog': { template: '<div class="dlg"><slot /></div>' },
        'el-empty': { template: '<div class="empty" />' },
        'el-form': { template: '<form><slot /></form>' },
        'el-form-item': { template: '<div><slot /></div>' },
        'el-icon': true,
        'el-input': { template: '<input />' },
        'el-option': { template: '<option />' },
        'el-pagination': { template: '<div class="pager" />' },
        'el-progress': { template: '<div class="prog" />' },
        'el-row': { template: '<div><slot /></div>' },
        'el-select': { template: '<select><slot /></select>' },
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template:
            '<td><slot :row="{ id: 1, backup_id: \'b1\', status: \'completed\', backup_type: \'full\' }" /></td>',
        },
        'el-tag': { template: '<span class="tag"><slot /></span>' },
        BackupDetailDialog: { template: '<div class="dlg-stub" />' },
        BackupRecordList: { template: '<div class="list-stub" />' },
        CreateBackupDialog: { template: '<div class="create-stub" />' },
      },
    },
  })
}

describe('BackupManagement', () => {
  beforeEach(() => {
    vi.mocked(API.getBackupRecords).mockReset()
    vi.mocked(API.getBackupStatistics).mockReset()
  })

  it('loads and renders backup records', async () => {
    vi.mocked(API.getBackupRecords).mockResolvedValue({
      data: { code: 0, data: { list: [], total: 0 } },
    } as any)
    vi.mocked(API.getBackupStatistics).mockResolvedValue({
      data: { code: 0, data: {} },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getBackupRecords)).toHaveBeenCalled()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
