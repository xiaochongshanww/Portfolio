<template>
  <BlockShell :block="block" tag="div" class="fallback-block">
    <div class="fallback-inner">
      <span class="fallback-tag">{{ block.type }}</span>
      <span class="fallback-text">{{ label }}</span>
    </div>
  </BlockShell>
</template>

<script>
import BlockShell from './BlockShell.vue'

/** @type {Record<string, string>} */
const LABELS = {
  gallery: '图片组',
  diagram: '架构图',
  embed: '交互内容',
  media: '媒体内容',
  attachment: '附件',
  tabs: '多标签内容',
  custom: '扩展内容',
}

export default {
  name: 'FallbackBlock',
  components: { BlockShell },
  props: { block: { type: Object, required: true } },
  computed: {
    label() {
      return LABELS[String(this.block.type)] || '该内容类型即将支持'
    },
  },
}
</script>

<style scoped>
.fallback-block {
  margin: 30px auto;
}
.fallback-inner {
  border: 1px dashed var(--line-strong);
  border-radius: 14px;
  background: var(--surface-2);
  padding: 22px;
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--muted);
  font-size: 13px;
}
.fallback-tag {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11px;
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 6px;
  padding: 2px 8px;
}
</style>
