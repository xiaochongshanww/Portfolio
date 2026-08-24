<template>
  <div class="topics-page shell">
    <section class="page-head">
      <div class="eyebrow">长期专题</div>
      <h1>把零散文章，沉淀成持续生长的主题。</h1>
      <p>专题不是标签集合，而是长期维护的知识入口。同一主题下的文章会随着理解和项目实践继续增加。</p>
    </section>

    <!-- loading -->
    <section v-if="loading" class="section section-last">
      <el-skeleton :rows="6" animated />
    </section>

    <!-- error -->
    <section v-else-if="error" class="section section-last">
      <div class="state-block">
        <p>专题加载失败,请稍后重试。</p>
        <button type="button" class="retry-btn" @click="loadAll">重试</button>
      </div>
    </section>

    <!-- empty -->
    <section v-else-if="!cards.length" class="section section-last">
      <div class="state-block">专题正在整理中。</div>
    </section>

    <!-- ready -->
    <section v-else class="section section-last">
      <div class="topic-grid">
        <a
          v-for="(t, i) in mainCards"
          :key="t.id"
          class="topic-card"
          :class="`tone-${t.tone || TONE_BY_INDEX[i % TONE_BY_INDEX.length]}`"
          :href="'/topics/' + t.slug"
          @click.prevent="goTopic(t.slug)"
        >
          <div class="topic-top">
            <div>
              <h2>{{ t.name }}</h2>
              <p>{{ t.description }}</p>
            </div>
            <span class="arrow">↗</span>
          </div>
          <div class="topic-bottom">
            <div class="topic-count">{{ t.count }} 篇文章{{ t.ongoing ? ' · 持续更新' : '' }}</div>
            <div v-if="t.latestTitle" class="topic-latest">最新：{{ t.latestTitle }}</div>
          </div>
        </a>
      </div>

      <!-- 超出 4 张主卡:折叠为次级链接行(C1) -->
      <div v-if="extraCards.length" class="topic-extras">
        <a
          v-for="t in extraCards"
          :key="t.id"
          :href="'/topics/' + t.slug"
          @click.prevent="goTopic(t.slug)"
        >{{ t.name }}({{ t.count }} 篇) →</a>
      </div>
    </section>
  </div>
</template>

<script setup>
/**
 * 专题列表(P1 分组 C,原型 xiaochongshan-2026-topics-v1)
 * 数据 = taxonomy categories ∪ topicOverrides;tone 未配置时按序取四色。
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { API } from '../api'
import { topicOverrideFor } from '../data/topicOverrides'
import { setMeta } from '../composables/useMeta'

/**
 * @typedef {Object} TopicCard
 * @property {number} id
 * @property {string} slug
 * @property {string} name
 * @property {string} description
 * @property {number} count
 * @property {string | null} tone
 * @property {boolean} ongoing
 * @property {string} latestTitle
 */

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
 * @property {string} [slug]
 * @property {number} [category_id]
 * @property {string} [published_at]
 * @property {string} [created_at]
 * @property {string} [updated_at]
 */

const TONE_BY_INDEX = ['green', 'blue', 'signal', 'sand']
const MAIN_CARD_LIMIT = 4

const router = useRouter()
const loading = ref(true)
const error = ref(false)
/** @type {import('vue').Ref<TopicCard[]>} */
const cards = ref([])

const mainCards = computed(() => cards.value.slice(0, MAIN_CARD_LIMIT))
const extraCards = computed(() => cards.value.slice(MAIN_CARD_LIMIT))

/** 最近 N 天内有更新视为「持续更新」
 * @param {PubArticle[]} articlesOfTopic
 */
function isOngoing(articlesOfTopic) {
  return articlesOfTopic.some(
    (a) => a.updated_at && a.updated_at > (a.published_at || a.created_at || ''),
  )
}

async function loadAll() {
  loading.value = true
  error.value = false
  try {
    const [taxRes, artRes] = await Promise.allSettled([
      API.getPublicTaxonomy(),
      // TODO(专题分页): 量级增大后改为按分类拉取最新一篇
      API.getPublicArticles({ page: 1, page_size: 50 }),
    ])
    if (taxRes.status !== 'fulfilled') throw new Error('taxonomy unavailable')

    /** @type {TaxCategory[]} */
    const cats = taxRes.value?.data?.data?.categories || []
    /** @type {PubArticle[]} */
    const articles = artRes.status === 'fulfilled' ? artRes.value?.data?.data?.list || [] : []

    cards.value = cats
      .map((c) => {
        const override = topicOverrideFor(c.id)
        const own = articles.filter((a) => a.category_id === c.id)
        const latest = own[0] // 列表默认按发布时间倒序
        return {
          id: c.id,
          slug: c.slug || String(c.id),
          name: c.name,
          description:
            override?.description || c.description || '长期维护的知识主题,持续补充相关文章。',
          count: c.article_count ?? own.length,
          tone: override?.tone || null,
          ongoing: isOngoing(own),
          latestTitle: latest?.title || '',
        }
      })
      .sort((a, b) => b.count - a.count)
  } catch (e) {
    error.value = true
  } finally {
    loading.value = false
  }
}

/** @param {string} slug */
function goTopic(slug) {
  router.push(`/topics/${slug}`)
}

onMounted(() => {
  setMeta({ title: '专题 · 小重山', description: '长期维护的知识主题入口。' })
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
.arrow {
  color: var(--muted);
}

.topic-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}
.topic-card {
  min-height: 210px;
  padding: 22px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--surface);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition:
    transform 0.16s ease,
    border-color 0.16s ease;
}
.topic-card:hover {
  transform: translateY(-2px);
  border-color: var(--line-strong);
}
.topic-card.tone-green { background: var(--green-soft); }
.topic-card.tone-blue { background: var(--blue-soft); }
.topic-card.tone-signal { background: var(--signal-soft); }
.topic-card.tone-sand { background: var(--sand); }
.topic-top {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}
.topic-top h2 {
  font-size: 27px;
  letter-spacing: -0.035em;
  margin: 0 0 8px;
}
.topic-top p {
  font-size: 14px;
  line-height: 1.65;
  color: var(--muted);
  margin: 0;
  max-width: 430px;
}
.topic-bottom {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
  margin-top: 28px;
}
.topic-count {
  font-size: 12px;
  color: var(--muted);
}
.topic-latest {
  font-size: 13px;
  font-weight: 650;
}

.topic-extras {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 22px;
  margin-top: 18px;
}
.topic-extras a {
  font-size: 13px;
  color: var(--muted);
}
.topic-extras a:hover {
  color: var(--text);
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
  .topic-grid {
    grid-template-columns: 1fr;
  }
}
</style>
