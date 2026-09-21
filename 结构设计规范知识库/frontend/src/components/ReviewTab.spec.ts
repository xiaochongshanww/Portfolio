import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  getAdminPageImageObjectUrl,
  getCorrectionCandidateDetail,
  getDocumentElement,
} from '../admin-api'
import ReviewTab from './ReviewTab.vue'

const api = vi.hoisted(() => ({
  addApprovedCorrection: vi.fn(),
  getAdminPageImageObjectUrl: vi.fn(),
  getCorrectionCandidateDetail: vi.fn(),
  getDocumentElement: vi.fn(),
  promoteCorrections: vi.fn(),
  updateCorrectionCandidate: vi.fn(),
}))

vi.mock('../admin-api', () => api)

const candidateDocs = [{
  doc: 'GB 50009-2012_.建筑结构荷载规范',
  source_file: 'GB 50009-2012_建筑结构荷载规范.pdf',
  path: 'candidate.json',
  candidate_count: 1,
  pending_count: 1,
  approved_count: 0,
  rejected_count: 0,
}]

const pendingCandidate = {
  id: 'formula_error_231',
  review_status: 'pending',
  severity: 'medium',
  page: 42,
  element_index: 231,
  issue_type: 'formula_error',
  suggested_text: '办公楼楼面活荷载标准值为 2.0 kN/m²。',
  evidence: { reason: '原图单位使用上标 ²。' },
}

describe('ReviewTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('URL', { revokeObjectURL: vi.fn() })
    api.getCorrectionCandidateDetail.mockResolvedValue({ corrections: [pendingCandidate] })
    api.getDocumentElement.mockResolvedValue({ text: '办公楼楼面活荷载标准值为 2.0 kN/m2。' })
    api.getAdminPageImageObjectUrl.mockResolvedValue('blob:page-42')
    api.updateCorrectionCandidate.mockResolvedValue({ status: 'approved' })
    api.addApprovedCorrection.mockResolvedValue({})
    api.promoteCorrections.mockResolvedValue({})
  })

  it('在左栏展示候选，并提供 PDF 工具和最终修正文预览', async () => {
    const wrapper = mount(ReviewTab, { props: { candidateDocs } })
    await flushPromises()

    expect(wrapper.get('.review-candidate-list').text()).toContain('formula_error_231')
    expect(wrapper.get('.review-candidate-list').text()).toContain('公式识别')
    expect(wrapper.get('.review-candidate-list').text()).toContain('待审')
    expect(wrapper.get('[data-testid="pdf-zoom-in"]')).toBeTruthy()
    expect(wrapper.get('[data-testid="pdf-fit-width"]')).toBeTruthy()
    expect(wrapper.get('[data-testid="review-action-bar"]').text()).toContain('批准')
    expect(wrapper.get('.review-final-preview').text()).toContain('最终修正文预览')
    expect(wrapper.get('.review-final-preview').text()).toContain('2.0 kN/m²')
    expect(getCorrectionCandidateDetail).toHaveBeenCalledWith({ path: { doc: candidateDocs[0].doc } })
    expect(getDocumentElement).toHaveBeenCalledWith({ path: { doc: candidateDocs[0].doc, element_index: 231 } })
    expect(getAdminPageImageObjectUrl).toHaveBeenCalledWith({ path: { doc: candidateDocs[0].doc, page: 42 } })
  })

  it('没有待审项时给出可操作的空状态，并可切换查看已批准项', async () => {
    api.getCorrectionCandidateDetail.mockResolvedValue({
      corrections: [{ ...pendingCandidate, review_status: 'approved' }],
    })
    const docs = [{ ...candidateDocs[0], pending_count: 0, approved_count: 1 }]
    const wrapper = mount(ReviewTab, { props: { candidateDocs: docs } })
    await flushPromises()

    expect(wrapper.text()).toContain('当前文档没有待审候选')
    expect(wrapper.findAll('.review-candidate-item')).toHaveLength(0)

    await wrapper.get('#review-status-filter').setValue('approved')
    await flushPromises()

    expect(wrapper.findAll('.review-candidate-item')).toHaveLength(1)
    expect(wrapper.get('.review-candidate-list').text()).toContain('已批准')
  })
})
