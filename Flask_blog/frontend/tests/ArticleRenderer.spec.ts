import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ArticleRenderer from '../src/components/article/ArticleRenderer.vue'

const stubs = {
  // BlockShell 用真实实现即可,无需 stub
}

function makeBlocks(types) {
  return types.map((type, i) => ({
    id: `b${i}`,
    type,
    width: undefined,
    ...(type === 'paragraph' ? { html: '段落内容' } : {}),
    ...(type === 'heading' ? { level: 2, text: '标题', anchor: '标题' } : {}),
    ...(type === 'list' ? { ordered: false, items: [{ html: '项' }] } : {}),
    ...(type === 'quote' ? { html: '引用', cite: '出处' } : {}),
    ...(type === 'callout' ? { tone: 'note', title: '提示', html: '内容' } : {}),
    ...(type === 'code' ? { language: 'python', code: 'print(1)' } : {}),
    ...(type === 'image' ? { src: '/x.png', alt: '图', caption: '图注' } : {}),
    ...(type === 'table' ? { head: ['A'], rows: [['1']] } : {}),
  }))
}

describe('ArticleRenderer', () => {
  it('renders all eight P0 block types', () => {
    const blocks = makeBlocks([
      'paragraph', 'heading', 'list', 'quote',
      'callout', 'code', 'image', 'table',
    ])
    const wrapper = mount(ArticleRenderer, {
      props: { blocks },
      global: { stubs },
    })
    expect(wrapper.findAll('.block-shell').length).toBe(8)
  })

  it('falls back for unimplemented block types (gallery/embed/media...)', () => {
    const blocks = makeBlocks(['gallery', 'embed'])
    const wrapper = mount(ArticleRenderer, { props: { blocks } })
    expect(wrapper.findAll('.fallback-block').length).toBeGreaterThanOrEqual(1)
  })

  it('applies content-width class from block.width or type default', () => {
    const blocks = [
      { id: 'p1', type: 'paragraph', html: 'x' },            // default text
      { id: 'c1', type: 'code', language: 'py', code: 'x' }, // default code
      { id: 't1', type: 'table', head: [], rows: [] },       // default wide
    ]
    const wrapper = mount(ArticleRenderer, { props: { blocks } })
    expect(wrapper.find('.content-width-text').exists()).toBe(true)
    expect(wrapper.find('.content-width-code').exists()).toBe(true)
    expect(wrapper.find('.content-width-wide').exists()).toBe(true)
  })

  it('renders legacy markdown-compatible heading with anchor id', () => {
    const blocks = [{ id: 'h', type: 'heading', level: 2, text: '基础', anchor: '基础' }]
    const wrapper = mount(ArticleRenderer, { props: { blocks } })
    expect(wrapper.find('#基础').exists()).toBe(true)
  })
})
