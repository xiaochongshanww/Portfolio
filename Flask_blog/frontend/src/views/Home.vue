<template>
  <div class="home-public">
    <!-- Intro(02 号规范 2.3):不是 Hero,只建立页面状态 -->
    <section class="page-intro">
      <div>
        <h1>最近在写，也在做。</h1>
        <p>Python · AI · 软件工程 · 产品实践</p>
      </div>
      <div class="live"><i />持续更新中</div>
    </section>

    <!-- 加载态 -->
    <section v-if="loading" class="section">
      <el-skeleton :rows="6" animated />
    </section>

    <!-- 错误态 -->
    <section v-else-if="error" class="section">
      <div class="state-block">
        <p>内容加载失败,请稍后重试。</p>
        <button type="button" class="retry-btn" @click="loadAll">重试</button>
      </div>
    </section>

    <!-- 空态 -->
    <section v-else-if="!articles.length" class="section">
      <div class="state-block">
        <p>还没有发布文章。</p>
      </div>
    </section>

    <template v-else>
      <!-- 最近更新(C2) -->
      <section v-if="featured" class="section">
        <div class="section-head">
          <h2>最近更新</h2>
          <a href="/archive" @click.prevent="$router.push('/archive')">全部文章 →</a>
        </div>
        <a class="latest-card" :href="'/article/' + featured.slug" @click.prevent="goArticle(featured.slug)">
          <div class="latest-copy">
            <span class="badge">新文章</span>
            <h3>{{ featured.title }}</h3>
            <p class="latest-summary">{{ featuredSummary }}</p>
            <div class="meta">
              <span>{{ featured.category || '文章' }}</span><i>·</i>
              <span>{{ formatDate(featured.published_at) }}</span>
            </div>
            <span class="read-more">阅读全文 →</span>
          </div>
          <div class="latest-visual">
            <TechnicalVisual
              :type="featuredVisualType"
              :text="''"
            />
          </div>
        </a>
      </section>

      <!-- 正在进行(C3):P0 本地占位数据 -->
      <section v-if="currentProject" class="section">
        <div class="section-head">
          <h2>正在进行</h2>
        </div>
        <div class="project-grid">
          <a class="project-copy" href="/projects" @click.prevent="$router.push('/projects')">
            <div>
              <div class="status">● {{ currentProject.statusLabel }}</div>
              <h3>{{ currentProject.name }}</h3>
              <p>{{ currentProject.description }}</p>
            </div>
            <strong>查看项目 ↗</strong>
          </a>
          <div class="project-preview">
            <div class="toolbar"><i /><i /><i /><span>{{ currentProject.name }}</span></div>
            <div class="canvas" />
          </div>
        </div>
      </section>

      <!-- 最近文章(C4) -->
      <section class="section">
        <div class="section-head">
          <h2>最近文章</h2>
          <a href="/archive" @click.prevent="$router.push('/archive')">进入归档 →</a>
        </div>
        <div class="feed">
          <ArticleFeedRow
            v-for="a in feedArticles"
            :key="a.id"
            :title="a.title"
            :summary="excerptOf(a)"
            :published-at="a.published_at || a.created_at"
            :href="'/article/' + a.slug"
          >
            <template #visual>
              <TechnicalVisual
                :type="visualTypeFor(a.category, a.tags)"
                :text="''"
              />
            </template>
          </ArticleFeedRow>
        </div>
      </section>

      <!-- 长期专题(C6):P0 用 categories 映射 -->
      <section v-if="topics.length" class="section section-last">
        <div class="section-head">
          <h2>长期专题</h2>
        </div>
        <div class="topic-grid">
          <a
            v-for="(t, i) in topics"
            :key="t.id"
            class="topic-card"
            :class="`topic-tone-${i % 4}`"
            :href="'/topics/' + t.slug"
            @click.prevent="$router.push('/topics/' + t.slug)"
          >
            <small>{{ t.count != null ? `${t.count} 篇文章` : '' }}</small>
            <h3>{{ t.name }}</h3>
            <span>{{ t.description || '持续更新的主题' }}</span>
          </a>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
/**
 * 公开站首页(impl-P0 分组 C)
 * 职责边界(02 号规范第 2 节):回答"最近写什么/在做什么/还有哪些/长期主题",
 * 不承担个人介绍、归档、项目全集;不显示作者/点赞等社区元数据。
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { API } from '../api'
import ArticleFeedRow from '../components/public/ArticleFeedRow.vue'
import TechnicalVisual from '../components/public/TechnicalVisual.vue'
import { visualTypeFor } from '../utils/visualMapping'

const router = useRouter()
const loading = ref(true)
const error = ref(false)
const articles = ref([])
const topics = ref([])

// C3 占位数据:P2 接入后端 Project API 后替换
const currentProject = {
  name: 'Structure Lab',
  statusLabel: '开发中',
  description: '把结构稳定性变成可以拖动、观察和验证的互动实验。',
}

const featured = computed(() => articles.value[0] || null)

const featuredSummary = computed(() => excerptOf(featured.value || {}))

const featuredVisualType = computed(() =>
  visualTypeFor(featured.value?.category, featured.value?.tags),
)

/** C4:跳过 featured 的剩余文章 */
const feedArticles = computed(() => articles.value.slice(1, 8))

function excerptOf(a) {
  const raw = a.summary || a.content_excerpt || ''
  return String(raw).replace(/[#*`>\[\]]/g, '').slice(0, 90)
}

function formatDate(s) {
  try {
    let str = s
    if (str && !str.endsWith('Z') && !str.includes('+') && !str.includes('-', 10)) str += 'Z'
    const d = new Date(str)
    return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`
  } catch (e) {
    return ''
  }
}

function goArticle(slug) {
  router.push(`/article/${slug}`)
}

async function loadAll() {
  loading.value = true
  error.value = false
  try {
    const [artRes, taxRes] = await Promise.allSettled([
      API.getPublicArticles({ page: 1, page_size: 10 }),
      API.getPublicTaxonomy(),
    ])
    if (artRes.status === 'fulfilled') {
      const data = artRes.value?.data?.data
      articles.value = data?.list || []
    } else {
      error.value = true
    }
    if (taxRes.status === 'fulfilled') {
      const cats = taxRes.value?.data?.data?.categories || []
      // C6:最多取 4 个分类作为专题卡;slug 兜底用 id
      topics.value = cats.slice(0, 4).map((c) => ({
        id: c.id,
        slug: c.slug || String(c.id),
        name: c.name,
        description: c.description || '',
        count: c.article_count ?? c.count ?? null,
      }))
    }
  } catch (e) {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.home-public {
  padding-top: 0;
}
.page-intro {
  padding: 30px 0 22px;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 28px;
}
.page-intro h1 {
  font-size: 27px;
  letter-spacing: -0.04em;
  margin: 0 0 7px;
}
.page-intro p {
  margin: 0;
  color: var(--muted);
  font-size: 15px;
}
.live {
  font-size: 13px;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}
.live i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--signal);
  box-shadow: 0 0 0 4px rgba(255, 92, 53, 0.12);
}

.section {
  padding: 40px 0;
  border-bottom: 1px solid var(--line);
}
.section-last {
  border-bottom: 0;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}
.section-head h2 {
  font-size: 15px;
  margin: 0;
  font-weight: 700;
}
.section-head a {
  font-size: 13px;
  color: var(--muted);
}
.section-head a:hover {
  color: var(--text);
}

/* C2 最近更新 */
.latest-card {
  display: grid;
  grid-template-columns: 1fr 360px;
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 20px;
  overflow: hidden;
  transition: border-color var(--transition);
}
.latest-card:hover {
  border-color: var(--line-strong);
}
.latest-copy {
  padding: 30px 32px;
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 10px;
  background: var(--signal-soft);
  color: var(--signal-ink);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}
.badge::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--signal);
}
.latest-copy h3 {
  font-size: 32px;
  line-height: 1.13;
  letter-spacing: -0.045em;
  margin: 18px 0 12px;
}
.latest-summary {
  font-size: 15px;
  line-height: 1.75;
  color: var(--muted);
  margin: 0;
  max-width: 640px;
}
.meta {
  display: flex;
  gap: 9px;
  flex-wrap: wrap;
  align-items: center;
  font-size: 12px;
  color: var(--muted);
  margin-top: 19px;
}
.meta i {
  font-style: normal;
}
.read-more {
  display: inline-flex;
  gap: 8px;
  margin-top: 21px;
  font-size: 14px;
  font-weight: 700;
}
.latest-visual {
  background: var(--surface-2);
  border-left: 1px solid var(--line);
  display: grid;
  place-items: center;
  padding: 28px;
}

/* C3 项目区 */
.project-grid {
  display: grid;
  grid-template-columns: 0.82fr 1.18fr;
  gap: 14px;
}
.project-copy {
  background: var(--text);
  color: var(--bg);
  border-radius: 18px;
  padding: 28px;
  min-height: 280px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.project-copy .status {
  font-size: 12px;
  color: #bbbbbb;
  display: flex;
  gap: 7px;
  align-items: center;
}
.project-copy h3 {
  font-size: 29px;
  letter-spacing: -0.04em;
  margin: 9px 0;
}
.project-copy p {
  font-size: 14px;
  line-height: 1.7;
  color: #bbbbbb;
  margin: 0;
}
.project-preview {
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 18px;
  min-height: 280px;
  position: relative;
  overflow: hidden;
}
.toolbar {
  height: 40px;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  padding: 0 14px;
  color: var(--muted);
  font-size: 11px;
  gap: 6px;
}
.toolbar i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--line-strong);
}
.canvas {
  position: absolute;
  inset: 58px 22px 22px;
  border: 1px solid var(--line);
  border-radius: 13px;
  background:
    linear-gradient(var(--line) 1px, transparent 1px),
    linear-gradient(90deg, var(--line) 1px, transparent 1px);
  background-size: 30px 30px;
}

/* C4 Feed */
.feed {
  display: grid;
  gap: 8px;
}

/* C6 专题 */
.topic-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.topic-card {
  min-height: 138px;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: transform var(--transition), border-color var(--transition);
}
.topic-card:hover {
  transform: translateY(-1px);
  border-color: var(--line-strong);
}
.topic-tone-0 { background: var(--green-soft); }
.topic-tone-1 { background: var(--blue-soft); }
.topic-tone-2 { background: var(--signal-soft); }
.topic-tone-3 { background: var(--sand); }
.topic-card small {
  font-size: 12px;
  color: var(--muted);
}
.topic-card h3 {
  font-size: 19px;
  margin: 0;
}
.topic-card span {
  font-size: 12px;
  color: var(--muted);
}

/* 状态块 */
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

@media (max-width: 900px) {
  .latest-card,
  .project-grid { grid-template-columns: 1fr; }
  .latest-visual {
    border-left: 0;
    border-top: 1px solid var(--line);
  }
  .topic-grid { grid-template-columns: repeat(2, 1fr); }
  .latest-copy h3 { font-size: 26px; }
}
@media (max-width: 650px) {
  .page-intro { flex-direction: column; align-items: flex-start; }
  .topic-grid { grid-template-columns: 1fr; }
  .home-public { padding-left: 0; padding-right: 0; }
}
@media (max-width: 650px) {
  .shell-padding { padding: 0; }
}
</style>

<style>
/* 公共页容器内边距:由壳提供,首页自身不重复 */
.public-main > * {
}
</style>
