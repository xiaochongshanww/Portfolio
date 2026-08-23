<template>
  <div class="article-renderer">
    <component
      :is="componentFor(block)"
      v-for="block in blocks"
      :key="block.id"
      :block="block"
    />
  </div>
</template>

<script>
/**
 * 统一 Block 渲染器(03 号规范第 27 节)。
 * P0 实现 8 个基础 Block;gallery/diagram/embed/media/attachment/tabs/custom
 * 渲染为 FallbackBlock,组件随 P1 补齐。
 * 兼容性红线:旧 Markdown 文章经 blocksFromMarkdown 后必须完整渲染。
 */
import ParagraphBlock from './ParagraphBlock.vue'
import HeadingBlock from './HeadingBlock.vue'
import ListBlock from './ListBlock.vue'
import QuoteBlock from './QuoteBlock.vue'
import CalloutBlock from './CalloutBlock.vue'
import CodeBlock from './CodeBlock.vue'
import ImageBlock from './ImageBlock.vue'
import TableBlock from './TableBlock.vue'
import FallbackBlock from './FallbackBlock.vue'

const blockComponentMap = {
  paragraph: ParagraphBlock,
  heading: HeadingBlock,
  list: ListBlock,
  quote: QuoteBlock,
  callout: CalloutBlock,
  code: CodeBlock,
  image: ImageBlock,
  table: TableBlock,
}

export default {
  name: 'ArticleRenderer',
  components: { FallbackBlock },
  props: {
    blocks: {
      type: /** @type {import('vue').PropType<import('../../types/articleBlocks').ArticleBlock[]>} */ (Array),
      required: true,
    },
  },
  methods: {
    componentFor(block) {
      const comp = blockComponentMap[block.type]
      if (!comp) {
        if (import.meta.env?.DEV) {
          console.warn(`[ArticleRenderer] 未实现的 Block 类型: ${block.type},使用 fallback`)
        }
        return 'FallbackBlock'
      }
      return comp
    },
  },
}
</script>

<style scoped>
.article-renderer {
  /* 内容轴由各 Block 的 content-width-* 类控制 */
}
</style>
