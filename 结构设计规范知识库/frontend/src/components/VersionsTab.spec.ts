import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import VersionsTab from './VersionsTab.vue'

const api = vi.hoisted(() => ({
  createAdminVersionCleanupPlan: vi.fn(),
  getAdminVersions: vi.fn(),
  startAdminVersionCleanup: vi.fn(),
  updateAdminVersionRetention: vi.fn(),
}))

vi.mock('../admin-api', () => api)
vi.mock('../api', () => ({ errorMessage: (error: unknown) => String(error) }))

const baseVersion = {
  version_label: 'KB-20260830-100000',
  path: 'version',
  size_bytes: 1024,
  file_count: 2,
  modified_at: '2026-08-30T10:00:00+08:00',
  age_hours: 1,
  gate_passed: true,
  pinned: false,
  pin_marker_invalid: false,
  pin_note: '',
  fingerprint: 'f'.repeat(64),
  safe: true,
  scan_error: null,
  protected: false,
  protection_reasons: [],
  cleanup_eligible: true,
  cleanup_reason: 'expired_successful',
}

const inventory = {
  schema_version: 1,
  generated_at: '2026-08-30T10:00:00+08:00',
  active_version_id: 'active-version',
  active_version_label: 'KB-20260830-100000',
  policy: {
    keep_recent_passed: 2,
    success_max_age_days: 30,
    failed_max_age_days: 7,
    minimum_age_hours: 24,
    high_watermark_bytes: 20 * 1024 ** 3,
    low_watermark_bytes: 16 * 1024 ** 3,
  },
  version_count: 3,
  total_bytes: 3072,
  cleanup_candidate_count: 2,
  cleanup_candidate_bytes: 2048,
  projected_bytes: 1024,
  target_unmet_bytes: 0,
  matched_version_count: 3,
  page_offset: 0,
  page_limit: 20,
  versions: [
    { ...baseVersion, version_id: 'active-version', state: 'active', cleanup_eligible: false, cleanup_reason: '' },
    { ...baseVersion, version_id: 'failed-version', state: 'failed_gate', cleanup_reason: 'expired_failed_or_incomplete', scan_error: '门禁检查失败' },
    { ...baseVersion, version_id: 'pinned-version', state: 'passed', pinned: true, pin_note: '用于回滚验证', protected: true, protection_reasons: ['pinned'], cleanup_eligible: false, cleanup_reason: '' },
  ],
}

function pagedInventory(versions: typeof inventory.versions, options: { query?: Record<string, unknown> } = {}) {
  const query = options.query || {}
  const text = String(query.q || '').trim().toLocaleLowerCase()
  const state = String(query.state || '')
  const scope = String(query.scope || '')
  const matched = versions.filter((item) => {
    if (state && item.state !== state) return false
    if (scope === 'cleanup' && !item.cleanup_eligible) return false
    if (scope === 'protected' && !item.protected) return false
    if (scope === 'pinned' && !item.pinned) return false
    if (!text) return true
    return [item.version_id, item.version_label, item.scan_error || '', item.cleanup_reason]
      .some(value => value.toLocaleLowerCase().includes(text))
  })
  const offset = Number(query.offset || 0)
  const limit = Number(query.limit || matched.length)
  return Promise.resolve({
    ...inventory,
    version_count: versions.length,
    matched_version_count: matched.length,
    page_offset: offset,
    page_limit: limit,
    versions: matched.slice(offset, offset + limit),
  })
}

describe('VersionsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getAdminVersions.mockImplementation((options = {}) => pagedInventory(inventory.versions, options))
    api.updateAdminVersionRetention.mockResolvedValue({ version_id: 'pinned-version', note: '更新后的原因' })
  })
  afterEach(() => vi.useRealTimers())

  it('支持版本清单筛选、分页和异常状态说明', async () => {
    vi.useFakeTimers()
    const manyVersions = {
      ...inventory,
      version_count: 21,
      versions: Array.from({ length: 21 }, (_, index) => ({
        ...baseVersion,
        version_id: `version-${String(index + 1).padStart(2, '0')}`,
        state: index === 0 ? 'active' : 'passed',
        cleanup_eligible: index > 0,
        cleanup_reason: index > 0 ? 'expired_successful' : '',
      })),
    }
    api.getAdminVersions.mockImplementation((options = {}) => pagedInventory(manyVersions.versions, options))
    const wrapper = mount(VersionsTab)
    await flushPromises()

    expect((wrapper.get('[aria-label="每页版本数"]').element as HTMLSelectElement).value).toBe('20')
    expect(wrapper.text()).toContain('KB-20260830-100000')
    expect(wrapper.text()).toContain('第 1 / 2 页，共 21 个')
    expect(wrapper.findAll('tbody tr')).toHaveLength(20)

    await wrapper.get('[aria-label="筛选版本状态"]').setValue('active')
    vi.advanceTimersByTime(250)
    await flushPromises()
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(wrapper.text()).toContain('活动')

    await wrapper.get('[aria-label="筛选版本状态"]').setValue('all')
    await wrapper.get('[aria-label="筛选版本范围"]').setValue('cleanup')
    vi.advanceTimersByTime(250)
    await flushPromises()
    expect(wrapper.findAll('tbody tr')).toHaveLength(20)
    expect(wrapper.find('tbody').text()).not.toContain('active-version')

    await wrapper.get('input[type="search"]').setValue('version-21')
    vi.advanceTimersByTime(250)
    await flushPromises()
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(wrapper.text()).toContain('version-21')
  })

  it('展示版本详情并保存人工固定备注', async () => {
    const wrapper = mount(VersionsTab)
    await flushPromises()

    const viewButtons = wrapper.findAll('button').filter(button => button.text() === '查看')
    await viewButtons[2].trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('版本详情')
    expect(wrapper.text()).toContain('门禁通过')
    expect((wrapper.find('textarea').element as HTMLTextAreaElement).value).toBe('用于回滚验证')

    const note = wrapper.find('textarea')
    await note.setValue('更新后的原因')
    const saveNoteButton = wrapper.findAll('button.btn-primary').at(-1)
    expect(saveNoteButton).toBeTruthy()
    await saveNoteButton!.trigger('click')
    await flushPromises()
    expect(api.updateAdminVersionRetention).toHaveBeenCalledWith({
      path: { version_id: 'pinned-version' },
      body: { pinned: true, note: '更新后的原因' },
    })
    expect(wrapper.text()).toContain('已保存版本 KB-20260830-100000 的固定备注')
  })
})
