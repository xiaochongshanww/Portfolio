import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import SearchPage from '../src/views/SearchPage.vue'

vi.mock('../src/api', () => ({
  API: {
    SearchService: { search: vi.fn() },
    TaxonomyService: { listCategories: vi.fn() },
    UsersService: { getApiV1Users: vi.fn() },
  },
}))

import { API } from '../src/api'

const inputStub = {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template:
    '<input class="el-in" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
}

function mountPage() {
  return mount(SearchPage, {
    global: {
      stubs: {
        'el-input': inputStub,
        'el-select': { template: '<select><slot /></select>' },
        'el-option': { template: '<option />' },
        'el-button': { template: '<button><slot /></button>' },
        'el-date-picker': true,
        'router-link': { template: '<a><slot /></a>' },
      },
    },
  })
}

describe('SearchPage', () => {
  beforeEach(() => {
    vi.mocked(API.TaxonomyService.listCategories).mockResolvedValue({ data: [] } as any)
    vi.mocked(API.UsersService.getApiV1Users).mockResolvedValue({
      data: { list: [] },
    } as any)
    vi.mocked(API.SearchService.search).mockReset()
  })

  it('searches and renders results', async () => {
    vi.mocked(API.SearchService.search).mockResolvedValue({
      data: {
        data: {
          list: [{ id: 1, title: 'Found', slug: 'found', excerpt: 'excerpt here' }],
          total: 1,
          facets: {},
        },
      },
    } as any)
    const wrapper = mountPage()
    await wrapper.find('.el-in').setValue('vue')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.SearchService.search)).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Found')
    expect(wrapper.text()).toContain('共 1 条结果')
  })

  it('shows empty state when no results', async () => {
    vi.mocked(API.SearchService.search).mockResolvedValue({
      data: { data: { list: [], total: 0, facets: {} } },
    } as any)
    const wrapper = mountPage()
    await wrapper.find('.el-in').setValue('nothing')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('无结果')
  })

  it('does not search when query is empty', async () => {
    const wrapper = mountPage()
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(vi.mocked(API.SearchService.search)).not.toHaveBeenCalled()
  })
})
