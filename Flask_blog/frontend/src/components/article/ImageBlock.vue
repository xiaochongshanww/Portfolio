<template>
  <BlockShell :block="block" tag="figure" class="image-block">
    <div class="image-frame">
      <img :src="block.src" :alt="block.alt || ''" loading="lazy">
    </div>
    <figcaption v-if="block.caption" class="image-caption">{{ block.caption }}</figcaption>
  </BlockShell>
</template>

<script>
import BlockShell from './BlockShell.vue'

export default {
  name: 'ImageBlock',
  components: { BlockShell },
  props: { block: { type: Object, required: true } },
}
</script>

<style scoped>
/* 03 号规范第 11 节:架构图默认 wide;caption 回到 text 宽度 */
.image-block {
  margin: 34px auto;
}
.image-frame {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--surface);
  overflow: hidden;
}
.image-frame img {
  display: block;
  width: 100%;
  height: auto;
}
.image-caption {
  width: min(100%, var(--w-text));
  margin: 10px auto 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
}
</style>
