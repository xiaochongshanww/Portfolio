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
    ['单独运行结构化评估', startAdminEvaluation, { top_k: 5, evaluation_set: 'structured' }],
    ['单独运行回答盲测', startAdminAnswerEvaluation, { evaluation_set: 'answer' }],
  ])('为%s发送内置评估集标识', async (label, operation, payload) => {
    const wrapper = mount(EvaluationTab, {
      props: { evaluation: {}, jobs: [] },
    })

    await button(wrapper, label).trigger('click')
    await flushPromises()

    expect(operation).toHaveBeenCalledWith({ body: payload })
    expect(JSON.stringify(vi.mocked(operation).mock.calls[0][0])).not.toContain('file')
  })

  it('按门禁状态展示待更新而不是把过期报告显示为通过', async () => {
    const wrapper = mount(EvaluationTab, {
      props: {
        evaluation: {
          latest: { case_count: 100, source_hit_rate: 1, clause_hit_rate: 1, keyword_hit_rate: 1, failures: [] },
          structured_latest: { case_count: 12, structured_table_hit_rate: 1, failures: [] },
          answer_latest: { case_count: 24, pass_rate: 1, failures: [] },
        },
        quality: {
          quality_gate: {
            passed: false,
            failed_checks: ['regular_report_freshness'],
            checks: [
              { name: 'regular_evaluation', status: 'passed', message: '常规评估 100 项，失败 0 项' },
              { name: 'regular_report_freshness', status: 'failed', message: '常规评估报告已过期' },
            ],
          },
          candidate_activation: { available: true, passed: true },
          regular_evaluation: { case_count: 100, authority_hit_rate: 1, failure_count: 0 },
          structured_evaluation: { case_count: 0, failure_count: 0 },
          answer_evaluation: { case_count: 0, failure_count: 0 },
        },
        jobs: [],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('常规检索评估')
    expect(wrapper.text()).toContain('待更新')
    expect(wrapper.text()).toContain('当前活动版本仍可继续使用')
  })

  it('顶部质量检查提交常规、结构化和回答级评估', async () => {
    const wrapper = mount(EvaluationTab, { props: { evaluation: {}, quality: {}, jobs: [] } })

    await button(wrapper, '运行可执行检查').trigger('click')
    await flushPromises()

    expect(startAdminEvaluation).toHaveBeenCalledWith({ body: { top_k: 5, evaluation_set: 'regular' } })
    expect(startAdminEvaluation).toHaveBeenCalledWith({ body: { top_k: 5, evaluation_set: 'structured' } })
    expect(startAdminAnswerEvaluation).toHaveBeenCalledWith({ body: { evaluation_set: 'answer' } })
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
