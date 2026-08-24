<template>
  <BlockShell :block="block" :tag="`h${block.level}`" class="heading-block">
    <!-- data-toc-anchor:ReadingRail 的 IntersectionObserver 据此高亮当前章节 -->
    <span :id="block.anchor" :data-toc-anchor="block.anchor">{{ block.text }}</span>
  </BlockShell>
</template>

<script>
import BlockShell from './BlockShell.vue'

export default {
  name: 'HeadingBlock',
  components: { BlockShell },
  props: { block: { type: Object, required: true } },
}
</script>

<style scoped>
.heading-block {
  color: var(--text);
  letter-spacing: -0.02em;
  /* 锚点跳转时避开 sticky header */
  scroll-margin-top: 90px;
}
.heading-block.h2,
h2.heading-block {
  font-size: 29px;
  line-height: 1.25;
  margin: 50px auto 18px;
}
h3.heading-block {
  font-size: 21px;
  line-height: 1.35;
  margin: 34px auto 14px;
}
h4.heading-block,
h5.heading-block,
h6.heading-block {
  font-size: 18px;
  margin: 28px auto 12px;
}
</style>
