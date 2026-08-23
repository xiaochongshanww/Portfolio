<template>
  <!-- RagFlowVisual: 问题 → 检索 → 上下文 → 生成 -->
  <div v-if="type === 'rag'" class="tv-flow">
    <span class="tv-node">问题<small>输入</small></span><i>→</i>
    <span class="tv-node">检索<small>召回</small></span><i>→</i>
    <span class="tv-node">上下文<small>组织</small></span><i>→</i>
    <span class="tv-node">生成<small>回答</small></span>
  </div>

  <!-- GitGraphVisual: commit graph -->
  <div v-else-if="type === 'git'" class="tv-mono">●──●──●<br>&nbsp;&nbsp;╲<br>&nbsp;&nbsp;&nbsp;●──●</div>

  <!-- TokenVisual: JWT 结构 -->
  <div v-else-if="type === 'token'" class="tv-mono">header.payload.signature</div>

  <!-- ArchitectureVisual: Role → Permission → Scope -->
  <div v-else-if="type === 'arch'" class="tv-mono">Role → Permission<br>↓<br>Scope → Resource</div>

  <!-- CustomVisual 兜底:纯文本等宽字符画 -->
  <div v-else-if="type === 'custom' && text" class="tv-mono">{{ text }}</div>

  <!-- 无匹配:不渲染(规范允许隐藏该列) -->
</template>

<script>
/**
 * TechnicalVisual(02 号规范第 11 节):表达内容而非装饰。
 * P0 实现 rag/git/token/arch 四种语义图 + custom 文本兜底;
 * 无匹配时不渲染任何内容。
 */
export default {
  name: 'TechnicalVisual',
  props: {
    type: { type: String, default: '' },
    /** custom 类型的等宽字符画文本 */
    text: { type: String, default: '' },
  },
}
</script>

<style scoped>
.tv-flow {
  display: grid;
  grid-template-columns: 1fr 18px 1fr 18px 1fr 18px 1fr;
  align-items: center;
  gap: 4px;
  width: 100%;
}
.tv-node {
  border: 1px solid var(--line-strong);
  background: var(--surface);
  border-radius: 12px;
  padding: 13px 4px;
  text-align: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}
.tv-node small {
  display: block;
  font-size: 10px;
  font-weight: 400;
  color: var(--muted);
  margin-top: 4px;
}
.tv-flow i {
  font-style: normal;
  color: var(--signal);
  text-align: center;
}

.tv-mono {
  height: 66px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface);
  display: grid;
  place-items: center;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 10px;
  color: var(--muted);
  padding: 8px;
  text-align: center;
  line-height: 1.5;
}

@media (max-width: 640px) {
  .tv-flow { grid-template-columns: 1fr; }
  .tv-flow i { transform: rotate(90deg); }
}
</style>
