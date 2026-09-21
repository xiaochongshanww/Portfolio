import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SourcesTab from './SourcesTab.vue'

const api = vi.hoisted(() => ({
  listSources: vi.fn(),
  uploadSource: vi.fn(),
  updateSource: vi.fn(),
  validateSource: vi.fn(),
  bootstrapSources: vi.fn(),
  replaceSource: vi.fn(),
  retireSource: vi.fn(),
  discardPendingSource: vi.fn(),
  deleteDraftSource: vi.fn(),
  planSourceChanges: vi.fn(),
  buildSourceChanges: vi.fn(),
}))

vi.mock('../source-api', () => api)

const source = {
  source_id: 'gb-50000-2026-abcd1234',
  lifecycle_status: 'ready',
  pending_action: 'add',
  active_asset_version_id: '',
  pending_asset_version_id: 'asset-one',
  metadata: {
    source_file: 'GB 50000-2026_测试规范.pdf',
    code: 'GB 50000-2026',
    name: '测试规范',
    aliases: [],
    page_image_access: 'disabled',
    image_access: 'disabled',
  },
  governance: { source_kind: 'user_upload', rights_status: 'B', reference_index: '' },
  versions: [{
    asset_version_id: 'asset-one', sha256: 'a'.repeat(64), original_filename: 'source.pdf',
    object_path: 'source_assets/objects/aa/a.pdf', size_bytes: 100, page_count: 3,
    uploaded_at: '2026-08-23T00:00:00Z', validation_status: 'validated', validation_errors: [],
  }],
  created_at: '2026-08-23T00:00:00Z',
  updated_at: '2026-08-23T00:00:00Z',
}

describe('SourcesTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.listSources.mockResolvedValue({
      catalog_revision: 2, active_revision_id: '', source_count: 1, pending_count: 1, sources: [source],
    })
    api.planSourceChanges.mockResolvedValue({
      catalog_revision: 2, active_revision_id: '', desired_source_count: 1, ready: true, blockers: [],
        changes: { added: [source.source_id], updated: [], replaced: [], retired: [], unchanged: [] },
    })
    api.updateSource.mockResolvedValue({ source })
    api.buildSourceChanges.mockResolvedValue({ revision_id: 'src-one', job: { job_id: 'job-one' } })
  })

  it('shows source metadata and opens a human-readable change plan', async () => {
    const wrapper = mount(SourcesTab)
    await flushPromises()

    expect(wrapper.text()).toContain('GB 50000-2026')
    expect(wrapper.text()).toContain('测试规范')
    expect(wrapper.text()).toContain('待新增')
    expect(wrapper.get('tbody tr').attributes('tabindex')).toBe('0')
    expect(wrapper.get('tbody tr').attributes('aria-selected')).toBe('true')

    await wrapper.get('button.btn-primary').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('确认来源变更')
    expect(wrapper.text()).toContain('新增 1')
    expect(wrapper.text()).toContain('只有检索与结构化门禁通过后才会切换在线版本')
  })

  it('saves edited metadata through the management API', async () => {
    const wrapper = mount(SourcesTab)
    await flushPromises()
    const nameInput = wrapper.findAll('input').find(input => input.element.value === '测试规范')
    expect(nameInput).toBeTruthy()
    await nameInput!.setValue('修订后的测试规范')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(api.updateSource).toHaveBeenCalledWith(
      source.source_id,
      expect.objectContaining({ metadata: expect.objectContaining({ name: '修订后的测试规范' }) }),
    )
  })
})
