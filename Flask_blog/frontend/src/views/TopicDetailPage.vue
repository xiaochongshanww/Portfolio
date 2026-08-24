<template>
  <div class="topic-detail-page shell">
    <!-- 404:slug 无对应专题 -->
    <section v-if="notFound" class="page-head">
      <div class="eyebrow">长期专题</div>
      <h1>没有找到这个专题。</h1>
      <p>它可能已被合并或移除,去专题列表看看其他主题。</p>
      <div class="notfound-actions">
        <a href="/topics" @click.prevent="router.push('/topics')">← 返回专题列表</a>
      </div>
    </section>

    <!-- loading -->
    <section v-else-if="loading" class="hero-fallback">
      <el-skeleton :rows="6" animated />
    </section>

    <!-- error -->
    <section v-else-if="error" class="hero-fallback">
      <div class="state-block">
        <p>专题加载失败,请稍后重试。</p>
        <button type="button" class="retry-btn" @click="load">重试</button>
      </div>
    </section>

    <template v-else-if="topic">
      <!-- D1:Hero + 统计卡 -->
      <section class="topic-hero">
        <div class="topic-hero-inner">
          <div>
            <div class="eyebrow">长期专题 / {{ topic.name }}</div>
            <h1>{{ topic.name }}</h1>
            <p>{{ topic.description }}</p>
          </div>
          <div class="topic-stat" :class="`tone-${topic.tone}`">
            <strong>{{ topic.count }}</strong>
            <span>篇文章{{ topic.ongoing ? ' · 持续更新' : '' }}</span>
          </div>
        </div>
      </section>

      <!-- D2:推荐从这里开始 -->
      <section v-if="featured" class="section">
        <div class="section-head">
          <h2>推荐从这里开始</h2>
        </div>
        <a
          class="featured"
          :href="'/article/' + featured.slug"
          @click.prevent="goArticle(featured.slug)"
        >
          <div class="featured-copy">
            <span v-if="firstTag" class="tag">{{ firstTag }}</span>
            <h2>{{ featured.title }}</h2>
            <p>{{ featured.summary || featured.content_excerpt || '' }}</p>
            <div class="meta featured-meta">{{ formatDate(featured.published_at || featured.created_at) }}</div>
          </div>
          <div class="featured-visual">
            <TechnicalVisual :type="visualType" :text="''" />
          </div>
        </a>
      </section>

      <!-- D3:全部文章(按更新时间排序) -->
      <section class="section section-last">
        <div class="section-head">
          <h2>全部文章</h2>
          <span class="meta">按更新时间排序</span>
        </div>

        <!-- empty -->
        <div v-if="!articles.length" class="state-block">这个专题还在整理中。</div>

        <div v-else class="article-list">
          <ArticleFeedRow
            v-for="a in sortedArticles"
            :key="a.id"
            :title="a.title"
            :summary="excerptOf(a)"
            :published-at="sortKeyOf(a)"
            :href="'/article/' + a.slug"
          >
            <template #meta>{{ firstTagOf(a) }}</template>
          </ArticleFeedRow>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
/**
 * 专题详情(P1 分组 D,原型 xiaochongshan-2026-topic-detail-v1)
 * 排序键 updated_at(缺失降级 published_at);推荐起点 topicOverrides → 最新一篇。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { API } from '../api'
import { topicOverrideFor } from '../data/topicOverrides'
import ArticleFeedRow from '../components/public/ArticleFeedRow.vue'
import TechnicalVisual from '../components/public/TechnicalVisual.vue'
import { visualTypeFor } from '../utils/visualMapping'
import { setMeta } from '../composables/useMeta'

const props = defineProps({
  slug: { type: String, default: '' },
})

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref(false)
const notFound = ref(false)

/**
 * @typedef {Object} TaxCategory
 * @property {number} id
 * @property {string} name
 * @property {string} [slug]
 * @property {number} [article_count]
 * @property {string | null} [description]
 */

/**
 * @typedef {Object} PubArticle
 * @property {number} id
 * @property {string} title
 * @property {string} slug
 * @property {string} [summary]
 * @property {string} [content_excerpt]
 * @property {string[]} [tags]
 * @property {string} [published_at]
 * @property {string} [created_at]
 * @property {string} [updated_at]
 */

/** @type {import('vue').Ref<TaxCategory | null>} */
const category = ref(null)
/** @type {import('vue').Ref<Array<PubArticle>>} */
const articles = ref([])

const TONE_BY_INDEX = ['green', 'blue', 'signal', 'sand']

const topic = computed(() => {
  const c = category.value
  if (!c) return null
  const override = topicOverrideFor(c.id)
  return {
    name: c.name,
    description: override?.description || c.description || '长期维护的知识主题,持续补充相关文章。',
    count: c.article_count ?? articles.value.length,
    tone: override?.tone || TONE_BY_INDEX[(c.id || 0) % TONE_BY_INDEX.length],
    ongoing: articles.value.some(
      (a) => a.updated_at && a.updated_at > (a.published_at || a.created_at || ''),
    ),
  }
})

/** 排序键:updated_at 优先,缺失降级 published_at/created_at(D3)
 * @param {PubArticle} a
 * @returns {string}
 */
function sortKeyOf(a) {
  return a.updated_at || a.published_at || a.created_at || ''
}

const sortedArticles = computed(() =>
  [...articles.value].sort((x, y) => (sortKeyOf(y) || '').localeCompare(sortKeyOf(x) || '')),
)

const featured = computed(() => {
  const override = topicOverrideFor(category.value?.id)
  if (override?.startArticleSlug) {
    const hit = articles.value.find((a) => a.slug === override.startArticleSlug)
    if (hit) return hit
  }
  // 降级:最新一篇(按排序键)
  return sortedArticles.value[0] || null
})

const firstTag = computed(() => firstTagOf(featured.value || {}))

const visualType = computed(() => {
  const t = visualTypeFor(topic.value?.name, featured.value?.tags)
  return t || 'rag'
})

/** @param {PubArticle | Record<string, never>} a */
function firstTagOf(a) {
  const tags = Array.isArray(a?.tags) ? a.tags : []
  return tags[0] || ''
}

/** @param {PubArticle} a */
function excerptOf(a) {
  const raw = a.summary || a.content_excerpt || ''
  return String(raw).replace(/[#*`>\[\]]/g, '').slice(0, 90)
}

/** @param {string | undefined} s */
function formatDate(s) {
  if (!s) return ''
  try {
    let str = s
    if (!str.endsWith('Z') && !str.includes('+') && !str.includes('-', 10)) str += 'Z'
    const d = new Date(str)
    return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`
  } catch (e) {
    return ''
  }
}

/** @param {string} slug */
function goArticle(slug) {
  router.push(`/article/${slug}`)
}

async function load() {
  const slugProp = props.slug || route.params.slug
  const slug = Array.isArray(slugProp) ? slugProp[0] : String(slugProp || '')
  loading.value = true
  error.value = false
  notFound.value = false
  category.value = null
  articles.value = []
  try {
    const taxResp = await API.getPublicTaxonomy()
    /** @type {TaxCategory[]} */
    const cats = taxResp?.data?.data?.categories || []
    const c = cats.find((x) => x.slug === slug || String(x.id) === slug)
    if (!c) {
      notFound.value = true
      return
    }
    category.value = c

    // TODO(专题分页): 量级增大后改分页拉取
    const artResp = await API.getPublicArticles({ page: 1, page_size: 50, category_id: c.id })
    /** @type {PubArticle[]} */
    articles.value = artResp?.data?.data?.list || []

    setMeta({
      title: `${c.name} · 专题 · 小重山`,
      description: topic.value?.description || '',
    })
  } catch (e) {
    error.value = true
  } finally {
    loading.value = false
  }
}

watch(() => props.slug, load)
onMounted(load)
</script>

<style scoped>
.topic-hero {
  padding: 44px 0 30px;
  border-bottom: 1px solid var(--line);
}
.topic-hero-inner {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 40px;
  align-items: end;
}
.eyebrow {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 10px;
}
.topic-hero h1 {
  font-size: 44px;
  letter-spacing: -0.05em;
  margin: 0 0 12px;
}
.topic-hero p {
  font-size: 16px;
  line-height: 1.7;
  color: var(--muted);
  margin: 0;
  max-width: 660px;
}
.topic-stat {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--green-soft);
  padding: 18px;
}
.topic-stat.tone-green { background: var(--green-soft); }
.topic-stat.tone-blue { background: var(--blue-soft); }
.topic-stat.tone-signal { background: var(--signal-soft); }
.topic-stat.tone-sand { background: var(--sand); }
.topic-stat strong {
  display: block;
  font-size: 34px;
  letter-spacing: -0.04em;
}
.topic-stat span {
  font-size: 12px;
  color: var(--muted);
}

.section {
  padding: 34px 0;
  border-bottom: 1px solid var(--line);
}
.section-last {
  border-bottom: 0;
}
.section-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}
.section-head h2 {
  font-size: 15px;
  margin: 0;
}
.meta {
  font-size: 12px;
  color: var(--muted);
}

/* 推荐起点 */
.featured {
  display: grid;
  grid-template-columns: 1fr 300px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--surface);
  overflow: hidden;
}
.featured-copy {
  padding: 26px;
}
.featured-copy .tag {
  display: inline-flex;
  padding: 5px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  font-size: 11px;
  color: var(--muted);
}
.featured-copy h2 {
  font-size: 28px;
  letter-spacing: -0.04em;
  margin: 10px 0;
}
.featured-copy p {
  font-size: 14px;
  line-height: 1.65;
  color: var(--muted);
  margin: 0;
}
.featured-meta {
  margin-top: 16px;
}
.featured-visual {
  border-left: 1px solid var(--line);
  background: var(--surface-2);
  display: grid;
  place-items: center;
  padding: 26px;
}

.article-list {
  display: grid;
  gap: 2px;
}

/* 404 / 状态 */
.notfound-actions {
  margin-top: 20px;
}
.notfound-actions a {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  border-bottom: 2px solid var(--signal);
  padding-bottom: 2px;
}
.hero-fallback {
  padding: 60px 0;
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

@media (max-width: 820px) {
  .topic-hero-inner,
  .featured {
    grid-template-columns: 1fr;
  }
  .featured-visual {
    border-left: 0;
    border-top: 1px solid var(--line);
  }
  .topic-hero h1 {
    font-size: 36px;
  }
}
</style>
