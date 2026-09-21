import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import JobsTab from './JobsTab.vue'

const api = vi.hoisted(() => ({
  getAdminJobLogs: vi.fn(),
  getAdminRebuildPlan: vi.fn(),
  startAdminAudit: vi.fn(),
  startAdminEvaluation: vi.fn(),
  startAdminRebuild: vi.fn(),
  startAdminReview: vi.fn(),
}))

vi.mock('../admin-api', () => api)
vi.mock('../api', () => ({ errorMessage: (error: unknown) => String(error) }))
vi.mock('../source-api', () => ({ republishSourceCandidate: vi.fn() }))

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
    expect(wrapper.text()).toContain('候选门禁')
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
})
