import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import About from '../src/views/About.vue'

describe('About', () => {
  it('renders the static about page', () => {
    const wrapper = mount(About, {
      global: {
        stubs: {
          'el-button': { template: '<button><slot /></button>' },
          'el-icon': true,
          'el-tag': { template: '<span><slot /></span>' },
        },
      },
    })
    expect(wrapper.find('.about-page').exists()).toBe(true)
    expect(wrapper.text().length).toBeGreaterThan(50)
  })
})
