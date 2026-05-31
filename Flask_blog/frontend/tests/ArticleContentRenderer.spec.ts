import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ArticleContentRenderer from '../src/components/ArticleContentRenderer.vue'

// Mock katex which has ESM/CJS compatibility issues in test
import { vi } from 'vitest'
vi.mock('katex', () => ({
  default: { renderToString: (s: string) => s },
  renderToString: (s: string) => s,
}))

describe('ArticleContentRenderer', () => {
  it('renders HTML content', () => {
    const wrapper = mount(ArticleContentRenderer, {
      props: {
        content: '<h1>Hello</h1><p>Test content</p>',
      },
      global: {
        stubs: {
          'el-backtop': true,
        },
      },
    })
    expect(wrapper.html()).toContain('Hello')
    expect(wrapper.html()).toContain('Test content')
  })

  it('renders empty content gracefully', () => {
    const wrapper = mount(ArticleContentRenderer, {
      props: { content: '' },
      global: { stubs: { 'el-backtop': true } },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('sanitizes dangerous HTML', () => {
    const wrapper = mount(ArticleContentRenderer, {
      props: {
        content: '<script>alert("xss")</script><p>Safe</p>',
      },
      global: { stubs: { 'el-backtop': true } },
    })
    // DOMPurify should strip the script tag
    expect(wrapper.html()).not.toContain('<script>')
    expect(wrapper.html()).toContain('Safe')
  })
})
