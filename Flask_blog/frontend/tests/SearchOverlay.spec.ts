import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const searchState = vi.hoisted(() => ({ fn: vi.fn() }))
const mocks = vi.hoisted(() => ({
  route: { query: {} },
  push: vi.fn(),
  replace: vi.fn(),
}))

vi.mock('../src/composables/useUnifiedSearch', () => ({
  unifiedSearch: (...a: unknown[]) => searchState.fn(...a),
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mocks.push, replace: mocks.replace }),
}))

import SearchOverlay from '../src/components/public/SearchOverlay.vue'
import { useSearchOverlay, recordRecentArticle } from '../src/composables/useSearchOverlay'

const RESULTS = [
  { type: 'article', title: '文章 A', snippet: 'sa', meta: '文章 · AI', href: '/article/a' },
  { type: 'topic', title: '专题 T', snippet: 'st', meta: '专题 · 3 篇', href: '/topics/t' },
]

function mountOverlay() {
  // stub teleport:弹层渲染在 wrapper 内,便于断言
  return mount(SearchOverlay, {
    global: { stubs: { teleport: true } },
  })
}

async function openViaHotkey() {
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))
  await flushPromises()
}

describe('SearchOverlay(P2-D1/D2)', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    searchState.fn.mockReset()
    searchState.fn.mockResolvedValue({ results: RESULTS, counts: { all: 2, article: 1, topic: 1, project: 0 } })
    localStorage.clear()
    // 复位模块级单例(上一用例可能残留 open 态)
    useSearchOverlay().closeOverlay()
  })
  afterEach(() => {
    vi.useRealTimers()
    document.body.style.overflow = ''
  })

  it('全局 Ctrl+K 唤起弹层', async () => {
    const wrapper = mountOverlay()
    await openViaHotkey()
    expect(wrapper.find('.so-panel').exists()).toBe(true)
  })

  it('打开时锁定 body 滚动,关闭恢复', async () => {
    const wrapper = mountOverlay()
    await openViaHotkey()
    expect(document.body.style.overflow).toBe('hidden')
    const { closeOverlay } = useSearchOverlay()
    closeOverlay()
    await flushPromises()
    expect(document.body.style.overflow).toBe('')
  })

  it('默认态展示最近浏览与推荐词', async () => {
    recordRecentArticle('a', '最近看过的文章')
    const wrapper = mountOverlay()
    await openViaHotkey()
    expect(wrapper.text()).toContain('最近浏览')
    expect(wrapper.text()).toContain('最近看过的文章')
    expect(wrapper.findAll('.so-chip').length).toBeGreaterThan(0)
  })

  it('输入触发搜索并按类型分组展示', async () => {
    const wrapper = mountOverlay()
    await openViaHotkey()
    await wrapper.find('input').setValue('rag')
    await vi.advanceTimersByTimeAsync(350)
    await flushPromises()
    const labels = wrapper.findAll('.so-group-label').map((n) => n.text())
    expect(labels).toContain('文章')
    expect(labels).toContain('专题')
    expect(wrapper.findAll('.so-item').length).toBe(2)
  })

  it('方向键移动选中项,Enter 导航并关闭', async () => {
    const wrapper = mountOverlay()
    await openViaHotkey()
    await wrapper.find('input').setValue('rag')
    await vi.advanceTimersByTimeAsync(350)
    await flushPromises()
    const input = wrapper.find('input')
    await input.trigger('keydown.down')
    const active = wrapper.findAll('.so-item').filter((i) => i.classes('active'))
    expect(active.length).toBe(1)
    expect(active[0].text()).toContain('专题 T')
    await input.trigger('keydown.enter')
    expect(mocks.push).toHaveBeenCalledWith('/topics/t')
    expect(wrapper.find('.so-panel').exists()).toBe(false)
  })

  it('ESC 关闭弹层', async () => {
    const wrapper = mountOverlay()
    await openViaHotkey()
    await wrapper.find('input').trigger('keydown.esc')
    await flushPromises()
    expect(wrapper.find('.so-panel').exists()).toBe(false)
  })

  it('backdrop 点击关闭', async () => {
    const wrapper = mountOverlay()
    await openViaHotkey()
    await wrapper.find('.so-backdrop').trigger('click')
    await flushPromises()
    expect(wrapper.find('.so-panel').exists()).toBe(false)
  })

  it('点击推荐词填入输入框并发起搜索', async () => {
    const wrapper = mountOverlay()
    await openViaHotkey()
    const chip = wrapper.findAll('.so-chip')[0]
    await chip.trigger('click')
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(chip.text())
    await vi.advanceTimersByTimeAsync(350)
    await flushPromises()
    expect(searchState.fn).toHaveBeenCalled()
  })
})
