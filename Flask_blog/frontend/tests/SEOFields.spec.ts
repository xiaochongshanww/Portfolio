import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SEOFields from '../src/components/SEOFields.vue'

function mountSeo(props: any = {}) {
  return mount(SEOFields, {
    props: { seoTitle: 't', seoDesc: 'd', ...props },
    global: {
      stubs: {
        'el-form-item': { template: '<div class="form-item"><slot /></div>' },
        'el-input': { template: '<input class="seo-input" />' },
        'el-icon': true,
      },
    },
  })
}

describe('SEOFields', () => {
  it('renders two input fields', () => {
    const wrapper = mountSeo()
    expect(wrapper.findAll('.seo-input').length).toBe(2)
  })

  it('reflects provided seoTitle and seoDesc props', () => {
    const wrapper = mountSeo({ seoTitle: 'my title', seoDesc: 'my desc' })
    expect(wrapper.props('seoTitle')).toBe('my title')
    expect(wrapper.props('seoDesc')).toBe('my desc')
  })
})
