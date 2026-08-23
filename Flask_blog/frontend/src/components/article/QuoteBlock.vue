<template>
  <BlockShell :block="block" tag="blockquote" class="quote-block">
    <p class="quote-text"><span v-html="block.html" /></p>
    <cite v-if="block.cite">— {{ block.cite }}</cite>
  </BlockShell>
</template>

<script>
import BlockShell from './BlockShell.vue'

export default {
  name: 'QuoteBlock',
  components: { BlockShell },
  props: { block: { type: Object, required: true } },
}
</script>

<style scoped>
/* 03 号规范第 9 节:左侧 3px signal 线,无大面积背景,无大引号图标 */
.quote-block {
  margin: 34px auto;
  border-left: 3px solid var(--signal);
  padding: 3px 0 3px 20px;
}
.quote-text {
  font-size: 20px;
  line-height: 1.65;
  color: #444444;
  margin: 0;
}
cite {
  display: block;
  font-size: 12px;
  font-style: normal;
  color: var(--muted);
  margin-top: 10px;
}
</style>
