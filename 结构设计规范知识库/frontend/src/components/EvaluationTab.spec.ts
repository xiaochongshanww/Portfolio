import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { listAdminEvaluationCases, startAdminAnswerEvaluation, startAdminEvaluation } from '../admin-api'
import EvaluationTab from './EvaluationTab.vue'

vi.mock('../admin-api', () => ({
  listAdminEvaluationCases: vi.fn(),
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
    vi.mocked(listAdminEvaluationCases).mockReset()
    vi.mocked(startAdminAnswerEvaluation).mockReset()
    vi.mocked(startAdminEvaluation).mockReset()
    vi.mocked(listAdminEvaluationCases).mockResolvedValue({
      evaluation_set: 'regular',
      total: 0,
      offset: 0,
      limit: 50,
      type_counts: {},
      cases: [],
    })
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

  it('浏览评估集用例及其详情', async () => {
    vi.mocked(listAdminEvaluationCases).mockResolvedValue({
      evaluation_set: 'regular',
      total: 1,
      offset: 0,
      limit: 50,
      type_counts: { clause: 1 },
      cases: [{
        id: 'case-001',
        query: '办公楼楼面活荷载取多少？',
        type: 'clause',
        expected_sources: ['GB 50009-2012'],
        expected_clause: '5.1.1',
        expected_keywords: ['活荷载'],
        expected_authority_type: '正文表格',
        top1_source_required: true,
        keyword_required: true,
        expected_table_id: '表5.1.1',
        expected_all: [],
        expected_any_groups: [],
        forbidden_terms: [],
        expected_citations: [],
        expected_unit_groups: [],
        requires_refusal: false,
        requires_image: true,
      }],
    })

    const wrapper = mount(EvaluationTab, { props: { evaluation: {}, jobs: [] } })
    await flushPromises()

    expect(wrapper.text()).toContain('办公楼楼面活荷载取多少？')
    expect(wrapper.text()).toContain('正文表格')
    expect(wrapper.text()).toContain('表5.1.1')
  })
})
