import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CommentsModeration from '../src/views/CommentsModeration.vue'

vi.mock('../src/api', () => ({
  API: {
    getPendingComments: vi.fn(),
    moderateComment: vi.fn(),
  },
}))

import { API } from '../src/api'

function mountPage() {
  return mount(CommentsModeration, {
    global: {
      stubs: {
        'el-button': { template: '<button><slot /></button>' },
        'el-empty': { template: '<div class="empty" />' },
        'el-icon': true,
        'el-table': { template: '<table><slot /></table>' },
        'el-table-column': {
          template:
            '<td><slot :row="{ id: 1, content: \'c\', article_id: 1 }" /></td>',
        },
      },
    },
  })
}

describe('CommentsModeration', () => {
  beforeEach(() => {
    vi.mocked(API.getPendingComments).mockReset()
  })

  it('loads and renders pending comments', async () => {
    vi.mocked(API.getPendingComments).mockResolvedValue({
      data: { code: 0, data: { list: [], total: 0 } },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(API.getPendingComments)).toHaveBeenCalled()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
