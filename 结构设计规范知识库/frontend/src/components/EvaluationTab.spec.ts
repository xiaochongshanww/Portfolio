import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { startAdminAnswerEvaluation, startAdminEvaluation } from '../admin-api'
import EvaluationTab from './EvaluationTab.vue'

vi.mock('../admin-api', () => ({
  startAdminAnswerEvaluation: vi.fn(),
  startAdminEvaluation: vi.fn(),
}))

function button(wrapper: VueWrapper, label: string) {
  const match = wrapper.findAll('button').find(item => item.text() === label)
  if (!match) throw new Error(`未找到按钮：${label}`)
  return match
}

describe('EvaluationTab', () => {
  beforeEach(() => {
    vi.mocked(startAdminAnswerEvaluation).mockReset()
    vi.mocked(startAdminEvaluation).mockReset()
    const response = {
      created_at: '2026-08-12T00:00:00Z',
      job_id: 'job-1',
      status: 'queued',
      step: 'queued',
      type: 'evaluate',
    }
    vi.mocked(startAdminAnswerEvaluation).mockResolvedValue(response)
    vi.mocked(startAdminEvaluation).mockResolvedValue(response)
  })

  it.each([
    ['常规评估', startAdminEvaluation, { top_k: 5, evaluation_set: 'regular' }],
    ['结构化专项', startAdminEvaluation, { top_k: 5, evaluation_set: 'structured' }],
    ['回答盲测', startAdminAnswerEvaluation, { evaluation_set: 'answer' }],
  ])('为%s发送内置评估集标识', async (label, operation, payload) => {
    const wrapper = mount(EvaluationTab, {
      props: { evaluation: {}, jobs: [] },
    })

    await button(wrapper, label).trigger('click')
    await flushPromises()

    expect(operation).toHaveBeenCalledWith({ body: payload })
    expect(JSON.stringify(vi.mocked(operation).mock.calls[0][0])).not.toContain('file')
  })
})
