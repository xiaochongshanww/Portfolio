import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { adminPost } from '../api'
import EvaluationTab from './EvaluationTab.vue'

vi.mock('../api', () => ({
  adminPost: vi.fn(),
}))

function button(wrapper: VueWrapper, label: string) {
  const match = wrapper.findAll('button').find(item => item.text() === label)
  if (!match) throw new Error(`未找到按钮：${label}`)
  return match
}

describe('EvaluationTab', () => {
  beforeEach(() => {
    vi.mocked(adminPost).mockReset()
    vi.mocked(adminPost).mockResolvedValue({
      created_at: '2026-08-12T00:00:00Z',
      job_id: 'job-1',
      status: 'queued',
      step: 'queued',
      type: 'evaluate',
    })
  })

  it.each([
    ['常规评估', '/admin/jobs/evaluate', { top_k: 5, evaluation_set: 'regular' }],
    ['结构化专项', '/admin/jobs/evaluate', { top_k: 5, evaluation_set: 'structured' }],
    ['回答盲测', '/admin/jobs/evaluate-answers', { evaluation_set: 'answer' }],
  ])('为%s发送内置评估集标识', async (label, endpoint, payload) => {
    const wrapper = mount(EvaluationTab, {
      props: { evaluation: {}, jobs: [] },
    })

    await button(wrapper, label).trigger('click')
    await flushPromises()

    expect(adminPost).toHaveBeenCalledWith(endpoint, payload)
    expect(JSON.stringify(vi.mocked(adminPost).mock.calls[0][1])).not.toContain('file')
  })
})
