<template>
  <div class="projects-page shell">
    <section class="page-head">
      <div class="eyebrow">项目</div>
      <h1>正在做的东西，比“作品集”更重要。</h1>
      <p>这里记录持续开发中的项目、实验和小工具。项目不是静态展示，而会随着版本、决策和文章一起更新。</p>
    </section>

    <!-- loading -->
    <section v-if="loading" class="section section-last">
      <el-skeleton :rows="8" animated />
    </section>

    <!-- error -->
    <section v-else-if="error" class="section section-last">
      <div class="state-block">
        <p>项目加载失败,请稍后重试。</p>
        <button type="button" class="retry-btn" @click="load">重试</button>
      </div>
    </section>

    <!-- empty -->
    <section v-else-if="!projects.length" class="section section-last">
      <div class="state-block">项目正在整理中,稍后会在这里展示。</div>
    </section>

    <template v-else>
      <!-- 当前项目:is_current 独占大区 -->
      <section v-if="current" class="section">
        <div class="section-head">
          <h2>当前项目</h2>
          <span class="meta">最近更新：{{ formatDate(current.updated_at) }}</span>
        </div>
        <div class="project-feature">
          <div class="project-copy">
            <div>
              <div class="status">● {{ statusLabel(current.status) }}</div>
              <h2>{{ current.name }}</h2>
              <p>{{ current.description }}</p>
            </div>
            <div>
              <a
                class="view-link"
                :href="current.link_url || '/projects/' + current.slug"
                :target="current.link_url ? '_blank' : undefined"
                :rel="current.link_url ? 'noopener noreferrer' : undefined"
                @click.prevent="!current.link_url && router.push('/projects/' + current.slug)"
              ><strong>查看项目 ↗</strong></a>
              <div v-if="techOf(current).length" class="tech-line">{{ techOf(current).join(' · ') }}</div>
            </div>
          </div>
          <div class="project-preview">
            <div class="preview-bar"><i /><i /><i /><span>{{ current.name }}</span></div>
            <div class="preview-stage">
              <!-- preview_type=image:真实截图 -->
              <img
                v-if="current.preview_type === 'image' && previewImage(current)"
                :src="previewImage(current)"
                :alt="current.name"
                loading="lazy"
              >
              <!-- preview_type=svg:语义示意(后台数据,经 DOMPurify 消毒) -->
              <!-- eslint-disable-next-line vue/no-v-html -- svg 来自管理端配置,出口消毒 -->
              <div
                v-else-if="current.preview_type === 'svg' && previewSvg(current)"
                class="preview-svg"
                v-html="previewSvg(current)"
              />
              <!-- none:规范空态 -->
              <div v-else class="preview-empty">当前版本暂未开放在线体验</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 其它项目与实验 -->
      <section class="section section-last">
        <div class="section-head">
          <h2>其它项目与实验</h2>
        </div>
        <div v-if="others.length" class="project-grid">
          <a
            v-for="p in others"
            :key="p.id"
            class="project-card"
            :href="'/projects/' + p.slug"
            @click.prevent="router.push('/projects/' + p.slug)"
          >
            <div>
              <span v-if="p.tag" class="tag">{{ p.tag }}</span>
              <h3>{{ p.name }}</h3>
              <p>{{ p.description }}</p>
            </div>
            <div class="project-footer">
              <span class="tech">{{ techOf(p).join(' · ') }}</span>
              <span class="arrow">↗</span>
            </div>
          </a>
        </div>
        <div v-else class="state-block">暂时没有其它项目。</div>
      </section>
    </template>
  </div>
</template>

<script setup>
/**
 * 项目列表页(P2-B1,原型 xiaochongshan-2026-projects-v1)
 * 数据来自 Project API;is_current 独占大区,其余 2 列轻卡。
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import DOMPurify from 'dompurify'
import { API } from '../api'
import { setMeta } from '../composables/useMeta'

/**
 * @typedef {Object} PubProject
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
 * @property {string} [updated_at]
 */

const router = useRouter()
const loading = ref(true)
const error = ref(false)
/** @type {import('vue').Ref<PubProject[]>} */
const projects = ref([])

const current = computed(() => projects.value.find((p) => p.is_current) || null)
const others = computed(() => projects.value.filter((p) => !p.is_current))

/** @type {Record<string,string>} */
const STATUS_LABEL = { active: '开发中', paused: '暂停', archived: '已归档' }

/** @param {string} s */
function statusLabel(s) {
  return STATUS_LABEL[s] || s || ''
}

/** @param {PubProject} p */
function techOf(p) {
  return Array.isArray(p.tech_stack) ? p.tech_stack : []
}

/** @param {PubProject} p */
function previewImage(p) {
  const url = p.preview_data?.url || ''
  return url || ''
}

/** preview svg 仅保留 svg 基础标签,防注入 */
/** @param {PubProject} p */
function previewSvg(p) {
  const svg = p.preview_data?.svg || ''
  if (!svg) return ''
  return DOMPurify.sanitize(svg, {
    ALLOWED_TAGS: ['svg', 'path', 'g', 'circle', 'rect', 'line', 'polyline', 'polygon', 'text', 'title'],
    ALLOWED_ATTR: ['viewBox', 'fill', 'stroke', 'stroke-width', 'cx', 'cy', 'r', 'x', 'y', 'width', 'height', 'd', 'points', 'opacity', 'transform', 'xmlns'],
  })
}

/** @param {string | undefined} s */
function formatDate(s) {
  if (!s) return ''
  try {
    let str = String(s)
    if (!str.endsWith('Z') && !str.includes('+') && !str.includes('-', 10)) str += 'Z'
    const d = new Date(str)
    return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月`
  } catch (e) {
    return ''
  }
}

async function load() {
  loading.value = true
  error.value = false
  try {
    const resp = await API.getPublicProjects()
    projects.value = resp?.data?.data?.list || []
  } catch (e) {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  setMeta({ title: '项目 · 小重山', description: '持续开发中的项目、实验和小工具。' })
  load()
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
.tag {
  display: inline-flex;
  padding: 5px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  font-size: 11px;
  color: var(--muted);
}

/* 当前项目大区 */
.project-feature {
  display: grid;
  grid-template-columns: 0.82fr 1.18fr;
  gap: 14px;
}
.project-copy {
  min-height: 300px;
  padding: 28px;
  border-radius: 18px;
  background: var(--text);
  color: var(--bg);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.project-copy .status {
  font-size: 12px;
  color: var(--on-inverse-soft);
}
.project-copy h2 {
  font-size: 31px;
  letter-spacing: -0.045em;
  margin: 8px 0 10px;
}
.project-copy p {
  font-size: 14px;
  line-height: 1.7;
  color: var(--on-inverse-soft);
  margin: 0;
}
.view-link strong {
  font-size: 15px;
}
.tech-line {
  margin-top: 9px;
  font-size: 11px;
  color: var(--on-inverse-faint);
}
.project-preview {
  min-height: 300px;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--surface);
}
.preview-bar {
  height: 42px;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 14px;
  font-size: 11px;
  color: var(--muted);
}
.preview-bar i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--line-strong);
}
.preview-stage {
  position: absolute;
  inset: 58px 24px 22px;
  border: 1px solid var(--line);
  border-radius: 13px;
  background:
    linear-gradient(var(--line) 1px, transparent 1px),
    linear-gradient(90deg, var(--line) 1px, transparent 1px);
  background-size: 30px 30px;
  display: grid;
  place-items: center;
  overflow: hidden;
}
.preview-stage img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.preview-svg {
  width: 88%;
  height: 88%;
}
.preview-empty {
  font-size: 12px;
  color: var(--muted);
}

/* 其它项目 2 列轻卡 */
.project-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}
.project-card {
  min-height: 200px;
  padding: 21px;
  border: 1px solid var(--line);
  border-radius: 17px;
  background: var(--surface);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: border-color var(--transition);
}
.project-card:hover {
  border-color: var(--line-strong);
}
.project-card h3 {
  font-size: 22px;
  margin: 8px 0;
}
.project-card p {
  font-size: 13px;
  line-height: 1.65;
  color: var(--muted);
  margin: 0;
}
.project-footer {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 20px;
  margin-top: 24px;
}
.tech {
  font-size: 11px;
  color: var(--muted);
}
.arrow {
  color: var(--muted);
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

@media (max-width: 850px) {
  .project-feature,
  .project-grid {
    grid-template-columns: 1fr;
  }
  .page-head {
    padding-top: 36px;
  }
  .page-head h1 {
    font-size: 34px;
  }
}
</style>
