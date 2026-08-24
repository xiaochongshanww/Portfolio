<template>
  <BlockShell :block="block" tag="aside" class="callout-block" :class="`tone-${block.tone || 'note'}`">
    <div v-if="block.title" class="callout-label">{{ block.title }}</div>
    <div class="callout-body"><span v-html="block.html" /></div>
  </BlockShell>
</template>

<script>
import BlockShell from './BlockShell.vue'

export default {
  name: 'CalloutBlock',
  components: { BlockShell },
  props: { block: { type: Object, required: true } },
}
</script>

<style scoped>
/* 03 号规范第 8 节:callout 不出现过多颜色,signal-soft 为默认强调 */
.callout-block {
  margin: 30px auto;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 18px 20px;
  background: var(--signal-soft);
}
.tone-note {
  border-color: color-mix(in srgb, var(--signal) 25%, var(--line));
}
.tone-info {
  background: var(--blue-soft);
  border-color: color-mix(in srgb, var(--blue-ink) 22%, var(--line));
}
.tone-success {
  background: var(--green-soft);
  border-color: color-mix(in srgb, var(--green-ink) 22%, var(--line));
}
.tone-warning {
  background: var(--signal-soft);
  border-color: var(--signal);
}
.callout-label {
  font-size: 12px;
  font-weight: 720;
  color: var(--signal-ink);
  margin-bottom: 6px;
}
.tone-info .callout-label { color: var(--blue-ink); }
.tone-success .callout-label { color: var(--green-ink); }
.callout-body {
  font-size: 15px;
  line-height: 1.7;
  color: var(--callout-note-text);
  margin: 0;
}
.tone-info .callout-body { color: var(--callout-info-text); }
.tone-success .callout-body { color: var(--callout-success-text); }
</style>
