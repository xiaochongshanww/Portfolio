import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import EvaluationSetsTab from './EvaluationSetsTab.vue'

const api = vi.hoisted(() => ({
  addAdminEvaluationCase: vi.fn(),
  createAdminEvaluationDraft: vi.fn(),
  deleteAdminEvaluationCase: vi.fn(),
  getAdminEvaluationDiff: vi.fn(),
  getAdminEvaluationSet: vi.fn(),
  listAdminEvaluationRevisions: vi.fn(),
  listAdminEvaluationSets: vi.fn(),
  publishAdminEvaluationDraft: vi.fn(),
  rollbackAdminEvaluationSet: vi.fn(),
  updateAdminEvaluationCase: vi.fn(),
  validateAdminEvaluationDraft: vi.fn(),
}))

vi.mock('../admin-api', () => api)
vi.mock('../api', () => ({ errorMessage: (error: unknown) => String(error) }))

const published = {
  revision_id: 'builtin-test',
  evaluation_set_id: 'regular' as const,
  name: '常规检索评估',
  status: 'published',
  case_count: 100,
  type_counts: { table: 100 },
  content_hash: 'hash',
  schema_version: '1',
  created_at: '2026-08-30T00:00:00Z',
  published_at: '2026-08-30T00:00:00Z',
  created_by: 'builtin',
  parent_revision_id: null,
  source: 'builtin',
  validation_summary: null,
}

const firstCase = {
  id: 'case-001',
  query: '办公楼楼面活荷载取多少？',
  type: 'table',
  expected_sources: ['GB 50009-2012'],
  expected_clause: '5.1.1',
  expected_keywords: ['活荷载'],
  expected_authority_type: 'table',
  top1_source_required: true,
  keyword_required: true,
  expected_table_id: '5.1.1',
}

function draftRevision(validated: boolean) {
  return {
    ...published,
    revision_id: 'draft',
    source: 'draft',
    status: 'draft',
    validation_summary: validated
      ? { ok: true, errors: [], warnings: [], content_hash: 'hash', case_count: 100 }
      : null,
  }
}

function detail(hasDraft: boolean, validated: boolean) {
  return {
    evaluation_set_id: 'regular' as const,
    name: '常规检索评估',
    kind: 'retrieval' as const,
    published_revision: published,
    draft: hasDraft ? draftRevision(validated) : null,
    case_count: 100,
    type_counts: { table: 100 },
    cases: [firstCase],
    draft_cases: hasDraft ? [firstCase] : [],
  }
}

function findButton(wrapper: VueWrapper, label: string) {
  const match = wrapper.findAll('button').find(item => item.text().trim() === label)
  if (!match) throw new Error(`Button not found: ${label}`)
  return match
}

function findLabelControl(wrapper: VueWrapper, label: string, selector: string) {
  const match = wrapper.findAll('label').find(item => item.text().trim().startsWith(label))
  if (!match) throw new Error(`Label not found: ${label}`)
  return match.get(selector)
}

describe('EvaluationSetsTab', () => {
  let hasDraft = false
  let validated = false

  beforeEach(() => {
    vi.clearAllMocks()
    hasDraft = false
    validated = false
    api.listAdminEvaluationSets.mockImplementation(async () => ({
      sets: [
        {
          evaluation_set_id: 'regular',
          name: '常规检索评估',
          kind: 'retrieval',
          published_revision: published,
          draft: hasDraft ? draftRevision(validated) : null,
          case_count: 100,
          updated_at: '2026-08-30T00:00:00Z',
        },
        {
          evaluation_set_id: 'structured',
          name: '结构化专项评估',
          kind: 'retrieval',
          published_revision: { ...published, evaluation_set_id: 'structured', name: '结构化专项评估', case_count: 12 },
          draft: null,
          case_count: 12,
          updated_at: '2026-08-30T00:00:00Z',
        },
        {
          evaluation_set_id: 'answer',
          name: '回答级盲测',
          kind: 'answer',
          published_revision: { ...published, evaluation_set_id: 'answer', name: '回答级盲测', case_count: 24 },
          draft: null,
          case_count: 24,
          updated_at: '2026-08-30T00:00:00Z',
        },
      ],
    }))
    api.getAdminEvaluationSet.mockImplementation(async () => detail(hasDraft, validated))
    api.listAdminEvaluationRevisions.mockResolvedValue({ revisions: [published] })
    api.createAdminEvaluationDraft.mockImplementation(async () => {
      hasDraft = true
      return { evaluation_set_id: 'regular', draft_status: 'draft', draft: draftRevision(false), case_count: 100, type_counts: { table: 100 }, cases: [firstCase] }
    })
    api.addAdminEvaluationCase.mockResolvedValue({})
    api.updateAdminEvaluationCase.mockResolvedValue({})
    api.deleteAdminEvaluationCase.mockResolvedValue({})
    api.validateAdminEvaluationDraft.mockImplementation(async () => {
      validated = true
      return { evaluation_set_id: 'regular', draft_status: 'validated', validation: { ok: true, errors: [], warnings: [], content_hash: 'hash', case_count: 100 } }
    })
    api.getAdminEvaluationDiff.mockResolvedValue({
      evaluation_set_id: 'regular',
      base_revision_id: 'builtin-test',
      draft_content_hash: 'hash',
      added: [],
      modified: [{ id: 'case-001', before: firstCase, after: { ...firstCase, query: '修改后的问题' } }],
      removed: [],
      changed_count: 1,
    })
  })

  async function mountWorkspace() {
    const wrapper = mount(EvaluationSetsTab)
    await flushPromises()
    await findButton(wrapper, '打开').trigger('click')
    await flushPromises()
    return wrapper
  }

  it('starts from an evaluation set catalog instead of exposing the whole lifecycle', async () => {
    const wrapper = mount(EvaluationSetsTab)
    await flushPromises()

    expect(wrapper.text()).toContain('常规检索评估')
    expect(wrapper.text()).toContain('结构化专项评估')
    expect(wrapper.text()).toContain('回答级盲测')
    expect(wrapper.text()).toContain('验证最终问答、引用截图和无依据拒答行为')
    expect(wrapper.text()).toContain('100 条已发布用例')
    expect(wrapper.find('[role="tablist"]').exists()).toBe(false)
    expect(api.getAdminEvaluationSet).not.toHaveBeenCalled()
  })

  it('opens one set as a focused workspace and keeps quality validation separate', async () => {
    const wrapper = await mountWorkspace()

    expect(wrapper.findAll('[role="tab"]').map(tab => tab.text())).toEqual(expect.arrayContaining(['用例 1', '版本记录', '发布']))
    expect(wrapper.text()).toContain('当前显示已发布内容；开始编辑后才能修改。')
    expect(wrapper.find('textarea[aria-label="评估用例 JSON"]').exists()).toBe(false)

    await findButton(wrapper, '前往质量验证').trigger('click')
    expect(wrapper.emitted('navigate')).toEqual([['evaluation']])
  })

  it('creates a draft and edits a case through the structured form', async () => {
    const wrapper = await mountWorkspace()

    await findButton(wrapper, '开始编辑').trigger('click')
    await flushPromises()
    expect(api.createAdminEvaluationDraft).toHaveBeenCalledWith({ path: { evaluation_set_id: 'regular' }, body: undefined })

    await findButton(wrapper, '编辑').trigger('click')
    expect(wrapper.text()).toContain('表单编辑')
    expect(wrapper.find('textarea[aria-label="评估用例 JSON"]').exists()).toBe(false)
    await findLabelControl(wrapper, '问题', 'textarea').setValue('修改后的问题')
    await findButton(wrapper, '保存用例').trigger('click')
    await flushPromises()

    expect(api.updateAdminEvaluationCase).toHaveBeenCalledWith({
      path: { evaluation_set_id: 'regular', case_id: 'case-001' },
      body: { case: { ...firstCase, query: '修改后的问题' } },
    })
    expect(wrapper.text()).toContain('用例已保存，请在发布页重新检查修改。')
  })

  it('supports adding and deleting draft cases without exposing raw JSON', async () => {
    const wrapper = await mountWorkspace()
    await findButton(wrapper, '开始编辑').trigger('click')
    await flushPromises()

    await findButton(wrapper, '新增用例').trigger('click')
    await findLabelControl(wrapper, '用例 ID', 'input').setValue('case-new')
    await findLabelControl(wrapper, '问题', 'textarea').setValue('新增问题')
    await findButton(wrapper, '新增用例').trigger('click')
    await flushPromises()
    expect(api.addAdminEvaluationCase).toHaveBeenCalledWith(expect.objectContaining({
      path: { evaluation_set_id: 'regular' },
      body: { case: expect.objectContaining({ id: 'case-new', query: '新增问题', type: 'general' }) },
    }))

    await findButton(wrapper, '编辑').trigger('click')
    await findButton(wrapper, '删除用例').trigger('click')
    expect(wrapper.get('[role="dialog"]').text()).toContain('确认从未发布修改中删除用例“case-001”')
    await findButton(wrapper, '确认删除').trigger('click')
    await flushPromises()
    expect(api.deleteAdminEvaluationCase).toHaveBeenCalledWith({ path: { evaluation_set_id: 'regular', case_id: 'case-001' } })
  })

  it('keeps revision history independent and requires confirmation for rollback', async () => {
    const historical = { ...published, revision_id: 'revision-old', source: 'managed', created_at: '2026-08-29T00:00:00Z', published_at: '2026-08-29T00:00:00Z' }
    api.listAdminEvaluationRevisions.mockResolvedValue({ revisions: [published, historical] })
    api.rollbackAdminEvaluationSet.mockResolvedValue({ affected_report_types: ['regular'] })
    const wrapper = await mountWorkspace()

    await findButton(wrapper, '版本记录').trigger('click')
    expect(wrapper.text()).toContain('每次发布都会保留一个历史版本')
    expect(wrapper.text()).toContain('版本 2026-08-29')
    const rollback = wrapper.findAll('button').find(item => item.text() === '恢复为当前版本' && item.attributes('disabled') === undefined)
    expect(rollback).toBeTruthy()
    await rollback!.trigger('click')
    await findButton(wrapper, '确认恢复').trigger('click')
    await flushPromises()

    expect(api.rollbackAdminEvaluationSet).toHaveBeenCalledWith({
      path: { evaluation_set_id: 'regular' },
      body: { revision_id: 'revision-old' },
    })
    expect(wrapper.text()).toContain('请在质量验证中心重新运行 常规检索评估')
  })

  it('groups difference review, validation and publishing inside the publish tab', async () => {
    api.publishAdminEvaluationDraft.mockImplementation(async () => {
      hasDraft = false
      return { affected_report_types: ['regular'] }
    })
    const wrapper = await mountWorkspace()
    await findButton(wrapper, '开始编辑').trigger('click')
    await flushPromises()
    await findButton(wrapper, '发布').trigger('click')

    expect(wrapper.text()).toContain('未发布修改')
    expect(wrapper.text()).toContain('发布检查')
    await findButton(wrapper, '检查修改').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('检查通过')
    await findButton(wrapper, '查看修改内容').trigger('click')
    await flushPromises()
    expect(findButton(wrapper, '发布修改').attributes('disabled')).toBeUndefined()

    await findButton(wrapper, '发布修改').trigger('click')
    expect(wrapper.get('[role="dialog"]').text()).toContain('新的正式版本')
    await findButton(wrapper, '确认发布').trigger('click')
    await flushPromises()

    expect(api.publishAdminEvaluationDraft).toHaveBeenCalledWith({ path: { evaluation_set_id: 'regular' } })
    expect(wrapper.text()).toContain('请在质量验证中心重新运行 常规检索评估')
  })

  it('preserves reviewed differences when validation refreshes unchanged content', async () => {
    const wrapper = await mountWorkspace()
    await findButton(wrapper, '开始编辑').trigger('click')
    await flushPromises()
    await findButton(wrapper, '发布').trigger('click')
    await findButton(wrapper, '查看修改内容').trigger('click')
    await flushPromises()
    expect(findButton(wrapper, '发布修改').attributes('disabled')).toBeDefined()

    await findButton(wrapper, '检查修改').trigger('click')
    await flushPromises()
    expect(findButton(wrapper, '发布修改').attributes('disabled')).toBeUndefined()
    expect(findButton(wrapper, '刷新修改内容').exists()).toBe(true)
  })

  it.each(['draft', 'base'])('invalidates reviewed differences when the %s content changes', async (changed) => {
    const wrapper = await mountWorkspace()
    await findButton(wrapper, '开始编辑').trigger('click')
    await flushPromises()
    await findButton(wrapper, '发布').trigger('click')
    await findButton(wrapper, '查看修改内容').trigger('click')
    await flushPromises()
    api.getAdminEvaluationSet.mockImplementation(async () => {
      const response = detail(true, true)
      if (changed === 'draft') response.draft = { ...draftRevision(true), content_hash: 'changed' }
      else response.published_revision = { ...published, revision_id: 'new-base', content_hash: 'changed' }
      return response
    })

    await findButton(wrapper, '检查修改').trigger('click')
    await flushPromises()
    expect(findButton(wrapper, '发布修改').attributes('disabled')).toBeDefined()
    expect(findButton(wrapper, '查看修改内容').exists()).toBe(true)
    expect(api.publishAdminEvaluationDraft).not.toHaveBeenCalled()
  })

  it('shows catalog load failures as a user-facing state', async () => {
    api.listAdminEvaluationSets.mockRejectedValueOnce(new Error('加载失败'))
    const wrapper = mount(EvaluationSetsTab)
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('加载失败')
  })
})
