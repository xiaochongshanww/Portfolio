import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const searchState = vi.hoisted(() => ({ fn: vi.fn() }))
const mocks = vi.hoisted(() => ({
  route: { query: {} as Record<string, string> },
  push: vi.fn(),
  replace: vi.fn(),
}))

vi.mock('../src/composables/useUnifiedSearch', () => ({
  unifiedSearch: (...a: unknown[]) => searchState.fn(...a),
}))
vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.push, replace: mocks.replace }),
}))

import SearchPage from '../src/views/SearchPage.vue'

const RESULTS = [
  { type: 'article', title: '深入理解 RAG', snippet: '检索与生成', meta: '文章 · AI 工程', href: '/article/rag' },
  { type: 'topic', title: 'AI 工程', snippet: 'RAG 与 Agent', meta: '专题 · 12 篇', href: '/topics/ai' },
  { type: 'project', title: 'RAG Playground', snippet: '实验项目', meta: '项目 · 实验', href: '/projects' },
]

function mountPage() {
  return mount(SearchPage, {
    global: { stubs: { 'el-skeleton': { template: '<div class="skel" />' } } },
  })
}

async function typeAndSearch(wrapper: ReturnType<typeof mountPage>, kw: string) {
  await wrapper.find('input').setValue(kw)
  // 触发防抖(B1:~300ms)
  await vi.advanceTimersByTimeAsync(350)
  await flushPromises()
}

describe('SearchPage(P1-B)', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mocks.route.query = {}
    mocks.replace.mockReset()
    mocks.push.mockReset()
    searchState.fn.mockReset()
    searchState.fn.mockResolvedValue({
      results: RESULTS,
      counts: { all: 3, article: 1, topic: 1, project: 1 },
    })
  })
  afterEach(() => vi.useRealTimers())

  it('防抖触发搜索并渲染三类结果与过滤 chips(B1/B2)', async () => {
    const wrapper = mountPage()
    await typeAndSearch(wrapper, 'rag')
    expect(searchState.fn).toHaveBeenCalledWith('rag')
    expect(wrapper.findAll('.result').length).toBe(3)
    const chips = wrapper.findAll('.filters button').map((b) => b.text())
    expect(chips).toContain('全部')
    expect(chips).toContain('文章 1')
    expect(chips).toContain('专题 1')
    expect(chips).toContain('项目 1')
  })

  it('类型 chips 过滤结果(B4)', async () => {
    const wrapper = mountPage()
    await typeAndSearch(wrapper, 'rag')
    const chipTopic = wrapper.findAll('.filters button').find((b) => b.text().startsWith('专题'))!
    await chipTopic.trigger('click')
    expect(wrapper.findAll('.result').length).toBe(1)
    expect(wrapper.find('.result h2').text()).toBe('AI 工程')
  })

  it('命中词高亮为结构化 mark,多命中全标(B3)', async () => {
    const wrapper = mountPage()
    await typeAndSearch(wrapper, 'rag')
    const marks = wrapper.findAll('.result h2 .hit')
    expect(marks.length).toBeGreaterThanOrEqual(2)
    expect(marks[0].text().toLowerCase()).toBe('rag')
  })

  it('XSS 红线:注入关键词不产生任何元素(B3)', async () => {
    searchState.fn.mockResolvedValue({
      results: [
        {
          type: 'article',
          title: '前 <img onerror=alert(1)> 后',
          snippet: 'x <script>y</script>',
          meta: '文章',
          href: '/article/x',
        },
      ],
      counts: { all: 1, article: 1, topic: 0, project: 0 },
    })
    const wrapper = mountPage()
    await typeAndSearch(wrapper, '<img onerror=alert(1)>')
    // 渲染后的 DOM 中不出现注入元素:无 img、无 script
    expect(wrapper.findAll('img').length).toBe(0)
    expect(wrapper.findAll('script').length).toBe(0)
    expect(wrapper.find('.result h2').text()).toContain('<img onerror=alert(1)>')
  })

  it('ESC 清空输入且不发请求(B1)', async () => {
    const wrapper = mountPage()
    const input = wrapper.find('input')
    await input.setValue('temp')
    await input.trigger('keydown.esc')
    expect((input.element as HTMLInputElement).value).toBe('')
    expect(searchState.fn).not.toHaveBeenCalled()
  })

  it('空态含引导文案(B4)', async () => {
    searchState.fn.mockResolvedValue({ results: [], counts: { all: 0, article: 0, topic: 0, project: 0 } })
    const wrapper = mountPage()
    await typeAndSearch(wrapper, '不存在的词')
    expect(wrapper.text()).toContain('没有找到与“不存在的词”相关的内容')
    expect(wrapper.text()).toContain('换个关键词')
  })

  it('搜索成功后同步 ?q=(B1)', async () => {
    const wrapper = mountPage()
    await typeAndSearch(wrapper, 'rag')
    expect(mocks.replace).toHaveBeenCalledWith({ query: { q: 'rag' } })
  })

  it('直链 ?q= 恢复搜索(B1)', async () => {
    mocks.route.query = { q: 'rag' }
    const wrapper = mountPage()
    await flushPromises()
    expect(searchState.fn).toHaveBeenCalledWith('rag')
    expect(wrapper.findAll('.result').length).toBe(3)
  })

  it('错误态可重试(B4)', async () => {
    searchState.fn.mockRejectedValue(new Error('boom'))
    const wrapper = mountPage()
    await typeAndSearch(wrapper, 'rag')
    expect(wrapper.text()).toContain('搜索失败')
    searchState.fn.mockResolvedValue({ results: RESULTS, counts: { all: 3, article: 1, topic: 1, project: 1 } })
    await wrapper.find('.retry-btn').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('.result').length).toBe(3)
  })
})
