/**
 * SearchOverlay 共享状态(D1/D2)
 * Header 按钮与全局 ⌘K 都触发同一个弹层;记录触发元素用于关闭时归还焦点(a11y)。
 */
import { ref } from 'vue'

const open = ref(false)
/** @type {import('vue').Ref<HTMLElement | null>} */
const triggerEl = ref(null)

export function useSearchOverlay() {
  /**
   * @param {HTMLElement | null} [source] 触发元素(关闭时焦点归还目标)
   */
  function openOverlay(source = null) {
    if (source instanceof HTMLElement) triggerEl.value = source
    open.value = true
  }

  function closeOverlay() {
    open.value = false
    const el = triggerEl.value
    triggerEl.value = null
    if (el && document.contains(el)) el.focus?.()
  }

  return { open, openOverlay, closeOverlay }
}

/** 最近浏览文章(localStorage 上限 8 条),Overlay 默认态展示 */
const RECENT_KEY = 'xcs:recent-articles'
const RECENT_LIMIT = 8

/**
 * @param {string} slug
 * @param {string} title
 */
export function recordRecentArticle(slug, title) {
  if (!slug || !title) return
  try {
    /** @type {Array<{slug:string,title:string}>} */
    let list = []
    try {
      list = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]')
    } catch (e) {
      list = []
    }
    list = list.filter((x) => x && x.slug !== slug)
    list.unshift({ slug, title })
    localStorage.setItem(RECENT_KEY, JSON.stringify(list.slice(0, RECENT_LIMIT)))
  } catch (e) {
    /* localStorage 不可用时静默 */
  }
}

/** @returns {Array<{slug:string,title:string}>} */
export function getRecentArticles() {
  try {
    const list = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]')
    return Array.isArray(list) ? list.filter((x) => x && x.slug && x.title) : []
  } catch (e) {
    return []
  }
}
