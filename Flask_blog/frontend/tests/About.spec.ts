import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import About from '../src/views/About.vue'
import {
  ABOUT_HEADLINE,
  ABOUT_NARRATIVE,
  ABOUT_NOW,
  ABOUT_TIMELINE,
} from '../src/data/aboutNow'

describe('About(P2-C1)', () => {
  const wrapper = mount(About)

  it('渲染叙事标题与三段文案', () => {
    expect(wrapper.find('.about-copy h1').text()).toBe(ABOUT_HEADLINE)
    const paras = wrapper.findAll('.about-copy p')
    expect(paras.length).toBe(ABOUT_NARRATIVE.length)
    expect(paras[0].text()).toBe(ABOUT_NARRATIVE[0])
  })

  it('「现在」侧栏渲染配置项', () => {
    const notes = wrapper.findAll('.note')
    expect(notes.length).toBe(ABOUT_NOW.length)
    expect(notes[0].find('b').text()).toBe('正在写')
  })

  it('时间线行数 ≤5', () => {
    const rows = wrapper.findAll('.timeline-row')
    expect(rows.length).toBeLessThanOrEqual(5)
    expect(rows.length).toBe(ABOUT_TIMELINE.length)
  })

  it('反履历粗校验:不含履历式关键词', () => {
    const text = wrapper.text()
    for (const banned of ['毕业', '学校', '大学', '公司', '岁', '%']) {
      expect(text).not.toContain(banned)
    }
  })
})
