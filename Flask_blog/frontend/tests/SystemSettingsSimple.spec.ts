import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import SystemSettingsSimple from '../src/views/admin/SystemSettingsSimple.vue'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn() },
}))
import { ElMessage } from 'element-plus'

function mountPage() {
  return mount(SystemSettingsSimple, {
    global: {
      stubs: {
        'el-card': { template: '<div class="card"><slot name="header" /><slot /></div>' },
        'el-tabs': { template: '<div class="tabs"><slot /></div>' },
        'el-tab-pane': { template: '<div class="pane"><slot /></div>' },
        'el-form': { template: '<form><slot /></form>' },
        'el-form-item': { template: '<div class="form-item"><slot /></div>' },
        'el-input': { template: '<input class="in" />' },
        'el-button': { template: '<button><slot /></button>' },
        'el-descriptions': { template: '<dl><slot /></dl>' },
        'el-descriptions-item': { template: '<dd><slot /></dd>' },
      },
    },
  })
}

describe('SystemSettingsSimple', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders the settings page with defaults', () => {
    const wrapper = mountPage()
    expect(wrapper.text()).toContain('系统设置')
    expect(wrapper.text()).toContain('保存设置')
    expect(wrapper.findAll('.form-item').length).toBeGreaterThanOrEqual(3)
  })

  it('shows success message on save', async () => {
    const wrapper = mountPage()
    await wrapper.find('button').trigger('click')
    await vi.advanceTimersByTimeAsync(1100)
    expect(ElMessage.success).toHaveBeenCalled()
  })
})
