<template>
  <component
    :is="href ? 'a' : 'div'"
    :href="href"
    class="feed-row"
    :class="{ 'feed-row-static': !href }"
  >
    <div class="feed-date">{{ dateLabel }}</div>
    <div class="feed-body">
      <h3 class="feed-title">{{ title }}</h3>
      <p v-if="summary" class="feed-summary">{{ summary }}</p>
    </div>
    <div v-if="$slots.visual" class="feed-visual">
      <slot name="visual" />
    </div>
    <!-- P1:行尾 meta(所属 tag 等),无 visual 时占用第三列 -->
    <div v-else-if="$slots.meta" class="feed-meta">
      <slot name="meta" />
    </div>
    <div class="feed-arrow" aria-hidden="true">→</div>
  </component>
</template>

<script>
/**
 * 文章 Feed 行(02 号规范第 10 节)
 * 桌面: Date | Title+Summary | Visual | →
 * 移动: Date 换行 + 隐藏 Visual
 * 禁止字段(作者/字数/点赞/收藏/评论/阅读量)不进入本组件 props。
 */
import { computed } from 'vue'

export default {
  name: 'ArticleFeedRow',
  props: {
    title: { type: String, required: true },
    summary: { type: String, default: '' },
    publishedAt: { type: String, required: true },
    href: { type: String, default: '' },
  },
  setup(props) {
    const dateLabel = computed(() => {
      try {
        let s = props.publishedAt
        if (s && !s.endsWith('Z') && !s.includes('+') && !s.includes('-', 10)) s += 'Z'
        const d = new Date(s)
        return `${d.getMonth() + 1} 月 ${d.getDate()} 日`
      } catch (e) {
        return ''
      }
    })
    return { dateLabel }
  },
}
</script>

<style scoped>
.feed-row {
  display: grid;
  grid-template-columns: 95px 1fr 170px 26px;
  gap: 20px;
  align-items: center;
  padding: 19px 14px;
  border-radius: 14px;
  border: 1px solid transparent;
}
/* hover 克制:仅背景与边框变化(01 号规范第 7 节) */
.feed-row:hover:not(.feed-row-static) {
  background: var(--surface);
  border-color: var(--line);
}
.feed-date {
  font-size: 13px;
  color: var(--muted);
}
.feed-title {
  font-size: 20px;
  letter-spacing: -0.02em;
  margin: 0 0 6px;
  line-height: 1.4;
}
.feed-summary {
  font-size: 13px;
  color: var(--muted);
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.feed-visual {
  min-width: 0;
}
.feed-meta {
  font-size: 12px;
  color: var(--muted);
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
}
.feed-arrow {
  color: var(--muted);
  text-align: center;
}

@media (max-width: 900px) {
  .feed-row { grid-template-columns: 80px 1fr 26px; }
  .feed-visual { display: none; }
}
@media (max-width: 650px) {
  .feed-row { grid-template-columns: 1fr 26px; }
  .feed-date { grid-column: 1 / -1; }
}
</style>
