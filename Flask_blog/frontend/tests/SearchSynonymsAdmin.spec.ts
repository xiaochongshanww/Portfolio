import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import SearchSynonymsAdmin from '../src/views/SearchSynonymsAdmin.vue'

vi.mock('../src/api', () => ({
  API: {
    getSearchSynonyms: vi.fn(),
    createSearchSynonym: vi.fn(),
    deleteSearchSynonym: vi.fn(),
  },
}))

import { API } from '../src/api'

describe('SearchSynonymsAdmin', () => {
  beforeEach(() => {
    vi.mocked(API.getSearchSynonyms).mockReset()
  })

  it('loads and renders synonyms', async () => {
    vi.mocked(API.getSearchSynonyms).mockResolvedValue({
      data: { code: 0, data: { list: [], total: 0 } },
    } as any)
    const wrapper = mount(SearchSynonymsAdmin, {
      global: {
        stubs: {
          'el-button': { template: '<button><slot /></button>' },
          'el-input': { template: '<input />' },
          'el-table': { template: '<table><slot /></table>' },
          'el-table-column': {
            template:
              '<td><slot :row="{ id: 1, from: \'a\', to: \'b\' }" /></td>',
          },
        },
      },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getSearchSynonyms)).toHaveBeenCalled()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
