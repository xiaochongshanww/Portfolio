<template>
  <div class="project-detail-page shell">
    <!-- 404 -->
    <section v-if="notFound" class="page-head">
      <div class="eyebrow">项目</div>
      <h1>没有找到这个项目。</h1>
      <p>它可能已被归档或移除,去项目列表看看其它正在进行的东西。</p>
      <div class="notfound-actions">
        <a href="/projects" @click.prevent="router.push('/projects')">← 返回项目列表</a>
      </div>
    </section>

    <!-- loading -->
    <section v-else-if="loading" class="fallback-space">
      <el-skeleton :rows="8" animated />
    </section>

    <!-- error -->
    <section v-else-if="error" class="fallback-space">
      <div class="state-block">
        <p>项目加载失败,请稍后重试。</p>
        <button type="button" class="retry-btn" @click="load">重试</button>
      </div>
    </section>

    <template v-else-if="project">
      <!-- ① Project Identity -->
      <section class="identity">
        <div class="eyebrow">项目{{ project.tag ? ' / ' + project.tag : '' }}</div>
        <h1>{{ project.name }}</h1>
        <p class="deck">{{ project.description }}</p>

        <!-- ② Live Status -->
        <div class="live-status">
          <span class="live-dot">● {{ statusLabel(project.status) }}</span>
          <span class="meta">最近更新 {{ formatDate(project.updated_at) }}</span>
          <a v-if="project.repo_url" :href="project.repo_url" target="_blank" rel="noopener noreferrer">Repo ↗</a>
          <a v-if="project.link_url" :href="project.link_url" target="_blank" rel="noopener noreferrer">在线体验 ↗</a>
          <span v-else class="meta demo-none">当前版本暂未开放在线体验</span>
        </div>
      </section>

      <!-- ③ Preview / Demo -->
      <section v-if="hasPreview" class="section">
        <div class="preview-box">
          <img
            v-if="project.preview_type === 'image' && previewImage"
            :src="previewImage"
            :alt="project.name"
            loading="lazy"
          >
          <!-- eslint-disable-next-line vue/no-v-html -- svg 来自管理端配置,出口消毒 -->
          <div v-else-if="project.preview_type === 'svg' && previewSvg" class="preview-svg" v-html="previewSvg" />
        </div>
      </section>

      <!-- ④ 为什么做 / ⑤ 现在做到哪里 / ⑥ 关键设计决策 -->
      <section v-for="block in textBlocks" :key="block.key" class="section">
        <div class="section-head"><h2>{{ block.title }}</h2></div>
        <div class="content-width-text body-text">
          <p v-for="(para, i) in block.paragraphs" :key="i">{{ para }}</p>
        </div>
      </section>

      <!-- ⑦ 相关技术文章:slug 全部失效时整体隐藏 -->
      <section v-if="relatedArticles.length" class="section">
        <div class="section-head"><h2>相关技术文章</h2></div>
        <div class="article-list">
          <ArticleFeedRow
            v-for="a in relatedArticles"
            :key="a.id"
            :title="a.title"
            :summary="excerptOf(a)"
            :published-at="a.published_at || a.created_at || ''"
            :href="'/article/' + a.slug"
          >
            <template #meta>{{ firstTagOf(a) }}</template>
          </ArticleFeedRow>
        </div>
      </section>

      <!-- ⑧ Changelog / ⑨ Next(next:true 的条目单独成区) -->
      <section v-if="changelogItems.length" class="section">
        <div class="section-head"><h2>Changelog</h2></div>
        <div class="timeline">
          <div v-for="(c, i) in changelogItems" :key="i" class="timeline-row">
            <div class="meta">{{ c.date }}</div>
            <div><h3>{{ c.title || '更新' }}</h3><p>{{ c.text }}</p></div>
          </div>
        </div>
      </section>

      <section v-if="nextItems.length" class="section section-last">
        <div class="section-head"><h2>Next</h2><span class="meta">接下来准备做的事</span></div>
        <div class="timeline">
          <div v-for="(c, i) in nextItems" :key="i" class="timeline-row">
            <div class="meta">{{ c.date }}</div>
            <div><h3>{{ c.title || '计划' }}</h3><p>{{ c.text }}</p></div>
          </div>
        </div>
      </section>
      <div v-else class="section-end" />
    </template>
  </div>
</template>

<script setup>
/**
 * 项目详情页(P2-B2,02 号规范第 6 节九段结构)
 * - Live Status 的最近更新取 updated_at,传达"持续进行"语义;
 * - 相关文章按 related_article_slugs 匹配,slug 全部失效时区块整体隐藏;
 * - Changelog 条目 {date,title,text,next?}:next:true 进入 Next 区。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DOMPurify from 'dompurify'
import { API } from '../api'
import ArticleFeedRow from '../components/public/ArticleFeedRow.vue'
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
 * @typedef {Object} PubProjectDetail
 * @property {number} id
 * @property {string} name
 * @property {string} slug
 * @property {string} [description]
 * @property {string} [tag]
 * @property {string[]} [tech_stack]
 * @property {string} status
 * @property {boolean} is_current
 * @property {string} preview_type
 * @property {{url?: string, alt?: string, svg?: string} | null} [preview_data]
 * @property {string} [link_url]
 * @property {string} [repo_url]
 * @property {string} [motivation]
 * @property {string} [progress]
 * @property {string} [design_notes]
 * @property {string[]} [related_article_slugs]
 * @property {Array<{date?: string, title?: string, text?: string, next?: boolean}>} [changelog]
 * @property {string} [updated_at]
 */

/** @type {import('vue').Ref<PubProjectDetail | null>} */
const project = ref(null)
/** @type {import('vue').Ref<any[]>} */
const relatedArticles = ref([])

/** @type {Record<string,string>} */
const STATUS_LABEL = { active: '开发中', paused: '暂停', archived: '已归档' }

/** @param {string} s */
function statusLabel(s) {
  return STATUS_LABEL[s] || s || ''
}

const previewImage = computed(() => project.value?.preview_data?.url || '')
const previewSvg = computed(() => {
  const svg = project.value?.preview_data?.svg || ''
  if (!svg) return ''
  return DOMPurify.sanitize(svg, {
    ALLOWED_TAGS: ['svg', 'path', 'g', 'circle', 'rect', 'line', 'polyline', 'polygon', 'text', 'title'],
    ALLOWED_ATTR: ['viewBox', 'fill', 'stroke', 'stroke-width', 'cx', 'cy', 'r', 'x', 'y', 'width', 'height', 'd', 'points', 'opacity', 'transform', 'xmlns'],
  })
})
const hasPreview = computed(() =>
  Boolean(
    (project.value?.preview_type === 'image' && previewImage.value) ||
      (project.value?.preview_type === 'svg' && previewSvg.value),
  ),
)

/** ④⑤⑥:有内容才渲染对应区块 */
const textBlocks = computed(() => {
  const p = project.value
  if (!p) return []
  const blocks = [
    { key: 'motivation', title: '为什么做', text: p.motivation },
    { key: 'progress', title: '现在做到哪里', text: p.progress },
    { key: 'design', title: '关键设计决策', text: p.design_notes },
  ]
  return blocks
    .filter((b) => String(b.text || '').trim())
    .map((b) => ({ ...b, paragraphs: String(b.text).split(/\n{2,}/).filter(Boolean) }))
})

/** changelog:{date,title,text,next?} */
const changelogItems = computed(() =>
  (Array.isArray(project.value?.changelog) ? project.value.changelog : []).filter((c) => c && !c.next),
)
const nextItems = computed(() =>
  (Array.isArray(project.value?.changelog) ? project.value.changelog : []).filter((c) => c && c.next),
)

/** @param {any} a */
function excerptOf(a) {
  const raw = a.summary || a.content_excerpt || ''
  return String(raw).replace(/[#*`>\[\]]/g, '').slice(0, 90)
}

/** @param {any} a */
function firstTagOf(a) {
  const tags = Array.isArray(a?.tags) ? a.tags : []
  return tags[0] || ''
}

/** @param {string | undefined} s */
function formatDate(s) {
  if (!s) return ''
  try {
    let str = String(s)
    if (!str.endsWith('Z') && !str.includes('+') && !str.includes('-', 10)) str += 'Z'
    const d = new Date(str)
    return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`
  } catch (e) {
    return ''
  }
}

/** 相关文章:公开列表按 slug 匹配,保持配置顺序
 * @param {string[]} slugs
 */
async function loadRelated(slugs) {
  if (!Array.isArray(slugs) || !slugs.length) {
    relatedArticles.value = []
    return
  }
  try {
    const resp = await API.getPublicArticles({ page: 1, page_size: 50 })
    /** @type {any[]} */
    const list = resp?.data?.data?.list || []
    const byslug = new Map(list.map((a) => [a.slug, a]))
    // slug 失效自动跳过;全部失效 → 空数组 → 区块隐藏
    relatedArticles.value = slugs.map((s) => byslug.get(s)).filter(Boolean)
  } catch (e) {
    relatedArticles.value = []
  }
}

async function load() {
  const slugParam = props.slug || route.params.slug
  const slug = Array.isArray(slugParam) ? slugParam[0] : String(slugParam || '')
  loading.value = true
  error.value = false
  notFound.value = false
  project.value = null
  try {
    const resp = await API.getPublicProjectBySlug(slug)
    project.value = resp?.data?.data || null
    if (!project.value) {
      notFound.value = true
      return
    }
    setMeta({
      title: `${project.value.name} · 项目 · 小重山`,
      description: project.value.description || '',
    })
    await loadRelated(project.value.related_article_slugs || [])
  } catch (e) {
    const err = /** @type {{response?: {status?: number}}} */ (e)
    const status = err?.response?.status
    if (status === 404) notFound.value = true
    else error.value = true
  } finally {
    loading.value = false
  }
}

watch(() => props.slug, load)
onMounted(load)
</script>

<style scoped>
.identity {
  padding: 44px 0 26px;
  border-bottom: 1px solid var(--line);
}
.eyebrow {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 10px;
}
.identity h1 {
  font-size: 44px;
  letter-spacing: -0.05em;
  margin: 0 0 12px;
}
.deck {
  font-size: 17px;
  line-height: 1.72;
  color: var(--muted);
  margin: 0 0 18px;
  max-width: 720px;
}
.live-status {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 13px;
}
.live-dot {
  color: var(--signal-ink);
  font-weight: 650;
}
.live-status a {
  color: var(--blue-ink);
}
.live-status .demo-none {
  font-size: 12px;
}
.meta {
  font-size: 12px;
  color: var(--muted);
}

.section {
  padding: 34px 0;
  border-bottom: 1px solid var(--line);
}
.section-last,
.section-end {
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

.body-text p {
  font-size: 16px;
  line-height: 1.85;
  color: var(--text);
  margin: 0 0 16px;
}

.preview-box {
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--surface);
  overflow: hidden;
}
.preview-box img {
  display: block;
  width: 100%;
}
.preview-svg {
  padding: 28px;
}
.preview-svg :deep(svg) {
  width: 100%;
  height: auto;
}

.article-list {
  display: grid;
  gap: 2px;
}

.timeline {
  display: grid;
}
.timeline-row {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 24px;
  padding: 16px 0;
  border-top: 1px solid var(--line);
}
.timeline-row:first-child {
  border-top: 0;
}
.timeline-row h3 {
  font-size: 16px;
  margin: 0 0 5px;
}
.timeline-row p {
  font-size: 13px;
  line-height: 1.6;
  color: var(--muted);
  margin: 0;
}

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
.fallback-space {
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

@media (max-width: 800px) {
  .identity h1 {
    font-size: 36px;
  }
  .timeline-row {
    grid-template-columns: 80px 1fr;
  }
}
</style>
