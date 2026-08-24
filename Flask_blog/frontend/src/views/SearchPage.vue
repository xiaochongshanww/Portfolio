<template>
  <div class="search-page shell">
    <section class="search-panel">
      <div class="eyebrow">搜索</div>
      <div class="search-box">
        <input
          ref="inputRef"
          v-model="q"
          type="text"
          placeholder="搜索文章、专题与项目"
          aria-label="搜索文章、专题与项目"
          @keydown.enter="searchNow"
          @keydown.esc.prevent="clearSearch"
        >
        <span class="key">ESC</span>
      </div>
      <div class="search-meta">
        <span v-if="searched && !loading">找到 {{ filteredResults.length }} 个与“{{ lastKeyword }}”相关的结果</span>
        <span>支持标题、正文、专题和项目</span>
      </div>
    </section>

    <!-- loading -->
    <section v-if="loading" class="section section-last">
      <el-skeleton :rows="6" animated />
    </section>

    <!-- error -->
    <section v-else-if="error" class="section section-last">
      <div class="state-block">
        <p>搜索失败,请稍后重试。</p>
        <button type="button" class="retry-btn" @click="searchNow">重试</button>
      </div>
    </section>

    <!-- empty -->
    <section v-else-if="searched && !filteredResults.length" class="section section-last">
      <div class="state-block">
        <p>没有找到与“{{ lastKeyword }}”相关的内容。</p>
        <p class="hint">可以换个关键词,或减少关键词字数再试。</p>
      </div>
    </section>

    <!-- ready -->
    <section v-else-if="filteredResults.length" class="section section-last">
      <div class="search-tools">
        <div class="filters">
          <button
            type="button"
            :class="{ active: typeFilter === 'all' }"
            @click="typeFilter = 'all'"
          >全部</button>
          <button
            v-for="f in typeFilters"
            :key="f.value"
            type="button"
            :class="{ active: typeFilter === f.value }"
            @click="typeFilter = f.value"
          >{{ f.label }} {{ counts[f.value] || 0 }}</button>
        </div>
        <div class="meta">按相关度</div>
      </div>

      <div class="result-list">
        <a
          v-for="r in filteredResults"
          :key="r.type + r.href + r.title"
          class="result"
          :href="r.href"
          @click.prevent="go(r.href)"
        >
          <div>
            <h2>
              <template v-for="(seg, i) in splitHighlight(r.title, lastKeyword)" :key="i">
                <mark v-if="seg.hit" class="hit">{{ seg.text }}</mark>
                <template v-else>{{ seg.text }}</template>
              </template>
            </h2>
            <p v-if="r.snippet">
              <template v-for="(seg, i) in splitHighlight(r.snippet, lastKeyword)" :key="i">
                <mark v-if="seg.hit" class="hit">{{ seg.text }}</mark>
                <template v-else>{{ seg.text }}</template>
              </template>
            </p>
          </div>
          <div class="meta">{{ r.meta }}</div>
          <div class="arrow">→</div>
        </a>
      </div>
    </section>

    <!-- 初始态:未搜索 -->
    <section v-else class="section section-last">
      <div class="state-block">输入关键词开始搜索。</div>
    </section>
  </div>
</template>

<script setup>
/**
 * 搜索页(P1 分组 B,原型 xiaochongshan-2026-search-v1)
 * 高亮走 splitHighlight 结构化渲染,禁止对搜索结果 v-html(XSS 红线)。
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { unifiedSearch } from '../composables/useUnifiedSearch'
import { splitHighlight } from '../utils/highlight'
import { setMeta } from '../composables/useMeta'

const route = useRoute()
const router = useRouter()

/** @type {import('vue').Ref<HTMLInputElement | null>} */
const inputRef = ref(null)
const q = ref('')
const lastKeyword = ref('')
const loading = ref(false)
const error = ref(false)
const searched = ref(false)

/** @typedef {import('../composables/useUnifiedSearch').UnifiedResult} UnifiedResult */
/** @typedef {{all:number, article:number, topic:number, project:number}} SearchCounts */
/** @typedef {'all'|'article'|'topic'|'project'} SearchTypeFilter */

/** @type {import('vue').Ref<Array<UnifiedResult>>} */
const results = ref([])
/** @type {import('vue').Ref<SearchCounts>} */
const counts = ref({ all: 0, article: 0, topic: 0, project: 0 })
/** @type {import('vue').Ref<SearchTypeFilter>} */
const typeFilter = ref('all')

/** @type {Record<'article'|'topic'|'project', string>} */
const TYPE_LABELS = { article: '文章', topic: '专题', project: '项目' }
/** @type {Array<'article'|'topic'|'project'>} */
const TYPE_KEYS = ['article', 'topic', 'project']
const typeFilters = computed(() => TYPE_KEYS.map((v) => ({ value: v, label: TYPE_LABELS[v] })))

const filteredResults = computed(() =>
  typeFilter.value === 'all'
    ? results.value
    : results.value.filter((r) => r.type === typeFilter.value),
)

/** @type {ReturnType<typeof setTimeout> | null} */
let debounceTimer = null

function scheduleSearch() {
  if (debounceTimer !== null) clearTimeout(debounceTimer)
  const kw = q.value.trim()
  if (!kw) return
  debounceTimer = setTimeout(() => searchNow(), 300)
}

async function searchNow() {
  if (debounceTimer !== null) clearTimeout(debounceTimer)
  const kw = q.value.trim()
  if (!kw) {
    // 空关键词:清空结果,不发请求
    searched.value = false
    results.value = []
    syncQuery('')
    return
  }
  loading.value = true
  error.value = false
  try {
    const { results: list, counts: c } = await unifiedSearch(kw)
    results.value = list
    counts.value = c
    lastKeyword.value = kw
    searched.value = true
    typeFilter.value = 'all'
    syncQuery(kw)
  } catch (e) {
    error.value = true
  } finally {
    loading.value = false
  }
}

/** ESC:清空并失焦,不离开页面 */
function clearSearch() {
  q.value = ''
  if (debounceTimer !== null) clearTimeout(debounceTimer)
  inputRef.value?.blur?.()
}

/** ?q= 同步(replace 避免防抖刷历史;刷新后由 query 恢复)
 * @param {string} kw
 */
function syncQuery(kw) {
  const query = { ...route.query }
  if (kw) query.q = kw
  else delete query.q
  router.replace({ query })
}

/** @param {string} href */
function go(href) {
  if (href) router.push(href)
}

watch(q, scheduleSearch)

onMounted(async () => {
  setMeta({ title: '搜索 · 小重山', description: '统一搜索文章、专题与项目。' })
  inputRef.value?.focus?.()
  // 直链 ?q= 时恢复搜索
  const initial = String(route.query.q || '').trim()
  if (initial) {
    q.value = initial
    await searchNow()
  }
})

onUnmounted(() => { if (debounceTimer !== null) clearTimeout(debounceTimer) })
</script>

<style scoped>
.search-panel {
  padding: 38px 0 28px;
  border-bottom: 1px solid var(--line);
}
.eyebrow {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 10px;
}
.search-box {
  position: relative;
}
.search-box input {
  width: 100%;
  height: 58px;
  padding: 0 52px 0 18px;
  border: 1px solid var(--line);
  border-radius: 15px;
  background: var(--surface);
  color: var(--text);
  font-size: 18px;
  outline: none;
}
.search-box input:focus {
  border-color: var(--line-strong);
  box-shadow: 0 0 0 4px rgba(0, 0, 0, 0.03);
}
.key {
  position: absolute;
  right: 15px;
  top: 16px;
  padding: 4px 7px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--surface-2);
  font-size: 11px;
  color: var(--muted);
}
.search-meta {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
  margin-top: 12px;
  font-size: 12px;
  color: var(--muted);
}

.section {
  padding: 34px 0;
}
.section-last {
  border-bottom: 0;
}
.meta {
  font-size: 12px;
  color: var(--muted);
}
.arrow {
  color: var(--muted);
}

.search-tools {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 20px;
}
.filters {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
}
.filters button {
  padding: 7px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
}
.filters button.active {
  background: var(--text);
  color: var(--bg);
  border-color: var(--text);
}

.result-list {
  display: grid;
  gap: 5px;
}
.result {
  display: grid;
  grid-template-columns: 1fr 120px 24px;
  gap: 20px;
  align-items: center;
  padding: 19px 12px;
  border: 1px solid transparent;
  border-radius: 13px;
}
.result:hover {
  background: var(--surface);
  border-color: var(--line);
}
.result h2 {
  font-size: 20px;
  margin: 0 0 6px;
}
.result p {
  font-size: 13px;
  line-height: 1.6;
  color: var(--muted);
  margin: 0;
}
.hit {
  background: var(--signal-soft);
  color: var(--signal-ink);
  padding: 1px 3px;
  border-radius: 3px;
}

.state-block {
  border: 1px dashed var(--line-strong);
  border-radius: 16px;
  padding: 48px 24px;
  text-align: center;
  color: var(--muted);
  font-size: 14px;
}
.state-block .hint {
  margin-top: 8px;
  font-size: 13px;
}
.retry-btn {
  margin-top: 14px;
  height: 36px;
  padding: 0 20px;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
}
.retry-btn:hover {
  border-color: var(--text);
}

@media (max-width: 700px) {
  .result {
    grid-template-columns: 1fr 24px;
  }
  .result > .meta {
    display: none;
  }
}
</style>
