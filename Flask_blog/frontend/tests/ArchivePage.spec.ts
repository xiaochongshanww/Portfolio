import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ArchivePage from '../src/views/ArchivePage.vue'

vi.mock('../src/api', () => ({
  API: { getPublicArticlesRaw: vi.fn() },
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

import { API } from '../src/api'

describe('ArchivePage', () => {
  beforeEach(() => {
    vi.mocked(API.getPublicArticlesRaw).mockReset()
  })

  it('renders archived articles', async () => {
    vi.mocked(API.getPublicArticlesRaw).mockResolvedValue({
      data: {
        data: {
          list: [
            { id: 1, title: 'Archived One', slug: 'a1', published_at: '2026-01-15T00:00:00Z' },
            { id: 2, title: 'Archived Two', slug: 'a2', published_at: '2025-12-10T00:00:00Z' },
          ],
        },
      },
    } as any)
    const wrapper = mount(ArchivePage, {
      global: { stubs: { 'el-icon': true } },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getPublicArticlesRaw)).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Archived One')
    expect(wrapper.text()).toContain('Archived Two')
  })

  it('renders empty archive without crash', async () => {
    vi.mocked(API.getPublicArticlesRaw).mockResolvedValue({
      data: { data: { list: [] } },
    } as any)
    const wrapper = mount(ArchivePage, {
      global: { stubs: { 'el-icon': true } },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('文章归档')
  })
})
