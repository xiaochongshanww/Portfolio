<template>
  <div class="archive-page shell">
    <section class="page-head">
      <div class="eyebrow">归档</div>
      <h1>按时间回看这些年写过的东西。</h1>
      <p>归档只解决一件事：快速找到过去写过的文章。这里不做卡片瀑布流，也不重复展示摘要。</p>
    </section>

    <!-- loading -->
    <section v-if="loading" class="section section-last">
      <el-skeleton :rows="8" animated />
    </section>

    <!-- error -->
    <section v-else-if="error" class="section section-last">
      <div class="state-block">
        <p>归档加载失败,请稍后重试。</p>
        <button type="button" class="retry-btn" @click="loadAll">重试</button>
      </div>
    </section>

    <!-- empty -->
    <section v-else-if="!groups.length" class="section section-last">
      <div class="state-block">还没有文章。</div>
    </section>

    <!-- ready -->
    <section v-else class="section section-last">
      <div class="archive-tools">
        <div class="meta">共 {{ visibleCount }} 篇文章</div>
        <div class="year-tabs">
          <button
            type="button"
            :class="{ active: !selectedYear }"
            @click="selectYear('')"
          >全部</button>
          <button
            v-for="y in years"
            :key="y"
            type="button"
            :class="{ active: selectedYear === y }"
            @click="selectYear(y)"
          >{{ y }}</button>
        </div>
      </div>

      <div v-for="g in visibleGroups" :key="g.year" class="archive-year">
        <div class="year-label">
          {{ g.year }}
          <small>{{ g.items.length }} 篇</small>
        </div>
        <div class="archive-list">
          <a
            v-for="a in g.items"
            :key="a.id"
            class="archive-row"
            :href="'/article/' + a.slug"
            @click.prevent="goArticle(a.slug)"
          >
            <div class="meta">{{ dateLabel(a.published_at || a.created_at) }}</div>
            <h3>{{ a.title }}</h3>
            <div class="topic">{{ a.category || '' }}</div>
          </a>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
/**
 * 归档页(P1 分组 A,原型 xiaochongshan-2026-archive-v1)
 * 高密度年份分组列表;不做卡片流、不显示摘要。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { API } from '../api'
import { setMeta } from '../composables/useMeta'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const error = ref(false)

/**
 * @typedef {Object} ArchiveArticle
 * @property {number} id
 * @property {string} title
 * @property {string} slug
 * @property {string} [category]
 * @property {string} [published_at]
 * @property {string} [created_at]
 */

/** @type {import('vue').Ref<ArchiveArticle[]>} */
const articles = ref([])

// TODO(归档分页): 当前量级(<100 篇)全量拉取可接受;
// 文章量上来后应改为分年接口(impl-P1 风险 2)
const MAX_PAGES = 20

async function loadAll() {
  loading.value = true
  error.value = false
  try {
    const all = []
    let page = 1
    // page_size 后端上限 50,循环取页直到 has_next 为假
    for (let i = 0; i < MAX_PAGES; i++) {
      const resp = await API.getPublicArticles({ page, page_size: 50 })
      const data = resp?.data?.data
      /** @type {ArchiveArticle[]} */
      all.push(...(data?.list || []))
      if (!data?.has_next) break
      page += 1
    }
    articles.value = all
  } catch (e) {
    error.value = true
  } finally {
    loading.value = false
  }
}

/** 年份分组:年份倒序,年内按日期倒序 */
const groups = computed(() => {
  /** @type {Map<number, Array<{a: ArchiveArticle, d: Date}>>} */
  const byYear = new Map()
  for (const a of articles.value) {
    const d = toDate(a.published_at || a.created_at)
    if (!d) continue
    const y = d.getFullYear()
    if (!byYear.has(y)) byYear.set(y, [])
    byYear.get(y)?.push({ a, d })
  }
  return [...byYear.entries()]
    .sort((x, y) => y[0] - x[0])
    .map(([year, items]) => ({
      year,
      items: items
        .sort((x, y) => y.d.getTime() - x.d.getTime())
        .map(({ a }) => a),
    }))
})

const years = computed(() => groups.value.map((g) => String(g.year)))

const selectedYear = ref('')

const visibleGroups = computed(() =>
  selectedYear.value
    ? groups.value.filter((g) => String(g.year) === selectedYear.value)
    : groups.value,
)

const visibleCount = computed(() =>
  visibleGroups.value.reduce((n, g) => n + g.items.length, 0),
)

/** @param {string | undefined} s */
function toDate(s) {
  if (!s) return null
  try {
    let str = s
    if (!str.endsWith('Z') && !str.includes('+') && !str.includes('-', 10)) str += 'Z'
    const d = new Date(str)
    return isNaN(d.getTime()) ? null : d
  } catch (e) {
    return null
  }
}

/** 原型行首日期格式 MM / DD
 * @param {string | undefined} s
 */
function dateLabel(s) {
  const d = toDate(s)
  if (!d) return ''
  return `${String(d.getMonth() + 1).padStart(2, '0')} / ${String(d.getDate()).padStart(2, '0')}`
}

/** 年份筛选同步 ?year=(push 保留历史,支持直链与后退)
 * @param {string} y
 */
function selectYear(y) {
  selectedYear.value = y
  const query = { ...route.query }
  if (y) query.year = y
  else delete query.year
  router.push({ query })
}

/** @param {string} slug */
function goArticle(slug) {
  router.push(`/article/${slug}`)
}

// 直链 ?year=2025 打开即为筛选态;后退/前进恢复
watch(
  () => route.query.year,
  (y) => {
    selectedYear.value = y ? String(y) : ''
  },
  { immediate: true },
)

onMounted(() => {
  setMeta({ title: '归档 · 小重山', description: '按时间回看全部文章。' })
  loadAll()
})
</script>

<style scoped>
.page-head {
  padding: 46px 0 28px;
  border-bottom: 1px solid var(--line);
}
.eyebrow {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 10px;
}
.page-head h1 {
  font-size: 40px;
  line-height: 1.12;
  letter-spacing: -0.048em;
  margin: 0 0 12px;
}
.page-head p {
  font-size: 16px;
  line-height: 1.72;
  color: var(--muted);
  margin: 0;
  max-width: 700px;
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

.archive-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 22px;
}
.year-tabs {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
}
.year-tabs button {
  padding: 7px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
}
.year-tabs button.active {
  background: var(--text);
  color: var(--bg);
  border-color: var(--text);
}

.archive-year {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 28px;
  padding: 22px 0;
  border-top: 1px solid var(--line);
}
.archive-year:first-of-type {
  border-top: 0;
}
.year-label {
  font-size: 28px;
  font-weight: 760;
  letter-spacing: -0.04em;
}
.year-label small {
  display: block;
  margin-top: 5px;
  font-size: 11px;
  font-weight: 400;
  color: var(--muted);
}
.archive-list {
  display: grid;
}
.archive-row {
  display: grid;
  grid-template-columns: 80px 1fr 120px;
  gap: 18px;
  align-items: center;
  padding: 14px 8px;
  border-radius: 10px;
}
.archive-row:hover {
  background: var(--surface);
}
.archive-row h3 {
  font-size: 16px;
  margin: 0;
}
.archive-row .topic {
  font-size: 12px;
  color: var(--muted);
  text-align: right;
}

.state-block {
  border: 1px dashed var(--line-strong);
  border-radius: 16px;
  padding: 48px 24px;
  text-align: center;
  color: var(--muted);
  font-size: 14px;
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

@media (max-width: 760px) {
  .page-head {
    padding-top: 36px;
  }
  .page-head h1 {
    font-size: 34px;
  }
  .archive-year {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  .archive-row {
    grid-template-columns: 65px 1fr;
  }
  .archive-row .topic {
    display: none;
  }
}
</style>
