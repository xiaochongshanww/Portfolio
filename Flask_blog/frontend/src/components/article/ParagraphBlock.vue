<template>
  <BlockShell :block="block" tag="p" class="para-block">
    <span v-html="block.html" />
  </BlockShell>
</template>

<script>
import BlockShell from './BlockShell.vue'

export default {
  name: 'ParagraphBlock',
  components: { BlockShell },
  props: { block: { type: Object, required: true } },
}
</script>

<style scoped>
.para-block {
  font-size: 17px;
  line-height: 1.9;
  color: var(--text);
  margin: 0 0 24px;
  overflow-wrap: break-word;
}
</style>
