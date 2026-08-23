<template>
  <BlockShell :block="block" tag="div" class="table-block">
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th v-for="(h, i) in block.head" :key="i"><span v-html="h" /></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, ri) in block.rows" :key="ri">
            <td v-for="(cell, ci) in row" :key="ci"><span v-html="cell" /></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="block.caption" class="table-caption">{{ block.caption }}</div>
  </BlockShell>
</template>

<script>
import BlockShell from './BlockShell.vue'

export default {
  name: 'TableBlock',
  components: { BlockShell },
  props: { block: { type: Object, required: true } },
}
</script>

<style scoped>
/* 03 号规范第 13 节:真实 table 语义 + 横向滚动,窄屏不压字号 */
.table-block {
  margin: 34px auto;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--surface);
  overflow: hidden;
}
.table-scroll {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
th, td {
  text-align: left;
  padding: 13px 15px;
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}
th {
  font-size: 12px;
  color: var(--muted);
  background: var(--surface-2);
}
tbody tr:last-child td {
  border-bottom: 0;
}
.table-caption {
  padding: 10px 15px;
  font-size: 12px;
  color: var(--muted);
}
</style>
