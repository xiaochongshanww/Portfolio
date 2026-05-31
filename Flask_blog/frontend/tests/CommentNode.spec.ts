import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CommentNode from '../src/components/CommentNode.vue'

describe('CommentNode', () => {
  const baseComment = {
    id: 1,
    content: 'This is a test comment',
    user_id: 1,
    author_name: 'Test User',
    created_at: '2024-01-01T00:00:00Z',
    children: [],
  }

  it('renders comment content', () => {
    const wrapper = mount(CommentNode, {
      props: { comment: baseComment },
      global: { stubs: ['el-avatar', 'el-button', 'el-input'] },
    })
    expect(wrapper.text()).toContain('This is a test comment')
    expect(wrapper.text()).toContain('Test User')
  })

  it('renders nested children', () => {
    const commentWithChild = {
      ...baseComment,
      children: [{
        id: 2,
        content: 'Nested reply',
        user_id: 2,
        author_name: 'Replier',
        created_at: '2024-01-01T01:00:00Z',
        children: [],
      }],
    }
    const wrapper = mount(CommentNode, {
      props: { comment: commentWithChild },
      global: { stubs: ['el-avatar', 'el-button', 'el-input'] },
    })
    expect(wrapper.text()).toContain('Nested reply')
    expect(wrapper.text()).toContain('Replier')
  })
})
