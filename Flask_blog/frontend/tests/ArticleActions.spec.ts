import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ArticleActions from '../src/components/ArticleActions.vue'

const buttonStub = { template: '<button><slot /></button>' }

function mountActions(props: any) {
  return mount(ArticleActions, {
    props: {
      isModerator: true,
      nextList: [],
      canSchedule: false,
      canUnschedule: false,
      canUnpublish: false,
      acting: false,
      canOperate: () => true,
      ...props,
    },
    global: { stubs: { 'el-button': buttonStub } },
  })
}

describe('ArticleActions', () => {
  it('renders nothing for non-moderator', () => {
    const wrapper = mountActions({ isModerator: false })
    expect(wrapper.find('.admin-actions').exists()).toBe(false)
  })

  it('renders next transition buttons with labels', () => {
    const wrapper = mountActions({ nextList: ['approve', 'reject'] })
    const text = wrapper.text()
    expect(text).toContain('approve')
    expect(text).toContain('reject')
  })

  it('renders schedule/unschedule/unpublish buttons when enabled', () => {
    const wrapper = mountActions({
      canSchedule: true,
      canUnschedule: true,
      canUnpublish: true,
    })
    const text = wrapper.text()
    expect(text).toContain('定时发布')
    expect(text).toContain('取消定时')
    expect(text).toContain('下线')
  })

  it('renders nothing when no actions available', () => {
    const wrapper = mountActions({ nextList: [] })
    expect(wrapper.find('.admin-actions').exists()).toBe(false)
  })

  it('emits transition on button click', async () => {
    const wrapper = mountActions({ nextList: ['approve'] })
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('transition')).toBeTruthy()
    expect(wrapper.emitted('transition')![0]).toEqual(['approve'])
  })
})
