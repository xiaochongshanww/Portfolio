import { mount, type VueWrapper } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import EvaluationCaseEditor from './EvaluationCaseEditor.vue'

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

describe('EvaluationCaseEditor', () => {
  it('uses a structured form by default and preserves compatible extension fields', async () => {
    const wrapper = mount(EvaluationCaseEditor, {
      props: {
        evaluationSetId: 'regular',
        mode: 'edit',
        modelValue: {
          id: 'load-live-value',
          query: '原问题',
          type: 'table',
          expected_sources: ['GB 50009-2012'],
          expected_keywords: ['活荷载'],
          expected_clause: '5.1.1',
          expected_authority_type: 'table',
          expected_table_id: '5.1.1',
          top1_source_required: true,
          keyword_required: true,
          custom_note: '保留字段',
        },
      },
    })

    expect(wrapper.find('textarea[aria-label="评估用例 JSON"]').exists()).toBe(false)
    await findLabelControl(wrapper, '问题', 'textarea').setValue('办公楼楼面活荷载取多少？')
    await findButton(wrapper, '保存用例').trigger('click')

    expect(wrapper.emitted('save')?.[0]?.[0]).toEqual(expect.objectContaining({
      id: 'load-live-value',
      query: '办公楼楼面活荷载取多少？',
      type: 'table',
      expected_sources: ['GB 50009-2012'],
      expected_keywords: ['活荷载'],
      expected_clause: '5.1.1',
      custom_note: '保留字段',
    }))
  })

  it('keeps raw JSON as an advanced mode and reports malformed input locally', async () => {
    const wrapper = mount(EvaluationCaseEditor, {
      props: {
        evaluationSetId: 'structured',
        mode: 'edit',
        modelValue: { id: 'table-001', query: '查询复杂表', type: 'structured_table', expected_table_id: '7.2.10' },
      },
    })

    await findButton(wrapper, '高级 JSON').trigger('click')
    const editor = wrapper.get('textarea[aria-label="评估用例 JSON"]')
    await editor.setValue('{ invalid json')
    await findButton(wrapper, '保存用例').trigger('click')
    expect(wrapper.get('[role="alert"]').text()).toContain('JSON')
    expect(wrapper.emitted('save')).toBeUndefined()

    await editor.setValue(JSON.stringify({ id: 'table-001', query: '修正后的复杂表问题', type: 'structured_table', expected_table_id: '7.2.10' }))
    await findButton(wrapper, '保存用例').trigger('click')
    expect(wrapper.emitted('save')?.[0]?.[0]).toEqual(expect.objectContaining({ query: '修正后的复杂表问题' }))
  })

  it('maps answer expectations into grouped fields without retrieval-only fields', async () => {
    const wrapper = mount(EvaluationCaseEditor, {
      props: {
        evaluationSetId: 'answer',
        mode: 'create',
        modelValue: { id: '', query: '', type: 'direct_value', requires_image: true },
      },
    })

    await findLabelControl(wrapper, '用例 ID', 'input').setValue('answer-001')
    await findLabelControl(wrapper, '问题', 'textarea').setValue('标准值是多少？')
    await findLabelControl(wrapper, '必须包含', 'textarea').setValue('2.0 kN/m²\nGB 50009-2012')
    await findLabelControl(wrapper, '任选命中组', 'textarea').setValue('表5.1.1 | 第5.1.1条')
    await findButton(wrapper, '新增用例').trigger('click')

    expect(wrapper.emitted('save')?.[0]?.[0]).toEqual(expect.objectContaining({
      id: 'answer-001',
      expected_all: ['2.0 kN/m²', 'GB 50009-2012'],
      expected_any_groups: [['表5.1.1', '第5.1.1条']],
      requires_image: true,
    }))
    expect(wrapper.emitted('save')?.[0]?.[0]).not.toHaveProperty('expected_sources')
  })
})
