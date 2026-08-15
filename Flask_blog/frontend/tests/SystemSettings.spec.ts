import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import SystemSettings from '../src/views/admin/SystemSettings.vue'

vi.mock('../src/apiClient', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: { code: 0, data: {} } })),
    post: vi.fn(() => Promise.resolve({ data: { code: 0, data: {} } })),
    put: vi.fn(() => Promise.resolve({ data: { code: 0, data: {} } })),
    delete: vi.fn(() => Promise.resolve({ data: { code: 0, data: {} } })),
  },
}))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()) },
}))

function mountPage() {
  return mount(SystemSettings, {
    global: {
      stubs: {
        'el-button': { template: '<button><slot /></button>' },
        'el-card': { template: '<div class="card"><slot /></div>' },
        'el-dialog': { template: '<div class="dlg"><slot /></div>' },
        'el-form': { template: '<form><slot /></form>' },
        'el-form-item': { template: '<div><slot /></div>' },
        'el-icon': true,
        'el-input': { template: '<input />' },
        'el-select': { template: '<select><slot /></select>' },
        'el-option': { template: '<option />' },
        'el-switch': { template: '<input type="checkbox" />' },
        'el-tabs': { template: '<div class="tabs"><slot /></div>' },
        'el-tab-pane': { template: '<div class="pane"><slot /></div>' },
        'el-upload': { template: '<div class="up" />' },
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template: '<td><slot :row="{ id: 1, filename: \'a\' }" /></td>',
        },
      },
    },
  })
}

describe('SystemSettings', () => {
  it('loads and renders settings', async () => {
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
