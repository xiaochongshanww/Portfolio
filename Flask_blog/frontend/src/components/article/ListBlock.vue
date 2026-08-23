<template>
  <BlockShell :block="block" :tag="block.ordered ? 'ol' : 'ul'" class="list-block">
    <li v-for="(item, i) in block.items" :key="i">
      <span v-html="item.html" />
    </li>
  </BlockShell>
</template>

<script>
import BlockShell from './BlockShell.vue'

export default {
  name: 'ListBlock',
  components: { BlockShell },
  props: { block: { type: Object, required: true } },
}
</script>

<style scoped>
.list-block {
  font-size: 17px;
  line-height: 1.85;
  color: var(--text);
  margin: 0 0 24px;
  padding-left: 23px;
}
.list-block li {
  margin: 7px 0;
}
</style>
