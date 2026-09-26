import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { revalidateSourceCandidate, republishSourceCandidate } from '../source-api'

import JobsTab from './JobsTab.vue'

const api = vi.hoisted(() => ({
  getAdminCandidateGateReport: vi.fn(),
  getAdminJobLogs: vi.fn(),
  getAdminRebuildPlan: vi.fn(),
  cancelAdminJob: vi.fn(),
  startAdminAudit: vi.fn(),
  startAdminEvaluation: vi.fn(),
  startAdminRebuild: vi.fn(),
  startAdminReview: vi.fn(),
}))
const sourceApi = vi.hoisted(() => ({
  revalidateSourceCandidate: vi.fn(),
  republishSourceCandidate: vi.fn(),
}))

vi.mock('../admin-api', () => api)
vi.mock('../api', () => ({ errorMessage: (error: unknown) => String(error) }))
vi.mock('../source-api', () => sourceApi)

const jobs = [
  {
    job_id: 'job-success',
    type: 'source_republish',
    status: 'succeeded',
    step: 'finished',
    created_at: '2026-08-24T14:00:39.743905+00:00',
    progress_at: '2026-08-24T14:02:10.295706+00:00',
    progress: { message: '候选版本已通过门禁并成为活动版本' },
  },
  {
    job_id: 'job-failed',
    type: 'source_rebuild',
    status: 'failed',
    step: 'candidate_gate',
    created_at: '2026-08-24T02:00:00+00:00',
    progress_at: '2026-08-24T02:07:40+00:00',
    error: '候选版本未通过预激活门禁: regular_evaluation',
    params: { source_catalog_revision: 'src-one' },
    progress: { message: '验证候选运行时并执行预激活评估' },
  },
] as any

describe('JobsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getAdminCandidateGateReport.mockResolvedValue({
      job_id: 'job-failed',
      available: true,
      candidate_version_id: 'candidate-1',
      passed: false,
      failed_checks: ['regular_evaluation'],
      checks: [{ name: 'regular_evaluation', status: 'failed', message: '100 项中失败 1 项' }],
      evaluation_sets_current: false,
      evaluation_set_status: [
        { evaluation_set_id: 'regular', snapshot_revision_id: 'builtin-old', current_revision_id: 'builtin-new', freshness: 'stale' },
        { evaluation_set_id: 'structured', snapshot_revision_id: 'builtin-structured', current_revision_id: 'builtin-structured', freshness: 'current' },
      ],
      regular_evaluation: {
        case_count: 100,
        failure_count: 1,
        failures: [{
          id: 'table-quality-division',
          type: 'table',
          query: '建筑工程分部工程和分项工程划分在哪个表？',
          expected_authority_type: 'body_or_table',
          source_hit: true,
          top1_source_hit: true,
          clause_hit: true,
          keyword_hit: true,
          table_hit: true,
          authority_hit: false,
          structured_table_hit: true,
          failed_checks: ['authority'],
          top_results: [
            { source_file: 'GB 50300-2013', clause_number: '4.0.1', section_type: 'body', score: 23.2099 },
            { source_file: 'GB 50300-2013', section_type: 'body_table', score: 23.1498 },
          ],
          top_structured_results: [
            { table_id: '4.0.6', table_name: '分部工程划分', score: 19.4 },
          ],
        }],
      },
      structured_evaluation: { case_count: 12, failure_count: 0, failures: [] },
    })
    api.getAdminJobLogs.mockResolvedValue({
      logs: [{
        ts: '2026-08-24T14:00:40.001950+00:00',
        level: 'info',
        step: 'candidate_gate',
        message: '验证候选运行时并执行预激活评估',
      }],
    })
    api.getAdminRebuildPlan.mockResolvedValue({
      fallback_to_full: false,
      fallback_reasons: [],
      counts: { reused: 1, added: 0, changed: 0, removed: 0 },
    })
    const response = { job_id: 'job-new', type: 'source_rebuild', status: 'queued', step: 'queued' }
    api.startAdminAudit.mockResolvedValue(response)
    api.startAdminEvaluation.mockResolvedValue(response)
    api.startAdminRebuild.mockResolvedValue(response)
    api.startAdminReview.mockResolvedValue(response)
    sourceApi.republishSourceCandidate.mockResolvedValue({
      job: { job_id: 'job-republish', type: 'source_republish', status: 'queued', step: 'queued' },
    })
    sourceApi.revalidateSourceCandidate.mockResolvedValue({
      job: {
        job_id: 'job-revalidation',
        type: 'candidate_revalidation',
        status: 'queued',
        step: 'queued',
        params: { candidate_job_id: 'job-failed' },
      },
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('localizes task identifiers and supports filtering and keyboard selection', async () => {
    const wrapper = mount(JobsTab, { props: { jobs } })
    await flushPromises()

    expect(wrapper.text()).toContain('候选版本发布')
    expect(wrapper.text()).toContain('已完成')
    expect(wrapper.text()).toContain('最近更新')
    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
    expect(wrapper.find('tbody tr').attributes('tabindex')).toBe('0')
    expect(wrapper.find('tbody tr').attributes('aria-selected')).toBe('true')

    await wrapper.get('#job-filter').setValue('failed')
    await flushPromises()
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(wrapper.text()).toContain('知识库重建')
    expect(wrapper.find('tbody').text()).not.toContain('候选版本发布')
    expect(wrapper.find('tbody tr').attributes('aria-selected')).toBe('true')
    expect(wrapper.find('aside').text()).toContain('知识库重建 · 候选门禁')
    expect(wrapper.find('aside').text()).toContain('已失败')

    await wrapper.find('tbody tr').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(api.getAdminJobLogs).toHaveBeenCalledWith({
      path: { job_id: 'job-failed' },
      query: { limit: 300 },
    })
    expect(api.getAdminCandidateGateReport).toHaveBeenCalledWith({
      path: { job_id: 'job-failed' },
    })
    expect(wrapper.text()).toContain('候选门禁')
    expect(wrapper.text()).toContain('候选激活门禁未通过')
    expect(wrapper.text()).toContain('table-quality-division')
    expect(wrapper.text()).toContain('评估集已更新')
    expect(wrapper.text()).toContain('builtin-old → builtin-new')
    expect(wrapper.text()).toContain('建筑工程分部工程和分项工程划分在哪个表？')
    expect(wrapper.text()).toContain('正文条文')
    expect(wrapper.text()).toContain('来源匹配：通过')
    expect(wrapper.text()).toContain('权威依据：未通过')
    expect(wrapper.text()).toContain('期望依据类型：正文条文或正文表格')
    expect(wrapper.text()).toContain('结构化表 1. 分部工程划分 · 4.0.6')
  })

  it('shows the latest passing revalidation without implying candidate activation', async () => {
    api.getAdminCandidateGateReport.mockResolvedValue({
      job_id: 'job-failed',
      available: true,
      report_source: 'revalidation',
      candidate_version_id: 'candidate-1',
      generated_at: '2026-09-25T22:36:55Z',
      passed: true,
      failed_checks: [],
      checks: [],
      evaluation_sets_current: true,
      evaluation_set_status: [],
      regular_evaluation: { case_count: 100, failure_count: 0, failures: [] },
      structured_evaluation: { case_count: 12, failure_count: 0, failures: [] },
    })
    const wrapper = mount(JobsTab, { props: { jobs: [jobs[1]] } })
    await wrapper.find('tbody tr').trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(wrapper.find('aside').text()).toContain('最近一次候选复核通过')
    expect(wrapper.find('aside').text()).toContain('复核结果不代表候选已发布或已激活')
    expect(sourceApi.republishSourceCandidate).not.toHaveBeenCalled()
  })

  it('paginates the task history inside the queue', async () => {
    const manyJobs = [
      ...jobs,
      ...Array.from({ length: 10 }, (_, index) => ({
        ...jobs[0],
        job_id: `job-extra-${index}`,
        type: 'evaluate',
        created_at: `2026-08-20T00:0${index % 9}:00+00:00`,
        progress_at: `2026-08-20T00:0${index % 9}:00+00:00`,
      })),
    ]
    const wrapper = mount(JobsTab, { props: { jobs: manyJobs } })
    await flushPromises()

    expect(wrapper.get('[aria-current="page"]').text()).toContain('第 1 / 2 页，共 12 条')
    expect(wrapper.findAll('tbody tr')).toHaveLength(10)
    expect(wrapper.get('[data-testid="job-queue-scroll"]').classes()).toContain('flex-1')
    expect(wrapper.get('[data-testid="job-pagination"]').classes()).toContain('shrink-0')

    const nextButton = wrapper.findAll('button').find(button => button.text() === '下一页')
    expect(nextButton).toBeTruthy()
    await nextButton!.trigger('click')
    await flushPromises()

    expect(wrapper.get('[aria-current="page"]').text()).toContain('第 2 / 2 页，共 12 条')
    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
    expect(wrapper.findAll('tbody tr')[0].text()).toContain('结构化评估')
    expect(nextButton!.attributes('disabled')).toBeDefined()
  })

  it('confirms rebuild parameters before submitting a task', async () => {
    const confirmMock = vi.fn(() => false)
    vi.stubGlobal('confirm', confirmMock)
    const wrapper = mount(JobsTab, { props: { jobs: [] } })

    await wrapper.get('button.btn-primary').trigger('click')
    expect(confirmMock).toHaveBeenCalledWith(expect.stringContaining('增量候选重建'))
    expect(api.startAdminRebuild).not.toHaveBeenCalled()

    confirmMock.mockReturnValue(true)
    await wrapper.get('button.btn-primary').trigger('click')
    await flushPromises()
    expect(api.startAdminRebuild).toHaveBeenCalledWith({
      body: expect.objectContaining({ mode: 'incremental', apply_corrections: true }),
    })
    vi.unstubAllGlobals()
  })

  it('explains candidate republish semantics and reuses the existing parse', async () => {
    const confirmMock = vi.fn(() => true)
    vi.stubGlobal('confirm', confirmMock)
    const failedJob = {
      ...jobs[1],
      candidate_republishable: true,
      candidate_republish_reason: '',
    }
    const wrapper = mount(JobsTab, { props: { jobs: [failedJob] } })
    await flushPromises()

    expect(wrapper.text()).toContain('按当前评估集重新执行激活门禁')
    expect(wrapper.text()).toContain('只有全部通过才会切换活动版本')
    const republishButton = wrapper.findAll('button').find(button => button.text() === '重新验证并尝试发布（不重新解析）')
    expect(republishButton).toBeTruthy()

    await republishButton!.trigger('click')
    await flushPromises()

    expect(confirmMock).toHaveBeenCalledWith('将重新执行候选门禁并发布该版本，不会重新解析 PDF。继续吗？')
    expect(republishSourceCandidate).toHaveBeenCalledWith('job-failed')
    expect(api.startAdminRebuild).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })

  it('submits candidate-only revalidation without invoking republish', async () => {
    const confirmMock = vi.fn(() => true)
    vi.stubGlobal('confirm', confirmMock)
    const failedJob = {
      ...jobs[1],
      candidate_republishable: true,
      candidate_republish_reason: '',
    }
    const wrapper = mount(JobsTab, { props: { jobs: [failedJob] } })
    await flushPromises()

    expect(wrapper.text()).toContain('仅复核候选（不发布）')
    expect(wrapper.text()).toContain('不会重解析、修改原失败任务或切换活动版本')
    const revalidateButton = wrapper.findAll('button').find(button => button.text() === '仅复核候选（不发布）')
    expect(revalidateButton).toBeTruthy()
    await revalidateButton!.trigger('click')
    await flushPromises()

    expect(confirmMock).toHaveBeenCalledWith(expect.stringContaining('不会重新解析、发布候选或切换活动版本'))
    expect(revalidateSourceCandidate).toHaveBeenCalledWith('job-failed')
    expect(republishSourceCandidate).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('候选版本复核 · 排队中')
    vi.unstubAllGlobals()
  })

  it('loads the report for a completed independent revalidation task', async () => {
    const revalidationJob = {
      job_id: 'job-revalidation',
      type: 'candidate_revalidation',
      status: 'succeeded',
      step: 'candidate_revalidate_report',
      created_at: '2026-09-26T00:00:00Z',
      params: { candidate_job_id: 'job-failed' },
    } as any
    api.getAdminCandidateGateReport.mockResolvedValue({
      job_id: 'job-revalidation',
      available: true,
      report_source: 'revalidation',
      candidate_version_id: 'job-failed',
      generated_at: '2026-09-26T00:00:00Z',
      passed: false,
      failed_checks: ['regular_evaluation'],
      checks: [],
      evaluation_sets_current: true,
      evaluation_set_status: [],
      regular_evaluation: { case_count: 100, failure_count: 1, failures: [] },
      structured_evaluation: { case_count: 12, failure_count: 0, failures: [] },
    })
    const wrapper = mount(JobsTab, { props: { jobs: [revalidationJob] } })
    await wrapper.find('tbody tr').trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(wrapper.text()).toContain('候选版本复核')
    expect(api.getAdminCandidateGateReport).toHaveBeenCalledWith({
      path: { job_id: 'job-revalidation' },
    })
    expect(wrapper.find('aside').text()).toContain('最近一次候选复核未通过')
  })

  it('loads the report when the selected revalidation task completes', async () => {
    const queuedJob = {
      job_id: 'job-revalidation',
      type: 'candidate_revalidation',
      status: 'queued',
      step: 'queued',
      created_at: '2026-09-26T00:00:00Z',
      params: { candidate_job_id: 'job-failed' },
    } as any
    const completedJob = {
      ...queuedJob,
      status: 'succeeded',
      step: 'finished',
      finished_at: '2026-09-26T00:02:00Z',
      outputs: { passed: true },
    }
    api.getAdminCandidateGateReport.mockResolvedValue({
      job_id: 'job-revalidation',
      available: true,
      report_source: 'revalidation',
      candidate_version_id: 'job-failed',
      generated_at: '2026-09-26T00:02:00Z',
      passed: true,
      failed_checks: [],
      checks: [],
      evaluation_sets_current: true,
      evaluation_set_status: [],
      regular_evaluation: { case_count: 100, failure_count: 0, failures: [] },
      structured_evaluation: { case_count: 12, failure_count: 0, failures: [] },
    })
    const wrapper = mount(JobsTab, { props: { jobs: [queuedJob] } })
    await flushPromises()
    expect(api.getAdminCandidateGateReport).not.toHaveBeenCalled()

    await wrapper.setProps({ jobs: [completedJob] })
    await flushPromises()

    expect(api.getAdminCandidateGateReport).toHaveBeenCalledWith({
      path: { job_id: 'job-revalidation' },
    })
    expect(wrapper.find('aside').text()).toContain('最近一次候选复核通过')
  })

  it('cancels a running build through the managed API and shows its pending state', async () => {
    const confirmMock = vi.fn(() => true)
    vi.stubGlobal('confirm', confirmMock)
    const runningBuild = {
      job_id: 'job-running-build',
      type: 'source_rebuild',
      status: 'running',
      step: 'build_version',
      created_at: '2026-09-26T00:00:00+00:00',
    } as any
    api.cancelAdminJob.mockResolvedValue({
      ...runningBuild,
      cancellation_requested: true,
      progress: { message: '已收到取消请求，等待当前解析或处理步骤安全停止' },
    })

    const wrapper = mount(JobsTab, { props: { jobs: [runningBuild] } })
    await flushPromises()
    await wrapper.get('aside button').trigger('click')
    await flushPromises()

    expect(confirmMock).toHaveBeenCalledWith(expect.stringContaining('确认取消此知识库构建任务'))
    expect(api.cancelAdminJob).toHaveBeenCalledWith({ path: { job_id: 'job-running-build' } })
    expect(wrapper.text()).toContain('取消请求已提交')
    expect(wrapper.text()).toContain('取消中')
    expect(wrapper.text()).toContain('已向构建任务 job-running-build 发出取消请求')
  })

  it('does not offer cancellation for non-build tasks or during version activation', async () => {
    const nonBuild = {
      ...jobs[0],
      job_id: 'job-running-eval',
      type: 'evaluate',
      status: 'running',
      step: 'evaluate',
    }
    const nonBuildWrapper = mount(JobsTab, { props: { jobs: [nonBuild as any] } })
    await flushPromises()
    expect(nonBuildWrapper.text()).not.toContain('取消构建任务')
    nonBuildWrapper.unmount()

    const activating = {
      ...nonBuild,
      job_id: 'job-activating',
      type: 'source_rebuild',
      step: 'activate_version',
    }
    const activationWrapper = mount(JobsTab, { props: { jobs: [activating as any] } })
    await flushPromises()
    expect(activationWrapper.text()).not.toContain('取消构建任务')
    expect(activationWrapper.text()).toContain('提交阶段不可取消')
    expect(api.cancelAdminJob).not.toHaveBeenCalled()
  })
})
