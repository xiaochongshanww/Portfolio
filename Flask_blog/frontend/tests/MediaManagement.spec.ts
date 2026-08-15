import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import MediaManagement from '../src/views/admin/MediaManagement.vue'

vi.mock('../src/api', () => ({
  API: {
    getMediaList: vi.fn(),
    getFolders: vi.fn(),
    getMediaStats: vi.fn(),
    deleteMedia: vi.fn(),
    deleteMediaFolder: vi.fn(),
    downloadMedia: vi.fn(),
    getFolderPath: vi.fn(),
  },
}))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
}))

import { API } from '../src/api'

function mountPage() {
  return mount(MediaManagement, {
    global: {
      stubs: {
        'el-button': { template: '<button><slot /></button>' },
        'el-card': { template: '<div class="card"><slot /></div>' },
        'el-dialog': { template: '<div class="dlg"><slot /></div>' },
        'el-empty': { template: '<div class="empty" />' },
        'el-icon': true,
        'el-input': { template: '<input />' },
        'el-option': { template: '<option />' },
        'el-pagination': { template: '<div class="pager" />' },
        'el-select': { template: '<select><slot /></select>' },
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template:
            '<td><slot :row="{ id: 1, filename: \'a.jpg\', mime_type: \'image/jpeg\', media_type: \'image\' }" /></td>',
        },
        'el-tree': { template: '<div class="tree"><slot /></div>' },
      },
    },
  })
}

describe('MediaManagement', () => {
  beforeEach(() => {
    vi.mocked(API.getMediaList).mockReset()
    vi.mocked(API.getFolders).mockReset()
    vi.mocked(API.getMediaStats).mockReset()
  })

  it('loads and renders media list', async () => {
    vi.mocked(API.getMediaList).mockResolvedValue({
      data: { code: 0, data: { items: [], total: 0 } },
    } as any)
    vi.mocked(API.getFolders).mockResolvedValue({
      data: { code: 0, data: { folders: [] } },
    } as any)
    vi.mocked(API.getMediaStats).mockResolvedValue({
      data: { code: 0, data: {} },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getMediaList)).toHaveBeenCalled()
  })

  it('renders when media API errors', async () => {
    vi.mocked(API.getMediaList).mockRejectedValue(new Error('boom'))
    vi.mocked(API.getFolders).mockResolvedValue({
      data: { code: 0, data: {} },
    } as any)
    vi.mocked(API.getMediaStats).mockResolvedValue({
      data: { code: 0, data: {} },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
