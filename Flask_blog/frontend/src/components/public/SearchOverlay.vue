<template>
  <Teleport to="body">
    <div v-if="open" class="so-backdrop" @click.self="closeOverlay()">
      <div class="so-panel" role="dialog" aria-modal="true" aria-label="站内搜索">
        <div class="so-input-row">
          <input
            ref="inputRef"
            v-model="q"
            type="text"
            placeholder="搜索文章、专题与项目…"
            aria-label="搜索文章、专题与项目"
            @keydown.enter.prevent="goActive"
            @keydown.esc.prevent="closeOverlay()"
            @keydown.down.prevent="move(1)"
            @keydown.up.prevent="move(-1)"
          >
          <span class="so-key">ESC</span>
        </div>

        <div class="so-body">
          <!-- loading -->
          <div v-if="searching" class="so-hint">搜索中…</div>

          <!-- 默认态:最近浏览 + 推荐词 -->
          <template v-else-if="!q.trim()">
            <template v-if="recent.length">
              <div class="so-group-label">最近浏览</div>
              <button
                v-for="(item, i) in recentItems"
                :key="'r-' + item.slug"
                type="button"
                class="so-item"
                :class="{ active: activeIndex === i }"
                @mouseenter="activeIndex = i"
                @click="go(item.href)"
              >
                <span class="so-item-title">{{ item.title }}</span>
                <span class="so-item-meta">文章</span>
              </button>
            </template>
            <div class="so-group-label">试试搜索</div>
            <div class="so-suggest">
              <button
                v-for="w in SUGGESTED"
                :key="w"
                type="button"
                class="so-chip"
                @click="useWord(w)"
              >{{ w }}</button>
            </div>
          </template>

          <!-- 结果态:按类型分组 -->
          <template v-else-if="flatResults.length">
            <div v-for="g in groupedResults" :key="g.label" class="so-group">
              <div class="so-group-label">{{ g.label }}</div>
              <button
                v-for="item in g.items"
                :key="item.href + item.title"
                type="button"
                class="so-item"
                :class="{ active: activeIndex === flatIndexOf(item) }"
                @mouseenter="activeIndex = flatIndexOf(item)"
                @click="go(item.href)"
              >
                <span class="so-item-title">{{ item.title }}</span>
                <span class="so-item-meta">{{ item.meta }}</span>
              </button>
            </div>
          </template>

          <!-- 空结果 -->
          <div v-else class="so-hint">没有找到与“{{ q.trim() }}”相关的内容。</div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
/**
 * ⌘K 全局搜索弹层(P2-D1)
 * - 快捷键 Ctrl/⌘+K 唤起,ESC/backdrop 关闭并归还焦点;
 * - 结果复用 P1 useUnifiedSearch,按 文章/专题/项目 分组;
 * - 打开期间锁定 body 滚动。
 */
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useSearchOverlay, getRecentArticles } from '../../composables/useSearchOverlay'
import { unifiedSearch } from '../../composables/useUnifiedSearch'

const SUGGESTED = ['RAG', '权限设计', 'Git Rebase', 'JWT']

/** @type {Record<string,string>} */
const TYPE_LABELS = { article: '文章', topic: '专题', project: '项目' }

export default {
  name: 'SearchOverlay',
  setup() {
    const router = useRouter()
    const { open, openOverlay, closeOverlay } = useSearchOverlay()

    /** @type {import('vue').Ref<HTMLInputElement | null>} */
    const inputRef = ref(null)
    const q = ref('')
    const searching = ref(false)
    /** @type {import('vue').Ref<Array<{type:string,title:string,snippet:string,meta:string,href:string}>>} */
    const results = ref([])
    /** @type {import('vue').Ref<Array<{slug:string,title:string}>>} */
    const recent = ref([])

    const recentItems = computed(() =>
      recent.value.map(
        /** @param {{slug:string,title:string}} r */
        (r) => ({ slug: r.slug, title: r.title, href: `/article/${r.slug}` }),
      ),
    )
    const flatResults = computed(() => results.value)

    const groupedResults = computed(() => {
      /** @type {Array<{label:string,items:typeof results.value}>} */
      const groups = []
      for (const type of ['article', 'topic', 'project']) {
        const items = results.value.filter((r) => r.type === type)
        if (items.length) groups.push({ label: TYPE_LABELS[type], items })
      }
      return groups
    })

    const activeIndex = ref(0)
    /** 键盘导航覆盖的扁平序列:无关键词时为最近浏览 */
    const navList = computed(() => (q.value.trim() ? flatResults.value : recentItems.value))

    /** @param {number} delta */
    function move(delta) {
      const n = navList.value.length
      if (!n) return
      activeIndex.value = (activeIndex.value + delta + n) % n
    }

    /** @param {{href:string}} item */
    /** @param {{href: string, title?: string}} item */
    function flatIndexOf(item) {
      return flatResults.value.findIndex(
        (r) => r.href === item.href && r.title === (item.title ?? r.title),
      )
    }

    function goActive() {
      const item = navList.value[activeIndex.value]
      if (item) go(item.href)
    }

    /** @param {string} href */
    function go(href) {
      if (!href) return
      closeOverlay()
      router.push(href)
    }

    /** @param {string} w */
    function useWord(w) {
      q.value = w
    }

    /** @type {ReturnType<typeof setTimeout> | null} */
    let timer = null
    watch(q, (kw) => {
      if (timer) clearTimeout(timer)
      activeIndex.value = 0
      if (!kw.trim()) {
        results.value = []
        searching.value = false
        return
      }
      searching.value = true
      timer = setTimeout(async () => {
        try {
          const { results: list } = await unifiedSearch(kw.trim())
          results.value = list
        } catch (/** @type {unknown} */ e) {
          results.value = []
        } finally {
          searching.value = false
        }
      }, 300)
    })

    // 打开:聚焦 + 锁滚动 + 载入最近浏览;关闭:恢复
    watch(open, async (v) => {
      document.body.style.overflow = v ? 'hidden' : ''
      if (v) {
        q.value = ''
        results.value = []
        activeIndex.value = 0
        recent.value = getRecentArticles()
        await nextTick()
        inputRef.value?.focus()
      }
    })

    /** 全局 ⌘K/Ctrl+K 唤起;触发元素=当前焦点元素(关闭时归还) */
    /** @param {KeyboardEvent} e */
    function onGlobalKeydown(e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        const el = document.activeElement instanceof HTMLElement ? document.activeElement : null
        openOverlay(el)
      }
    }

    onMounted(() => window.addEventListener('keydown', onGlobalKeydown))
    onUnmounted(() => {
      window.removeEventListener('keydown', onGlobalKeydown)
      if (timer) clearTimeout(timer)
      document.body.style.overflow = ''
    })

    return {
      open, closeOverlay, inputRef, q, searching,
      recent, recentItems, SUGGESTED,
      flatResults, groupedResults, activeIndex,
      move, flatIndexOf, go, goActive, useWord,
    }
  },
}
</script>

<style scoped>
.so-backdrop {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgba(10, 10, 9, 0.32);
  backdrop-filter: blur(3px);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 12vh 20px 20px;
}
.so-panel {
  width: min(640px, 100%);
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--surface);
  box-shadow: 0 26px 70px rgba(0, 0, 0, 0.28);
  overflow: hidden;
}
.so-input-row {
  position: relative;
  border-bottom: 1px solid var(--line);
}
.so-input-row input {
  width: 100%;
  height: 54px;
  padding: 0 56px 0 18px;
  border: 0;
  background: transparent;
  color: var(--text);
  font-size: 17px;
  outline: none;
}
.so-key {
  position: absolute;
  right: 14px;
  top: 17px;
  padding: 4px 7px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--surface-2);
  font-size: 11px;
  color: var(--muted);
}
.so-body {
  padding: 10px 8px 12px;
  overflow: auto;
}
.so-group-label {
  padding: 8px 10px 6px;
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 0.04em;
}
.so-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 11px 10px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.so-item.active {
  background: var(--surface-2);
}
.so-item-title {
  font-size: 14px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.so-item-meta {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--muted);
}
.so-suggest {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 2px 10px 6px;
}
.so-chip {
  padding: 6px 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  color: var(--muted);
  font-size: 13px;
  cursor: pointer;
}
.so-chip:hover {
  color: var(--text);
  border-color: var(--line-strong);
}
.so-hint {
  padding: 26px 10px;
  text-align: center;
  font-size: 13px;
  color: var(--muted);
}
</style>
