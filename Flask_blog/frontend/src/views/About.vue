<template>
  <div class="about-page shell">
    <section class="about-grid">
      <div class="about-copy">
        <div class="eyebrow">关于</div>
        <h1>{{ ABOUT_HEADLINE }}</h1>
        <p v-for="(para, i) in ABOUT_NARRATIVE" :key="i">{{ para }}</p>
      </div>
      <aside class="side-note">
        <h3>现在</h3>
        <div class="note-list">
          <div v-for="item in ABOUT_NOW" :key="item.label" class="note">
            <b>{{ item.label }}</b>
            <span>{{ item.text }}</span>
          </div>
        </div>
      </aside>
    </section>

    <section class="section section-last">
      <div class="section-head">
        <h2>这几年在做什么</h2>
      </div>
      <div class="timeline">
        <div v-for="row in ABOUT_TIMELINE" :key="row.year + row.title" class="timeline-row">
          <div class="year">{{ row.year }}</div>
          <div>
            <h3>{{ row.title }}</h3>
            <p>{{ row.text }}</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
/**
 * 关于页(P2-C1,原型 xiaochongshan-2026-about-v1)
 * 反履历:无姓名/年龄/学校/公司/技能百分比;内容全部来自 data/aboutNow.ts。
 */
import { onMounted } from 'vue'
import {
  ABOUT_HEADLINE,
  ABOUT_NARRATIVE,
  ABOUT_NOW,
  ABOUT_TIMELINE,
} from '../data/aboutNow'
import { setMeta } from '../composables/useMeta'

onMounted(() => {
  setMeta({ title: '关于 · 小重山', description: ABOUT_NARRATIVE[0] || '' })
})
</script>

<style scoped>
.about-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 60px;
  padding: 42px 0 34px;
  border-bottom: 1px solid var(--line);
}
.eyebrow {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 10px;
}
.about-copy h1 {
  font-size: 42px;
  letter-spacing: -0.05em;
  margin: 0 0 18px;
}
.about-copy p {
  font-size: 16px;
  line-height: 1.85;
  color: var(--text-2);
  margin: 0 0 18px;
  max-width: 700px;
}

.side-note {
  border: 1px solid var(--line);
  border-radius: 17px;
  background: var(--surface);
  padding: 20px;
  align-self: start;
}
.side-note h3 {
  font-size: 14px;
  margin: 0 0 12px;
}
.note-list {
  display: grid;
  gap: 11px;
}
.note {
  padding-top: 11px;
  border-top: 1px solid var(--line);
}
.note:first-child {
  padding-top: 0;
  border-top: 0;
}
.note b {
  display: block;
  font-size: 13px;
}
.note span {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.5;
}

.section {
  padding: 34px 0;
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

.timeline {
  display: grid;
}
.timeline-row {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 24px;
  padding: 17px 0;
  border-top: 1px solid var(--line);
}
.timeline-row:first-child {
  border-top: 0;
}
.timeline-row .year {
  font-size: 13px;
  color: var(--muted);
}
.timeline-row h3 {
  font-size: 17px;
  margin: 0 0 5px;
}
.timeline-row p {
  font-size: 13px;
  line-height: 1.6;
  color: var(--muted);
  margin: 0;
}

@media (max-width: 800px) {
  .about-grid {
    grid-template-columns: 1fr;
    gap: 28px;
  }
  .about-copy h1 {
    font-size: 34px;
  }
  .timeline-row {
    grid-template-columns: 80px 1fr;
  }
}
</style>
