<template>
  <BlockShell :block="block" tag="figure" class="code-block">
    <div class="code-head">
      <span class="code-title">{{ block.filename || block.language }}</span>
      <button type="button" class="copy-btn" @click="copy">
        {{ copied ? '已复制' : '复制' }}
      </button>
    </div>
    <div class="code-body" v-html="highlighted" />
  </BlockShell>
</template>

<script>
import { ref, onMounted } from 'vue'
import BlockShell from './BlockShell.vue'
import { highlightCode } from '../../utils/blockHighlighter'

export default {
  name: 'CodeBlock',
  components: { BlockShell },
  props: { block: { type: Object, required: true } },
  setup(props) {
    const highlighted = ref('')
    const copied = ref(false)

    onMounted(async () => {
      try {
        highlighted.value = await highlightCode(props.block.code, props.block.language || 'text')
      } catch (e) {
        // shiki 失败时降级为纯文本,不阻塞阅读
        const esc = String(props.block.code ?? '')
          .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        highlighted.value = `<pre class="shiki-plain"><code>${esc}</code></pre>`
      }
    })

    async function copy() {
      try {
        await navigator.clipboard.writeText(props.block.code)
        copied.value = true
        setTimeout(() => { copied.value = false }, 1600)
      } catch (e) { /* 剪贴板不可用时静默 */ }
    }

    return { highlighted, copied, copy }
  },
}
</script>

<style scoped>
/* 03 号规范第 10 节:独立组件,头部栏 + 复制 + 横向滚动 */
.code-block {
  margin: 30px auto;
  border-radius: 15px;
  background: var(--code);
  overflow: hidden;
}
.code-head {
  height: 42px;
  border-bottom: 1px solid var(--code-line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 15px;
  color: var(--code-head);
  font-size: 11px;
}
.code-title {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.copy-btn {
  border: 1px solid var(--code-btn-border);
  background: var(--code-btn-bg);
  color: var(--code-btn-text);
  border-radius: 7px;
  padding: 5px 8px;
  font-size: 10px;
  cursor: pointer;
}
.copy-btn:hover { color: var(--code-text); }
.code-body {
  font-size: 13px;
  line-height: 1.75;
}
.code-body :deep(pre) {
  margin: 0;
  padding: 20px 22px;
  overflow-x: auto;
  background: transparent !important;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.code-body :deep(code) {
  display: block;
  background: transparent !important;
  font-family: inherit;
}
</style>
