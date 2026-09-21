import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import OverviewTab from './OverviewTab.vue'

const documents = {
  built: true,
  documents: [],
  document_count: 7,
  chunk_count: 2689,
  image_count: 0,
  data_version_hash: '382c8904807c1234',
  built_at: '2026-08-24T02:06:20Z',
  parser_backend: 'mineru',
  missing_artifact_count: 0,
  applied_correction_count: 5,
  audit_status: { finding_count: 3, high_risk_count: 0 },
}

const quality = {
  pending_task_count: 14,
  recent_failed_job_count: 0,
  unresolved_failed_job_count: 0,
  candidate_activation: { available: true, passed: true },
  structured_evaluation: { structured_table_hit_rate: 1 },
  answer_evaluation: { pass_rate: 1 },
}

describe('OverviewTab', () => {
  it('shows the machine-audit stage as done and keeps one current stage', () => {
    const wrapper = mount(OverviewTab, {
      props: {
        ready: {
          ready: true,
          status: 'ready',
          reasons: [],
          built_at: documents.built_at,
          checked_at: documents.built_at,
          checks: {},
          data_version_hash: documents.data_version_hash,
          version: documents.data_version_hash,
        },
        documents,
        metrics: {},
        quality,
      },
    })

    const stages = wrapper.findAll('.workflow-stage')
    expect(stages).toHaveLength(7)
    expect(wrapper.text()).toContain('机器审计')
    expect(stages[2].classes()).toContain('workflow-stage-done')
    expect(wrapper.findAll('.workflow-stage-current')).toHaveLength(1)
    expect(wrapper.findAll('.workflow-stage-current')[0].text()).toContain('复杂表')
    expect(stages[5].classes()).toContain('workflow-stage-pending')
  })

  it('keeps the hero as the only primary action for the overview', () => {
    const wrapper = mount(OverviewTab, {
      props: { ready: null, documents, metrics: {}, quality },
    })

    expect(wrapper.findAll('.btn-primary')).toHaveLength(1)
    expect(wrapper.find('.current-stage-panel .btn-primary').exists()).toBe(false)
    expect(wrapper.find('.cockpit-hero').text()).toContain('完成 14 个复杂表结构化任务')
    expect(wrapper.find('.cockpit-hero-meta').text()).toContain('阻塞发布：是')
  })
})
