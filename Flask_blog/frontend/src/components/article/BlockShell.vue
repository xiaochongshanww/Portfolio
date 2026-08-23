<template>
  <component
    :is="tag"
    class="block-shell"
    :class="`content-width-${resolvedWidth}`"
  >
    <slot />
  </component>
</template>

<script>
/**
 * Block 宽度外壳:所有 Block 组件通过它消费 block.width,
 * 映射到全局 content-width-* 类(03 号规范第 27 节——组件不得自写宽度 CSS)。
 */
import { DEFAULT_BLOCK_WIDTH } from '../../types/articleBlocks'

export default {
  name: 'BlockShell',
  props: {
    /** ArticleBlock 或至少含 type/width 字段 */
    block: { type: Object, required: true },
    tag: { type: String, default: 'div' },
  },
  computed: {
    resolvedWidth() {
      return this.block.width || DEFAULT_BLOCK_WIDTH[this.block.type] || 'text'
    },
  },
}
</script>

<style scoped>
.block-shell {
  /* 宽度由全局 content-width-* 提供;此处只做纵向节奏 */
}
.block-shell + .block-shell {
  margin-top: 0; /* 节奏由各 Block 自身 margin 控制 */
}
</style>
