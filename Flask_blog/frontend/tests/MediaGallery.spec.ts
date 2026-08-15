import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import MediaGallery from '../src/views/MediaGallery.vue'

vi.mock('../src/api', () => ({
  API: {
    getMediaList: vi.fn(),
    downloadMedia: vi.fn(),
  },
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('../stores/user', () => ({
  useUserStore: () => ({ user: { role: 'author' }, isAuthenticated: true }),
}))

import { API } from '../src/api'

function mountPage() {
  return mount(MediaGallery, {
    global: {
      plugins: [createPinia()],
      stubs: {
        'el-button': { template: '<button><slot /></button>' },
        'el-card': { template: '<div class="card"><slot /></div>' },
        'el-dialog': { template: '<div class="dlg"><slot /></div>' },
        'el-empty': { template: '<div class="empty" />' },
        'el-icon': true,
        'el-input': { template: '<input />' },
        'el-pagination': { template: '<div class="pager" />' },
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template:
            '<td><slot :row="{ id: 1, filename: \'a.jpg\', mime_type: \'image/jpeg\' }" /></td>',
        },
        MediaDetailDialog: { template: '<div class="d-stub" />' },
        MediaUploadDialog: { template: '<div class="u-stub" />' },
        MediaEditDialog: { template: '<div class="e-stub" />' },
        FolderCreateDialog: { template: '<div class="f-stub" />' },
        MediaSelector: { template: '<div class="s-stub" />' },
      },
    },
  })
}

describe('MediaGallery', () => {
  beforeEach(() => {
    vi.mocked(API.getMediaList).mockReset()
  })

  it('loads and renders media gallery', async () => {
    vi.mocked(API.getMediaList).mockResolvedValue({
      data: { code: 0, data: { list: [], total: 0 } },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getMediaList)).toHaveBeenCalled()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
