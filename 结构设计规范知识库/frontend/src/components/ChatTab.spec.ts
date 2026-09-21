import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ChatTab from './ChatTab.vue'

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('ChatTab', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('renders Markdown citation images instead of exposing the raw path', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({
      choices: [{ message: { content: '依据如下：\n\n![第214页](/images/page-214.png)\n\n**2.0 kN/m²**' } }],
    })))

    const wrapper = mount(ChatTab)
    const input = wrapper.get('input[aria-label="验证问题"]')
    await input.setValue('办公楼楼面活荷载标准值取多少？')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const image = wrapper.get('.answer-preview img')
    expect(image.attributes('src')).toBe('/images/page-214.png')
    expect(wrapper.find('.answer-preview').text()).toContain('2.0 kN/m²')
    expect(wrapper.find('.answer-preview').text()).not.toContain('![第214页]')
  })
})
